#!/usr/bin/env python3
"""Publication figures for the report (chapters 4 and 8).

Standalone: it does NOT import or modify analyze.py / analyze_rt.py and it does
not write into experiments/analysis*/. It reads the raw per-request CSVs of the
"measured" runs (same filters and formulas as analyze.py: eval_s > 0,
tokens/s = eval_count / eval_s, throttles = nr_throttled delta,
CPUs used = cpu_usec_delta / wall_s) and writes PNG (300 dpi) + PDF into
docs/informe/figuras/resultados/.

Every number printed on a figure comes from a data file:
  Exp 1-4 medians   -> experiments/analysis/summary.csv (same values as summary.md)
  Exp 5 means       -> experiments/analysis_rt/summary.md (throttles, CPUs used, N)
  dots              -> raw CSVs in experiments/results/ and experiments/results_rt/

Figures
  exp1_host_docker.png        Figura 8.1
  exp2_cuota.png              Figura 8.2
  exp2_cuota_throttling.png   Figura 8.3
  exp3_competidores.png       Figura 8.4
  exp4_nice.png               Figura 8.5
  exp5_tiempo_real.png        Figura 4.1

Dependencies (isolated environment, system python has none of them):
  python3 -m venv /tmp/plotenv && /tmp/plotenv/bin/pip install matplotlib pandas numpy
Run:
  /tmp/plotenv/bin/python experiments/plot_figures.py
"""
import glob
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
RESULTS_RT = os.path.join(HERE, "results_rt")
SUMMARY = os.path.join(HERE, "analysis", "summary.csv")
SUMMARY_RT = os.path.join(HERE, "analysis_rt", "summary.md")
OUT = os.path.join(HERE, "..", "docs", "informe", "figuras", "resultados")

# Okabe-Ito (colorblind safe). Prompt identity is also encoded with the marker.
C_SHORT, C_LONG, C_GREY, C_RED = "#0072B2", "#D55E00", "#6B6B6B", "#CC3311"
PROMPTS = {"short": ("Prompt corto", C_SHORT, "o"), "long": ("Prompt largo", C_LONG, "^")}
W = 16 / 2.54  # text width of the A4 page with 2.5 cm margins (inches)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Carlito", "Calibri", "Liberation Sans", "DejaVu Sans"],
    "font.size": 9.5, "axes.titlesize": 10, "axes.labelsize": 9.5,
    "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 8.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.7, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "axes.grid": True, "axes.axisbelow": True, "grid.color": "#E3E3E3", "grid.linewidth": 0.5,
    "figure.dpi": 100, "savefig.dpi": 300, "pdf.fonttype": 42,
})


# ----------------------------------------------------------------- data ----
def load(results):
    frames = []
    for path in sorted(glob.glob(os.path.join(results, "exp*_*.csv"))):
        cond = re.sub(r"_\d{8}-\d{6}$", "", os.path.basename(path)[:-4])
        df = pd.read_csv(path)
        m = df[(df.run_type == "measured") & (df.eval_s > 0)].copy()
        m["condition"] = cond
        m["tokens_per_s"] = m.eval_count / m.eval_s
        m["throttles"] = m.nr_throttled_after - m.nr_throttled_before
        m["throttled_s"] = (m.throttled_usec_after - m.throttled_usec_before) / 1e6
        m["cpus_used"] = m.cpu_usec_delta / (m.wall_s * 1e6)
        frames.append(m)
    return pd.concat(frames, ignore_index=True)


def parse_rt_summary(path):
    """{(condition, prompt): dict} from the first table of analysis_rt/summary.md."""
    out, header = {}, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("|"):
                if header and out:
                    break
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells[0] == "Condición" and "Runner" in cells:
                header = cells
            elif header and not set(cells[0]) <= {"-"}:
                row = dict(zip(header, cells))
                out[(row["Condición"], row["Prompt"])] = row
    return out


DF = load(RESULTS)
DF_RT = load(RESULTS_RT)
SUM = pd.read_csv(SUMMARY).set_index(["condition", "prompt"])
RT = parse_rt_summary(SUMMARY_RT)


def vals(df, cond, prompt, col):
    return df[(df.condition == cond) & (df.prompt == prompt)][col].to_numpy()


def med(cond, prompt, col):
    return SUM.loc[(cond, prompt), col + "_median"]


def n_of(cond):
    return int(SUM.loc[(cond, "short"), "tokens_per_s_n"])


def fmt(x, nd=2, comma=True):
    s = "%.*f" % (nd, x)
    return s.replace(".", ",") if comma else s


# ------------------------------------------------------------- drawing -----
def strip(ax, x, y, color, marker, width=0.16, seed=0, size=11, alpha=0.55, stat="median"):
    """Individual observations with deterministic jitter, plus median and IQR
    (stat="median") or only the mean (stat="mean", used for the N = 5 conditions)."""
    y = np.asarray(y, dtype=float)
    jit = np.random.default_rng(seed).uniform(-width, width, len(y))
    ax.scatter(x + jit, y, s=size, color=color, marker=marker, alpha=alpha,
               linewidths=0, zorder=3, rasterized=False)
    if stat == "median":
        q1, q3 = np.percentile(y, [25, 75])
        ax.plot([x, x], [q1, q3], color="black", lw=1.6, solid_capstyle="butt", zorder=4)
        ax.plot([x - width * 1.5, x + width * 1.5], [np.median(y)] * 2, color="black", lw=1.2, zorder=5)
    else:
        ax.plot([x - width * 1.5, x + width * 1.5], [y.mean()] * 2, color="black", lw=1.2, ls=(0, (2, 1)), zorder=5)


def plain_log(ax, ticks, axis="y"):
    fmt_fn = FuncFormatter(lambda v, _: ("%g" % v).replace(".", ","))
    if axis == "y":
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(FixedLocator(ticks))
        ax.yaxis.set_major_formatter(fmt_fn)
        ax.yaxis.set_minor_locator(NullLocator())
    else:
        ax.set_xscale("log")
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.xaxis.set_major_formatter(fmt_fn)
        ax.xaxis.set_minor_locator(NullLocator())


def prompt_legend(fig, extra=(), ncol=None, median=True):
    h = [Line2D([], [], marker=m, color=c, ls="", ms=5.5, label=l) for l, c, m in PROMPTS.values()]
    if median:
        h += [Line2D([], [], color="black", lw=1.6, label="Mediana y rango intercuartílico (RIC)")]
    h += list(extra)
    fig.legend(handles=h, loc="outside upper center", ncol=ncol or len(h), frameon=False,
               handletextpad=0.3, columnspacing=1.2)


def categorical(ax, labels, ylabel, title=None):
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.set_ylabel(ylabel)
    ax.grid(axis="x", visible=False)
    if title:
        ax.set_title(title, loc="left", fontweight="bold")


def label(ax, x, y_anchor, text, color, up):
    ax.annotate(text, (x, y_anchor), xytext=(0, 3 if up else -3), textcoords="offset points",
                ha="center", va="bottom" if up else "top", fontsize=7.5, color=color, fontweight="bold",
                bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none", alpha=0.75), zorder=6)


def draw_conditions(ax, conds, col, offset=0.22, nd=2, comma=True):
    """Both prompts for every condition, annotated with the median (summary.csv).
    The label of the larger median sits above the 90th percentile of its points, the other below the 10th."""
    top = max(vals(DF, c, p, col).max() for c in conds for p in PROMPTS)
    for i, cond in enumerate(conds):
        meds, data = {}, {}
        for k, p in enumerate(PROMPTS):
            data[p] = vals(DF, cond, p, col)
            strip(ax, i + (-offset if p == "short" else offset), data[p], PROMPTS[p][1], PROMPTS[p][2],
                  width=offset * 0.6, seed=i * 7 + k)
            meds[p] = med(cond, p, col)
        hi = max(meds, key=meds.get)
        for p in PROMPTS:
            # A label under points that sit near zero would cross the x axis: put it above.
            up = p == hi or (col == "tokens_per_s" and ax.get_yscale() == "linear"
                             and np.percentile(data[p], 10) < 0.1 * top)
            label(ax, i + (-offset if p == "short" else offset), np.percentile(data[p], 90 if up else 10),
                  fmt(meds[p], nd, comma), PROMPTS[p][1], up)


def check_visible(ax, conds, col):
    lo, hi = ax.get_ylim()
    for cond in conds:
        for p in PROMPTS:
            v = vals(DF, cond, p, col)
            assert v.min() >= lo and v.max() <= hi, (cond, p, col, v.min(), v.max(), lo, hi)


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, "%s.%s" % (name, ext)))
    plt.close(fig)
    print("wrote", name)


# --------------------------------------------------------------- figures ---
def fig_exp1():
    conds = ["exp1_host", "exp1_docker"]
    labels = [f"{environment} · {prompt}\nN = {n_of(cond)}"
              for prompt in ("corto", "largo")
              for environment, cond in zip(("Host", "Docker"), conds)]
    fig, axes = plt.subplots(2, 1, figsize=(W, 16.2 / 2.54), layout="constrained")
    panels = [
        ("tokens_per_s", "Tokens/s", 2, "a) Velocidad de generación: más alto es mejor"),
        ("ttft_client_s", "TTFT (s, escala log)", 3, "b) Espera hasta el primer token: más bajo es mejor"),
    ]
    for ax, (col, ylab, nd, title) in zip(axes, panels):
        for c, p in enumerate(PROMPTS):
            for i, cond in enumerate(conds):
                x = c * len(conds) + i
                data = vals(DF, cond, p, col)
                strip(ax, x, data, PROMPTS[p][1], PROMPTS[p][2], width=0.2, seed=i + c)
                ax.annotate("Mediana " + fmt(med(cond, p, col), nd),
                            (x, np.percentile(data, 90)), xytext=(0, 9),
                            textcoords="offset points", ha="center", va="bottom", fontsize=9.5)
        categorical(ax, labels, ylab, title)
        ax.axvline(1.5, color="#DADFE5", lw=1, zorder=1)
        if col == "ttft_client_s":
            plain_log(ax, [0.05, 0.1, 0.2, 0.5, 1])
            ax.set_ylim(0.045, 1.65)
        else:
            ax.set_ylim(0, 34)
        check_visible(ax, conds, col)
    fig.get_layout_engine().set(h_pad=0.09)
    prompt_legend(fig, ncol=3)
    save(fig, "exp1_host_docker")


QUOTA_CONDS = ["exp2_nolimit", "exp2_cpus8", "exp2_cpus4", "exp2_cpus2", "exp2_cpus1"]
QUOTA_LABELS = ["Sin\nlímite", "8 CPUs", "4 CPUs", "2 CPUs", "1 CPU"]
DASH = (0, (4, 3))


def baseline(axes, cond, cols):
    for p in PROMPTS:
        for a, col in zip(axes, cols):
            a.axhline(med(cond, p, col), color=PROMPTS[p][1], lw=0.7, ls=DASH, alpha=0.7, zorder=1)


def ns_text(fig, text):
    fig.supxlabel(text, fontsize=8.5, color=C_GREY)


def fig_exp2():
    fig, axes = plt.subplots(2, 1, figsize=(W, 16.3 / 2.54), layout="constrained")
    ax = axes[0]
    categorical(ax, QUOTA_LABELS, "Tokens/s", "a) Velocidad de generación: más alto es mejor")
    ax.set_ylim(0, 33)
    ax.set_yticks(range(0, 31, 5))
    draw_conditions(ax, QUOTA_CONDS, "tokens_per_s")
    check_visible(ax, QUOTA_CONDS, "tokens_per_s")
    ax = axes[1]
    categorical(ax, QUOTA_LABELS, "TTFT (s), escala logarítmica", "b) Espera hasta el primer token: más bajo es mejor")
    plain_log(ax, [0.1, 0.3, 1, 3, 10, 30])
    ax.set_ylim(0.045, 40)
    draw_conditions(ax, QUOTA_CONDS, "ttft_client_s")
    check_visible(ax, QUOTA_CONDS, "ttft_client_s")
    baseline(axes, "exp2_nolimit", ["tokens_per_s", "ttft_client_s"])
    fig.get_layout_engine().set(h_pad=0.09)
    prompt_legend(fig, [Line2D([], [], color=C_GREY, lw=0.8, ls=DASH, label="Mediana sin límite")], ncol=2)
    ns_text(fig, "N = 30 repeticiones por condición y prompt. Cuota en cpu.max.")
    save(fig, "exp2_cuota")


def fig_exp2_throttling():
    conds = QUOTA_CONDS[1:][::-1]  # 1, 2, 4, 8 CPUs
    quota = [1, 2, 4, 8]
    fig, axes = plt.subplots(2, 1, figsize=(W, 16.2 / 2.54), layout="constrained", sharex=True)
    fig.get_layout_engine().set(h_pad=0.10, hspace=0.07)
    ax = axes[0]
    ax.plot([0, 9], [0, 9], color=C_GREY, lw=0.9, ls=DASH, zorder=1)
    ax.text(6.0, 4.6, "consumo = cuota", color=C_GREY, fontsize=8.5, ha="left", va="center", rotation=0)
    for p, (lab, color, marker) in PROMPTS.items():
        for q, cond in zip(quota, conds):
            v = vals(DF, cond, p, "cpus_used")
            ax.scatter(q + np.random.default_rng(q).uniform(-0.12, 0.12, len(v)), v, s=7, color=color,
                       marker=marker, alpha=0.5, linewidths=0, zorder=3)
        ax.plot(quota, [SUM.loc[(c, p), "cpus_used_mean"] for c in conds], color=color, lw=1.0, marker=marker,
                ms=5.3, mfc="none", zorder=4)
    ax.set_ylabel("CPUs usadas por el cgroup")
    ax.set_title("a) Consumo de CPU del contenedor frente a su cuota", loc="left", fontweight="bold")
    ax.set_ylim(0, 9.5)
    ax = axes[1]
    for p, (lab, color, marker) in PROMPTS.items():
        ys = [SUM.loc[(c, p), "throttles_per_run"] for c in conds]
        for q, cond in zip(quota, conds):
            v = vals(DF, cond, p, "throttles")
            ax.scatter(q + np.random.default_rng(q + 1).uniform(-0.12, 0.12, len(v)), v, s=7, color=color,
                       marker=marker, alpha=0.5, linewidths=0, zorder=3)
        ax.plot(quota, ys, color=color, lw=1.0, marker=marker, ms=5.3, mfc="none", zorder=4)
        for q, y in zip(quota, ys):
            ax.annotate("%.0f" % y, (q, y), xytext=(10 if p == "long" else -10, 3 if p == "long" else -3),
                        textcoords="offset points", ha="left" if p == "long" else "right",
                        va="bottom" if p == "long" else "top", fontsize=8, color=color, fontweight="bold",
                        bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none", alpha=0.75), zorder=6)
    ax.set_ylabel("Throttles por corrida")
    ax.set_title("b) Veces que el kernel frenó al cgroup (nr_throttled de cpu.stat)", loc="left", fontweight="bold")
    ax.set_ylim(0, 1000)
    ax.set_xticks(quota)
    ax.set_xticklabels(["%d CPU%s" % (q, "" if q == 1 else "s") for q in quota])
    ax.set_xlim(0, 9)
    ax.set_xlabel("Cuota de CPU (cpu.max). N = 30 por cuota y prompt")
    for a in axes:
        a.grid(axis="x", visible=True)
    prompt_legend(fig, [Line2D([], [], color="black", lw=1.0, marker="o", mfc="none", ms=5.3, label="Media")], ncol=3, median=False)
    save(fig, "exp2_cuota_throttling")


def two_panel(conds, labels, name, ylims, ticks, ref=None, ref_label=None, legend_ncol=None, xlabel=None):
    fig, axes = plt.subplots(2, 1, figsize=(W, 16.2 / 2.54), layout="constrained")
    fig.get_layout_engine().set(h_pad=0.10, hspace=0.07)
    for ax, col, ylab, title, lim, tk in zip(axes, ["tokens_per_s", "ttft_client_s"],
                                             ["Tokens/s, escala logarítmica", "TTFT (s), escala logarítmica"],
                                             ["a) Velocidad de generación: más alto es mejor",
                                              "b) Espera hasta el primer token: más bajo es mejor"],
                                             ylims, ticks):
        draw_conditions(ax, conds, col)
        categorical(ax, labels, ylab, title)
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=8.5)
        plain_log(ax, tk)
        ax.set_ylim(*lim)
        check_visible(ax, conds, col)
    extra = []
    if ref:
        baseline(axes, ref, ["tokens_per_s", "ttft_client_s"])
        extra = [Line2D([], [], color=C_GREY, lw=0.8, ls=DASH, label=ref_label)]
    prompt_legend(fig, extra, ncol=legend_ncol)
    save(fig, name)


def fig_exp3():
    conds = ["exp3_comp0", "exp3_comp1", "exp3_comp2", "exp3_comp3"]
    labels = ["0", "1", "2", "3"]
    labels = ["%s\nN = %d" % (l, n_of(c)) for l, c in zip(labels, conds)]
    two_panel(conds, labels, "exp3_competidores", [(0.35, 55), (0.06, 14)],
              [[0.5, 1, 2, 5, 10, 20], [0.1, 0.3, 1, 3, 10]], "exp3_comp0", "Mediana sin competencia (0 competidores)",
              xlabel="Cantidad de competidores stress-ng (nice 0)", legend_ncol=2)


def fig_exp4():
    conds = ["exp4_nice0", "exp4_nice10", "exp4_nice19", "exp4_nice19_cpus2"]
    labels = ["nice 0", "nice 10", "nice 19", "nice 19\n+ 2 CPUs"]
    labels = ["%s\nN = %d" % (l, n_of(c)) for l, c in zip(labels, conds)]
    two_panel(conds, labels, "exp4_nice", [(0.07, 70), (0.06, 40)],
              [[0.1, 0.3, 1, 3, 10, 30], [0.1, 0.3, 1, 3, 10, 30]], "exp3_comp0",
              "Mediana sin competencia (Exp 3, N = 30)", legend_ncol=2,
              xlabel="Prioridad de los competidores y cuota del contenedor")


def fig_exp5():
    comma = True
    allf = pd.concat([DF, DF_RT], ignore_index=True)
    fig, axes = plt.subplots(3, 1, figsize=(W, 19.8 / 2.54), layout="constrained")
    fig.get_layout_engine().set(h_pad=0.13, hspace=0.07)
    off = 0.2

    def mean_of(cond, p, key):
        return float(RT[(cond, p)][key])

    def draw(ax, data, conds, col, key, nd, seed0, fmt_fn=None):
        for i, cond in enumerate(conds):
            meds = {p: mean_of(cond, p, key) for p in PROMPTS}
            hi = max(meds, key=meds.get)
            for k, p in enumerate(PROMPTS):
                x = i + (-off if p == "short" else off)
                v = vals(data, cond, p, col)
                strip(ax, x, v, PROMPTS[p][1], PROMPTS[p][2], width=0.13, seed=seed0 + i * 5 + k, stat="mean")
                up = p == hi
                txt = fmt_fn(cond, p) if fmt_fn else fmt(meds[p], nd, comma)
                label(ax, x, v.max() if up else v.min(), txt, PROMPTS[p][1], up)

    ca = ["exp3_comp1", "exp5_comp1_fifo", "exp5_comp1_rr"]
    la = ["OTHER\n(EEVDF)", "FIFO", "RR"]
    la = ["%s\nN = %d" % (l, len(vals(allf, c, "short", "tokens_per_s"))) for l, c in zip(la, ca)]
    ax = axes[0]
    draw(ax, allf, ca, "tokens_per_s", "tokens/s media", 2, 0)
    categorical(ax, la, "Tokens/s, escala logarítmica", "a) Velocidad de Ollama según la política del competidor")
    plain_log(ax, [0.3, 0.5, 1, 2, 5])
    ax.set_ylim(0.33, 6)
    ax.set_xlabel("Política SCHED_* del competidor", fontsize=8.5)

    cb = ["exp5_cpus2", "exp5_cpus2_rr"]
    lb = ["OTHER", "RR"]
    lb = ["%s\nN = %d" % (l, len(vals(DF_RT, c, "short", "tokens_per_s"))) for l, c in zip(lb, cb)]
    ax = axes[1]
    draw(ax, DF_RT, cb, "tokens_per_s", "tokens/s media", 2, 30)
    categorical(ax, lb, "Tokens/s", "b) Velocidad de Ollama con cuota de 2 CPUs")
    ax.set_ylim(0, 34)
    ax.set_yticks(range(0, 31, 5))
    ax.set_xlabel("Política SCHED_* de Ollama", fontsize=8.5)

    ax = axes[2]
    ax.axhline(2, color=C_RED, lw=1.0, ls=DASH, zorder=2)
    ax.text(1.0, 2.3, "cuota = 2 CPUs", color=C_RED, fontsize=8, ha="center", va="bottom")
    note_y = [6.5, 10.0]
    for i, cond in enumerate(cb):
        for k, p in enumerate(PROMPTS):
            x = i + (-off if p == "short" else off)
            strip(ax, x, vals(DF_RT, cond, p, "cpus_used"), PROMPTS[p][1], PROMPTS[p][2], width=0.13,
                  seed=60 + i * 5 + k, stat="mean")
        for p in PROMPTS:
            r = RT[(cond, p)]
            note_x = i + (-off if p == "short" else off)
            ax.text(note_x, note_y[i], "%s CPUs\n%s frenadas" % (fmt(float(r["CPUs usadas"]), 2, comma),
                                                              r["Throttles/corrida"]),
                    color=PROMPTS[p][1], fontsize=8, fontweight="bold", ha="center", va="top", linespacing=0.95)
    categorical(ax, lb, "CPUs usadas", "c) CPU utilizada por Ollama frente a la cuota")
    ax.set_ylim(0, 14.5)
    ax.set_xlabel("Política SCHED_* de Ollama", fontsize=8.5)
    prompt_legend(fig, [Line2D([], [], color="black", lw=1.2, ls=(0, (2, 1)), label="Media")], ncol=3, median=False)
    save(fig, "exp5_tiempo_real")


if __name__ == "__main__":
    fig_exp1()
    fig_exp2()
    fig_exp2_throttling()
    fig_exp3()
    fig_exp4()
    fig_exp5()
