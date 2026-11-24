#!/usr/bin/env python3
"""Run every experiment condition through run_protocol.py (Exp 1 to 4).

For each condition it configures the Ollama container (CPU quota and cpuset),
starts the stress-ng competitors INSIDE the container cgroup (so nice and the
number of competitors really compete with Ollama under cgroups v2), runs the
protocol, and stops the competitors before the next condition.

Usage:
  python3 run_matrix.py --n 1          # pilot: one measured run per prompt
  python3 run_matrix.py                # full run, N of each condition
  python3 run_matrix.py --only exp2
  python3 run_matrix.py --list         # print the conditions and exit
  python3 run_matrix.py --only exp5    # exploratory real-time policies (opt-in, SPEC D6/D7)

Exp 5 never runs without --only: its conditions start SCHED_FIFO/SCHED_RR tasks.
"""
import argparse
import glob
import os
import shlex
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONTAINER = "ollama-docker"
HOST_PORT, DOCKER_PORT = 11434, 11435
ALL_CPUS = "0-23"
HOST_CGROUP = "/sys/fs/cgroup/system.slice/ollama.service"
PINNED = "6-11,18-23"  # 6 physical cores = 12 logical CPUs (N and N+12 are SMT siblings), avoids core 0.
# Ollama runs 12 threads; with fewer CPUs than threads llama.cpp barriers stall (oversubscription).

# name, experiment, target, cpus quota (None = no limit), cpuset, competitors, competitor nice, N
# N per condition (decision 2026-11-19, option A): 30 by default; 10 where Ollama
# collapses under competition (~0.5 tokens/s), otherwise one condition takes 5+ hours.
CONDITIONS = [
    ("exp1_host",            "exp1", "host",   None, ALL_CPUS, 0,  0,  30),
    ("exp1_docker",          "exp1", "docker", None, ALL_CPUS, 0,  0,  30),
    ("exp2_nolimit",         "exp2", "docker", None, ALL_CPUS, 0,  0,  30),
    ("exp2_cpus8",           "exp2", "docker", 8,    ALL_CPUS, 0,  0,  30),
    ("exp2_cpus4",           "exp2", "docker", 4,    ALL_CPUS, 0,  0,  30),
    ("exp2_cpus2",           "exp2", "docker", 2,    ALL_CPUS, 0,  0,  30),
    ("exp2_cpus1",           "exp2", "docker", 1,    ALL_CPUS, 0,  0,  30),
    ("exp3_comp0",           "exp3", "docker", None, PINNED,   0,  0,  30),
    ("exp3_comp1",           "exp3", "docker", None, PINNED,   1,  0,  30),
    ("exp3_comp2",           "exp3", "docker", None, PINNED,   2,  0,  10),
    ("exp3_comp3",           "exp3", "docker", None, PINNED,   3,  0,  10),
    ("exp4_nice0",           "exp4", "docker", None, PINNED,   12, 0,  10),
    ("exp4_nice10",          "exp4", "docker", None, PINNED,   12, 10, 30),
    ("exp4_nice19",          "exp4", "docker", None, PINNED,   12, 19, 30),
    ("exp4_nice19_cpus2",    "exp4", "docker", 2,    PINNED,   12, 19, 30),
    # Exp 5 (exploratory, SPEC D6/D7): real-time policies, N = 5, no hypothesis tests.
    ("exp5_comp1_fifo",      "exp5", "docker", None, PINNED,   1,  0,  5),
    ("exp5_comp1_rr",        "exp5", "docker", None, PINNED,   1,  0,  5),
    ("exp5_cpus2",           "exp5", "docker", 2,    ALL_CPUS, 0,  0,  5),
    ("exp5_cpus2_rr",        "exp5", "docker", 2,    ALL_CPUS, 0,  0,  5),
]

# Scheduling policy of the competitors and of the Ollama runner (llama-server) threads.
# Conditions not listed here run with SCHED_OTHER (EEVDF) for both.
# name: (competitor policy, runner policy); policies: "other", "fifo", "rr" (priority 1)
POLICIES = {
    "exp5_comp1_fifo": ("fifo", "other"),
    "exp5_comp1_rr":   ("rr",   "other"),
    "exp5_cpus2_rr":   ("other", "rr"),
}
# Experiments that only run when named in --only (a full run never starts real-time tasks).
OPT_IN = {"exp5"}
RT_PRIO = 1
CHRT_FLAG = {"fifo": "-f", "rr": "-r"}
POLICY_NAME = {"other": "SCHED_OTHER", "fifo": "SCHED_FIFO", "rr": "SCHED_RR"}


def policies(name):
    return POLICIES.get(name, ("other", "other"))


def sh(cmd, check=True):
    res = subprocess.run(cmd, capture_output=True, text=True)
    if check and res.returncode != 0:
        sys.exit("command failed: %s\n%s" % (" ".join(cmd), res.stderr.strip()))
    return res.stdout.strip()


class CompetitorError(Exception):
    """The stress-ng competitors are not in the expected state."""


def read_text(path):
    with open(path) as f:
        return f.read().strip()


def cpu_temp():
    """Tctl of the AMD k10temp sensor in degrees C, or None."""
    for hw in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            if read_text(os.path.join(hw, "name")) == "k10temp":
                return int(read_text(os.path.join(hw, "temp1_input"))) / 1000.0
        except OSError:
            pass
    return None


def container_cgroup():
    cid = sh(["sudo", "-n", "docker", "inspect", "-f", "{{.Id}}", CONTAINER])
    return "/sys/fs/cgroup/system.slice/docker-%s.scope" % cid


def configure_container(quota, cpuset):
    # Limits use --cpus (writes cpu.max). To REMOVE a limit, "--cpus 0" does not
    # work (cpu.max keeps the old quota); "--cpu-quota -1" does. cpu.max is
    # checked below, so a wrong state aborts the run.
    d = ["sudo", "-n", "docker", "update"]
    sh(d + ["--cpu-quota", "-1", "--cpuset-cpus", cpuset, CONTAINER])
    if quota:
        sh(d + ["--cpus", str(quota), CONTAINER])
    cg = container_cgroup()
    cpu_max = read_text(os.path.join(cg, "cpu.max"))
    cpus = read_text(os.path.join(cg, "cpuset.cpus"))
    expected = "max 100000" if not quota else "%d 100000" % int(quota * 100000)
    if cpu_max != expected:
        sys.exit("cpu.max is %r, expected %r" % (cpu_max, expected))
    if cpus != cpuset:
        sys.exit("cpuset.cpus is %r, expected %r" % (cpus, cpuset))
    return cg, cpu_max, cpus


def competitor_pids(cg):
    """PIDs of the stress-ng processes (parent and workers) inside the container cgroup.

    Only processes in that cgroup are touched: they were put there by
    start_competitors, so an unrelated stress-ng elsewhere is never killed."""
    in_cg = set(read_text(os.path.join(cg, "cgroup.procs")).split())
    pids = sh(["pgrep", "-f", "^stress-ng"], check=False).split()
    return [p for p in pids if p in in_cg]


def count_workers(cg):
    workers = sh(["pgrep", "-x", "stress-ng-cpu"], check=False).split()
    in_cg = set(read_text(os.path.join(cg, "cgroup.procs")).split())
    return [p for p in workers if p in in_cg]


def stop_competitors(cg=None, proc=None):
    """Stop the competitors started in the container cgroup and reap their sudo parent."""
    cg = cg or container_cgroup()
    pids = competitor_pids(cg)
    if pids:
        subprocess.run(["sudo", "-n", "kill", "-TERM"] + pids, capture_output=True)
    for _ in range(50):
        if not competitor_pids(cg):
            break
        time.sleep(0.2)
    else:
        raise CompetitorError("stress-ng is still running in %s" % cg)
    if proc is not None:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def thread_policy(pid):
    """Scheduling policy of a task from /proc (field 41 of stat): SCHED_OTHER, SCHED_FIFO, ... or None."""
    try:
        stat = read_text("/proc/%s/stat" % pid)
    except OSError:
        return None
    fields = stat.rsplit(")", 1)[1].split()  # fields after comm, starting at field 3 (state)
    code = int(fields[41 - 3])
    return {0: "SCHED_OTHER", 1: "SCHED_FIFO", 2: "SCHED_RR", 3: "SCHED_BATCH",
            5: "SCHED_IDLE", 6: "SCHED_DEADLINE"}.get(code, str(code))


def start_competitors(cg, count, nice, cpuset, policy="other"):
    # The shell joins the container cgroup first; stress-ng and its workers inherit it.
    # With a real-time policy, chrt runs first: the workers inherit SCHED_FIFO/SCHED_RR.
    chrt = "chrt %s %d " % (CHRT_FLAG[policy], RT_PRIO) if policy != "other" else ""
    script = "echo $$ > %s && exec %snice -n %d taskset -c %s stress-ng --cpu %d --cpu-method matrixprod --quiet" % (
        shlex.quote(os.path.join(cg, "cgroup.procs")), chrt, nice, shlex.quote(cpuset), count)
    proc = subprocess.Popen(["sudo", "-n", "sh", "-c", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    workers = count_workers(cg)
    if len(workers) != count:
        stop_competitors(cg, proc)
        raise CompetitorError("%d stress-ng workers in the container cgroup, expected %d" % (len(workers), count))
    for pid in workers:
        ni = sh(["ps", "-o", "ni=", "-p", pid], check=False).strip()
        aff = sh(["taskset", "-cp", pid], check=False).rsplit(":", 1)[-1].strip()
        if policy != "other":
            # ps shows nice "-" for real-time tasks: check the policy instead
            pol = thread_policy(pid)
            if pol != POLICY_NAME[policy] or aff != cpuset:
                stop_competitors(cg, proc)
                raise CompetitorError("worker %s has policy=%s affinity=%s, expected policy=%s affinity=%s" % (
                    pid, pol, aff, POLICY_NAME[policy], cpuset))
            continue
        if ni != str(nice) or aff != cpuset:
            stop_competitors(cg, proc)
            raise CompetitorError("worker %s has nice=%s affinity=%s, expected nice=%d affinity=%s" % (
                pid, ni, aff, nice, cpuset))
    return proc


def rt_args(comp_policy, runner_policy):
    """Extra run_protocol.py arguments; empty for SCHED_OTHER, so Exp 1 to 4 run exactly as before."""
    if comp_policy == runner_policy == "other":
        return []
    return ["--competitor-policy", comp_policy, "--runner-policy", runner_policy]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, help="force N for every condition (pilot: --n 1); default: N of each condition")
    ap.add_argument("--only", help="run only one experiment (exp1..exp4) or a comma-separated list of condition names")
    ap.add_argument("--out", default=os.path.expanduser("~/tp/results"), help="output directory")
    ap.add_argument("--list", action="store_true", help="print the conditions and exit")
    args = ap.parse_args()

    sel = set((args.only or "").split(","))
    conds = [c for c in CONDITIONS if (not args.only and c[1] not in OPT_IN) or c[1] in sel or c[0] in sel]
    known = {c[0] for c in CONDITIONS} | {c[1] for c in CONDITIONS}
    if args.only and not sel <= known:
        sys.exit("unknown condition or experiment: %s" % ", ".join(sorted(sel - known)))
    if args.list:
        for c in conds:
            extra = ""
            if c[0] in POLICIES:
                extra = " competitor_policy=%s runner_policy=%s" % policies(c[0])
            print("%-20s target=%-6s cpus=%-4s cpuset=%-11s competitors=%-2d nice=%-2d N=%d%s" % (
                c[0], c[2], c[3] or "-", c[4], c[5], c[6], args.n if args.n is not None else c[7], extra))
        return

    stop_competitors()
    failed = []
    try:
        for i, (name, _exp, target, quota, cpuset, comp, nice, n) in enumerate(conds, 1):
            print("\n=== [%d/%d] %s === %s temp=%sC" % (i, len(conds), name, time.strftime("%H:%M:%S"), cpu_temp()), flush=True)
            cg, cpu_max, cpus = configure_container(quota, cpuset)
            print("container cpu.max=%s cpuset=%s" % (cpu_max, cpus), flush=True)
            proc = None
            comp_policy, runner_policy = policies(name)
            if comp:
                try:
                    proc = start_competitors(cg, comp, nice, cpuset, comp_policy)
                except CompetitorError as exc:
                    print("FAILED: %s (%s), continuing" % (name, exc), flush=True)
                    failed.append(name)
                    continue
                if comp_policy != "other":
                    print("started %d stress-ng workers, %s priority %d, in the container cgroup" % (
                        comp, POLICY_NAME[comp_policy], RT_PRIO), flush=True)
                else:
                    print("started %d stress-ng workers, nice %d, in the container cgroup" % (comp, nice), flush=True)
            port, other = (HOST_PORT, DOCKER_PORT) if target == "host" else (DOCKER_PORT, HOST_PORT)
            measured_cg = HOST_CGROUP if target == "host" else cg
            res = subprocess.run([sys.executable, os.path.join(HERE, "run_protocol.py"), "--condition", name,
                                  "--port", str(port), "--other-port", str(other),
                                  "--n", str(args.n if args.n is not None else n),
                                  "--cgroup", measured_cg, "--competitors", str(comp), "--competitor-nice", str(nice),
                                  "--out", args.out] + rt_args(comp_policy, runner_policy))
            # the competitors must still be alive when the condition ends (audit 2026-11-19)
            alive = len(count_workers(cg)) if comp else 0
            stop_competitors(cg, proc)
            print("end %s %s temp=%sC competitors_alive=%d/%d" % (
                name, time.strftime("%H:%M:%S"), cpu_temp(), alive, comp), flush=True)
            if res.returncode != 0 or alive != comp:
                # keep going: one failed condition must not waste the rest of the night
                print("FAILED: %s (exit %d, competitors alive %d/%d), continuing" % (
                    name, res.returncode, alive, comp), flush=True)
                failed.append(name)
    finally:
        try:
            stop_competitors()
        finally:
            # always remove the limits, even if the cleanup above failed
            configure_container(None, ALL_CPUS)
            print("\ncontainer restored to no limits", flush=True)
    if failed:
        sys.exit("failed conditions: %s" % ", ".join(failed))
    print("all %d conditions finished" % len(conds))


if __name__ == "__main__":
    main()
