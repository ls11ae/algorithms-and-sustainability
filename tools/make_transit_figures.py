"""Figures for "Algorithms and Sustainability", lecture 6, part B: public transit (own work, CC BY 4.0).

Usage:  python3 tools/make_transit_figures.py lectures/figures
A small constructed timetable around TU Dortmund. The stop names are real, the network is simplified and
all times are invented for the example.

Writes:
  transit-terms.svg        the example network: stops, routes, trips, change times
  transit-graphs.svg       time-expanded and time-dependent model of a part of the example
  csa-step-0..5.svg        Connection Scan Algorithm, earliest arrival from Campus Süd (7:50) to Essen Hbf
  raptor-round-0..3.svg    RAPTOR on the same query, round by round (lecture 7)
  tb-transfers.svg         Trip-Based routing: trips reached with 1, 2, 3 trips and the transfers between them
and prints the connections and the CSA trace.
Needs: matplotlib, numpy. Font as in make_figures.py (LATO_DIR).
"""
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
                     "svg.hashsalt": "aus-2627-transit", "mathtext.fontset": "custom",
                     "mathtext.it": f"{FAMILY}:italic", "mathtext.rm": FAMILY, "mathtext.bf": f"{FAMILY}:bold",
                     "mathtext.cal": f"{FAMILY}:italic", "mathtext.sf": FAMILY, "mathtext.tt": FAMILY})
INK, GREY, LIGHT = "#282a2e", "#8e908c", "#d9d9d6"
BLUE, ORANGE, RED, GREEN, PURPLE = "#0A97D9", "#E8700A", "#DD1367", "#3F7E44", "#6250d6"
WHITE, PALEBLUE, PALEGREEN, PALERED = "#ffffff", "#e7f4fb", "#e3efe4", "#f8e0ea"


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


def hm(t):
    return f"{t // 60}:{t % 60:02d}"


def T(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


# ---------------------------------------------------------------- the example timetable
# stop id: name, schematic position, minimum change time (min)
STOPS = {"CS": ("Campus Süd", (6.2, 0.0), 0), "UNI": ("Dortmund Universität", (6.2, 1.5), 2),
         "DO": ("Dortmund Hbf", (8.6, 2.6), 5), "BO": ("Bochum Hbf", (2.6, 2.2), 4), "E": ("Essen Hbf", (-1.2, 1.5), 4)}
# trip id, line, colour, [(stop, arrival, departure)]
TRIPS = [
    ("H", "H-Bahn", ORANGE, [("CS", None, "7:56"), ("UNI", "8:00", None)]),
    ("S1a", "S1", BLUE, [("DO", None, "7:52"), ("UNI", "8:01", "8:01"), ("BO", "8:20", "8:20"), ("E", "8:41", None)]),
    ("S1b", "S1", BLUE, [("BO", None, "7:45"), ("UNI", "8:04", "8:04"), ("DO", "8:12", None)]),
    ("S1c", "S1", BLUE, [("DO", None, "8:12"), ("UNI", "8:21", "8:21"), ("BO", "8:40", "8:40"), ("E", "9:01", None)]),
    ("REa", "RE", RED, [("DO", None, "8:09"), ("BO", "8:19", "8:19"), ("E", "8:31", None)]),
    ("REb", "RE", RED, [("DO", None, "8:17"), ("BO", "8:27", "8:27"), ("E", "8:39", None)]),
]
TRIP_COL = {t[0]: t[2] for t in TRIPS}
TRIP_LINE = {t[0]: t[1] for t in TRIPS}
SOURCE, START, TARGET = "CS", T("7:50"), "E"


def connections():
    conns = []
    for tid, line, col, stops in TRIPS:
        for (a, _, dep), (b, arr, _) in zip(stops, stops[1:]):
            conns.append(dict(trip=tid, dep_stop=a, arr_stop=b, dep=T(dep), arr=T(arr)))
    conns.sort(key=lambda c: (c["dep"], c["arr"]))
    return conns


def csa(conns, source, start, target):
    """Earliest-arrival Connection Scan (Dibbelt et al. 2018) with minimum change times at stops.
    At the source no change time is needed. Returns the trace (one entry per scanned connection)."""
    d = {s: None for s in STOPS}
    d[source] = start
    reached, enter, trace = set(), {}, []
    for i, c in enumerate(conns):
        if d[target] is not None and c["dep"] >= d[target]:
            trace.append(dict(i=i, status="stop", d=dict(d), reached=set(reached)))
            break
        a = c["dep_stop"]
        change = 0 if a == source else STOPS[a][2]
        boardable = d[a] is not None and d[a] + change <= c["dep"]
        if c["trip"] in reached or boardable:
            if c["trip"] not in reached:
                enter[c["trip"]] = c
            reached.add(c["trip"])
            b = c["arr_stop"]
            improved = d[b] is None or c["arr"] < d[b]
            if improved:
                d[b] = c["arr"]
            status = "improves" if improved else "reached, no improvement"
        else:
            status = "not reachable"
        trace.append(dict(i=i, status=status, d=dict(d), reached=set(reached)))
    return trace, d


# ---------------------------------------------------------------- 1) network and terms
def fig_terms():
    fig, ax = plt.subplots(figsize=(10.4, 3.9))
    lines = [("S1", BLUE, [STOPS[s][1] for s in ["DO", "UNI", "BO", "E"]]),
             ("RE", RED, [(8.6, 2.6), (6.0, 3.15), (2.6, 2.2), (-1.2, 1.5)]),
             ("H-Bahn", ORANGE, [STOPS[s][1] for s in ["CS", "UNI"]])]
    for name, col, pts in lines:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, lw=6, solid_capstyle="round", zorder=1)
    ax.text(7.6, 1.6, "S1", color=BLUE, fontsize=19, fontweight="bold", va="top")
    ax.text(5.75, 3.35, "RE", color=RED, fontsize=19, fontweight="bold")
    ax.text(6.45, 0.6, "H-Bahn", color=ORANGE, fontsize=19, fontweight="bold")
    place = {"CS": (6.2, -0.3, "center", "top"), "UNI": (5.9, 1.25, "right", "top"),
             "DO": (8.6, 2.95, "center", "bottom"), "BO": (2.6, 2.55, "center", "bottom"),
             "E": (-1.2, 1.15, "center", "top")}
    for sid, (name, (x, y), ch) in STOPS.items():
        ax.add_patch(mpatches.Circle((x, y), 0.19, fc=WHITE, ec=INK, lw=2.2, zorder=3))
        tx, ty, ha, va = place[sid]
        ax.text(tx, ty, name, ha=ha, va=va, fontsize=17, color=INK, zorder=4)
        if ch:
            ax.text(tx, ty + (-0.55 if va == "top" else 0.55), f"change {ch} min", ha=ha, va=va, fontsize=14,
                    color=GREY, zorder=4)
    ax.annotate("connection: S1 dep. 8:04 Universität,\narr. 8:12 Dortmund Hbf", xy=(7.75, 2.2),
                xytext=(9.0, 0.75), fontsize=15, color=INK, ha="left", va="center",
                arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.4))
    ax.set_xlim(-2.6, 13.6)
    ax.set_ylim(-1.2, 4.0)
    ax.set_aspect("equal")
    ax.axis("off")
    save(fig, "transit-terms.svg")


# ---------------------------------------------------------------- 2) time-expanded and time-dependent
def fig_graphs():
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.4, 4.6), gridspec_kw=dict(width_ratios=[1.1, 1]))
    col = {"UNI": 0.0, "DO": 2.4, "BO": 4.8}
    sel = [("S1b", "UNI", "DO", "8:04", "8:12"), ("REa", "DO", "BO", "8:09", "8:19"),
           ("REb", "DO", "BO", "8:17", "8:27")]
    y = lambda t: -(T(t) - T("8:00")) / 3.0
    names = {"UNI": "Universität", "DO": "DO Hbf", "BO": "BO Hbf"}
    for sid, x in col.items():
        ax.plot([x, x], [y("7:59"), y("8:30")], color=LIGHT, lw=1.4, zorder=0)
        ax.text(x, y("7:59") + 0.3, names[sid], ha="center", va="bottom", fontsize=15, color=INK)
    events = {}
    for tid, a, b, dep, arr in sel:
        x0, x1 = col[a], col[b]
        ax.annotate("", xy=(x1, y(arr)), xytext=(x0, y(dep)),
                    arrowprops=dict(arrowstyle="-|>", color=TRIP_COL[tid], lw=2.6, shrinkA=6, shrinkB=6))
        ang = np.degrees(np.arctan2(y(arr) - y(dep), x1 - x0))
        ax.text((x0 + x1) / 2 + 0.1, (y(dep) + y(arr)) / 2 + 0.15, TRIP_LINE[tid], ha="center", va="bottom",
                fontsize=14, color=TRIP_COL[tid], rotation=ang, rotation_mode="anchor")
        events.setdefault(a, set()).add(dep)
        events.setdefault(b, set()).add(arr)
    for sid, ts in events.items():
        ts = sorted(ts, key=T)
        for t in ts:
            ax.plot(col[sid], y(t), "o", ms=8, color=INK, zorder=4)
            arriving = any(b == sid and arr == t for _, a, b, dep, arr in sel)
            if sid == "BO":
                ax.text(col[sid] + 0.16, y(t), t, ha="left", va="center", fontsize=13.5, color=GREY)
            elif arriving:
                ax.text(col[sid] - 0.14, y(t) - 0.14, t, ha="right", va="top", fontsize=13.5, color=GREY)
            else:
                ax.text(col[sid] - 0.16, y(t), t, ha="right", va="center", fontsize=13.5, color=GREY)
        for t0, t1 in zip(ts, ts[1:]):
            ax.annotate("", xy=(col[sid], y(t1)), xytext=(col[sid], y(t0)),
                        arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.4, shrinkA=5, shrinkB=5))
    ax.text(2.4, y("8:30") - 0.2, "node = event; waiting downwards", ha="center", va="top", fontsize=14,
            color=GREY)
    ax.set_title("time-expanded", fontsize=17, color=INK, pad=6)
    ax.set_xlim(-1.2, 5.9)
    ax.set_ylim(y("8:30") - 1.0, y("7:59") + 1.1)
    ax.axis("off")
    ts = np.arange(T("8:00"), T("8:30") + 0.01, 0.25)
    dep_times = [T("8:09"), T("8:17"), T("8:29")]
    arr_times = [T("8:19"), T("8:27"), T("8:39")]

    def arrival(t):
        for dpt, a in zip(dep_times, arr_times):
            if t <= dpt:
                return a
        return np.nan
    bx.plot(ts - T("8:00"), [arrival(t) - T("8:00") for t in ts], color=RED, lw=2.8, drawstyle="steps-post")
    for dpt, a in zip(dep_times, arr_times):
        bx.plot(dpt - T("8:00"), a - T("8:00"), "o", ms=7, color=RED)
    bx.set_xlabel("depart DO Hbf (min after 8:00)", fontsize=15, color=INK)
    bx.set_ylabel("arrive BO Hbf (min after 8:00)", fontsize=15, color=INK)
    bx.set_title("time-dependent: edge DO Hbf to BO Hbf", fontsize=17, color=INK, pad=6)
    bx.set_xlim(0, 30)
    bx.set_ylim(10, 42)
    bx.set_xticks([0, 10, 20, 30])
    bx.set_yticks([10, 20, 30, 40])
    for sp in ("top", "right"):
        bx.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        bx.spines[sp].set_color(GREY)
    bx.tick_params(colors=GREY, labelsize=13.5)
    bx.text(1.0, 41.0, "later departure never\narrives earlier (FIFO)", fontsize=14.5, color=INK, va="top")
    fig.tight_layout(w_pad=2.0)
    save(fig, "transit-graphs.svg")


# ---------------------------------------------------------------- 3) Connection Scan, step by step
SHORT = {"CS": "Campus Süd", "UNI": "Universität", "DO": "Dortmund Hbf", "BO": "Bochum Hbf", "E": "Essen Hbf"}


def fig_csa():
    conns = connections()
    trace, d = csa(conns, SOURCE, START, TARGET)
    print("== CSA example: connections sorted by departure")
    for i, c in enumerate(conns, 1):
        print(f"   {i:2d} {hm(c['dep'])} {STOPS[c['dep_stop']][0]:22s} -> {hm(c['arr'])} {STOPS[c['arr_stop']][0]:22s} "
              f"{c['trip']}")
    for e in trace:
        print(f"   row {e['i'] + 1:2d}: {e['status']:24s} arrivals",
              {STOPS[s][0]: (hm(t) if t is not None else '-') for s, t in e['d'].items()})
    print("   earliest arrival at", STOPS[TARGET][0], hm(d[TARGET]))
    shown = [0, 3, 5, 8, 11, len(trace)]
    msgs = {0: "start: Campus Süd at 7:50; scan the connections by departure time",
            3: "rows 1–2: stop not reached yet; row 3: H-Bahn, Universität at 8:00",
            5: "row 4: S1 at 8:01 too early (8:00 + 2 min change); row 5: Dortmund Hbf at 8:12",
            8: "rows 6–7 too early (8:12 + 5 min change); row 8: RE, Bochum Hbf at 8:27",
            11: "rows 9–10 too early (8:27 + 4); row 11: S1 reached, Bochum stays 8:27",
            len(trace): "row 12: in the RE, Essen at 8:39; row 13 leaves 8:40 ≥ 8:39: stop"}
    fs = 15.5
    for idx, k in enumerate(shown):
        st = trace[k - 1] if k else dict(d={s: (START if s == SOURCE else None) for s in STOPS}, reached=set())
        fig = plt.figure(figsize=(10.4, 6.0))
        ax = fig.add_axes([0.0, 0.09, 0.66, 0.91])
        bx = fig.add_axes([0.68, 0.09, 0.32, 0.91])
        n = len(conns)
        heads = ["", "dep.", "from", "to", "arr.", "trip"]
        xs = [0.15, 0.85, 2.15, 4.75, 7.3, 8.4]
        W = 9.9
        for x, h in zip(xs, heads):
            ax.text(x, 0.75, h, fontsize=fs - 1.5, color=GREY, ha="left", va="center", fontweight="bold")
        for i, c in enumerate(conns):
            yy = -i
            status = None
            for e in trace[:k]:
                if e["i"] == i:
                    status = e["status"]
            fc = {"improves": PALEGREEN, "reached, no improvement": PALEGREEN, "not reachable": "#f2f2f1",
                  "stop": PALERED}.get(status)
            if fc:
                ax.add_patch(mpatches.Rectangle((0.0, yy - 0.46), W, 0.92, fc=fc, ec="none", zorder=0))
            if idx and i == trace[k - 1]["i"]:
                ax.add_patch(mpatches.Rectangle((0.0, yy - 0.46), W, 0.92, fc="none", ec=ORANGE, lw=2.4, zorder=1))
            col = GREY if status == "not reachable" else INK
            trip = "H-Bahn" if c["trip"] == "H" else TRIP_LINE[c["trip"]] + " " + c["trip"][-1]
            vals = [str(i + 1), hm(c["dep"]), SHORT[c["dep_stop"]], SHORT[c["arr_stop"]], hm(c["arr"]), trip]
            for j, (x, v) in enumerate(zip(xs, vals)):
                ax.text(x, yy, v, fontsize=fs, color=TRIP_COL[c["trip"]] if j == 5 else col, ha="left",
                        va="center")
        ax.set_xlim(0, 10.0)
        ax.set_ylim(-(n - 1) - 0.6, 1.2)
        ax.axis("off")
        bx.text(0.0, 0.75, "earliest arrival", fontsize=fs - 1.5, color=GREY, fontweight="bold", va="center")
        for j, sid in enumerate(["CS", "UNI", "DO", "BO", "E"]):
            yy = -j * 1.3
            t = st["d"][sid]
            prev_k = shown[idx - 1] if idx > 0 else 0          # compare with the previous frame, not the previous row
            prev = trace[prev_k - 1]["d"][sid] if prev_k else (START if sid == SOURCE else None)
            changed = idx > 0 and t != prev
            bx.text(0.0, yy, SHORT[sid], fontsize=fs, color=INK, va="center")
            bx.text(5.6, yy, hm(t) if t is not None else "∞", fontsize=fs + 1, va="center", ha="right",
                    color=ORANGE if changed else (BLUE if t is not None else GREY), fontweight="bold")
        yy = -5 * 1.3 - 0.3
        bx.text(0.0, yy, "trips reached", fontsize=fs - 1.5, color=GREY, fontweight="bold", va="center")
        names = [("H-Bahn" if r == "H" else f"{TRIP_LINE[r]} {r[-1]}") for r in sorted(st["reached"])]
        for j, nm in enumerate(names or ["none"]):
            bx.text(0.0 + 2.9 * (j % 2), yy - 1.1 - 1.0 * (j // 2), nm, fontsize=fs, va="center",
                    color=INK if names else GREY)
        bx.set_xlim(0, 6.0)
        bx.set_ylim(-(n - 1) - 0.6, 1.2)
        bx.axis("off")
        fig.text(0.01, 0.035, msgs[k], fontsize=fs + 0.5, color=INK, ha="left", va="center")
        save(fig, f"csa-step-{idx}.svg")
    return conns, trace, d


# ---------------------------------------------------------------- 4) RAPTOR, round by round (lecture 7)
def routes_of(trips):
    """Group trips with the same stop sequence into routes; trips of a route sorted by departure."""
    routes = {}
    for tid, line, col, stops in trips:
        key = (line, tuple(s for s, _, _ in stops))
        routes.setdefault(key, []).append((tid, {s: (T(a) if a else None, T(d) if d else None)
                                                 for s, a, d in stops}))
    for key in routes:
        routes[key].sort(key=lambda x: x[1][key[1][0]][1])
    return routes


def raptor(source, start, target, rounds=6):
    routes = routes_of(TRIPS)
    tau = [{s: None for s in STOPS}]
    tau[0][source] = start
    best = dict(tau[0])
    marked = {source}
    log = []
    for k in range(1, rounds + 1):
        tau.append(dict(tau[k - 1]))
        newly, boarded = {}, []
        queue = {}
        for (line, seq), trips in routes.items():
            idx = [i for i, p in enumerate(seq) if p in marked]
            if idx:
                queue[(line, seq)] = min(idx)
        marked = set()
        for (line, seq), i0 in queue.items():
            trips = routes[(line, seq)]
            cur, enter = None, None
            for i in range(i0, len(seq)):
                p = seq[i]
                if cur is not None:
                    arr = trips[cur][1][p][0]
                    bound = min(x for x in (best[p], best[target]) if x is not None) if (best[p] or best[target]) else None
                    if arr is not None and (bound is None or arr < bound):
                        tau[k][p] = arr
                        best[p] = arr
                        marked.add(p)
                        newly[p] = (arr, trips[cur][0], enter)
                if tau[k - 1][p] is not None and i < len(seq) - 1:
                    ready = tau[k - 1][p] + (0 if p == source else STOPS[p][2])
                    for j, (tid, times) in enumerate(trips):
                        dep = times[p][1]
                        if dep is not None and dep >= ready:
                            if cur is None or dep < trips[cur][1][p][1]:
                                cur, enter = j, p
                                boarded.append((trips[j][0], p, dep))
                            break
        log.append(dict(k=k, routes=list(queue), improved=newly, boarded=boarded, marked=set(marked)))
        if not marked:
            break
    return tau, log


def fig_raptor():
    tau, log = raptor(SOURCE, START, TARGET)
    print("== RAPTOR example: Campus Süd 7:50 to Essen Hbf")
    for e in log:
        print(f"   round {e['k']}: routes scanned", [f"{l} from {SHORT[seq[0]]}" for l, seq in e['routes']],
              "; boarded", [(t, SHORT[p], hm(d)) for t, p, d in e['boarded']],
              "; improved", {SHORT[p]: (hm(a), t) for p, (a, t, _) in e['improved'].items()})
    print("   Pareto set at Essen Hbf:", [(k, hm(tau[k][TARGET])) for k in range(1, len(tau))
                                         if tau[k][TARGET] is not None and (k == 1 or tau[k][TARGET] != tau[k - 1][TARGET])])
    pos = {s: STOPS[s][1] for s in STOPS}
    segs = {"H": ["CS", "UNI"], "S1a": ["DO", "UNI", "BO", "E"], "S1b": ["BO", "UNI", "DO"],
            "S1c": ["DO", "UNI", "BO", "E"], "REa": ["DO", "BO", "E"], "REb": ["DO", "BO", "E"]}
    rel = {"RE": [(8.6, 2.6), (6.0, 3.15), (2.6, 2.2), (-1.2, 1.5)]}
    order = ["CS", "UNI", "DO", "BO", "E"]
    nr = 3
    for kk in range(0, nr + 1):
        fig = plt.figure(figsize=(11.6, 4.6))
        ax = fig.add_axes([0.0, 0.0, 0.6, 1.0])
        tx = fig.add_axes([0.62, 0.0, 0.38, 1.0])
        for name, col, pts in [("S1", BLUE, [pos[s] for s in ["DO", "UNI", "BO", "E"]]), ("RE", RED, rel["RE"]),
                               ("H-Bahn", ORANGE, [pos[s] for s in ["CS", "UNI"]])]:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=LIGHT, lw=6, solid_capstyle="round", zorder=1)
        if kk:
            e = log[kk - 1]
            for p, (arr, tid, enter) in e["improved"].items():
                seq = segs[tid]
                if tid.startswith("RE"):
                    pts = {"DO": (8.6, 2.6), "BO": (2.6, 2.2), "E": (-1.2, 1.5)}
                    path = [(8.6, 2.6), (6.0, 3.15), (2.6, 2.2), (-1.2, 1.5)]
                    i0 = 0 if enter == "DO" else (2 if enter == "BO" else 3)
                    i1 = 0 if p == "DO" else (2 if p == "BO" else 3)
                    xy = path[i0:i1 + 1]
                else:
                    i0, i1 = seq.index(enter), seq.index(p)
                    xy = [pos[s] for s in seq[i0:i1 + 1]]
                ax.plot([q[0] for q in xy], [q[1] for q in xy], color=TRIP_COL[tid], lw=6, solid_capstyle="round",
                        zorder=2)
        for sid, (x, y) in pos.items():
            imp = kk and sid in log[kk - 1]["improved"]
            ax.add_patch(mpatches.Circle((x, y), 0.19, fc=ORANGE if imp else WHITE, ec=INK, lw=2.2, zorder=3))
        place = {"CS": (6.2, -0.3, "center", "top"), "UNI": (5.9, 1.25, "right", "top"),
                 "DO": (8.6, 2.95, "center", "bottom"), "BO": (2.6, 2.55, "center", "bottom"),
                 "E": (-1.2, 1.15, "center", "top")}
        for sid, (tx0, ty0, ha, va) in place.items():
            ax.text(tx0, ty0, SHORT[sid], ha=ha, va=va, fontsize=16, color=INK, zorder=4)
        ax.set_xlim(-2.4, 9.6)
        ax.set_ylim(-1.0, 3.7)
        ax.set_aspect("equal")
        ax.axis("off")
        # table: arrival per round
        tx.text(0.0, 6.0, "arrival with ≤ k trips", fontsize=14, color=GREY, fontweight="bold", va="center")
        for j in range(nr + 1):
            tx.text(4.6 + 1.25 * j, 5.1, f"k = {j}", fontsize=14, color=INK if j == kk else GREY, ha="center",
                    va="center", fontweight="bold" if j == kk else "normal")
        if kk:
            tx.add_patch(mpatches.Rectangle((4.6 + 1.25 * kk - 0.6, -0.55), 1.2, 6.1, fc=PALEBLUE, ec="none", zorder=0))
        for r, sid in enumerate(order):
            yy = 4.1 - r * 1.0
            tx.text(0.0, yy, SHORT[sid], fontsize=15, color=INK, va="center")
            for j in range(min(kk, nr) + 1):
                t = tau[j][sid] if j < len(tau) else None
                prev = tau[j - 1][sid] if j else None
                if t is None:
                    txt, col = "–", GREY
                elif j and t == prev:
                    txt, col = hm(t), GREY
                else:
                    txt, col = hm(t), (ORANGE if j == kk else INK)
                tx.text(4.6 + 1.25 * j, yy, txt, fontsize=15, color=col, ha="center", va="center",
                        fontweight="bold" if (j == kk and col == ORANGE) else "normal")
        tx.set_xlim(0, 9.4)
        tx.set_ylim(-0.8, 6.4)
        tx.axis("off")
        save(fig, f"raptor-round-{kk}.svg")
    return tau, log


# ---------------------------------------------------------------- 5) Trip-Based routing: trips and transfers
def fig_tb():
    fig, ax = plt.subplots(figsize=(11.0, 4.3))
    X = [0.0, 5.4, 10.8]
    lv = {"H": (X[0], 1.0), "S1b": (X[1], 2.2), "S1c": (X[1], 0.2), "S1a": (X[1], -1.6), "REb": (X[2], 2.2),
          "REa": (X[2], 0.7)}
    lab = {"H": "H-Bahn\nCampus Süd 7:56", "S1b": "S1 b\nUniversität 8:04", "S1c": "S1 c\nUniversität 8:21",
           "REb": "RE b\nDortmund Hbf 8:17", "S1a": "S1 a\nUniversität 8:01", "REa": "RE a\nDortmund Hbf 8:09"}
    W, Hh = 2.75, 0.95
    for tid, (x, y) in lv.items():
        ok = tid not in ("S1a", "REa")
        ax.add_patch(mpatches.FancyBboxPatch((x - W / 2, y - Hh / 2), W, Hh, boxstyle="round,pad=0.05",
                                             fc=WHITE if ok else "#f2f2f1", ec=TRIP_COL[tid] if ok else LIGHT,
                                             lw=2.4 if ok else 1.4, zorder=2))
        ax.text(x, y, lab[tid], ha="center", va="center", fontsize=14, color=INK if ok else GREY, zorder=3,
                linespacing=1.2)
    arrows = [("H", "S1b", "8:00 + 2 ≤ 8:04", True, (-0.75, 0.3)),
              ("H", "S1c", "8:00 + 2 ≤ 8:21", True, (-0.75, -0.3)),
              ("S1b", "REb", "8:12 + 5 ≤ 8:17", True, (0.0, 0.2)),
              ("H", "S1a", "8:01: too early", False, (-0.6, -0.45)),
              ("S1b", "REa", "8:09: too early", False, (-0.7, -0.4))]
    for a, b, txt, ok, (dx, dy) in arrows:
        (x0, y0), (x1, y1) = lv[a], lv[b]
        ax.annotate("", xy=(x1 - W / 2 - 0.12, y1), xytext=(x0 + W / 2 + 0.12, y0),
                    arrowprops=dict(arrowstyle="-|>", color=INK if ok else LIGHT, lw=2.0 if ok else 1.4,
                                    ls="-" if ok else (0, (4, 3))))
        mx, my = (x0 + x1) / 2 + dx, (y0 + y1) / 2 + dy
        ax.text(mx, my, txt, ha="center", va="bottom" if dy > 0 else "top", fontsize=13.5,
                color=INK if ok else GREY)
    for x, t in zip(X, ["1 trip", "2 trips", "3 trips"]):
        ax.text(x, 3.3, t, ha="center", va="center", fontsize=15, color=GREY, fontweight="bold")
    ax.text(X[2] + W / 2 + 0.25, 2.2, "Essen\n8:39", ha="left", va="center", fontsize=15, color=RED,
            fontweight="bold")
    ax.text(X[1] + W / 2 + 0.25, 0.2, "Essen\n9:01", ha="left", va="center", fontsize=15, color=BLUE,
            fontweight="bold")
    ax.set_xlim(-1.7, 13.6)
    ax.set_ylim(-2.2, 3.55)
    ax.axis("off")
    save(fig, "tb-transfers.svg")


if __name__ == "__main__":
    fig_terms()
    fig_graphs()
    fig_csa()
    fig_raptor()
    fig_tb()
