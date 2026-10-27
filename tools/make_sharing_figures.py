"""Figures for "Algorithms and Sustainability", sharing energy fairly (own work, CC BY 4.0).

Usage:  python3 tools/make_sharing_figures.py lectures/figures
Small constructed examples only (no data needed).

Writes:
  sharing-0.svg   five wallboxes behind a congested connection (30 kW): their demands (55.1 kW in total)
  sharing-1.svg   the same, split in proportion to the demands
  sharing-2.svg   the same, max-min fair (water-filling, the "uniform rule")
  sharing-net.svg two congested hours, a heat pump that needs both and two wallboxes: max-min fair, proportionally
                  fair, maximum total
and prints the numbers quoted on the slides (also the round-robin example and the exercise).
Needs: matplotlib, numpy. Font as in make_figures.py (LATO_DIR).
"""
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
FD = os.environ.get("LATO_DIR", "")
if FD and os.path.exists(os.path.join(FD, "LatoLatin-Regular.ttf")):
    for f in ["LatoLatin-Regular.ttf", "LatoLatin-Bold.ttf", "LatoLatin-Italic.ttf"]:
        font_manager.fontManager.addfont(os.path.join(FD, f))
    FAMILY = "LatoLatin"
else:
    FAMILY = "DejaVu Sans"
plt.rcParams.update({"font.family": FAMILY, "font.size": 15, "svg.fonttype": "path", "savefig.transparent": False,
                     "svg.hashsalt": "aus-2627-sharing", "mathtext.fontset": "custom",
                     "mathtext.it": f"{FAMILY}:italic", "mathtext.rm": FAMILY, "mathtext.bf": f"{FAMILY}:bold",
                     "mathtext.cal": f"{FAMILY}:italic", "mathtext.sf": FAMILY, "mathtext.tt": FAMILY})
if FAMILY != "LatoLatin":
    plt.rcParams["mathtext.fontset"] = "dejavusans"      # without LATO_DIR: default fonts (figures differ slightly)
INK, GREY, LIGHT = "#282a2e", "#8e908c", "#d9d9d6"
BLUE, ORANGE, RED, GREEN, PURPLE = "#0A97D9", "#E8700A", "#DD1367", "#3F7E44", "#6250d6"
WHITE, PALEBLUE = "#ffffff", "#e7f4fb"


def save(fig, name):
    path = os.path.join(out, name)
    fig.patch.set_facecolor("white")
    fig.savefig(path, bbox_inches="tight", pad_inches=0.06, metadata={"Date": None})
    plt.close(fig)
    num = re.compile(r"-?\d+\.\d+")
    short = lambda m: f"{float(m.group()):.2f}".rstrip("0").rstrip(".")
    with open(path, encoding="utf-8") as f:
        svg = f.read()
    svg = re.sub(r'(\sd=")([^"]*)(")', lambda m: m.group(1) + num.sub(short, m.group(2)) + m.group(3), svg)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)


def style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(GREY)
    ax.tick_params(colors=GREY, labelsize=14)


# ---------------------------------------------------------------- 1) one congested connection
CAP = 30.0
NAMES = ["A", "B", "C", "D", "E"]
DEMAND = [3.7, 7.4, 11.0, 11.0, 22.0]          # usual wallbox powers in kW


def water_filling(d, cap):
    """Max-min fair split of a divisible resource with demands d (the uniform rule): x_i = min(d_i, level)."""
    order = sorted(range(len(d)), key=lambda i: d[i])
    x = [0.0] * len(d)
    left, k = cap, len(d)
    for pos, i in enumerate(order):
        share = left / (k - pos)
        if d[i] <= share:
            x[i] = d[i]
            left -= d[i]
        else:
            level = share
            for j in order[pos:]:
                x[j] = level
            return x, level
    return x, max(d)


def proportional(d, cap):
    s = sum(d)
    return [cap * di / s for di in d] if s > cap else list(d)


def bars(name, alloc=None, label=None, level=None, colour=BLUE):
    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    style(ax)
    xs = np.arange(len(DEMAND))
    ax.bar(xs, DEMAND, width=0.62, color=WHITE, edgecolor=GREY, linewidth=1.6, hatch="//", zorder=1,
           label="demand")
    if alloc is not None:
        ax.bar(xs, alloc, width=0.62, color=colour, zorder=2, label=label)
        for i, a in enumerate(alloc):
            ax.text(xs[i], a + 0.4, f"{a:.1f}", ha="center", va="bottom", fontsize=15, color=INK, zorder=3)
    if level is not None:
        ax.axhline(level, color=ORANGE, lw=2.2, ls="--", zorder=4, label=f"water level {level:.2f} kW")
    ax.set_xticks(xs)
    ax.set_xticklabels([f"wallbox {n}\n{d:g} kW" for n, d in zip(NAMES, DEMAND)], fontsize=15, color=INK)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.set_ylim(0, 24)
    ax.set_ylabel("power (kW)", fontsize=15, color=INK)
    total = sum(alloc) if alloc is not None else sum(DEMAND)
    what = "allocated" if alloc is not None else "demanded"
    ax.set_title(f"connection {CAP:g} kW · {what} {total:.1f} kW", fontsize=15, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=15, loc="upper left", bbox_to_anchor=(0.0, 0.93))
    save(fig, name)


def fig_sharing():
    bars("sharing-0.svg")
    p = proportional(DEMAND, CAP)
    bars("sharing-1.svg", p, "in proportion to demand", colour=PURPLE)
    w, level = water_filling(DEMAND, CAP)
    bars("sharing-2.svg", w, "max-min fair", level=level, colour=BLUE)
    print(f"== one connection, {CAP:g} kW, demands {DEMAND} (sum {sum(DEMAND):.1f})")
    print("   proportional to demand:", [round(v, 2) for v in p])
    print(f"   max-min fair (water level {level:.3f}):", [round(v, 3) for v in w])
    print("   equal split would give 6 kW each, 2.3 kW of it unused by wallbox A")
    jain = lambda x: sum(x) ** 2 / (len(x) * sum(v * v for v in x))
    print(f"   Jain's index: proportional {jain(p):.4f}, max-min fair {jain(w):.4f}")
    return w


# ---------------------------------------------------------------- 2) two lines, three households
def fig_network():
    """Two congested hours with capacity 1 each (normalised). Device 0 (a heat pump at one constant setting) runs in
    both hours, wallbox 1 charges only in hour 1, wallbox 2 only in hour 2: x0 + x1 <= 1, x0 + x2 <= 1 (Kelly's
    two-link network). Allocations: max-min fair, proportionally fair (max sum of logs), maximum total."""
    alloc = {"max-min fair": (0.5, 0.5, 0.5), "proportionally fair": (1 / 3, 2 / 3, 2 / 3), "maximum total": (0.0, 1.0, 1.0)}
    # check proportional fairness numerically: maximise log x0 + log x1 + log x2 with x0 + x1 <= 1, x0 + x2 <= 1
    best = max(((x0, 1 - x0, 1 - x0) for x0 in np.linspace(0.001, 0.999, 9999)),
               key=lambda t: sum(np.log(t)))
    assert abs(best[0] - 1 / 3) < 1e-3
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    ax.set_xlim(-0.2, 10.2)
    ax.set_ylim(-0.4, 4.45)
    ax.axis("off")
    # two hours as columns
    for x0, lab in [(3.6, "hour 1 (capacity 1)"), (6.9, "hour 2 (capacity 1)")]:
        ax.add_patch(plt.Rectangle((x0, 1.55), 3.1, 2.75, fc="#f3f3f1", ec=LIGHT, lw=1.5, zorder=0))
        ax.text(x0 + 1.55, 4.15, lab, ha="center", va="center", fontsize=15, color=INK)
    rows = [(3.35, "heat pump 0", RED, 3.75, 9.85), (2.55, "wallbox 1", BLUE, 3.75, 6.55),
            (1.85, "wallbox 2", GREEN, 7.05, 9.85)]
    for y, lab, col, xa, xb in rows:
        ax.text(3.4, y, lab, ha="right", va="center", fontsize=15, color=col, fontweight="bold")
        ax.add_patch(plt.Rectangle((xa, y - 0.2), xb - xa, 0.4, fc=col, ec=WHITE, zorder=2))
    table = [("", "pump 0", "box 1", "box 2", "total")]
    for k, (a, b, c) in alloc.items():
        table.append((k, f"{a:.2f}", f"{b:.2f}", f"{c:.2f}", f"{a + b + c:.2f}"))
    ys = [1.05, 0.6, 0.15, -0.3]
    xs = [0.0, 4.2, 5.7, 7.2, 8.7]
    for r, y in zip(table, ys):
        for j, (txt, x) in enumerate(zip(r, xs)):
            ax.text(x, y, txt, ha="left", va="center", fontsize=15,
                    color=INK if r is not table[0] else GREY, fontweight="bold" if r is table[0] and j else "normal")
    save(fig, "sharing-net.svg")
    print("== two hours: max-min (1/2, 1/2, 1/2) total 1.5; proportionally fair (1/3, 2/3, 2/3) total 5/3;"
          " maximum total (0, 1, 1) total 2; loss against the maximum: max-min 25 %, proportional 1/6")


# ---------------------------------------------------------------- 3) indivisible: round robin
SLOTS = ["17:00", "18:00", "19:00", "20:00", "21:00", "22:00"]
VALUES = {"Ana": [6, 5, 4, 3, 2, 1], "Ben": [6, 5, 4, 3, 2, 1], "Cem": [6, 5, 4, 3, 2, 1]}   # all prefer early slots


def round_robin(values, order):
    left = list(range(len(SLOTS)))
    bundles = {a: [] for a in order}
    while left:
        for a in order:
            if not left:
                break
            best = max(left, key=lambda s: (values[a][s], -s))
            bundles[a].append(best)
            left.remove(best)
    return bundles


def ef1(values, bundles):
    for a in bundles:
        va = sum(values[a][s] for s in bundles[a])
        for b in bundles:
            if a == b or not bundles[b]:
                continue
            vb = sum(values[a][s] for s in bundles[b])
            if va < vb - max(values[a][s] for s in bundles[b]):
                return False
    return True


def rr_example():
    order = ["Ana", "Ben", "Cem"]
    bun = round_robin(VALUES, order)
    print("== round robin, order", order)
    for a in order:
        own = sum(VALUES[a][s] for s in bun[a])
        others = {b: sum(VALUES[a][s] for s in bun[b]) for b in order if b != a}
        print(f"   {a}: slots {[SLOTS[s] for s in sorted(bun[a])]}, own value {own}, value of the others' bundles {others}")
    print("   EF1:", ef1(VALUES, bun))


def exercise():
    x, level = water_filling([2, 5, 8, 10], 20)
    print(f"== exercise: capacity 20, demands 2, 5, 8, 10 -> {x}, level {level}")


if __name__ == "__main__":
    fig_sharing()
    fig_network()
    rr_example()
    exercise()
