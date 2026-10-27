"""Figures for "Algorithms and Sustainability", lecture 5: route planning (own work, CC BY 4.0).

Usage:  python3 tools/make_routing_figures.py lectures/figures
Small constructed graphs only (no data needed); the map figures of the Dortmund running example come
from the separate routing-viz project (OpenStreetMap data) once it exists.

Writes:
  dijkstra-step-0..7.svg          Dijkstra on a seven-node graph, one settled node per step
  astar-dijkstra.svg, astar.svg   the same query with Dijkstra and with A* (settled nodes)
  search-spaces.svg               schematic search spaces: Dijkstra, bidirectional, A*, CH
  ch-contract-0..4.svg            contraction of a small network, one node per step
  ch-query.svg                    CH query: upward searches from s and t, meeting node, unpacking
  ch-exercise.svg, ch-exercise-solution.svg   which shortcuts does contracting v need?
and prints the numbers quoted on the slides (distances, settled nodes, shortcuts).
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
                     "svg.hashsalt": "aus-2627-routing", "mathtext.fontset": "custom",
                     "mathtext.it": f"{FAMILY}:italic", "mathtext.rm": FAMILY, "mathtext.bf": f"{FAMILY}:bold",
                     "mathtext.cal": f"{FAMILY}:italic", "mathtext.sf": FAMILY, "mathtext.tt": FAMILY})
INK, GREY, LIGHT = "#282a2e", "#8e908c", "#d9d9d6"
BLUE, ORANGE, RED, GREEN = "#0A97D9", "#E8700A", "#DD1367", "#3F7E44"
WHITE = "#ffffff"


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


# ---------------------------------------------------------------- graphs and algorithms
def adjacency(edges):
    adj = {}
    for (u, v), w in edges.items():
        adj.setdefault(u, {})[v] = w
        adj.setdefault(v, {})[u] = w
    return adj


def dijkstra_trace(adj, s, target=None, h=None):
    """Dijkstra (or A* with potential h) from s. Returns the list of steps; each step records the node
    settled, the tentative distances after relaxing its edges, the parents and the relaxed edges."""
    h = h or {}
    dist, parent, done = {s: 0}, {s: None}, []
    pq = [(h.get(s, 0), 0, s)]
    steps = [dict(settled=None, dist=dict(dist), parent=dict(parent), relaxed=[], done=[])]
    while pq:
        k, d, u = heapq.heappop(pq)
        if u in done or d > dist[u]:
            continue
        done.append(u)
        relaxed = []
        for v, w in sorted(adj[u].items()):
            if v in done:
                continue
            if d + w < dist.get(v, np.inf):
                dist[v], parent[v] = d + w, u
                heapq.heappush(pq, (d + w + h.get(v, 0), d + w, v))
                relaxed.append((u, v))
        steps.append(dict(settled=u, dist=dict(dist), parent=dict(parent), relaxed=relaxed, done=list(done)))
        if u == target:
            break
    return steps


def path_to(parent, t):
    p = [t]
    while parent[p[-1]] is not None:
        p.append(parent[p[-1]])
    return p[::-1]


def draw_graph(ax, pos, edges, labels=None, node_fc=None, node_ec=None, edge_col=None, edge_lw=None,
               weights=True, r=0.27, fs=15, label_col=None, wpos=None, curved=None):
    labels = labels or {}
    curved = curved or {}
    for (u, v), w in edges.items():
        col = (edge_col or {}).get((u, v), (edge_col or {}).get((v, u), GREY))
        lw = (edge_lw or {}).get((u, v), (edge_lw or {}).get((v, u), 1.6))
        (x0, y0), (x1, y1) = pos[u], pos[v]
        rad = curved.get((u, v), curved.get((v, u), 0.0))
        ax.add_patch(mpatches.FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-", connectionstyle=f"arc3,rad={rad}",
                                              color=col, lw=lw, zorder=1, shrinkA=0, shrinkB=0,
                                              linestyle=(0, (4, 3)) if lw < 0 else "-"))
        if weights:
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            dx, dy = y1 - y0, x0 - x1
            nrm = np.hypot(dx, dy) or 1
            off = (wpos or {}).get((u, v), (wpos or {}).get((v, u), 0.17))
            if rad:                                   # quadratic Bezier of arc3: midpoint + rad/2 * (dy, -dx)
                mx, my = mx + 0.5 * rad * (y1 - y0), my - 0.5 * rad * (x1 - x0)
                sgn = 1 if rad > 0 else -1
                off = -sgn * abs(off) * 1.2
            ax.text(mx + dx / nrm * off, my + dy / nrm * off, str(w), ha="center", va="center", fontsize=fs - 1,
                    color=col if col != GREY else INK, zorder=4,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.9))
    for v, (x, y) in pos.items():
        fc = (node_fc or {}).get(v, WHITE)
        ec = (node_ec or {}).get(v, INK)
        ax.add_patch(mpatches.Circle((x, y), r, fc=fc, ec=ec, lw=1.8, zorder=3))
        txt = labels.get(v, "")
        if txt:
            ax.text(x, y, txt, ha="center", va="center", fontsize=fs, zorder=5,
                    color=(label_col or {}).get(v, WHITE if fc not in (WHITE, LIGHT) else INK), fontweight="bold")
    ax.set_aspect("equal")
    ax.axis("off")


# ---------------------------------------------------------------- 1) Dijkstra, step by step
D_POS = {"s": (0, 1), "a": (1.4, 2.1), "b": (1.4, -0.1), "c": (2.8, 1), "d": (4.2, 2.1), "e": (4.2, -0.1),
         "t": (5.6, 1)}
D_EDGES = {("s", "a"): 2, ("s", "b"): 1, ("a", "c"): 2, ("b", "c"): 4, ("a", "d"): 5, ("c", "d"): 1,
           ("c", "e"): 3, ("b", "e"): 6, ("d", "t"): 3, ("e", "t"): 2}


def fig_dijkstra():
    adj = adjacency(D_EDGES)
    steps = dijkstra_trace(adj, "s")
    for k, st in enumerate(steps):
        fig, ax = plt.subplots(figsize=(7.4, 3.9))
        fc, ec, ecol, elw, lab, lcol = {}, {}, {}, {}, {}, {}
        for v in D_POS:
            d = st["dist"].get(v)
            lab[v] = "∞" if d is None else str(d)
            if v in st["done"]:
                fc[v] = BLUE
            elif d is not None:
                fc[v], lcol[v] = "#e7f4fb", INK
        if st["settled"]:
            fc[st["settled"]] = ORANGE
        for v, p in st["parent"].items():
            if p is not None:
                ecol[(p, v)] = BLUE if v in st["done"] else "#7cc3ea"
                elw[(p, v)] = 3.2
        for u, v in st["relaxed"]:
            ecol[(u, v)], elw[(u, v)] = ORANGE, 3.4
        draw_graph(ax, D_POS, D_EDGES, labels=lab, node_fc=fc, edge_col=ecol, edge_lw=elw, label_col=lcol)
        for v, (x, y) in D_POS.items():
            ax.text(x, y + 0.42 if y > 1.5 or v in ("s", "c", "t") else y - 0.42, v, ha="center",
                    va="bottom" if (y > 1.5 or v in ("s", "c", "t")) else "top", fontsize=15, color=INK,
                    fontstyle="italic")
        ax.set_xlim(-0.5, 6.1)
        ax.set_ylim(-0.75, 2.75)
        save(fig, f"dijkstra-step-{k}.svg")
    order = [st["settled"] for st in steps[1:]]
    final = steps[-1]
    print("== Dijkstra example: settle order", " ".join(order))
    print("   distances", {v: final["dist"][v] for v in D_POS}, "; path to t:", "-".join(path_to(final["parent"], "t")))
    for st in steps[1:]:
        print(f"   settle {st['settled']}: tentative", {v: st['dist'][v] for v in D_POS if v in st['dist']})
    return steps


# ---------------------------------------------------------------- 2) A* vs Dijkstra
A_POS = {"s": (0, 0), "u1": (1.5, 1.2), "u2": (3.0, 1.2), "t": (4.5, 0), "l1": (1.5, -1.2), "l2": (3.0, -1.2)}
A_EDGES = {("s", "u1"): 2, ("u1", "u2"): 2, ("u2", "t"): 2, ("s", "l1"): 1, ("l1", "l2"): 2, ("l2", "t"): 6}
A_H = {"s": 5, "u1": 3, "u2": 1, "t": 0, "l1": 6, "l2": 4}


def check_potential(adj, h, t):
    dist_t = {}
    for v in adj:
        st = dijkstra_trace(adj, v, target=t)
        dist_t[v] = st[-1]["dist"][t]
    consistent = all(h[u] <= w + h[v] for u in adj for v, w in adj[u].items())
    admissible = all(h[v] <= dist_t[v] for v in adj)
    return consistent, admissible, dist_t


def fig_astar():
    adj = adjacency(A_EDGES)
    cons, adm, dist_t = check_potential(adj, A_H, "t")
    res = {}
    for name, h in [("astar-dijkstra.svg", None), ("astar.svg", A_H)]:
        steps = dijkstra_trace(adj, "s", target="t", h=h)
        done = steps[-1]["done"]
        res[name] = done
        fig, ax = plt.subplots(figsize=(6.4, 4.4))
        fc = {v: BLUE for v in done}
        ecol, elw = {}, {}
        p = path_to(steps[-1]["parent"], "t")
        for u, v in zip(p, p[1:]):
            ecol[(u, v)], elw[(u, v)] = ORANGE, 3.6
        lab = {v: (str(steps[-1]["dist"][v]) if v in done else "") for v in A_POS}
        draw_graph(ax, A_POS, A_EDGES, labels=lab, node_fc=fc, edge_col=ecol, edge_lw=elw)
        for v, (x, y) in A_POS.items():
            above = y >= 0
            txt = v.replace("u1", "$u_1$").replace("u2", "$u_2$").replace("l1", "$\\ell_1$").replace(
                "l2", "$\\ell_2$")
            if v in ("s", "t"):
                txt = f"${v}$"
            ax.text(x, y + 0.38 if above else y - 0.38, txt, ha="center", va="bottom" if above else "top",
                    fontsize=15, color=INK)
            if h:
                hx, hy, ha = {"s": (-0.38, 0, "right"), "t": (0.38, 0, "left")}.get(v, (0, -0.42 if above else 0.42, "center"))
                ax.text(x + hx, y + hy, f"h={A_H[v]}", ha=ha, va="center", fontsize=13, color=ORANGE)
        ax.text(2.25, -2.15, f"{'A*' if h else 'Dijkstra'}: {len(done)} of {len(A_POS)} nodes settled",
                ha="center", va="center", fontsize=15, color=INK, fontweight="bold")
        ax.set_xlim(-1.1, 5.6)
        ax.set_ylim(-2.45, 2.0)
        save(fig, name)
    print(f"== A* example: h consistent {cons}, admissible {adm}; exact distances to t {dist_t}")
    print(f"   Dijkstra settles {res['astar-dijkstra.svg']}, A* settles {res['astar.svg']}")
    return res


# ---------------------------------------------------------------- 3) schematic search spaces
def fig_search_spaces():
    fig, axs = plt.subplots(1, 4, figsize=(12.4, 3.4))
    s, t = np.array([0.0, 0.0]), np.array([2.0, 0.0])
    titles = ["Dijkstra", "bidirectional", "A*", "contraction hierarchies"]
    for ax, title in zip(axs, titles):
        ax.set_xlim(-2.35, 4.35)
        ax.set_ylim(-2.95, 3.0)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=15, color=INK, pad=4)
    axs[0].add_patch(mpatches.Circle(s, 2.0, fc="#cfe9f6", ec=BLUE, lw=1.6))
    axs[1].add_patch(mpatches.Circle(s, 1.0, fc="#cfe9f6", ec=BLUE, lw=1.6))
    axs[1].add_patch(mpatches.Circle(t, 1.0, fc="#fbe0c6", ec=ORANGE, lw=1.6))
    axs[2].add_patch(mpatches.Ellipse((1.0, 0), 2.6, 1.25, fc="#cfe9f6", ec=BLUE, lw=1.6))
    axs[3].add_patch(mpatches.Polygon([(-0.45, 0), (0.45, 0), (1.0, 1.6)], closed=True, fc="#cfe9f6", ec=BLUE, lw=1.4))
    axs[3].add_patch(mpatches.Polygon([(1.55, 0), (2.45, 0), (1.0, 1.6)], closed=True, fc="#fbe0c6", ec=ORANGE, lw=1.4))
    for ax in axs:
        for p, name in [(s, "$s$"), (t, "$t$")]:
            ax.plot(*p, "o", ms=7, color=INK, zorder=5)
            ax.text(p[0], p[1] - 0.32, name, ha="center", va="top", fontsize=15, color=INK)
    axs[3].plot(1.0, 1.6, "o", ms=8, color=RED, zorder=6)
    axs[3].text(1.3, 1.75, "meet at the\nhighest node", ha="left", va="bottom", fontsize=12.5, color=RED)
    axs[0].text(1.0, -2.2, "area $\\sim r^2$", ha="center", va="top", fontsize=13, color=GREY)
    axs[1].text(1.0, -2.2, "$2\\cdot(r/2)^2 = r^2/2$", ha="center", va="top", fontsize=13, color=GREY)
    axs[2].text(1.0, -2.2, "towards $t$", ha="center", va="top", fontsize=13, color=GREY)
    axs[3].text(1.0, -2.2, "only upwards", ha="center", va="top", fontsize=13, color=GREY)
    fig.tight_layout(w_pad=0.5)
    save(fig, "search-spaces.svg")


# ---------------------------------------------------------------- 4) contraction hierarchies
C_POS = {0: (0, 0), 1: (1.4, 0), 2: (2.8, 0), 3: (4.2, 0), 4: (5.6, 0), 5: (1.4, 1.25), 6: (4.2, -1.25)}
C_EDGES = {(0, 1): 2, (1, 2): 2, (2, 3): 2, (3, 4): 2, (0, 5): 3, (5, 2): 3, (2, 6): 2, (6, 4): 3}
C_ORDER = [1, 5, 3, 6, 0, 4, 2]           # contraction order: least important first
C_NAME = {0: "s", 1: "a", 2: "m", 3: "b", 4: "t", 5: "x", 6: "y"}


def witness(adj, u, w, banned, limit):
    dist, pq, done = {u: 0}, [(0, u)], set()
    while pq:
        d, x = heapq.heappop(pq)
        if x in done or d > limit:
            continue
        done.add(x)
        if x == w:
            return d
        for y, c in adj[x].items():
            if y in banned:
                continue
            if d + c < dist.get(y, np.inf):
                dist[y] = d + c
                heapq.heappush(pq, (d + c, y))
    return None


def build_ch(edges, order):
    adj = adjacency(edges)
    removed, shortcuts, log = set(), {}, []
    for v in order:
        nb = sorted(u for u in adj[v] if u not in removed)
        for u, w in itertools.combinations(nb, 2):
            via = adj[v][u] + adj[v][w]
            wd = witness(adj, u, w, removed | {v}, via)
            log.append((v, u, w, via, wd))
            if wd is None or wd > via:
                if via < adj[u].get(w, np.inf):
                    adj[u][w] = adj[w][u] = via
                    shortcuts[(u, w)] = (via, v)
        removed.add(v)
    return adj, shortcuts, log


def fig_ch():
    adj, shortcuts, log = build_ch(C_EDGES, C_ORDER)
    rank = {v: k for k, v in enumerate(C_ORDER)}
    print("== CH example: order", " ".join(C_NAME[v] for v in C_ORDER))
    for v, u, w, via, wd in log:
        print(f"   contract {C_NAME[v]}: {C_NAME[u]}-{C_NAME[w]} via {C_NAME[v]} = {via}, "
              f"witness {'none' if wd is None else wd} -> {'shortcut' if (wd is None or wd > via) else 'no shortcut'}")
    print("   shortcuts:", {f"{C_NAME[u]}-{C_NAME[w]}": f"{d} (via {C_NAME[m]})" for (u, w), (d, m) in shortcuts.items()})
    # frames: contract the first four nodes one by one
    frames = [[]] + [C_ORDER[:k] for k in range(1, 5)]
    for k, gone in enumerate(frames):
        fig, ax = plt.subplots(figsize=(7.4, 3.6))
        edges = dict(C_EDGES)
        sc_now = {e: d for e, (d, m) in shortcuts.items() if m in gone}
        ecol, elw = {}, {}
        for e in list(edges):
            if e[0] in gone or e[1] in gone:
                ecol[e] = LIGHT
        all_edges = dict(edges)
        for (u, w), d in sc_now.items():
            all_edges[(u, w)] = d
            ecol[(u, w)], elw[(u, w)] = ORANGE, 3.0
        fc = {v: (LIGHT if v in gone else WHITE) for v in C_POS}
        ec = {v: (GREY if v in gone else INK) for v in C_POS}
        if gone:
            fc[gone[-1]], ec[gone[-1]] = ORANGE, ORANGE
        lab = {v: C_NAME[v] for v in C_POS}
        lcol = {v: (WHITE if (gone and v == gone[-1]) else (GREY if v in gone else INK)) for v in C_POS}
        curved = {(0, 2): 0.42, (2, 4): -0.42}
        draw_graph(ax, C_POS, all_edges, labels=lab, node_fc=fc, node_ec=ec, edge_col=ecol, edge_lw=elw,
                   label_col=lcol, curved=curved)
        msg = ["the network", "contract a: shortcut s–m (4), no other path ≤ 4",
               "contract x: s–m via x is 6, witness s–m (4): no shortcut",
               "contract b: shortcut m–t (4), detour via y is 5",
               "contract y: m–t via y is 5, witness m–t (4): no shortcut"][k]
        ax.text(2.8, -2.2, msg, ha="center", va="center", fontsize=14.5, color=INK)
        ax.set_xlim(-0.5, 6.1)
        ax.set_ylim(-2.5, 2.3)
        save(fig, f"ch-contract-{k}.svg")
    # hierarchy view with the query: x = position along the road, y = contraction order
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    hx = {0: 0.0, 1: 1.4, 2: 2.8, 3: 4.2, 4: 5.6, 5: 1.0, 6: 4.6}
    hpos = {v: (hx[v], 0.8 * rank[v]) for v in C_POS}
    edges = dict(C_EDGES)
    edges.update({e: d for e, (d, m) in shortcuts.items()})
    ecol = {e: LIGHT for e in edges}
    elw = {}
    ecol[(0, 2)], elw[(0, 2)] = BLUE, 3.4
    ecol[(2, 4)], elw[(2, 4)] = ORANGE, 3.4
    fc = {v: WHITE for v in C_POS}
    fc[0], fc[4], fc[2] = BLUE, ORANGE, RED
    lab = {v: C_NAME[v] for v in C_POS}
    lcol = {v: INK for v in C_POS}
    lcol[0] = lcol[4] = lcol[2] = WHITE
    draw_graph(ax, hpos, edges, labels=lab, node_fc=fc, edge_col=ecol, edge_lw=elw, label_col=lcol,
               weights=False)
    for (u, w), col in [((0, 2), BLUE), ((2, 4), ORANGE)]:
        (x0, y0), (x1, y1) = hpos[u], hpos[w]
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.25, "4", ha="center", va="bottom", fontsize=14, color=col,
                fontweight="bold")
    ax.annotate("", xy=(-0.9, 4.9), xytext=(-0.9, 0.0), arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.4))
    ax.text(-1.05, 2.45, "contraction order", rotation=90, ha="right", va="center", fontsize=13, color=GREY)
    ax.set_xlim(-1.6, 6.1)
    ax.set_ylim(-0.45, 5.3)
    save(fig, "ch-query.svg")
    return shortcuts


# ---------------------------------------------------------------- 5) exercise: contract v
X_POS = {"v": (1.5, 1.0), "a": (0, 2.0), "b": (3.0, 2.0), "c": (1.5, -0.6)}
X_EDGES = {("v", "a"): 2, ("v", "b"): 3, ("v", "c"): 4, ("a", "b"): 4, ("b", "c"): 8}


def fig_exercise():
    adj = adjacency(X_EDGES)
    res = []
    for u, w in itertools.combinations(["a", "b", "c"], 2):
        via = adj["v"][u] + adj["v"][w]
        wd = witness(adj, u, w, {"v"}, via)
        res.append((u, w, via, wd))
    print("== CH exercise: contract v")
    for u, w, via, wd in res:
        print(f"   {u}-{w}: via v {via}, witness {wd} -> {'shortcut' if (wd is None or wd > via) else 'no shortcut'}")
    for solution in (False, True):
        fig, ax = plt.subplots(figsize=(4.6, 3.9))
        ecol = {e: LIGHT for e in X_EDGES if "v" in e} if solution else {}
        fc = {"v": (LIGHT if solution else ORANGE)}
        lab = {x: x for x in X_POS}
        lcol = {x: INK for x in X_POS}
        lcol["v"] = GREY if solution else WHITE
        draw_graph(ax, X_POS, X_EDGES, labels=lab, node_fc=fc, edge_col=ecol, label_col=lcol,
                   wpos={("b", "c"): -0.22})
        if solution:                                  # shortcuts drawn on top, curved outwards
            for u, w, via, wd in res:
                if wd is not None and wd <= via:
                    continue
                (x0, y0), (x1, y1) = X_POS[u], X_POS[w]
                rad = 0.45 if (u, w) == ("a", "c") else -0.4
                ax.add_patch(mpatches.FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-",
                                                      connectionstyle=f"arc3,rad={rad}", color=ORANGE, lw=3.0,
                                                      zorder=2, shrinkA=0, shrinkB=0))
                mx = (x0 + x1) / 2 + 0.5 * rad * (y1 - y0) * 1.25
                my = (y0 + y1) / 2 - 0.5 * rad * (x1 - x0) * 1.25
                ax.text(mx, my, str(via), ha="center", va="center", fontsize=14, color=ORANGE, fontweight="bold",
                        zorder=4, bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.9))
        ax.set_xlim(-0.8, 3.8)
        ax.set_ylim(-1.1, 2.6)
        save(fig, "ch-exercise-solution.svg" if solution else "ch-exercise.svg")
    return res


# ---------------------------------------------------------------- main
fig_dijkstra()
fig_astar()
fig_search_spaces()
fig_ch()
fig_exercise()
