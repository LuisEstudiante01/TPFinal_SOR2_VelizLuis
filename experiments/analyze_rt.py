#!/usr/bin/env python3
"""Descriptive summary of Exp 5 (exploratory real-time policies, SPEC D6/D7).

N = 5 per condition: only descriptive statistics, no hypothesis tests and no
P95 (with N = 5 it would be the maximum). Each Exp 5 condition is shown next to
its reference condition, so the effect of the policy can be read directly:

  exp5_comp1_fifo, exp5_comp1_rr  vs  exp3_comp1  (1 competitor, SCHED_OTHER, N = 30)
  exp5_cpus2_rr                   vs  exp5_cpus2  (same session) and exp2_cpus2 (N = 30)

The main analysis (analyze.py, experiments/analysis/) is not touched: adding
these comparisons there would change the Holm-adjusted p-values of the report.

Usage:
  python3 analyze_rt.py --results results_rt --base results --out analysis_rt
"""
import argparse
import glob
import json
import os

import pandas as pd

from analyze import describe, load

REFERENCES = {
    "exp5_comp1_fifo": "exp3_comp1",
    "exp5_comp1_rr": "exp3_comp1",
    "exp5_cpus2": "exp2_cpus2",
    "exp5_cpus2_rr": "exp5_cpus2",
}
ORDER = ["exp3_comp1", "exp5_comp1_fifo", "exp5_comp1_rr", "exp2_cpus2", "exp5_cpus2", "exp5_cpus2_rr"]
QUOTA = {"exp2_cpus2": 2.0, "exp5_cpus2": 2.0, "exp5_cpus2_rr": 2.0}


def policies(results):
    """{condition: (competitor policy, runner policy, meta)} from the .meta.json files."""
    out = {}
    for path in glob.glob(os.path.join(results, "exp*_*.meta.json")):
        with open(path) as f:
            meta = json.load(f)
        out[meta["condition"]] = (meta.get("competitor_policy", "SCHED_OTHER"),
                                  meta.get("runner_policy", "SCHED_OTHER"), meta)
    return out


def fmt(x, digits=2):
    return "%.*f" % (digits, x)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--results", default=os.path.join(here, "results_rt"), help="Exp 5 CSVs")
    ap.add_argument("--base", default=os.path.join(here, "results"), help="CSVs of the reference conditions")
    ap.add_argument("--out", default=os.path.join(here, "analysis_rt"))
    args = ap.parse_args()

    rt, _ = load(args.results)
    base, _ = load(args.base)
    df = pd.concat([rt, base[base.condition.isin(set(REFERENCES.values()))]], ignore_index=True)
    pol = policies(args.base)
    pol.update(policies(args.results))

    means = {}
    rows = []
    for cond in ORDER:
        for prompt in ("short", "long"):
            g = df[(df.condition == cond) & (df.prompt == prompt)]
            if g.empty:
                continue
            ttft, tps = describe(g.ttft_client_s), describe(g.tokens_per_s)
            means[(cond, prompt)] = (ttft["mean"], tps["mean"])
            comp, runner, _ = pol.get(cond, ("SCHED_OTHER", "SCHED_OTHER", {}))
            cpus = g.cpus_used.mean()
            rows.append([cond, comp, runner, prompt, str(ttft["n"]),
                         fmt(ttft["mean"], 3), fmt(ttft["median"], 3), fmt(ttft["max"], 3),
                         fmt(tps["mean"]), fmt(tps["min"]), fmt(tps["max"]), "%.1f%%" % tps["cv_pct"],
                         fmt(cpus), "%.0f" % g.throttles.mean(), fmt(g.throttled_ms.mean() / 1000.0, 1),
                         "%.0f%%" % (100 * cpus / QUOTA[cond]) if cond in QUOTA else "-"])

    lines = ["# Exp 5 exploratoria: políticas de tiempo real (generado por analyze_rt.py)", "",
             "Solo corridas `measured`. Exp 5 tiene N = 5 por prompt: estadística descriptiva, sin tests ni P95. "
             "Las condiciones de referencia (`exp3_comp1`, `exp2_cpus2`) vienen de la corrida principal (N = 30). "
             "`CPUs usadas` = `usage_usec` del cgroup / tiempo de pared (incluye a los competidores). "
             "`% de la cuota` = CPUs usadas / CPUs de `cpu.max`.", "",
             "| Condición | Competidor | Runner | Prompt | N | TTFT media (s) | TTFT mediana (s) | TTFT máx. (s) "
             "| tokens/s media | tokens/s mín. | tokens/s máx. | tokens/s CV | CPUs usadas | Throttles/corrida "
             "| Throttled/corrida (s) | % de la cuota |",
             "|" + "---|" * 16]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    lines += ["", "## Contra la referencia", "",
              "| Condición | Referencia | Prompt | TTFT | tokens/s |", "|---|---|---|---|---|"]
    for cond, ref in REFERENCES.items():
        for prompt in ("short", "long"):
            if (cond, prompt) in means and (ref, prompt) in means:
                (t1, s1), (t0, s0) = means[(cond, prompt)], means[(ref, prompt)]
                lines.append("| %s | %s | %s | ×%.2f | ×%.2f |" % (cond, ref, prompt, t1 / t0, s1 / s0))
    lines += ["", "## Entorno de tiempo real", ""]
    for cond in ORDER:
        meta = pol.get(cond, (None, None, {}))[2]
        if "sched_rt_runtime_us" in meta:
            lines.append("- `%s`: sched_rt_runtime_us = %s, sched_rt_period_us = %s, fair_server = %s/%s ns, "
                         "prioridad RT = %s, hilos de llama-server verificados = %s, kernel %s." % (
                             cond, meta.get("sched_rt_runtime_us"), meta.get("sched_rt_period_us"),
                             meta.get("fair_server_runtime_ns"), meta.get("fair_server_period_ns"),
                             meta.get("rt_priority"), meta.get("runner_policy_checked_threads", "-"),
                             meta.get("kernel")))
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "summary.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", path)


if __name__ == "__main__":
    main()
