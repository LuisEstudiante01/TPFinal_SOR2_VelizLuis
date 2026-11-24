#!/usr/bin/env python3
"""Single measurement protocol for every TP experiment (SPEC X1-X4, A3, A4).

Same model, prompts and inference parameters for every condition. Only the
condition under test changes (host vs Docker, CPU quota, competition, nice).
Standard library only, so it runs on a fresh Ubuntu Server.

Per series it does, in order:
  1. checks the CPU governor and unloads the model of the OTHER Ollama instance
  2. unloads the model of this instance and does one COLD run (model load time,
     reported apart from inference, X3)
  3. one WARMUP run per prompt (discarded from the statistics)
  4. N MEASURED runs per prompt, interleaved (short, long, short, long, ...)

Every prompt starts with a unique request id. Without it Ollama reuses the KV
cache of the previous identical prompt and the TTFT of the long prompt would be
close to zero after the first run.

Output: one CSV row per run plus a .meta.json with the environment.
"""
import argparse
import csv
import datetime
import glob
import http.client
import json
import os
import platform
import subprocess
import sys
import time

MODEL = "llama3.2:3b"
OPTIONS = {"temperature": 0, "seed": 1, "num_predict": 128, "num_ctx": 4096}

SHORT = "Explain what a CPU scheduler does in an operating system, and why fairness matters."

LONG = (
    "Read the following passage about process scheduling and then follow the instruction at the end.\n\n"
    "A CPU scheduler is the part of an operating system kernel that decides which runnable task gets "
    "to use a processor core and for how long. Because there are usually many more runnable tasks than "
    "cores, the scheduler must divide processor time among them while keeping the system responsive. "
    "Early schedulers used simple policies such as first come first served or round robin with a fixed "
    "time slice. Modern general purpose kernels aim for something harder: they try to be fair, to keep "
    "latency low for interactive work, to use every core efficiently and to waste as little energy as "
    "possible, all at the same time. These goals often conflict, so every design is a compromise.\n\n"
    "For many years the Linux kernel used the Completely Fair Scheduler, usually called CFS. CFS keeps "
    "the runnable tasks in a red black tree ordered by virtual runtime, which is the amount of processor "
    "time a task has received scaled by its weight. The task with the smallest virtual runtime is always "
    "picked next, so tasks that have received less time are favoured. The weight comes from the nice "
    "value: a lower nice value gives a larger weight and therefore a larger share of the processor. "
    "To reduce latency, CFS also relied on a set of heuristics and tunable parameters, such as the "
    "minimum granularity and the wakeup preemption rules, which made its behaviour hard to reason about.\n\n"
    "Starting with kernel 6.6 the fair class uses EEVDF, which stands for Earliest Eligible Virtual "
    "Deadline First. Each task has a lag that measures how much service it is owed compared with an ideal "
    "fluid system. A task is eligible when its lag is not negative, and among the eligible tasks the "
    "scheduler picks the one with the earliest virtual deadline. Tasks that ask for shorter time slices "
    "receive earlier deadlines and so are served sooner, which gives latency sensitive work a principled "
    "way to get low delay without extra heuristics.\n\n"
    "Control groups add another layer. With cgroups version two, the cpu controller can limit a group of "
    "processes with cpu.max, which sets a quota of runtime allowed in every period. When the group uses "
    "up its quota before the period ends, its tasks are throttled until the next period starts, and the "
    "counters nr_throttled and throttled_usec in cpu.stat record how often and for how long that happened.\n\n"
    "Instruction: summarize the passage above in exactly three short bullet points."
)

PROMPTS = {"short": SHORT, "long": LONG}


def http_json(port, method, path, body=None, timeout=600):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    conn.request(method, path, json.dumps(body) if body is not None else None,
                 {"Content-Type": "application/json"})
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    if resp.status != 200:
        raise RuntimeError("HTTP %d from %s %s: %s" % (resp.status, method, path, raw[:200]))
    return json.loads(raw or b"{}")


def unload(port, timeout=15):
    """Unload the model and wait until /api/ps confirms it (X3: the cold run needs a real load)."""
    http_json(port, "POST", "/api/generate", {"model": MODEL, "keep_alive": 0, "stream": False})
    deadline = time.time() + timeout
    while loaded_models(port):
        if time.time() > deadline:
            raise RuntimeError("model still loaded on port %d after unload" % port)
        time.sleep(0.5)


def loaded_models(port):
    try:
        return [m["name"] for m in http_json(port, "GET", "/api/ps", timeout=5).get("models", [])]
    except OSError:
        return []


def generate(port, prompt):
    """One streamed generation. Returns the final stats plus client-side timings."""
    body = {"model": MODEL, "prompt": prompt, "stream": True, "keep_alive": "10m", "options": OPTIONS}
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=900)
    t0 = time.perf_counter()
    conn.request("POST", "/api/generate", json.dumps(body), {"Content-Type": "application/json"})
    resp = conn.getresponse()
    if resp.status != 200:
        raw = resp.read()
        conn.close()
        raise RuntimeError("HTTP %d from /api/generate: %s" % (resp.status, raw[:200]))
    ttft, final = None, None
    while True:
        line = resp.readline()
        if not line:
            break
        if not line.strip():
            continue
        chunk = json.loads(line)
        if ttft is None and chunk.get("response"):
            ttft = time.perf_counter() - t0
        if chunk.get("done"):
            final = chunk
    wall = time.perf_counter() - t0
    conn.close()
    if final is None:
        raise RuntimeError("stream ended without a final chunk")
    return final, ttft, wall


def read_cpu_stat(cgroup):
    stat = {"nr_throttled": "", "throttled_usec": "", "usage_usec": ""}
    if not cgroup:
        return stat
    try:
        with open(os.path.join(cgroup, "cpu.stat")) as f:
            for line in f:
                key, _, val = line.partition(" ")
                if key in stat:
                    stat[key] = int(val)
    except OSError:
        pass
    return stat


def read_cgroup_file(cgroup, name):
    """Content of a cgroup interface file, or None (e.g. cpuset.cpus of a service without cpuset)."""
    try:
        with open(os.path.join(cgroup, name)) as f:
            return f.read().strip() or None
    except OSError:
        return None


def detect_cgroup(port, container):
    if port != 11434:  # 11434 is the host service; any other port is the container
        out = subprocess.run(["sudo", "-n", "docker", "inspect", "-f", "{{.Id}}", container],
                             capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            path = "/sys/fs/cgroup/system.slice/docker-%s.scope" % out.stdout.strip()
            return path if os.path.isdir(path) else ""
        return ""
    path = "/sys/fs/cgroup/system.slice/ollama.service"
    return path if os.path.isdir(path) else ""


def runner_threads():
    """Thread count of every running llama-server (Ollama runner) process, host and container."""
    out = subprocess.run(["pgrep", "-x", "llama-server"], capture_output=True, text=True).stdout.split()
    counts = {}
    for pid in out:
        try:
            with open("/proc/%s/status" % pid) as f:
                for line in f:
                    if line.startswith("Threads:"):
                        counts[pid] = int(line.split()[1])
        except OSError:
            pass
    return counts


POLICY_CODES = {0: "SCHED_OTHER", 1: "SCHED_FIFO", 2: "SCHED_RR", 3: "SCHED_BATCH", 5: "SCHED_IDLE", 6: "SCHED_DEADLINE"}
POLICY_NAME = {"other": "SCHED_OTHER", "fifo": "SCHED_FIFO", "rr": "SCHED_RR"}
CHRT_FLAG = {"fifo": "-f", "rr": "-r"}
RT_PRIO = 1


def task_policies(pid):
    """{tid: policy name} of every thread of pid, from /proc/<pid>/task/<tid>/stat (field 41)."""
    out = {}
    for tid in os.listdir("/proc/%s/task" % pid):
        try:
            with open("/proc/%s/task/%s/stat" % (pid, tid)) as f:
                fields = f.read().rsplit(")", 1)[1].split()
        except OSError:
            continue
        out[tid] = POLICY_CODES.get(int(fields[41 - 3]), fields[41 - 3])
    return out


def cgroup_runners(cgroup):
    """PIDs of the llama-server processes inside the measured cgroup."""
    procs = set((read_cgroup_file(cgroup, "cgroup.procs") or "").split())
    return [p for p in runner_threads() if p in procs]


def set_runner_policy(cgroup, policy):
    """Give every thread of the llama-server of this cgroup a real-time policy (chrt -a), then check it.

    New threads inherit the policy of the thread that creates them."""
    pids = cgroup_runners(cgroup)
    if len(pids) != 1:
        sys.exit("expected one llama-server in %s, found %s" % (cgroup, pids))
    res = subprocess.run(["sudo", "-n", "chrt", "-a", CHRT_FLAG[policy], "-p", str(RT_PRIO), pids[0]],
                         capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit("chrt failed: %s" % res.stderr.strip())
    return check_runner_policy(cgroup, policy)


def check_runner_policy(cgroup, policy):
    """Abort unless every llama-server thread of the cgroup has the policy. Returns (pid, threads)."""
    pids = cgroup_runners(cgroup)
    if len(pids) != 1:
        sys.exit("expected one llama-server in %s, found %s (the runner restarted?)" % (cgroup, pids))
    pols = task_policies(pids[0])
    wrong = {t: p for t, p in pols.items() if p != POLICY_NAME[policy]}
    if wrong:
        sys.exit("llama-server threads without %s: %s" % (POLICY_NAME[policy], wrong))
    return pids[0], len(pols)


def rt_settings():
    """Real-time throttling of the host: sched_rt_* sysctls and the fair server of CPU 0 (debugfs, needs sudo)."""
    out = {}
    for name in ("sched_rt_runtime_us", "sched_rt_period_us"):
        try:
            with open("/proc/sys/kernel/" + name) as f:
                out[name] = int(f.read())
        except (OSError, ValueError):
            out[name] = None
    for name in ("runtime", "period"):
        res = subprocess.run(["sudo", "-n", "cat", "/sys/kernel/debug/sched/fair_server/cpu0/" + name],
                             capture_output=True, text=True)
        out["fair_server_" + name + "_ns"] = int(res.stdout) if res.returncode == 0 and res.stdout.strip().isdigit() else None
    return out


def governors():
    found = set()
    for p in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor"):
        with open(p) as f:
            found.add(f.read().strip())
    return sorted(found)


COLUMNS = ["condition", "run_type", "prompt", "rep", "timestamp", "ttft_client_s",
           "prompt_eval_count", "prompt_eval_s", "eval_count", "eval_s", "tokens_per_s",
           "load_s", "total_s", "wall_s", "nr_throttled_before", "nr_throttled_after",
           "throttled_usec_before", "throttled_usec_after", "cpu_usec_delta", "attempt"]
RETRY_NONCE_OFFSET = 5000  # a retry never reuses the prompt of the failed attempt (prompt cache)


def run_once(args, cgroup, writer, run_type, prompt_name, rep, nonce):
    for attempt in (1, 2):
        used = nonce if attempt == 1 else nonce + RETRY_NONCE_OFFSET
        prompt = "[request %04d] %s" % (used, PROMPTS[prompt_name])
        before = read_cpu_stat(cgroup)
        try:
            final, ttft, wall = generate(args.port, prompt)
            break
        except (OSError, RuntimeError, ValueError) as exc:
            if attempt == 2:
                raise
            print("request failed (%s), retrying once with a new request id" % exc, flush=True)
            time.sleep(5)
    after = read_cpu_stat(cgroup)
    eval_s = final.get("eval_duration", 0) / 1e9
    delta = (after["usage_usec"] - before["usage_usec"]) if before["usage_usec"] != "" and after["usage_usec"] != "" else ""
    row = {
        "condition": args.condition, "run_type": run_type, "prompt": prompt_name, "rep": rep,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "ttft_client_s": "%.4f" % ttft if ttft is not None else "",
        "prompt_eval_count": final.get("prompt_eval_count", ""),
        "prompt_eval_s": "%.4f" % (final.get("prompt_eval_duration", 0) / 1e9),
        "eval_count": final.get("eval_count", ""), "eval_s": "%.4f" % eval_s,
        "tokens_per_s": "%.4f" % (final.get("eval_count", 0) / eval_s) if eval_s else "",
        "load_s": "%.4f" % (final.get("load_duration", 0) / 1e9),
        "total_s": "%.4f" % (final.get("total_duration", 0) / 1e9), "wall_s": "%.4f" % wall,
        "nr_throttled_before": before["nr_throttled"], "nr_throttled_after": after["nr_throttled"],
        "throttled_usec_before": before["throttled_usec"], "throttled_usec_after": after["throttled_usec"],
        "cpu_usec_delta": delta, "attempt": attempt,
    }
    writer.writerow(row)
    args.fh.flush()
    print("%-8s %-5s rep=%-3s ttft=%ss tok/s=%s throttled=%s->%s" % (
        run_type, prompt_name, rep, row["ttft_client_s"], row["tokens_per_s"],
        row["nr_throttled_before"], row["nr_throttled_after"]), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--condition", required=True, help="label of the condition, e.g. host, docker, quota50")
    ap.add_argument("--port", type=int, required=True, help="Ollama port to measure (host 11434, docker 11435)")
    ap.add_argument("--other-port", type=int, help="port of the other Ollama instance; its model is unloaded first")
    ap.add_argument("--container", default="ollama-docker", help="Docker container name (for cpu.stat)")
    ap.add_argument("--cgroup", help="cgroup directory to read cpu.stat from (autodetected by default)")
    ap.add_argument("--n", type=int, default=30, help="measured runs per prompt (default 30)")
    ap.add_argument("--out", default=os.path.expanduser("~/tp/results"), help="output directory")
    ap.add_argument("--competitors", type=int, default=0, help="stress-ng workers started by run_matrix.py (recorded in .meta.json)")
    ap.add_argument("--competitor-nice", type=int, default=0, help="nice of those workers (recorded in .meta.json)")
    ap.add_argument("--competitor-policy", choices=["other", "fifo", "rr"], default="other",
                    help="scheduling policy of those workers (recorded in .meta.json; Exp 5)")
    ap.add_argument("--runner-policy", choices=["other", "fifo", "rr"], default="other",
                    help="real-time policy given to the llama-server threads after the cold run (Exp 5)")
    ap.add_argument("--allow-governor", action="store_true", help="do not abort if the governor is not performance")
    args = ap.parse_args()

    gov = governors()
    if gov != ["performance"] and not args.allow_governor:
        sys.exit("CPU governor is %s, expected ['performance']. Run: sudo cpupower frequency-set -g performance" % gov)

    if args.other_port:
        if loaded_models(args.other_port):
            print("unloading model from the other instance (port %d)" % args.other_port)
            unload(args.other_port)
        if loaded_models(args.other_port):
            sys.exit("the other instance still has a model loaded; aborting")

    cgroup = args.cgroup if args.cgroup is not None else detect_cgroup(args.port, args.container)
    # 1: never record a series with silently empty cpu.stat columns
    if not cgroup or read_cpu_stat(cgroup)["nr_throttled"] == "":
        sys.exit("cannot read cpu.stat from cgroup %r" % cgroup)
    os.makedirs(args.out, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = os.path.join(args.out, "%s_%s" % (args.condition, stamp))

    tags = http_json(args.port, "GET", "/api/tags", timeout=10)
    digest = next((m["digest"] for m in tags.get("models", []) if m["name"] == MODEL), None)
    if digest is None:
        sys.exit("model %s is not installed on port %d" % (MODEL, args.port))
    meta = {
        "condition": args.condition, "port": args.port, "n_per_prompt": args.n, "model": MODEL,
        "model_digest": digest, "options": OPTIONS,
        "ollama_version": http_json(args.port, "GET", "/api/version", timeout=10).get("version"),
        "kernel": platform.release(), "governor": gov, "cgroup": cgroup or None,
        "prompts_chars": {k: len(v) for k, v in PROMPTS.items()},
        "cpu_max": read_cgroup_file(cgroup, "cpu.max"), "cpuset_cpus": read_cgroup_file(cgroup, "cpuset.cpus"),
        "competitors": args.competitors, "competitor_nice": args.competitor_nice,
        "started": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    real_time = args.competitor_policy != "other" or args.runner_policy != "other"
    if real_time:
        meta["competitor_policy"] = POLICY_NAME[args.competitor_policy]
        meta["runner_policy"] = POLICY_NAME[args.runner_policy]
        meta["rt_priority"] = RT_PRIO
        meta.update(rt_settings())

    unload(args.port)
    with open(base + ".csv", "w", newline="") as fh:
        args.fh = fh
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        run_once(args, cgroup, writer, "cold", "short", 0, 0)
        if args.runner_policy != "other":
            # the runner exists only after the cold run; warmup and measured runs use the new policy
            pid, threads = set_runner_policy(cgroup, args.runner_policy)
            print("llama-server %s: %d threads set to %s priority %d" % (
                pid, threads, POLICY_NAME[args.runner_policy], RT_PRIO), flush=True)
        for name in PROMPTS:
            run_once(args, cgroup, writer, "warmup", name, 0, 1)
        nonce = 2
        for rep in range(1, args.n + 1):
            for name in PROMPTS:
                run_once(args, cgroup, writer, "measured", name, rep, nonce)
                nonce += 1

    # total threads of the llama-server process (compute threads + HTTP server threads);
    # the compute threads are n_threads = 12 (one per physical core), see the Ollama log
    meta["runner_threads_total"] = runner_threads()
    if args.runner_policy != "other":
        # same runner, every thread (also those created later) still real-time
        pid, threads = check_runner_policy(cgroup, args.runner_policy)
        meta["runner_policy_checked_threads"] = threads
    meta["finished"] = datetime.datetime.now().isoformat(timespec="seconds")
    with open(base + ".meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print("wrote", base + ".csv")


if __name__ == "__main__":
    main()
