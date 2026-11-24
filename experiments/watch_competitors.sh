#!/bin/sh
# Read-only monitor for a run_matrix.py run: every 15 s, the current condition
# and the state of the competitors in the Ollama container cgroup.
# Output: CSV on stdout (time,condition,workers,nice,cpu_max,cpuset).
LOG=${1:-$HOME/tp/night.log}
SESSION=${2:-night}
CG=$(ls -d /sys/fs/cgroup/system.slice/docker-*.scope 2>/dev/null)
if [ "$(printf '%s\n' "$CG" | grep -c .)" -ne 1 ]; then
  echo "expected exactly one docker scope cgroup, found: $CG" >&2
  exit 1
fi
echo "time,condition,stress_workers_in_cg,nice_values,cpu_max,cpuset"
while tmux has-session -t "$SESSION" 2>/dev/null; do
  COND=$(grep "^===" "$LOG" 2>/dev/null | tail -1 | awk '{print $3}')
  [ -n "$COND" ] || COND="-"
  W=0; NI=""
  for p in $(pgrep -x stress-ng-cpu); do
    if grep -qx "$p" "$CG/cgroup.procs"; then W=$((W+1)); NI="$NI $(ps -o ni= -p "$p" | tr -d ' ')"; fi
  done
  NI=$(echo $NI | tr ' ' '\n' | sort -u | tr '\n' ' ' | sed 's/ $//')
  echo "$(date +%H:%M:%S),$COND,$W,\"$NI\",\"$(cat "$CG/cpu.max")\",\"$(cat "$CG/cpuset.cpus")\""
  sleep 15
done
