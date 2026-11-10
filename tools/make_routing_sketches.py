"""Two schematic figures for lecture 5 (route planning), own work, CC BY 4.0; no data.

Usage:  LATO_DIR=public/support/fonts python3 tools/make_routing_sketches.py lectures/figures
Writes
  dijkstra-invariant.svg  why Dijkstra's algorithm is correct: the settled set S around s, the next
                          node u with the smallest key, and another s-u path P that leaves S over
                          the edge (x, y);
  ch-up-down.svg          why upward searches suffice in a contraction hierarchy: a shortest path
                          drawn with the rank as height; its valley v is replaced by the shortcut
                          u-w, and the two upward searches meet at the highest node m.
"""
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Ellipse, FancyArrowPatch

out = sys.argv[1]
FD = os.environ.get("LATO_DIR", "")
if FD and os.path.exists(os.path.join(FD, "LatoLatin-Regular.ttf")):
    for f in ["LatoLatin-Regular.ttf", "LatoLatin-Bold.ttf", "LatoLatin-Italic.ttf"]:
        font_manager.fontManager.addfont(os.path.join(FD, f))
    FAMILY = "LatoLatin"
else:
    FAMILY = "sans-serif"
plt.rcParams.update({"font.family": FAMILY, "font.size": 15, "svg.fonttype": "path",
                     "svg.hashsalt": "aus-2627-routing-sketches", "mathtext.fontset": "custom",
                     "mathtext.it": f"{FAMILY}:italic", "mathtext.rm": FAMILY, "mathtext.bf": f"{FAMILY}:bold"})
INK, GREY = "#282a2e", "#8e908c"
BLUE, BLUE_BG, ORANGE = "#0A97D9", "#dcEFF9", "#E8700A"



def save(fig, name):
    path = os.path.join(out, name)
    fig.patch.set_facecolor("white")
    fig.savefig(path, bbox_inches="tight", pad_inches=0.05, metadata={"Date": None})
    num = re.compile(r"-?\d+\.\d+")
    svg = open(path, encoding="utf-8").read()
    svg = re.sub(r'(\sd=")([^"]*)(")', lambda m: m.group(1) + num.sub(lambda k: f"{float(k.group()):.2f}".rstrip("0").rstrip("."), m.group(2)) + m.group(3), svg)
    open(path, "w", encoding="utf-8").write(svg)
    plt.close(fig)
    print("wrote", path)


def node(ax, P, name, fc="white", ec=INK, tc=INK, label=None, r=0.24):
    x, y = P[name]
    ax.add_patch(plt.Circle((x, y), r, fc=fc, ec=ec, lw=2, zorder=5))
    if label is None:
        label = f"${name}$"
    ax.text(x, y - 0.01, label, ha="center", va="center", fontsize=16, color=tc, zorder=6)


def curve(ax, P, a, b, rad, arrow="-", **kw):
    ax.add_patch(FancyArrowPatch(P[a], P[b], connectionstyle=f"arc3,rad={rad}", arrowstyle=arrow,
                                 shrinkA=13, shrinkB=13, zorder=3, **kw))


# ---------------------------------------------------------------- Dijkstra invariant
fig, ax = plt.subplots(figsize=(6.6, 3.9))
ax.add_patch(Ellipse((0.0, 0.0), 4.6, 3.3, fc=BLUE_BG, ec=BLUE, lw=2, zorder=0))
ax.text(-0.15, -1.22, "settled set $S$", color=BLUE, fontsize=15, ha="center", va="center")

P = {"s": (-1.3, -0.35), "x": (1.25, 0.75), "v": (1.35, -0.75), "y": (3.15, 1.35), "u": (3.0, -0.85)}

# shortest-path tree inside S and the tree edge to u
curve(ax, P, "s", "v", 0.15, color=BLUE, lw=2.5)
curve(ax, P, "v", "u", 0.0, color=BLUE, lw=2.5)
# another path P: s ... x (inside S), x -> y (leaves S), y ... u (rest of P)
curve(ax, P, "s", "x", -0.25, color=INK, lw=2, linestyle=(0, (5, 4)))
curve(ax, P, "x", "y", 0.0, color=INK, lw=2)
curve(ax, P, "y", "u", -0.35, color=INK, lw=2, linestyle=(0, (5, 4)))
for name in ("s", "x", "v"):
    node(ax, P, name, fc="white", ec=BLUE, tc=INK)
node(ax, P, "y")
node(ax, P, "u", fc=ORANGE, ec=ORANGE, tc="white")

ax.text(2.05, 1.95, "$x$ settled: $d(y) \\leq$length of $P$ up to $y$", ha="center", va="center", fontsize=13, color=INK)
ax.text(3.55, 1.3, "$d(y) \\geq d(u)$", ha="left", va="center", fontsize=15, color=INK)
ax.text(3.55, 0.9, "($u$ has the smallest $d$)", ha="left", va="center", fontsize=12.5, color=GREY)
ax.text(3.98, 0.15, "rest of $P \\geq 0$", ha="left", va="center", fontsize=15, color=INK)
ax.text(3.98, -0.25, "(weights$\\geq 0$)", ha="left", va="center", fontsize=12.5, color=GREY)
ax.text(3.45, -1.3, "next: settle $u$", ha="left", va="center", fontsize=15, color=ORANGE)
ax.text(-0.25, 0.72, "$P$", ha="center", va="center", fontsize=15, color=INK)
ax.set_xlim(-2.5, 6.6)
ax.set_ylim(-1.8, 2.2)
ax.set_aspect("equal")
ax.axis("off")
save(fig, "dijkstra-invariant.svg")

# ---------------------------------------------------------------- CH: up, then down
fig, ax = plt.subplots(figsize=(5.3, 3.55))
P = {"s": (0.3, 1.3), "u": (1.4, 3.0), "v": (2.85, 0.95), "w": (3.5, 3.9), "m": (4.5, 5.0),
     "z": (5.5, 3.3), "t": (6.4, 1.8)}
R = 0.28
# rank axis
ax.add_patch(FancyArrowPatch((-1.4, 0.3), (-1.4, 5.3), arrowstyle="-|>", mutation_scale=16, color=GREY, lw=1.5))
ax.text(-1.75, 2.8, "contracted later", rotation=90, ha="center", va="center", fontsize=14, color=GREY)
# the old piece of the path through the valley v
curve(ax, P, "u", "v", 0.0, color=GREY, lw=1.6, linestyle=(0, (2, 3)))
curve(ax, P, "v", "w", 0.0, color=GREY, lw=1.6, linestyle=(0, (2, 3)))
# up: search from s; the shortcut u-w is dashed, as in the demo
curve(ax, P, "s", "u", 0.0, arrow="-|>", mutation_scale=16, color=BLUE, lw=2.5)
curve(ax, P, "u", "w", 0.0, arrow="-|>", mutation_scale=16, color=BLUE, lw=2.5, linestyle=(0, (5, 3)))
curve(ax, P, "w", "m", 0.0, arrow="-|>", mutation_scale=16, color=BLUE, lw=2.5)
# down, read backwards: search from t
curve(ax, P, "t", "z", 0.0, arrow="-|>", mutation_scale=16, color=ORANGE, lw=2.5)
curve(ax, P, "z", "m", 0.0, arrow="-|>", mutation_scale=16, color=ORANGE, lw=2.5)
node(ax, P, "s", ec=BLUE, r=R)
node(ax, P, "u", ec=BLUE, r=R)
node(ax, P, "w", ec=BLUE, r=R)
node(ax, P, "v", ec=GREY, tc=GREY, r=R)
node(ax, P, "m", fc=INK, ec=INK, tc="white", r=R)
node(ax, P, "z", ec=ORANGE, label="", r=R)
node(ax, P, "t", ec=ORANGE, r=R)
ax.text(3.9, 5.8, "highest node $m$: the searches meet", ha="center", va="center", fontsize=15, color=INK)
ax.text(1.4, 4.3, "shortcut $u$–$w$", ha="center", va="center", fontsize=15, color=BLUE)
ax.text(3.15, 0.25, "valley $v$:", ha="center", va="center", fontsize=15, color=GREY)
ax.text(3.15, -0.2, "lower than $u$, $w$", ha="center", va="center", fontsize=15, color=GREY)
ax.text(0.3, 0.6, "search from $s$:", ha="center", va="center", fontsize=15, color=BLUE)
ax.text(0.3, 0.15, "only up", ha="center", va="center", fontsize=15, color=BLUE)
ax.text(6.4, 1.1, "search from $t$:", ha="center", va="center", fontsize=15, color=ORANGE)
ax.text(6.4, 0.65, "only up", ha="center", va="center", fontsize=15, color=ORANGE)
ax.set_xlim(-2.0, 7.8)
ax.set_ylim(-0.55, 6.1)
ax.set_aspect("equal")
ax.axis("off")
save(fig, "ch-up-down.svg")
