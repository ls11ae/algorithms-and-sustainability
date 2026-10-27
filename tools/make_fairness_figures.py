"""Figures for "Algorithms and Sustainability", fair clustering (own work, CC BY 4.0).

Usage:  python3 tools/make_fairness_figures.py lectures/figures
A small constructed example only (no data needed): 24 families in two groups (A and B) in an invented town,
which places k = 3 schools. Distances are Euclidean, in km.

Writes:
  fair-town.svg           the town: families of group A (circles) and group B (triangles)
  fair-kcenter.svg        optimal 3-center clustering (centres among the families' locations) and its balance
  fair-fairlets.svg       fairlets (Chierichetti et al. 2017): a bottleneck perfect matching between groups A and B
  fair-optimal.svg        the best clustering in which every cluster has balance 1 (computed exactly)
  fair-radius.svg         individual fairness (Jung, Kannan, Lutz 2020): neighbourhood radius r(x) of two families
and prints the numbers quoted on the slides.
Needs: matplotlib, numpy, scipy. Font as in make_figures.py (LATO_DIR).
"""
import itertools
import math
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from scipy.optimize import linear_sum_assignment

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
                     "svg.hashsalt": "aus-2627-fairness", "mathtext.fontset": "custom",
                     "mathtext.it": f"{FAMILY}:italic", "mathtext.rm": FAMILY, "mathtext.bf": f"{FAMILY}:bold",
                     "mathtext.cal": f"{FAMILY}:italic", "mathtext.sf": FAMILY, "mathtext.tt": FAMILY})
if FAMILY != "LatoLatin":
    plt.rcParams["mathtext.fontset"] = "dejavusans"      # without LATO_DIR: default fonts (figures differ slightly)
INK, GREY, LIGHT = "#282a2e", "#8e908c", "#d9d9d6"
BLUE, ORANGE, RED, GREEN, PURPLE = "#0A97D9", "#E8700A", "#DD1367", "#3F7E44", "#6250d6"
WHITE = "#ffffff"
CLUSTER = [GREEN, PURPLE, RED]


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


# ---------------------------------------------------------------- the town (constructed)
# Group A lives mostly in the west, group B mostly in the east; a few families of each group live elsewhere.
A = [(0.8, 1.2), (1.4, 2.4), (0.6, 3.3), (1.9, 1.0), (2.3, 3.0), (1.2, 4.4), (2.0, 5.2), (2.9, 2.0),
     (0.4, 5.6), (3.0, 4.2), (6.6, 1.0), (7.9, 5.4)]
B = [(7.4, 1.4), (8.6, 2.2), (9.4, 1.0), (7.8, 3.2), (9.2, 3.6), (8.4, 4.4), (6.8, 2.6), (9.6, 5.0),
     (6.4, 4.6), (8.8, 6.0), (1.6, 6.3), (3.6, 0.8)]
P = np.array(A + B, dtype=float)
GROUP = ["A"] * len(A) + ["B"] * len(B)
N, K = len(P), 3
D = np.sqrt(((P[:, None, :] - P[None, :, :]) ** 2).sum(-1))


def radius(centres, assign=None):
    if assign is None:
        return D[:, centres].min(axis=1).max()
    return max(D[i, assign[i]] for i in range(N))


def balance(members):
    a = sum(1 for i in members if GROUP[i] == "A")
    b = len(members) - a
    if a == 0 or b == 0:
        return 0.0
    return min(a / b, b / a)


def optimal_kcenter(points_idx, k):
    best = None
    for cs in itertools.combinations(points_idx, k):
        r = D[np.ix_(points_idx, cs)].min(axis=1).max()
        if best is None or r < best[0] - 1e-12:
            best = (r, cs)
    return best


def perfect_matching(allowed):
    """Kuhn's algorithm; allowed[a][b] is True if A-family a may be paired with B-family b."""
    na, nb = len(allowed), len(allowed[0])
    match_b = [-1] * nb

    def augment(a, seen):
        for b in range(nb):
            if allowed[a][b] and not seen[b]:
                seen[b] = True
                if match_b[b] < 0 or augment(match_b[b], seen):
                    match_b[b] = a
                    return True
        return False

    for a in range(na):
        if not augment(a, [False] * nb):
            return None
    return {match_b[b]: b for b in range(nb)}


IA = [i for i in range(N) if GROUP[i] == "A"]
IB = [i for i in range(N) if GROUP[i] == "B"]


def bottleneck_fairlets():
    """Fairlets for balance 1: a perfect matching A-B that minimises the longest pair (bottleneck), then among those
    the one with the smallest total length (only for nicer pictures)."""
    cand = sorted(set(D[a, b] for a in IA for b in IB))
    lo, hi = 0, len(cand) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if perfect_matching([[D[a, b] <= cand[mid] + 1e-12 for b in IB] for a in IA]) is not None:
            hi = mid
        else:
            lo = mid + 1
    t = cand[lo]
    cost = np.array([[D[a, b] if D[a, b] <= t + 1e-12 else 1e6 for b in IB] for a in IA])
    ra, cb = linear_sum_assignment(cost)
    return t, [(IA[i], IB[j]) for i, j in zip(ra, cb)]


def optimal_fair_kcenter():
    """Exact optimum for balance 1 with centres among the families, every centre in its own cluster: for fixed
    centres, radius R is feasible iff there is a perfect A-B matching in which both families of a pair are within R
    of a common centre (a pair that contains a centre family must use that centre)."""
    best = None
    for cs in itertools.combinations(range(N), K):
        cand = sorted(set(D[i, c] for i in range(N) for c in cs))
        if best is not None:
            cand = [r for r in cand if r < best[0] - 1e-12]
            if not cand:
                continue

        def usable(a, b):
            own = [c for c in (a, b) if c in cs]
            if len(own) == 2:
                return []
            return own if own else list(cs)

        def feasible(R):
            ok = [[any(D[a, c] <= R + 1e-12 and D[b, c] <= R + 1e-12 for c in usable(a, b)) for b in IB] for a in IA]
            return perfect_matching(ok)

        if feasible(cand[-1]) is None:
            continue
        lo, hi = 0, len(cand) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if feasible(cand[mid]) is not None:
                hi = mid
            else:
                lo = mid + 1
        best = (cand[lo], cs, feasible(cand[lo]))
    return best


def neighbourhood_radius():
    """r(x): smallest radius of a ball around x containing at least n/k families (x included)."""
    m = math.ceil(N / K)
    return np.array([np.sort(D[i])[m - 1] for i in range(N)])


def greedy_individual(r):
    """Jung, Kannan, Lutz (2020): go through the families by increasing r(x); open a centre at x if no open centre
    is within 2 r(x). Balls B(x, r(x)) of open centres are disjoint, so at most k centres open."""
    order = sorted(range(N), key=lambda i: (r[i], i))
    cs = []
    for i in order:
        if all(D[i, c] > 2 * r[i] + 1e-12 for c in cs):
            cs.append(i)
    return cs


# ---------------------------------------------------------------- drawing helpers
def town_axes(figsize=(8.4, 5.6)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(-0.4, 10.4)
    ax.set_ylim(-1.0, 7.0)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color(LIGHT)
    ax.plot([9.0, 10.0], [-0.75, -0.75], color=INK, lw=2.5)
    ax.text(9.5, -0.6, "1 km", ha="center", va="bottom", fontsize=13, color=INK)
    return fig, ax


def draw_families(ax, colour_of=None, size=150, zorder=4):
    for i in range(N):
        col = colour_of(i) if colour_of else (BLUE if GROUP[i] == "A" else ORANGE)
        mk = "o" if GROUP[i] == "A" else "^"
        ax.scatter(P[i, 0], P[i, 1], s=size, marker=mk, facecolor=col, edgecolor=WHITE, linewidth=1.5, zorder=zorder)


def legend_groups(ax, loc="upper center", extra=()):
    h = [Line2D([], [], marker="o", ls="", markersize=12, markerfacecolor=BLUE, markeredgecolor=WHITE,
                label="group A"),
         Line2D([], [], marker="^", ls="", markersize=12, markerfacecolor=ORANGE, markeredgecolor=WHITE,
                label="group B")] + list(extra)
    ax.legend(handles=h, loc=loc, ncol=len(h), frameon=False, fontsize=15, bbox_to_anchor=(0.5, 1.12))


def school(ax, i, col=INK):
    ax.scatter(P[i, 0], P[i, 1], s=520, marker="s", facecolor="none", edgecolor=col, linewidth=2.6, zorder=6)


KC_LABELS = {5: (4.4, 5.7), 0: (1.5, -0.45), 15: (5.4, 3.55)}      # label positions (centre index: x, y)
FAIR_LABELS = {6: (4.0, 5.75), 18: (7.9, -0.45), 23: (1.5, -0.45)}
SCHOOL_HANDLE = Line2D([], [], marker="s", ls="", markersize=15, markerfacecolor="none", markeredgecolor=INK,
                       markeredgewidth=2.4, label="school")


def draw_clusters(ax, cs, assign):
    for i in range(N):
        c = assign[i]
        ax.plot([P[i, 0], P[c, 0]], [P[i, 1], P[c, 1]], color=CLUSTER[cs.index(c)], lw=1.6, alpha=0.75, zorder=2)
    for c in cs:
        school(ax, c, CLUSTER[cs.index(c)])


def cluster_label(ax, cs, assign, where):
    for j, c in enumerate(cs):
        mem = [i for i in range(N) if assign[i] == c]
        a = sum(1 for i in mem if GROUP[i] == "A")
        b = len(mem) - a
        bal = balance(mem)
        x, y = where[c]
        ax.text(x, y, f"{a} A, {b} B\nbalance {bal:.2f}".replace(".00", ""), ha="center",
                va="center", fontsize=15, color=CLUSTER[j], fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc=WHITE, ec="none", alpha=0.9), zorder=8)


# ---------------------------------------------------------------- figures
def fig_town():
    fig, ax = town_axes()
    draw_families(ax)
    legend_groups(ax)
    save(fig, "fair-town.svg")


def fig_kcenter(r_opt, cs):
    assign = {i: cs[int(np.argmin(D[i, list(cs)]))] for i in range(N)}
    cs = list(cs)
    fig, ax = town_axes()
    draw_clusters(ax, cs, assign)
    draw_families(ax)
    legend_groups(ax, extra=[SCHOOL_HANDLE])
    cluster_label(ax, cs, assign, KC_LABELS)
    ax.text(5.0, 6.75, f"largest distance {r_opt:.2f} km", ha="center", va="center", fontsize=15, color=INK)
    save(fig, "fair-kcenter.svg")
    return assign


def fig_fairlets(t, pairs, fair_r, fair_cs, fair_assign):
    fig, ax = town_axes()
    for a, b in pairs:
        ax.plot([P[a, 0], P[b, 0]], [P[a, 1], P[b, 1]], color=INK, lw=2.2, zorder=3)
    draw_families(ax)
    legend_groups(ax, extra=[Line2D([], [], color=INK, lw=2.2, label="fairlet (pair)")])
    ax.text(5.0, 6.75, f"longest pair {t:.2f} km", ha="center", va="center", fontsize=15, color=INK)
    save(fig, "fair-fairlets.svg")


def fig_optimal(fopt, fcs, match):
    fcs = list(fcs)
    assign = {}
    for ai, bj in match.items():
        a, b = IA[ai], IB[bj]
        own = [c for c in (a, b) if c in fcs]
        c = own[0] if own else min(fcs, key=lambda c: (max(D[a, c], D[b, c]), c))
        assign[a] = c
        assign[b] = c
    fig, ax = town_axes()
    draw_clusters(ax, fcs, assign)
    draw_families(ax)
    legend_groups(ax, extra=[SCHOOL_HANDLE])
    cluster_label(ax, fcs, assign, FAIR_LABELS)
    ax.text(5.0, 6.75, f"largest distance {radius(None, assign):.2f} km", ha="center", va="center", fontsize=15,
            color=INK)
    save(fig, "fair-optimal.svg")
    return assign


RADIUS_LABEL = {5: (0.0, -0.6), 14: (-1.2, 0.75)}


def fig_radius(r, show, greedy_cs, kc_cs):
    fig, ax = town_axes()
    for i in show:
        ax.add_patch(plt.Circle(P[i], r[i], fc=(0.04, 0.59, 0.85, 0.08) if GROUP[i] == "A" else (0.91, 0.44, 0.04, 0.08),
                                ec=BLUE if GROUP[i] == "A" else ORANGE, lw=2.0, zorder=1))
        ax.text(P[i, 0] + RADIUS_LABEL[i][0], P[i, 1] + RADIUS_LABEL[i][1], f"r(x) = {r[i]:.2f} km", ha="center",
                va="center", fontsize=15,
                color=INK, bbox=dict(boxstyle="round,pad=0.2", fc=WHITE, ec="none", alpha=0.9), zorder=8)
    draw_families(ax)
    legend_groups(ax)
    ax.text(5.0, 6.75, f"ball around x with {math.ceil(N / K)} of the {N} families", ha="center", va="center",
            fontsize=15, color=INK)
    save(fig, "fair-radius.svg")
    return max(D[i, greedy_cs].min() / r[i] for i in range(N))


if __name__ == "__main__":
    fig_town()
    r_opt, cs = optimal_kcenter(list(range(N)), K)
    assign = fig_kcenter(r_opt, cs)
    print("== town: n =", N, "families (12 in group A, 12 in group B), k =", K)
    print(f"   optimal 3-center: centres {sorted(cs)}, radius {r_opt:.3f} km")
    for c in cs:
        mem = [i for i in range(N) if assign[i] == c]
        print(f"     cluster of {c}: {sum(GROUP[i] == 'A' for i in mem)} A, {sum(GROUP[i] == 'B' for i in mem)} B,"
              f" balance {balance(mem):.3f}")
    t, pairs = bottleneck_fairlets()
    reps = [a for a, b in pairs]                       # representative of a fairlet: its group-A family
    rr, rcs = optimal_kcenter(reps, K)
    rcs = list(rcs)
    fair_assign = {}
    for a, b in pairs:
        c = rcs[int(np.argmin(D[a, rcs]))]
        fair_assign[a] = c
        fair_assign[b] = c
    fair_r = radius(None, fair_assign)
    fig_fairlets(t, pairs, fair_r, rcs, fair_assign)
    print(f"== fairlets: bottleneck {t:.3f} km; 3-center on the {len(reps)} representatives: radius {rr:.3f} km;"
          f" fair clustering radius {fair_r:.3f} km (bound {t:.3f} + {rr:.3f} = {t + rr:.3f})")
    for c in rcs:
        mem = [i for i in range(N) if fair_assign[i] == c]
        print(f"     cluster of {c}: {sum(GROUP[i] == 'A' for i in mem)} A, {sum(GROUP[i] == 'B' for i in mem)} B")
    fopt, fcs, fmatch = optimal_fair_kcenter()
    fassign = fig_optimal(fopt, fcs, fmatch)
    for c in fcs:
        mem = [i for i in range(N) if fassign[i] == c]
        print(f"     optimal fair cluster of {c}: {sum(GROUP[i] == 'A' for i in mem)} A,"
              f" {sum(GROUP[i] == 'B' for i in mem)} B")
    print(f"   optimal fair (balance 1) 3-center radius {fopt:.3f} km with centres {sorted(fcs)};"
          f" price of fairness {fopt / r_opt:.2f}; fairlet solution / fair optimum {fair_r / fopt:.2f}")
    r = neighbourhood_radius()
    g = greedy_individual(r)
    dense, sparse = 5, 14                 # a family in the dense west, one at the sparse south-east corner
    worst_g = fig_radius(r, [dense, sparse], g, list(cs))
    ratio_kc = max(D[i, list(cs)].min() / r[i] for i in range(N))
    print(f"== individual fairness: r(x) from {r.min():.3f} to {r.max():.3f} km (dense family {dense},"
          f" sparse family {sparse}); greedy opens {len(g)} centres {g}; worst d/r {worst_g:.3f};"
          f" radius of the greedy solution {D[:, g].min(axis=1).max():.3f} km;"
          f" optimal 3-center has worst d/r {ratio_kc:.3f}")
