#!/usr/bin/env python3
"""Diagramas del capítulo 6 (implementación). Uso: .venv/bin/python docs/informe/figuras/diagramas.py
Genera arquitectura.png y pipeline.png en el mismo directorio que este script."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.dirname(os.path.abspath(__file__))
plt.rcParams["font.family"] = "DejaVu Sans"


def box(ax, x, y, w, h, text, fc="#ffffff", ec="#333333", fs=10.5, ls="-", bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fc, ec=ec, lw=1.3, ls=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal")


def arrow(ax, p, q, text=None, color="#333333", dy=0.12):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="->", color=color, lw=1.4))
    if text:
        ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + dy, text, ha="center", fontsize=9.5, color=color)


def arquitectura():
    fig, ax = plt.subplots(figsize=(11, 8.6))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7.2)
    ax.axis("off")
    # hardware
    box(ax, 0.2, 0.2, 10.6, 0.9, "Hardware: AMD Ryzen 9 9900X, 12 núcleos / 24 CPUs lógicas (SMT)\n29 GiB RAM · governor performance",
        fc="#e8e8e8", bold=True)
    # kernel
    box(ax, 0.2, 1.2, 10.6, 1.0, "", fc="#dce9f7")
    ax.text(0.4, 1.95, "Kernel Linux 7.0.0-43 (EEVDF, base_slice_ns = 2,8 ms) · cgroups v2 (cgroup2fs)\ncpu.max · cpuset.cpus · cpu.stat · nice / taskset",
            fontsize=10, fontweight="bold", va="center")
    ax.text(0.4, 1.4, "Instrumentación: perf sched · pidstat · /proc/<pid>/task/<tid>/schedstat", fontsize=10, va="center")
    # servicios / user space
    box(ax, 0.2, 2.4, 10.6, 3.3, "", fc="#fdf6e3", ls="--")
    ax.text(0.4, 5.4, "Espacio de usuario (Ubuntu Server 26.04.1 LTS)", fontsize=9, fontweight="bold", va="center")
    # host ollama
    box(ax, 0.4, 3.9, 3.0, 1.25, "Ollama 0.40.16 (host)\nservicio systemd\npuerto 11434\nllama-server, 12 hilos", fc="#e2f0d9")
    ax.text(2.0, 3.6, "cgroup system.slice/ollama.service", fontsize=8.7, ha="center", style="italic")
    # docker container cgroup
    box(ax, 3.7, 2.6, 4.2, 2.5, "", fc="#fff2cc", ec="#b8860b")
    ax.text(5.8, 4.85, "Docker «ollama-docker» · 11435", fontsize=10, fontweight="bold", ha="center")
    ax.text(5.8, 4.55, "docker-<id>.scope · cpu.max · cpuset · cpu.stat", fontsize=8.7, ha="center", style="italic")
    box(ax, 3.9, 3.2, 1.9, 1.12, "Ollama 0.40.16\nllama-server\n12 hilos", fc="#e2f0d9", fs=9.6)
    box(ax, 5.9, 3.2, 1.9, 1.12, "stress-ng\n(competidores)\nnice 0/10/19", fc="#f8d7da", fs=9.6)
    ax.text(5.8, 2.8, "competidores en el MISMO cgroup que Ollama", fontsize=8.7, ha="center", color="#a02020")
    # scripts
    box(ax, 8.2, 2.6, 2.5, 2.5, "", fc="#ffffff")
    ax.text(9.45, 4.85, "Scripts (Python)", fontsize=10, fontweight="bold", ha="center")
    ax.text(9.45, 3.85, "run_matrix.py\nrun_protocol.py\nsched_capture.py\nwatch_competitors.sh\nanalyze.py", fontsize=9.5, ha="center", va="center")
    arrow(ax, (8.2, 3.9), (7.7, 3.9), None)
    ax.text(9.45, 4.55, "← API HTTP · docker update", fontsize=8.7, ha="center", style="italic")
    # ssh
    box(ax, 0.2, 6.0, 3.2, 0.9, "Operador: WSL2 → SSH + tmux\n(solo control, no mide)", fc="#ffffff", fs=9.6)
    arrow(ax, (9.45, 6.45), (9.45, 5.1), None)
    ax.text(6.4, 6.6, "ejecuta las corridas por SSH", fontsize=9.5, ha="center")
    ax.plot([3.4, 9.45], [6.45, 6.45], color="#333333", lw=1.4)
    ax.text(6.6, 6.9, "Banco de pruebas Linux nativo", fontsize=12, fontweight="bold", ha="center")
    arrow(ax, (0.6, 3.9), (0.6, 2.2), None)
    arrow(ax, (5.8, 2.6), (5.8, 2.2), None)
    fig.savefig(os.path.join(OUT, "arquitectura.png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def pipeline():
    fig, ax = plt.subplots(figsize=(11, 5.7))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    w, h, y = 1.99, 1.63, 2.53
    items = [
        ("run_matrix.py\n15 condiciones:\ndocker update\n(cpu.max, cpuset)\nstress-ng y\nverificación", "#fff2cc"),
        ("run_protocol.py\ncold · warmup ·\nN medidas\n(prompt corto/largo)", "#e2f0d9"),
        ("API de Ollama\nPOST /api/generate\n(stream)\nTTFT, tokens/s", "#dce9f7"),
        ("CSV + .meta.json\n(una fila por corrida;\ncpu.stat\nantes y después)", "#ffffff"),
        ("analyze.py\nmedia, CV, P95,\nIC95, Welch,\nMann-Whitney", "#fdf6e3"),
    ]
    xs = [0.15 + i * 2.15 for i in range(5)]
    for x, (t, c) in zip(xs, items):
        box(ax, x, y, w, h, t, fc=c, fs=9.6)
    for i in range(4):
        arrow(ax, (xs[i] + w, y + h / 2), (xs[i + 1], y + h / 2))
    box(ax, xs[4], 1.02, w, 0.9, "summary.md / .csv\nfiguras .png", fc="#ffffff", fs=9.6)
    arrow(ax, (xs[4] + w / 2, y), (xs[4] + w / 2, 1.92))
    box(ax, xs[0], 1.07, w, 0.8, "cgroup del\ncontenedor\ncpu.max · cpu.stat", fc="#f2f2f2", fs=7.5)
    arrow(ax, (xs[0] + w / 2, 1.87), (xs[0] + w / 2, y), None)
    arrow(ax, (xs[0] + w, 1.47), (xs[3] + w / 2 - 0.3, y), None, color="#777777")
    box(ax, 1.9, 0.1, 3.75, 0.85, "watch_competitors.sh\n(cada 15 s, solo lectura)", fc="#f8d7da", fs=8)
    box(ax, 6.15, 0.1, 4.35, 0.85, "sched_capture.py (aparte): perf sched, pidstat,\nschedstat en ventana de 20 s", fc="#f8d7da", fs=8)
    ax.text(5.5, 4.3, "Pipeline de una medición", fontsize=12, fontweight="bold", ha="center")
    fig.savefig(os.path.join(OUT, "pipeline.png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    arquitectura()
    pipeline()
    print("ok")
