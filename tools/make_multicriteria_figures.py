"""Figures for "Algorithms and Sustainability", lecture 6, part A: several criteria (own work, CC BY 4.0).

Usage:  python3 tools/make_multicriteria_figures.py lectures/figures
Small constructed examples only (no data needed).

Writes:
  pareto-quiz.svg, pareto-quiz-solution.svg   nine routes (time, stress): which are Pareto-optimal?
                                              solution with the Pareto set and the lower convex hull
  martins-step-0..5.svg           multi-criteria Dijkstra (Martins) on a four-node graph
  pareto-chain.svg                2^k Pareto-optimal paths on a chain
  mcch-envelope.svg               the u-w paths of the example as lines over lambda, with the lower envelope
  mcch-witness-0..2.svg           witness search of Funke and Storandt (2013), step by step
and prints the numbers quoted on the slides.
Needs: matplotlib, numpy. Font as in make_figures.py (LATO_DIR).
"""
import heapq
import itertools
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
FD = os.environ.get("LATO_DIR", "")
if FD and os.path.exists(os.path.join(FD, "LatoLatin-Regular.ttf")):
    for f in ["LatoLatin-Regular.ttf", "LatoLatin-Bold.ttf", "LatoLatin-Italic.ttf"]:
        font_manager.fontManager.addfont(os.path.join(FD, f))
    FAMILY = "LatoLatin"
else:
    FAMILY = "sans-serif"
plt.rcParams.update({"font.family": FAMILY, "font.size": 14, "svg.fonttype": "path", "savefig.transparent": False,
                     "svg.hashsalt": "aus-2627-multicriteria", "mathtext.fontset": "custom",
                     "mathtext.it": f"{FAMILY}:italic", "mathtext.rm": FAMILY, "mathtext.bf": f"{FAMILY}:bold",
                     "mathtext.cal": f"{FAMILY}:italic", "mathtext.sf": FAMILY, "mathtext.tt": FAMILY})
INK, GREY, LIGHT = "#282a2e", "#8e908c", "#d9d9d6"
BLUE, ORANGE, RED, GREEN = "#0A97D9", "#E8700A", "#DD1367", "#3F7E44"
WHITE, PALEBLUE, PALEGREEN = "#ffffff", "#e7f4fb", "#e3efe4"
LAM = "λ"                                  # not in LatoLatin as text: use mathtext $\lambda$ in labels


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


def fmt(c):
    return f"({c[0]}, {c[1]})"


def dominates(a, b):
    """a dominates b: at least as good in every criterion, better in one (minimisation)."""
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def pareto(points):
    return [p for p in points if not any(dominates(q, p) for q in points if q != p)]


def lower_hull(points):
    """Lower-left convex hull of the Pareto points (monotone chain), from small x to large x."""
    pts = sorted(set(points))
    hull = []
    for p in pts:
        while len(hull) >= 2:
            (x1, y1), (x2, y2) = hull[-2], hull[-1]
            if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) <= 0:
                hull.pop()
            else:
                break
        hull.append(p)
    return pareto(hull)


# ---------------------------------------------------------------- 1) Pareto quiz
ROUTES = {"A": (22, 9.0), "B": (24, 6.0), "C": (27, 5.0), "D": (30, 2.4), "E": (33, 2.0), "F": (26, 8.0),
          "G": (31, 5.5), "H": (35, 3.5), "I": (28, 7.0)}


def fig_pareto():
    pts = list(ROUTES.values())
    par = pareto(pts)
    hull = lower_hull(par)
    unsupported = [p for p in par if p not in hull]
    name = {v: k for k, v in ROUTES.items()}
    print("== Pareto quiz: Pareto-optimal", sorted(name[p] for p in par), "; on the lower convex hull",
          [name[p] for p in hull], "; unsupported", [name[p] for p in unsupported])
    for solution in (False, True):
        fig, ax = plt.subplots(figsize=(6.6, 4.2))
        if solution:
            xs = sorted(par)
            stair_x, stair_y = [xs[0][0]], [10.4]
            for (x, y), nxt in zip(xs, xs[1:] + [(37.5, None)]):
                stair_x += [x, nxt[0]]
                stair_y += [y, y]
            ax.fill_between(stair_x, stair_y, 10.4, step=None, color=PALEBLUE, zorder=0, lw=0)
            ax.plot(stair_x, stair_y, color=BLUE, lw=1.2, alpha=0.6, zorder=1)
            ax.plot([p[0] for p in hull], [p[1] for p in hull], color=GREEN, lw=2.2, ls=(0, (5, 3)), zorder=2)
            ax.text(20.9, 3.5, "lower convex hull:\nweighted sums find these", color=GREEN, fontsize=12.5,
                    ha="left", va="top")
            ax.text(34.2, 9.6, "dominated", color=GREY, fontsize=12.5, ha="right", va="center")
        for k, (x, y) in ROUTES.items():
            if not solution:
                col, ec = WHITE, INK
            elif (x, y) in unsupported:
                col, ec = ORANGE, ORANGE
            elif (x, y) in par:
                col, ec = BLUE, BLUE
            else:
                col, ec = LIGHT, GREY
            ax.plot(x, y, "o", ms=12, mfc=col, mec=ec, mew=1.8, zorder=4)
            ax.text(x + 0.45, y + 0.35, k, fontsize=14, color=INK if not solution or (x, y) in par else GREY,
                    zorder=5, fontweight="bold")
        if solution:
            cx, cy = ROUTES["C"]
            ax.annotate("Pareto-optimal, but no\nweighted sum finds it", xy=(cx + 0.25, cy + 0.15),
                        xytext=(cx + 1.8, cy + 1.9), fontsize=12.5, color=ORANGE, ha="left", va="bottom",
                        arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=1.3))
        ax.set_xlim(20.5, 37.5)
        ax.set_ylim(0.8, 10.4)
        ax.set_xlabel("travel time (min)", fontsize=14, color=INK)
        ax.set_ylabel("stress (score)", fontsize=14, color=INK)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(GREY)
        ax.tick_params(colors=GREY, labelsize=12)
        save(fig, "pareto-quiz-solution.svg" if solution else "pareto-quiz.svg")
    return par, hull, unsupported


# ---------------------------------------------------------------- 2) Martins' algorithm
M_POS = {"s": (0, 1.0), "a": (2.0, 2.15), "b": (2.0, -0.15), "t": (4.0, 1.0)}
M_EDGES = {("s", "a"): (1, 3), ("s", "b"): (3, 1), ("a", "b"): (1, 1), ("a", "t"): (2, 4), ("b", "t"): (2, 2)}
M_BOTH = {("a", "b")}                             # the only edge usable in both directions


def martins(edges, s, both=()):
    """Label-setting multi-criteria Dijkstra (Martins 1984) on a directed graph (edges in `both` are used in
    both directions). Labels are extracted in lexicographic order. Returns the trace and the final bags."""
    adj = {}
    for (u, v), c in edges.items():
        adj.setdefault(u, {})[v] = c
        adj.setdefault(v, {})
        if (u, v) in both:
            adj[v][u] = c
    zero = (0, 0)
    bags = {v: [] for v in adj}
    bags[s] = [zero]
    final = {v: [] for v in adj}
    pq = [(zero, s)]
    steps = [dict(extracted=None, inserted=[], rejected=[], removed=[], queue=sorted(pq), bags={v: list(b) for v, b in bags.items()},
                  final={v: list(b) for v, b in final.items()})]
    while pq:
        lab, u = heapq.heappop(pq)
        if lab not in bags[u]:                    # removed meanwhile (dominated by a later label)
            continue
        final[u].append(lab)
        inserted, rejected, removed = [], [], []
        for v, c in sorted(adj[u].items()):
            new = (lab[0] + c[0], lab[1] + c[1])
            if any(dominates(b, new) or b == new for b in bags[v]):
                rejected.append((v, new))
                continue
            for b in list(bags[v]):
                if dominates(new, b):
                    bags[v].remove(b)
                    removed.append((v, b))
            bags[v].append(new)
            heapq.heappush(pq, (new, v))
            inserted.append((v, new))
        steps.append(dict(extracted=(u, lab), inserted=inserted, rejected=rejected, removed=removed,
                          queue=sorted((l, v) for l, v in pq if l in bags[v]),
                          bags={v: list(b) for v, b in bags.items()}, final={v: list(b) for v, b in final.items()}))
    return steps, final


def draw_mgraph(ax, ecol=None, elw=None, node_fc=None):
    ecol, elw, node_fc = ecol or {}, elw or {}, node_fc or {}
    for (u, v), c in M_EDGES.items():
        (x0, y0), (x1, y1) = M_POS[u], M_POS[v]
        col = ecol.get((u, v), ecol.get((v, u), GREY))
        ax.add_patch(mpatches.FancyArrowPatch((x0, y0), (x1, y1),
                                              arrowstyle="<|-|>" if (u, v) in M_BOTH else "-|>",
                                              mutation_scale=16, color=col, lw=elw.get((u, v), elw.get((v, u), 1.8)),
                                              shrinkA=19, shrinkB=19, zorder=1))
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        off = {("s", "a"): (-0.28, 0.2), ("s", "b"): (-0.28, -0.2), ("a", "b"): (-0.45, 0.0),
               ("a", "t"): (0.28, 0.2), ("b", "t"): (0.28, -0.2)}[(u, v)]
        ax.text(mx + off[0], my + off[1], fmt(c), ha="center", va="center", fontsize=13,
                color=col if col != GREY else INK, zorder=4,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.9))
    for v, (x, y) in M_POS.items():
        ax.add_patch(mpatches.Circle((x, y), 0.25, fc=node_fc.get(v, WHITE), ec=INK, lw=1.8, zorder=3))
        ax.text(x, y, v, ha="center", va="center", fontsize=15, fontstyle="italic", zorder=5,
                color=WHITE if node_fc.get(v, WHITE) not in (WHITE, PALEBLUE) else INK)


BAG_ANCHOR = {"s": (-0.42, 1.0, "right", "center"), "a": (2.0, 2.55, "center", "bottom"),
              "b": (2.0, -0.55, "center", "top"), "t": (4.42, 1.0, "left", "center")}


def draw_bags(ax, st, last=False):
    """Labels next to each node: final (blue), tentative (ink), new (orange), rejected (red, struck)."""
    new = {(v, l) for v, l in st["inserted"]}
    ext = None if last else st["extracted"]
    for v in M_POS:
        items = []
        for l in sorted(set(st["final"][v]) | set(st["bags"][v])):
            if ext and (v, l) == (ext[0], ext[1]):
                items.append((fmt(l), ORANGE, True, False))
            elif l in st["final"][v]:
                items.append((fmt(l), BLUE, True, False))
            elif (v, l) in new:
                items.append((fmt(l), ORANGE, False, False))
            else:
                items.append((fmt(l), INK, False, False))
        for w, l in st["rejected"] + st["removed"]:
            if w == v:
                items.append((fmt(l), RED, False, True))
        x, y, ha, va = BAG_ANCHOR[v]
        if not items:
            continue
        # stack the labels vertically for s and t, horizontally for a and b
        if v in ("s", "t"):
            n = len(items)
            for k, (txt, col, bold, struck) in enumerate(items):
                yy = y + 0.36 * (n - 1) / 2 - 0.36 * k
                t = ax.text(x, yy, txt, ha=ha, va="center", fontsize=13.5, color=col,
                            fontweight="bold" if bold else "normal", zorder=6)
                if struck:
                    strike(ax, t)
        else:
            n = len(items)
            for k, (txt, col, bold, struck) in enumerate(items):
                xx = x + 1.0 * (k - (n - 1) / 2)
                t = ax.text(xx, y, txt, ha="center", va=va, fontsize=13.5, color=col,
                            fontweight="bold" if bold else "normal", zorder=6)
                if struck:
                    strike(ax, t)


STRIKES = []


def strike(ax, t):
    STRIKES.append((ax, t))


def apply_strikes(fig):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for ax, t in STRIKES:
        bb = t.get_window_extent(renderer=r).transformed(ax.transData.inverted())
        ym = (bb.y0 + bb.y1) / 2
        ax.plot([bb.x0 - 0.02, bb.x1 + 0.02], [ym, ym], color=RED, lw=1.6, zorder=7)
    STRIKES.clear()


def fig_martins():
    steps, final = martins(M_EDGES, "s", both=M_BOTH)
    print("== Martins example: final labels at t", final["t"])
    for k, st in enumerate(steps[1:], 1):
        u, lab = st["extracted"]
        print(f"   step {k}: extract {u}{fmt(lab)}; insert", ", ".join(f"{v}{fmt(l)}" for v, l in st["inserted"]) or "-",
              "; reject", ", ".join(f"{v}{fmt(l)}" for v, l in st["rejected"]) or "-",
              "; queue", " ".join(f"{v}{fmt(l)}" for l, v in st["queue"]) or "empty")
    shown = [0, 1, 2, 3, 4, 6, len(steps) - 1]
    shown = sorted(set(shown))
    texts = {0: "start: one label (0, 0) at s",
             1: "s: new labels at a and b",
             2: "a (1, 3): new labels at b and t",
             3: "b (2, 4): (3, 5) at a is dominated by (1, 3)",
             4: "b (3, 1): new labels at a and t",
             6: "a (4, 2): both new labels are dominated",
             len(steps) - 1: "done: three Pareto-optimal labels at t"}
    for idx, k in enumerate(shown):
        st = steps[k]
        fig, ax = plt.subplots(figsize=(8.4, 4.6))
        ecol, elw, fc = {}, {}, {}
        last = k == len(steps) - 1
        if st["extracted"] and not last:
            u, lab = st["extracted"]
            fc[u] = ORANGE
            for v, l in st["inserted"]:
                ecol[(u, v)], elw[(u, v)] = ORANGE, 3.4
        draw_mgraph(ax, ecol=ecol, elw=elw, node_fc=fc)
        draw_bags(ax, st, last=last)
        q = st["queue"]
        qtxt = "queue:  " + ("   ".join(f"{v}{fmt(l)}" for l, v in q) if q else "empty")
        ax.text(2.0, -1.45, qtxt, ha="center", va="center", fontsize=13.5, color=INK)
        ax.text(2.0, 3.35, texts.get(k, ""), ha="center", va="center", fontsize=14.5, color=INK)
        ax.set_xlim(-1.75, 5.75)
        ax.set_ylim(-1.75, 3.6)
        ax.set_aspect("equal")
        ax.axis("off")
        apply_strikes(fig)
        save(fig, f"martins-step-{idx}.svg")
    return steps, final, len(shown)


# ---------------------------------------------------------------- 3) exponentially many Pareto paths
def fig_chain(k=4):
    fig, ax = plt.subplots(figsize=(9.6, 2.3))
    xs = np.arange(k + 1) * 1.6
    for i in range(k):
        w = 2 ** i
        for rad, lab, va, dy in [(-0.45, f"({w}, 0)", "bottom", 0.45), (0.45, f"(0, {w})", "top", -0.45)]:
            ax.add_patch(mpatches.FancyArrowPatch((xs[i], 0), (xs[i + 1], 0), arrowstyle="-",
                                                  connectionstyle=f"arc3,rad={rad}", color=GREY, lw=1.8,
                                                  shrinkA=0, shrinkB=0))
            ax.text((xs[i] + xs[i + 1]) / 2, dy * 0.9, lab, ha="center", va=va, fontsize=15, color=INK)
    for i, x in enumerate(xs):
        ax.add_patch(mpatches.Circle((x, 0), 0.15, fc=WHITE, ec=INK, lw=1.8, zorder=3))
    ax.text(xs[0] - 0.3, 0, "$s$", ha="right", va="center", fontsize=17)
    ax.text(xs[-1] + 0.3, 0, "$t$", ha="left", va="center", fontsize=17)
    ax.set_xlim(-0.6, xs[-1] + 0.6)
    ax.set_ylim(-1.0, 1.0)
    ax.set_aspect("equal")
    ax.axis("off")
    save(fig, "pareto-chain.svg")
    total = 2 ** k - 1
    pts = [(x, total - x) for x in range(total + 1)]
    par = pareto(pts)
    print(f"== chain with k = {k}: {len(pts)} paths, {len(par)} Pareto-optimal, all with x + y = {total}")


# ---------------------------------------------------------------- 4) CH for several criteria
W_POS = {"u": (0, 1.0), "v": (1.5, 1.0), "w": (3.0, 1.0), "x": (1.5, -0.25), "y": (1.5, 2.25)}
W_EDGES = {("u", "v"): (2, 3), ("v", "w"): (3, 4), ("u", "x"): (4, 1), ("x", "w"): (4, 1), ("u", "y"): (1, 5),
           ("y", "w"): (1, 5)}
W_PATHS = {"π = u–v–w": ("u", "v", "w"), "u–x–w": ("u", "x", "w"), "u–y–w": ("u", "y", "w")}


def path_cost(p):
    c = [0, 0]
    for a, b in zip(p, p[1:]):
        e = W_EDGES.get((a, b), W_EDGES.get((b, a)))
        c[0] += e[0]
        c[1] += e[1]
    return tuple(c)


def best_path(lam):
    """Dijkstra in G_lambda (weights lam*time + (1-lam)*stress) from u to w on the small graph."""
    adj = {}
    for (a, b), c in W_EDGES.items():
        wgt = lam * c[0] + (1 - lam) * c[1]
        adj.setdefault(a, {})[b] = wgt
        adj.setdefault(b, {})[a] = wgt
    dist, par, pq, done = {"u": 0.0}, {"u": None}, [(0.0, "u")], set()
    while pq:
        d, x = heapq.heappop(pq)
        if x in done:
            continue
        done.add(x)
        for y, wgt in adj[x].items():
            if d + wgt < dist.get(y, np.inf) - 1e-12:
                dist[y], par[y] = d + wgt, x
                heapq.heappush(pq, (d + wgt, y))
    p, x = [], "w"
    while x is not None:
        p.append(x)
        x = par[x]
    return tuple(p[::-1])


def witness_search(pi):
    """Algorithm 2 of Funke and Storandt (2013): is the reference path pi optimal for some lambda in [0, 1]?"""
    cpi = path_cost(pi)
    low, upp, log = 0.0, 1.0, []
    while True:
        lam = (low + upp) / 2
        p = best_path(lam)
        cp = path_cost(p)
        entry = dict(lam=lam, path=p, cost=cp, low=low, upp=upp)
        if p == pi:
            log.append({**entry, "result": "pi optimal: shortcut needed"})
            return True, log
        if dominates(cp, cpi):
            log.append({**entry, "result": "pi dominated: no shortcut"})
            return False, log
        lam0 = (cp[1] - cpi[1]) / (cpi[0] - cpi[1] - cp[0] + cp[1])
        if not (low <= lam0 <= upp):
            log.append({**entry, "cross": lam0, "result": "interval empty: no shortcut"})
            return False, log
        if cpi[1] > cp[1]:                        # pi has more stress: pi can only win for larger lambda
            low = lam0
        else:
            upp = lam0
        log.append({**entry, "cross": lam0, "new": (low, upp), "result": "continue"})


def line(c, lam):
    return lam * c[0] + (1 - lam) * c[1]


def style_lam_axes(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(1.5, 10.5)
    ax.set_xlabel(r"$\lambda$", fontsize=18, color=INK, labelpad=2)
    ax.set_ylabel(r"$\lambda\cdot$time $+ (1-\lambda)\cdot$stress", fontsize=15, color=INK)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
    ax.set_xticklabels(["0", "0.25", "0.5", "0.75", "1"])
    ax.set_yticks([2, 4, 6, 8, 10])
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(GREY)
    ax.tick_params(colors=GREY, labelsize=13.5)


PATH_COL = {"π = u–v–w": ORANGE, "u–x–w": BLUE, "u–y–w": GREEN}


def draw_wgraph(ax, highlight=None):
    for (a, b), c in W_EDGES.items():
        (x0, y0), (x1, y1) = W_POS[a], W_POS[b]
        col = GREY
        if highlight and a in highlight and b in highlight:
            col = PATH_COL[[k for k, v in W_PATHS.items() if v == highlight][0]]
        ax.plot([x0, x1], [y0, y1], color=col, lw=3.0 if col != GREY else 1.8, zorder=1)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dy = 0.22 if my >= 1.0 else -0.22
        if my == 1.0:
            dy = 0.2
        ax.text(mx, my + dy, fmt(c), ha="center", va="center", fontsize=14, color=INK, zorder=4,
                bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.9))
    for v, (x, y) in W_POS.items():
        ax.add_patch(mpatches.Circle((x, y), 0.22, fc=ORANGE if v == "v" else WHITE, ec=INK, lw=1.6, zorder=3))
        ax.text(x, y, v, ha="center", va="center", fontsize=16, fontstyle="italic", zorder=5,
                color=WHITE if v == "v" else INK)
    ax.set_xlim(-0.35, 3.35)
    ax.set_ylim(-0.6, 2.6)
    ax.set_aspect("equal")
    ax.axis("off")


def fig_mcch():
    costs = {k: path_cost(p) for k, p in W_PATHS.items()}
    pi = W_PATHS["π = u–v–w"]
    needed, log = witness_search(pi)
    print("== MC-CH witness search: path costs (time, stress)", costs)
    for e in log:
        print(f"   lambda = {e['lam']:.4f}: best path {'-'.join(e['path'])} {e['cost']}, interval before "
              f"[{e['low']:.3f}, {e['upp']:.3f}], crossing {e.get('cross', float('nan')):.3f} -> {e['result']}")
    print("   shortcut needed:", needed)
    lam = np.linspace(0, 1, 201)
    # (a) the lines of the three u-w paths over lambda, with the lower envelope
    fig, bx = plt.subplots(figsize=(6.4, 4.5))
    for k, c in costs.items():
        bx.plot(lam, line(c, lam), color=PATH_COL[k], lw=3.0 if k.startswith("π") else 2.4,
                ls=(0, (6, 3)) if k.startswith("π") else "-", zorder=3)
    env = np.min([line(c, lam) for c in costs.values()], axis=0)
    bx.fill_between(lam, 1.5, env, color=LIGHT, alpha=0.45, lw=0, zorder=1)
    bx.text(0.5, 2.6, "lower envelope", fontsize=15, color=GREY, ha="center", va="bottom")
    for k, c in costs.items():
        nm = k.replace("π = ", "π: ")
        xl, ha = {"π = u–v–w": (0.98, "right"), "u–x–w": (0.98, "right"), "u–y–w": (0.04, "left")}[k]
        dy = {"π = u–v–w": -0.75, "u–x–w": 0.35, "u–y–w": 0.35}[k]
        bx.text(xl, line(c, xl) + dy, f"{nm} {fmt(c)}", color=PATH_COL[k], fontsize=15, ha=ha, va="bottom",
                zorder=5)
    style_lam_axes(bx)
    fig.tight_layout()
    save(fig, "mcch-envelope.svg")
    # (b) witness search, frame by frame
    frames = [None] + log
    for idx, e in enumerate(frames):
        fig, (gx, bx) = plt.subplots(1, 2, figsize=(10.0, 4.2), gridspec_kw=dict(width_ratios=[0.85, 1.45]))
        draw_wgraph(gx, highlight=e["path"] if e else None)
        known = ["π = u–v–w"] + [k for f in log[:idx] for k, p in W_PATHS.items() if p == f["path"]]
        if idx == 0:
            low, upp = 0.0, 1.0
        else:
            low, upp = e.get("new", (e["low"], e["low"]))
        for k in dict.fromkeys(known):
            c = costs[k]
            bx.plot(lam, line(c, lam), color=PATH_COL[k], lw=2.6 if k.startswith("π") else 2.0,
                    ls=(0, (6, 3)) if k.startswith("π") else "-", zorder=3)
            xl = 0.97 if k != "u–y–w" else 0.16
            bx.text(xl, line(c, xl) + 0.35, k, color=PATH_COL[k], fontsize=15,
                    ha="right" if k != "u–y–w" else "left", va="bottom", zorder=5)
        if idx == 0:
            bx.axvspan(0, 1, color=PALEGREEN, zorder=0)
            msg = "is π optimal for some $\\lambda$? interval [0, 1]"
        else:
            bx.axvline(e["lam"], color=INK, lw=1.2, ls=(0, (2, 2)), zorder=2)
            c = e["cost"]
            bx.plot(e["lam"], line(c, e["lam"]), "x", ms=11, mew=2.6, color=INK, zorder=6)
            bx.plot(e["cross"], line(costs["π = u–v–w"], e["cross"]), "o", ms=8, mfc=WHITE, mec=RED, mew=2.0,
                    zorder=6)
            if e["result"] == "continue":
                bx.axvspan(low, upp, color=PALEGREEN, zorder=0)
                msg = (f"$\\lambda = {e['lam']:g}$: best is {'–'.join(e['path'])}; π can only win for "
                       f"$\\lambda \\geq {e['cross']:g}$")
            else:
                bx.axvspan(e["low"], e["upp"], color=PALEGREEN, zorder=0)
                bx.axvspan(0, e["cross"], color="#f8e0ea", zorder=0, alpha=0.8)
                msg = (f"$\\lambda = {e['lam']:g}$: best is {'–'.join(e['path'])}; π would need "
                       f"$\\lambda \\leq {e['cross']:g}$: no $\\lambda$ left, no shortcut")
        style_lam_axes(bx)
        fig.text(0.5, 0.0, msg, ha="center", va="top", fontsize=16.5, color=INK)
        fig.tight_layout(w_pad=1.5)
        save(fig, f"mcch-witness-{idx}.svg")
    return costs, log


if __name__ == "__main__":
    fig_pareto()
    fig_martins()
    fig_chain()
    fig_mcch()
