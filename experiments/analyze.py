#!/usr/bin/env python3
"""Statistical analysis of the experiment results (SPEC A4, X5, O1-O4).

Reads every <condition>_<stamp>.csv written by run_protocol.py (only the
"measured" rows), and writes into --out:
  summary.csv      one row per condition and prompt: N, mean, sd, CV, median,
                   P95, 95% CI of the mean for TTFT and tokens/s, throttling,
                   average CPUs used by the cgroup, cold load time
  comparisons.csv  each condition against its experiment baseline: relative
                   difference of the means, Welch t-test and Mann-Whitney U
  summary.md       the same tables in Markdown, grouped by experiment
  *.png            one figure per experiment
Needs pandas, scipy and matplotlib (installed on the test server).

Usage: python3 analyze.py --results ~/tp/results --out ~/tp/analysis
"""
import argparse
import glob
import json
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

# baseline of each experiment, and the comparisons the hypotheses need
BASELINES = {
    "exp1": "exp1_host",
    "exp2": "exp2_nolimit",
    "exp3": "exp3_comp0",
    "exp4": "exp4_nice0",
}
EXTRA_PAIRS = [("exp4_nice19", "exp4_nice19_cpus2"), ("exp3_comp0", "exp4_nice19")]
ORDER = ["exp1_host", "exp1_docker", "exp2_nolimit", "exp2_cpus8", "exp2_cpus4", "exp2_cpus2",
         "exp2_cpus1", "exp3_comp0", "exp3_comp1", "exp3_comp2", "exp3_comp3", "exp4_nice0",
         "exp4_nice10", "exp4_nice19", "exp4_nice19_cpus2"]
METRICS = {"ttft_client_s": "TTFT (s)", "tokens_per_s": "tokens/s"}
REQUIRED = {"run_type", "prompt", "ttft_client_s", "eval_count", "eval_s", "load_s", "wall_s",
            "nr_throttled_before", "nr_throttled_after", "throttled_usec_before", "throttled_usec_after",
            "cpu_usec_delta", "prompt_eval_count"}


def load(results):
    frames, cold = [], {}
    for path in sorted(glob.glob(os.path.join(results, "exp*_*.csv"))):
        cond = re.sub(r"_\d{8}-\d{6}$", "", os.path.basename(path)[:-4])
        try:
            df = pd.read_csv(path)
            missing = REQUIRED - set(df.columns)
            if missing:
                raise ValueError("missing columns %s" % sorted(missing))
        except (ValueError, pd.errors.ParserError) as exc:
            raise SystemExit("cannot read %s: %s" % (path, exc))
        meta_path = path[:-4] + ".meta.json"
        meta = {}
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
        c = df[df.run_type == "cold"]
        cold[cond] = float(c.load_s.iloc[0]) if len(c) else np.nan
        m = df[(df.run_type == "measured") & (df.eval_s > 0)].copy()
        if m.empty:
            raise SystemExit("no valid measured rows in %s" % path)
        m["condition"] = cond
        m["experiment"] = cond.split("_")[0]
        # tokens/s from the raw columns: the CSV column is rounded to 2 decimals,
        # which hides the variability of the slow conditions (~0.47 tokens/s)
        m["tokens_per_s"] = m.eval_count / m.eval_s
        m["throttles"] = m.nr_throttled_after - m.nr_throttled_before
        m["throttled_ms"] = (m.throttled_usec_after - m.throttled_usec_before) / 1000.0
        m["cpus_used"] = m.cpu_usec_delta / (m.wall_s * 1e6)
        m["n_declared"] = meta.get("n_per_prompt")
        frames.append(m)
    if not frames:
        raise SystemExit("no result CSVs in %s" % results)
    return pd.concat(frames, ignore_index=True), cold


def describe(x):
    x = np.asarray(x, dtype=float)
    n, mean, sd = len(x), x.mean(), x.std(ddof=1) if len(x) > 1 else 0.0
    half = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n) if n > 1 else np.nan
    return {"n": n, "mean": mean, "sd": sd, "cv_pct": 100 * sd / mean if mean else np.nan,
            "median": np.median(x), "p5": np.percentile(x, 5), "p95": np.percentile(x, 95),
            "min": x.min(), "max": x.max(),
            "ci95_low": mean - half, "ci95_high": mean + half}


def summarize(df, cold):
    rows = []
    for (cond, prompt), g in df.groupby(["condition", "prompt"]):
        row = {"condition": cond, "experiment": g.experiment.iloc[0], "prompt": prompt}
        for col in METRICS:
            for k, v in describe(g[col]).items():
                row["%s_%s" % (col, k)] = v
        row["throttles_per_run"] = g.throttles.mean()
        row["throttled_ms_per_run"] = g.throttled_ms.mean()
        row["cpus_used_mean"] = g.cpus_used.mean()
        row["cold_load_s"] = cold.get(cond)
        row["prompt_tokens"] = int(g.prompt_eval_count.iloc[0])
        row["eval_tokens_min"] = int(g.eval_count.min())
        rows.append(row)
    out = pd.DataFrame(rows)
    out["order"] = out.condition.map({c: i for i, c in enumerate(ORDER)})
    return out.sort_values(["order", "prompt"]).drop(columns="order")


def cliffs_delta(x, y):
    """Cliff's delta of y against x: P(y > x) - P(y < x), in [-1, 1] (effect size)."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    gt = (y[:, None] > x[None, :]).sum()
    lt = (y[:, None] < x[None, :]).sum()
    return (gt - lt) / (len(x) * len(y))


def holm(pvalues):
    """Holm-Bonferroni adjusted p-values (same order as the input)."""
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(p) - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def compare(df):
    pairs = [(base, c) for exp, base in BASELINES.items()
             for c in ORDER if c.startswith(exp + "_") and c != base] + EXTRA_PAIRS
    present = set(df.condition)
    rows = []
    for a, b in pairs:
        if a not in present or b not in present:
            continue
        for prompt in ("short", "long"):
            for col in METRICS:
                x = df[(df.condition == a) & (df.prompt == prompt)][col].astype(float)
                y = df[(df.condition == b) & (df.prompt == prompt)][col].astype(float)
                if len(x) < 2 or len(y) < 2 or x.mean() == 0:
                    continue
                rows.append({"baseline": a, "condition": b, "prompt": prompt, "metric": col,
                             "baseline_mean": x.mean(), "condition_mean": y.mean(),
                             "diff_pct": 100 * (y.mean() - x.mean()) / x.mean(),
                             "welch_p": stats.ttest_ind(x, y, equal_var=False).pvalue,
                             "mannwhitney_p": stats.mannwhitneyu(x, y).pvalue,
                             "cliffs_delta": cliffs_delta(x, y)})
    out = pd.DataFrame(rows)
    if not out.empty:
        # correction for multiple comparisons over the whole family of tests
        out["welch_p_holm"] = holm(out.welch_p)
        out["mannwhitney_p_holm"] = holm(out.mannwhitney_p)
    return out


def markdown(summary, comparisons):
    lines = ["# Resultados (generado por analyze.py)", "",
             "Solo corridas `measured`. CV = coeficiente de variación. IC95 = intervalo de confianza "
             "del 95% de la media (t de Student). P5 = el 5% más lento en tokens/s. "
             "`Throttled` = tiempo total throttleado del cgroup por corrida (`throttled_usec`, suma de todas las CPUs). "
             "`CPUs usadas` = consumo medio del cgroup (en Exp 3 y 4 incluye a los competidores). "
             "† = N < 30: P95 y P5 orientativos. "
             "Cliff's delta = tamaño del efecto (de -1 a 1; |d| > 0.47 es grande). "
             "p Holm = p ajustado por comparaciones múltiples (Holm-Bonferroni).", ""]
    for exp in ("exp1", "exp2", "exp3", "exp4"):
        s = summary[summary.experiment == exp]
        if s.empty:
            continue
        lines += ["## %s" % exp, "",
                  "| Condición | Prompt | N | TTFT media (s) | TTFT mediana (s) | TTFT P95 (s) | TTFT CV | "
                  "tokens/s media | tokens/s IC95 | tokens/s mediana | tokens/s P5 | tokens/s P95 | tokens/s mín. | "
                  "tokens/s CV | Throttles/corrida | Throttled/corrida (s) | CPUs usadas | Carga en frío (s) |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in s.iterrows():
            mark = "†" if r.ttft_client_s_n < 30 else ""
            lines.append("| %s | %s | %d%s | %.3f | %.3f | %.3f | %.1f%% | %.2f | %.2f a %.2f | %.2f | %.2f | %.2f | "
                         "%.2f | %.1f%% | %.0f | %.1f | %.2f | %.2f |" % (
                r.condition, r.prompt, r.ttft_client_s_n, mark, r.ttft_client_s_mean, r.ttft_client_s_median,
                r.ttft_client_s_p95, r.ttft_client_s_cv_pct, r.tokens_per_s_mean, r.tokens_per_s_ci95_low,
                r.tokens_per_s_ci95_high, r.tokens_per_s_median, r.tokens_per_s_p5, r.tokens_per_s_p95,
                r.tokens_per_s_min, r.tokens_per_s_cv_pct, r.throttles_per_run, r.throttled_ms_per_run / 1000.0,
                r.cpus_used_mean, r.cold_load_s))
        c = comparisons[comparisons.condition.str.startswith(exp + "_")] if not comparisons.empty else comparisons
        if not c.empty:
            lines += ["", "| Base | Condición | Prompt | Métrica | Diferencia | Cliff's delta | p (Welch) | p Holm (Welch) | "
                      "p (Mann-Whitney) | p Holm (Mann-Whitney) |",
                      "|---|---|---|---|---|---|---|---|---|---|"]
            for _, r in c.iterrows():
                lines.append("| %s | %s | %s | %s | %+.1f%% | %+.2f | %.2g | %.2g | %.2g | %.2g |" % (
                    r.baseline, r.condition, r.prompt, METRICS[r.metric], r.diff_pct, r.cliffs_delta,
                    r.welch_p, r.welch_p_holm, r.mannwhitney_p, r.mannwhitney_p_holm))
        lines.append("")
    return "\n".join(lines)


def plots(df, out):
    for exp in ("exp1", "exp2", "exp3", "exp4"):
        conds = [c for c in ORDER if c.startswith(exp + "_") and c in set(df.condition)]
        if not conds:
            continue
        fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))
        for row, (prompt, label) in enumerate((("short", "prompt corto"), ("long", "prompt largo"))):
            for ax, col in zip(axes[row], ("tokens_per_s", "ttft_client_s")):
                data = [df[(df.condition == c) & (df.prompt == prompt)][col] for c in conds]
                ax.boxplot(data, showfliers=True)
                ax.set_xticks(range(1, len(conds) + 1))
                ax.set_xticklabels([c.split("_", 1)[1] for c in conds], rotation=30)
                ax.set_title("%s, %s: %s" % (exp, label, METRICS[col]))
                if exp in ("exp2", "exp3", "exp4"):
                    ax.set_yscale("log")
        fig.tight_layout()
        fig.savefig(os.path.join(out, "%s.png" % exp), dpi=150)
        plt.close(fig)
    q = [c for c in ORDER if c.startswith("exp2_cpus") and c in set(df.condition)]
    if q:
        quota = [int(c.replace("exp2_cpus", "")) for c in q]
        g = df[df.condition.isin(q) & (df.prompt == "long")]
        tps = [g[g.condition == c].tokens_per_s.mean() for c in q]
        thr = [g[g.condition == c].throttles.mean() for c in q]
        fig, ax1 = plt.subplots(figsize=(6, 4))
        l1 = ax1.plot(quota, tps, "o-", label="tokens/s (eje izquierdo)")
        ax1.set_xlabel("cuota (CPUs, cpu.max)")
        ax1.set_ylabel("tokens/s")
        ax2 = ax1.twinx()
        l2 = ax2.plot(quota, thr, "s--", color="tab:red", label="throttles por corrida (eje derecho)")
        ax2.set_ylabel("throttles por corrida")
        ax1.legend(l1 + l2, [line.get_label() for line in l1 + l2], loc="upper center")
        ax1.set_title("Exp 2: rendimiento y throttling según la cuota (prompt largo)")
        fig.tight_layout()
        fig.savefig(os.path.join(out, "exp2_quota_throttling.png"), dpi=150)
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default=os.path.expanduser("~/tp/results"))
    ap.add_argument("--out", default=os.path.expanduser("~/tp/analysis"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    df, cold = load(args.results)
    summary = summarize(df, cold)
    comparisons = compare(df)
    summary.to_csv(os.path.join(args.out, "summary.csv"), index=False)
    comparisons.to_csv(os.path.join(args.out, "comparisons.csv"), index=False)
    with open(os.path.join(args.out, "summary.md"), "w") as f:
        f.write(markdown(summary, comparisons))
    plots(df, args.out)
    print("conditions: %d, measured runs: %d, written to %s" % (df.condition.nunique(), len(df), args.out))


if __name__ == "__main__":
    main()
