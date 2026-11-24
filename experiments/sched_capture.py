#!/usr/bin/env python3
"""Scheduler metrics capture for O4 ("relate the results to cpu.stat and the
scheduler metrics"). Separate from the measurement run: perf adds overhead.

For each selected condition of run_matrix.py it configures the container and
the competitors exactly as the measurement run, keeps Ollama generating
back-to-back (long prompt, same OPTIONS as run_protocol.py) and, during a fixed
window, records:
  - /proc/<pid>/task/<tid>/schedstat of every llama-server thread: time on CPU
    and time waiting in the run queue (run delay), per thread
  - cpu.stat of the cgroup: throttles and throttled time in the window
  - perf sched record + latency: scheduling delay and switches per task
  - pidstat -u -w -t: CPU% and voluntary / involuntary context switches
Outputs (in --out): <condition>/{perf_latency.txt,pidstat.txt,schedstat.json}
and summary.csv. Raw perf.data files stay in --raw (large, not versioned).

Usage (on the test server, from ~/tp):
  python3 sched_capture.py --window 20 --out ~/tp/sched --raw ~/tp/sched_raw
  python3 sched_capture.py --only exp2_nolimit --window 5   # quick test
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import threading
import time

import run_matrix as rm
import run_protocol as rp

SELECTED = ["exp2_nolimit", "exp2_cpus4", "exp2_cpus1", "exp3_comp0", "exp3_comp1",
            "exp4_nice10", "exp4_nice19", "exp4_nice19_cpus2"]


def llama_pid():
    pids = subprocess.run(["pgrep", "-x", "llama-server"], capture_output=True, text=True).stdout.split()
    if len(pids) != 1:
        sys.exit("expected exactly one llama-server process, found %s" % pids)
    return pids[0]


def schedstat(pid):
    """{tid: (run_ns, wait_ns, timeslices)} for every thread of pid."""
    out = {}
    for tid in os.listdir("/proc/%s/task" % pid):
        try:
            with open("/proc/%s/task/%s/schedstat" % (pid, tid)) as f:
                run, wait, slices = (int(x) for x in f.read().split())
            out[tid] = (run, wait, slices)
        except OSError:
            pass
    return out


class Generator(threading.Thread):
    """Back-to-back generations on the container until stop is set."""

    def __init__(self):
        super().__init__(daemon=True)
        self.stop = threading.Event()
        self.done = 0
        self.error = None

    def run(self):
        nonce = 9000
        while not self.stop.is_set():
            try:
                rp.generate(rm.DOCKER_PORT, "[request %04d] %s" % (nonce, rp.LONG))
                self.done += 1
            except Exception as exc:  # noqa: BLE001 - reported in the summary
                self.error = str(exc)
                return
            nonce += 1


def perf_latency_totals(text, comm):
    """Sum the rows of `perf sched latency` whose task name starts with comm."""
    runtime = switches = 0.0
    delay_weighted = 0.0
    max_delay = 0.0
    for line in text.splitlines():
        cols = [c.strip() for c in line.split("|")]
        if len(cols) < 6 or not cols[0].startswith(comm):
            continue
        try:
            rt = float(cols[1].split()[0])
            sw = float(cols[2])
            avg = float(cols[3].replace("avg:", "").split()[0])
            mx = float(cols[4].replace("max:", "").split()[0])
        except (ValueError, IndexError):
            continue
        runtime += rt
        switches += sw
        delay_weighted += avg * sw
        max_delay = max(max_delay, mx)
    return {"runtime_ms": runtime, "switches": switches,
            "avg_delay_ms": delay_weighted / switches if switches else 0.0, "max_delay_ms": max_delay}


def pidstat_totals(text):
    """Average per-second totals over the window of the llama-server threads."""
    cpu = cs = ncs = 0.0
    samples = set()
    for line in text.splitlines():
        parts = line.split()
        # -h -u -w -t columns: Time UID TGID TID %usr %system %guest %wait %CPU CPU cswch/s nvcswch/s Command
        if len(parts) < 13 or ":" not in parts[0]:
            continue
        try:
            if parts[3] == "-":  # process line (TID "-"): CPU% of the whole process
                cpu += float(parts[8])
                samples.add(parts[0])
            elif parts[2] == "-":  # thread line (TGID "-"): context switches of one thread
                cs += float(parts[10])
                ncs += float(parts[11])
        except ValueError:
            continue
    n = len(samples) or 1
    return {"cpu_pct": cpu / n, "cswch_per_s": cs / n, "nvcswch_per_s": ncs / n}


def capture(cond, window, out_dir, raw_dir):
    name, _exp, _target, quota, cpuset, comp, nice, _n = cond
    print("\n=== %s === %s" % (name, time.strftime("%H:%M:%S")), flush=True)
    rm.stop_competitors()
    cg, cpu_max, cpus = rm.configure_container(quota, cpuset)
    if rp.loaded_models(rm.HOST_PORT):
        rp.unload(rm.HOST_PORT)
    rp.generate(rm.DOCKER_PORT, "[request 8999] warmup")  # load the model before competitors
    proc = rm.start_competitors(cg, comp, nice, cpuset) if comp else None
    pid = llama_pid()
    gen = Generator()
    gen.start()
    time.sleep(3)  # let the generation loop settle

    d = os.path.join(out_dir, name)
    os.makedirs(d, exist_ok=True)
    raw = os.path.join(raw_dir, "%s.perf.data" % name)
    perf = subprocess.Popen(["sudo", "-n", "perf", "sched", "record", "-a", "-o", raw, "--", "sleep", str(window)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pidstat = subprocess.Popen(["pidstat", "-h", "-u", "-w", "-t", "-p", pid, "1", str(window)],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    s0, c0, t0 = schedstat(pid), rp.read_cpu_stat(cg), time.perf_counter()
    time.sleep(window)
    s1, c1, t1 = schedstat(pid), rp.read_cpu_stat(cg), time.perf_counter()
    pid_text = pidstat.communicate()[0]
    perf.wait()
    gen.stop.set()
    gen.join(timeout=900)
    alive = len(rm.count_workers(cg)) if comp else 0
    rm.stop_competitors(cg, proc)

    lat = subprocess.run(["sudo", "-n", "perf", "sched", "latency", "-i", raw, "--sort", "max"],
                         capture_output=True, text=True).stdout
    subprocess.run(["sudo", "-n", "chown", "%d:%d" % (os.getuid(), os.getgid()), raw])
    with open(os.path.join(d, "perf_latency.txt"), "w") as f:
        f.write(lat)
    with open(os.path.join(d, "pidstat.txt"), "w") as f:
        f.write(pid_text)
    threads = {tid: [s1[tid][i] - s0[tid][i] for i in range(3)] for tid in s1 if tid in s0}
    with open(os.path.join(d, "schedstat.json"), "w") as f:
        json.dump({"pid": pid, "window_s": t1 - t0, "threads": threads}, f, indent=1)

    elapsed = t1 - t0
    busy = {t: v for t, v in threads.items() if v[0] > 0.05 * elapsed * 1e9}  # compute threads
    run_s = sum(v[0] for v in busy.values()) / 1e9
    wait_s = sum(v[1] for v in busy.values()) / 1e9
    row = {"condition": name, "cpu_max": cpu_max, "cpuset": cpus, "competitors": comp, "competitor_nice": nice,
           "competitors_alive_at_end": alive, "window_s": round(elapsed, 2), "generations_done": gen.done,
           "generator_error": gen.error or "",
           "busy_threads": len(busy),
           "ollama_run_cpus": round(run_s / elapsed, 3),
           "ollama_runqueue_wait_cpus": round(wait_s / elapsed, 3),
           "ollama_wait_share_pct": round(100 * wait_s / (run_s + wait_s), 2) if run_s + wait_s else 0,
           "throttles_per_s": round((c1["nr_throttled"] - c0["nr_throttled"]) / elapsed, 2),
           "throttled_ms_per_s": round((c1["throttled_usec"] - c0["throttled_usec"]) / 1000 / elapsed, 2),
           "cgroup_cpus_used": round((c1["usage_usec"] - c0["usage_usec"]) / 1e6 / elapsed, 3)}
    for prefix, comm in (("perf_ollama_", "llama-server"), ("perf_stress_", "stress-ng-cpu")):
        for k, v in perf_latency_totals(lat, comm).items():
            row[prefix + k] = round(v, 3)
    for k, v in pidstat_totals(pid_text).items():
        row["pidstat_" + k] = round(v, 1)
    print(json.dumps(row), flush=True)
    if comp and alive != comp:
        print("WARNING: %d of %d competitors alive at the end" % (alive, comp), flush=True)
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", type=int, default=20, help="capture window in seconds (default 20)")
    ap.add_argument("--only", help="comma-separated condition names (default: the 8 selected)")
    ap.add_argument("--out", default=os.path.expanduser("~/tp/sched"))
    ap.add_argument("--raw", default=os.path.expanduser("~/tp/sched_raw"))
    args = ap.parse_args()
    names = args.only.split(",") if args.only else SELECTED
    conds = [c for c in rm.CONDITIONS if c[0] in names]
    if len(conds) != len(names):
        sys.exit("unknown condition in %s" % names)
    if rp.governors() != ["performance"]:
        sys.exit("governor is not performance")
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.raw, exist_ok=True)
    rows = []
    try:
        for cond in conds:
            rows.append(capture(cond, args.window, args.out, args.raw))
    finally:
        rm.stop_competitors()
        rm.configure_container(None, rm.ALL_CPUS)
        print("container restored to no limits", flush=True)
    path = os.path.join(args.out, "summary.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", path)


if __name__ == "__main__":
    main()
