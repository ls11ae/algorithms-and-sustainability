"""Figures for "Algorithms and Sustainability", lecture 1 (own work, CC BY 4.0).

Usage:  python3 tools/make_figures.py lectures/figures
Needs:  matplotlib, numpy, scipy. Text is converted to paths, so the SVGs look the same
everywhere. Font: Lato (as in the TU Dortmund Decker theme); set LATO_DIR to a folder with
LatoLatin-Regular.ttf, LatoLatin-Bold.ttf and LatoLatin-Italic.ttf, otherwise the default
matplotlib font is used.
Data: eco-routing field test from Minett et al. (2011), Tables II and III (Delft -> Zoetermeer);
data-center electricity from IEA (2025), Energy and AI, CC BY 4.0."""
import sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon
from scipy.spatial import ConvexHull

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
FD = os.environ.get("LATO_DIR", "")
HAVE_LATO = bool(FD) and os.path.exists(os.path.join(FD, "LatoLatin-Regular.ttf"))
if HAVE_LATO:
    for f in ["LatoLatin-Regular.ttf", "LatoLatin-Bold.ttf", "LatoLatin-Italic.ttf"]:
        font_manager.fontManager.addfont(os.path.join(FD, f))
plt.rcParams.update({
    "font.family": "LatoLatin" if HAVE_LATO else "sans-serif", "font.size": 15, "svg.fonttype": "path",
    "axes.edgecolor": "#4d4d4c", "axes.labelcolor": "#282a2e", "xtick.color": "#4d4d4c",
    "ytick.color": "#4d4d4c", "axes.spines.top": False, "axes.spines.right": False,
    "savefig.transparent": True, "svg.hashsalt": "aus-2627", "mathtext.fontset": "custom", "mathtext.it": "LatoLatin:italic",
    "mathtext.rm": "LatoLatin", "mathtext.bf": "LatoLatin:bold",
})
INK, GREY = "#282a2e", "#8e908c"
SDG = {3: "#4C9F38", 7: "#FCC30B", 10: "#DD1367", 11: "#FD9D24", 13: "#3F7E44", 14: "#0A97D9",
       15: "#56C02B", 16: "#00689D", 17: "#19486A"}


def save(fig, name):
    fig.savefig(os.path.join(out, name), bbox_inches="tight", pad_inches=0.05, metadata={"Date": None})
    plt.close(fig)


# 1) Two animal tracks with an optimal discrete Fréchet coupling ("leash")
t = np.linspace(0, 1, 14)
A = np.c_[6 * t, np.sin(2.2 * np.pi * t)]
u = np.linspace(0, 1, 12)
B = np.c_[6 * u + 0.1, np.sin(2.2 * np.pi * u + 0.15) - 0.3 - 1.0 * np.exp(-((u - 0.52) / 0.11) ** 2)]
n, m = len(A), len(B)
D = np.linalg.norm(A[:, None, :] - B[None, :, :], axis=2)
ca = np.full((n, m), np.inf)
for i in range(n):
    for j in range(m):
        if i == 0 and j == 0:
            ca[i, j] = D[0, 0]
        else:
            prev = min(ca[i - 1, j] if i else np.inf, ca[i, j - 1] if j else np.inf,
                       ca[i - 1, j - 1] if i and j else np.inf)
            ca[i, j] = max(D[i, j], prev)
pairs, i, j = [(n - 1, m - 1)], n - 1, m - 1
while (i, j) != (0, 0):
    cand = [(p, q) for p, q in [(i - 1, j - 1), (i - 1, j), (i, j - 1)] if p >= 0 and q >= 0]
    i, j = min(cand, key=lambda pq: (ca[pq], D[pq]))
    pairs.append((i, j))
pairs = pairs[::-1]
fig, ax = plt.subplots(figsize=(5.8, 3.0))
d = [np.linalg.norm(A[p] - B[q]) for p, q in pairs]
k_max = int(np.argmax(d))
for k, (p, q) in enumerate(pairs):
    ax.plot(*zip(A[p], B[q]), color=GREY if k != k_max else INK, lw=1.0 if k != k_max else 2.2,
            ls=(0, (2, 2)) if k != k_max else "-", zorder=1)
ax.plot(*A.T, "-o", color=SDG[14], lw=2.4, ms=5, zorder=3)
ax.plot(*B.T, "-o", color=SDG[13], lw=2.4, ms=5, zorder=3)
pa, pb = A[pairs[k_max][0]], B[pairs[k_max][1]]
ax.annotate("longest leash", xy=((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2), xytext=(4.0, -1.85),
            fontsize=13, color=INK, arrowprops=dict(arrowstyle="-", color=INK, lw=0.8))
ax.text(A[-1, 0] + 0.25, A[-1, 1] + 0.05, "track A", color=SDG[14], fontsize=14, fontweight="bold", va="center")
ax.text(B[-1, 0] + 0.25, B[-1, 1] - 0.15, "track B", color=SDG[13], fontsize=14, fontweight="bold", va="center")
ax.set_aspect("equal"); ax.axis("off")
save(fig, "tracks-frechet.svg")

# 2) Eco-routing field test (Minett et al. 2011, Delft -> Zoetermeer, Tables II-III)
routes = [("Motorway", 15.6, 1.34, 20.2), ("Provincial", 15.7, 0.76, 13.8), ("Local", 21.0, 0.73, 13.2)]
fig, ax = plt.subplots(figsize=(5.6, 3.6))
xs = [r[1] for r in routes]; ys = [r[2] for r in routes]
ax.step(xs, ys, where="post", color=SDG[11], lw=1.5, alpha=0.6, zorder=1)
ax.scatter(xs, ys, s=160, color=SDG[11], edgecolor=INK, linewidth=1.2, zorder=3)
offs = {"Motorway": (-0.35, 0.0), "Provincial": (-0.35, 0.0), "Local": (-0.25, 0.09)}
for name, x, y, km in routes:
    dx, dy = offs[name]
    ax.text(x + dx, y + dy, f"{name}\n{km} km", fontsize=13, va="center",
            ha="left" if dx > 0 else "right", color=INK)
ax.annotate("", xy=(16.05, 0.81), xytext=(16.05, 1.29),
            arrowprops=dict(arrowstyle="->", color=SDG[3], lw=2))
ax.text(16.3, 1.05, "almost the same time,\n43% less fuel", fontsize=13, color=SDG[3], ha="left",
        va="center", fontweight="bold")
ax.set_xlim(11.0, 22.0); ax.set_ylim(0.6, 1.5)
ax.set_xlabel("travel time (min)"); ax.set_ylabel("fuel (liters)")
save(fig, "ecorouting-minett2011.svg")

# 3) Speed scaling warm-up: P(s)=s^3, fixed work w=1
fig, axs = plt.subplots(1, 2, figsize=(5.6, 3.0), sharey=False)
labels = ["speed 1", "speed ½"]
for ax, vals, title, col in [(axs[0], [1, 2], "time", "#d6d6d6"), (axs[1], [1, 0.25], "energy", SDG[7])]:
    bars = ax.bar(labels, vals, color=col, edgecolor=INK, width=0.6)
    for b_, v in zip(bars, vals):
        ax.text(b_.get_x() + b_.get_width() / 2, v + 0.05, {1: "1", 2: "2", 0.25: "¼"}[v],
                ha="center", va="bottom", fontsize=15, fontweight="bold", color=INK)
    ax.set_title(title, fontsize=15, color=INK)
    ax.set_ylim(0, 2.4); ax.set_yticks([])
    ax.spines["left"].set_visible(False)
fig.tight_layout()
save(fig, "speed-scaling.svg")

# 4) Data centre electricity (IEA 2025, Energy and AI, CC BY 4.0)
fig, ax = plt.subplots(figsize=(4.6, 3.4))
b1 = ax.bar(["2024"], [415], color=SDG[7], edgecolor=INK, width=0.55)
b2 = ax.bar(["2030\n(projection)"], [945], color="white", edgecolor=INK, hatch="///", width=0.55)
ax.text(0, 440, "415 TWh", ha="center", va="bottom", fontsize=14, fontweight="bold")
ax.text(0, 200, "≈1.5%\nof global\nelectricity", ha="center", va="center", fontsize=12)
ax.text(1, 965, "≈945 TWh", ha="center", va="bottom", fontsize=14, fontweight="bold")
ax.set_ylim(0, 1200); ax.set_ylabel("data centers (TWh/year)")
save(fig, "datacentres-iea2025.svg")

# 5) Fair clustering: clustering by location vs. fair clustering
rng = np.random.default_rng(5)
placed = []
def band(n, x0, x1):
    pts = []
    for lo, hi, k in [(0.0, 1.0, n // 2), (1.6, 2.6, n - n // 2)]:
        while k:
            p = np.array([rng.uniform(x0, x1), rng.uniform(lo, hi)])
            if all(np.linalg.norm(p - q) > 0.42 for q in placed):
                placed.append(p); pts.append(p); k -= 1
    return np.array(pts)
red = band(10, 0.0, 2.2)
blue = band(10, 2.9, 5.1)
P = np.r_[red, blue]
grp = np.r_[np.zeros(len(red)), np.ones(len(blue))]


def draw(ax, lab, title):
    for c in np.unique(lab):
        pts = P[lab == c]
        h = ConvexHull(pts)
        poly = Polygon(pts[h.vertices], closed=True, facecolor="#eeeeee", edgecolor=GREY, lw=1.2,
                       joinstyle="round", zorder=1)
        ax.add_patch(poly)
    ax.scatter(*P[grp == 0].T, marker="o", s=70, color=SDG[10], edgecolor=INK, lw=0.6, zorder=3)
    ax.scatter(*P[grp == 1].T, marker="^", s=80, color=SDG[16], edgecolor=INK, lw=0.6, zorder=3)
    ax.set_title(title, fontsize=14, color=INK)
    ax.set_aspect("equal"); ax.axis("off")


fig, axs = plt.subplots(1, 2, figsize=(6.4, 3.0))
by_loc = (P[:, 0] > 2.5).astype(int)
draw(axs[0], by_loc, "nearest-center clusters")
by_fair = (P[:, 1] > 1.3).astype(int)
draw(axs[1], by_fair, "balanced (fair) clusters")
fig.tight_layout()
save(fig, "fair-clustering.svg")

# 6) Algorithm engineering cycle (after Sanders 2009), simplified
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
fig, ax = plt.subplots(figsize=(6.4, 4.6))
ax.set_xlim(0, 10); ax.set_ylim(0, 7.4); ax.axis("off")


def node(x, y, text, w=2.3, h=0.8, fc="#ffffff", ec=SDG[17], bold=True, fs=14):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.05,rounding_size=0.15",
                                fc=fc, ec=ec, lw=1.6, zorder=2))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=INK,
            fontweight="bold" if bold else "normal", zorder=3)


def arrow(a, b, rad=0.0, color=SDG[17], ls="-"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=16, lw=1.6, color=color,
                                 connectionstyle=f"arc3,rad={rad}", linestyle=ls, zorder=1))


node(5, 6.75, "application question\n(e.g., eco-routing)", w=4.2, h=0.95, fc="#f2f2f2", ec=GREY, bold=False, fs=12.5)
node(5, 5.45, "realistic model", w=2.8)
node(5, 4.05, "design")
node(7.9, 2.8, "analysis")
node(5, 1.5, "implementation", w=2.8)
node(2.1, 2.8, "experiments", w=2.5)
node(8.6, 0.45, "library / tool", w=2.4, h=0.7, fc="#f2f2f2", ec=GREY, bold=False, fs=12.5)
arrow((5, 6.25), (5, 5.88), color=GREY)
arrow((5, 5.03), (5, 4.48))
arrow((6.1, 3.8), (7.3, 3.2), rad=-0.15)
arrow((7.4, 2.38), (6.35, 1.75), rad=-0.15)
arrow((3.65, 1.65), (2.55, 2.38), rad=-0.15)
arrow((2.6, 3.22), (3.9, 3.85), rad=-0.15)
arrow((6.2, 1.25), (7.6, 0.68), color=GREY)
ax.text(1.35, 3.85, "insights,\nnew hypotheses", fontsize=11.5, color=GREY, ha="center", va="bottom", style="italic")
ax.text(8.7, 3.55, "correctness,\nguarantees", fontsize=11.5, color=GREY, ha="center", va="bottom", style="italic")
save(fig, "ae-cycle.svg")

# 7) Trajectory segmentation: one synthetic animal track, split into behavioral phases
rng7 = np.random.default_rng(7)


def leg(p0, p1, k, noise):
    s = np.linspace(0, 1, k)[:, None]
    return p0 + s * (p1 - p0) + rng7.normal(0, noise, (k, 2))


mig1 = leg(np.array([0.0, 0.0]), np.array([2.3, 1.45]), 8, 0.04)
ang = rng7.uniform(0, 2 * np.pi, 8)
rest = np.array([2.75, 1.7]) + np.c_[np.cos(ang), np.sin(ang)] * rng7.uniform(0.05, 0.17, (8, 1))
forage = np.array([[3.2, 1.45], [3.45, 0.95], [3.8, 1.3], [3.6, 0.7], [4.1, 0.6], [4.0, 1.1],
                   [4.45, 1.35], [4.3, 0.85], [4.8, 0.75], [4.9, 1.25], [5.25, 1.1]])
mig2 = leg(forage[-1], np.array([6.6, 3.0]), 7, 0.04)[1:]
phases = [(mig1, "migrating", SDG[14]), (rest, "resting", SDG[11]), (forage, "foraging", SDG[13]),
          (mig2, "migrating", SDG[14])]
fig, ax = plt.subplots(figsize=(4.6, 2.9))
track = np.vstack([p for p, _, _ in phases])
ax.plot(*track.T, "-", color=GREY, lw=1.0, zorder=1)
for pts, name, col in phases:
    ax.plot(*pts.T, "-o", color=col, lw=2.4, ms=5, mec=INK, mew=0.5, zorder=3)
label_pos = {0: (0.55, 1.05), 1: (2.6, 2.2), 2: (4.25, 0.15), 3: (5.0, 2.75)}
for k, (pts, name, col) in enumerate(phases):
    x, y = label_pos[k]
    ax.text(x, y, name, color=col, fontsize=14, fontweight="bold", ha="center", va="center")
ax.annotate("start", xy=mig1[0], xytext=(0.35, -0.45), fontsize=12, color=GREY, ha="center",
            arrowprops=dict(arrowstyle="-", color=GREY, lw=0.8))
ax.set_aspect("equal"); ax.axis("off")
save(fig, "segmentation.svg")

print("figures written to", out)
