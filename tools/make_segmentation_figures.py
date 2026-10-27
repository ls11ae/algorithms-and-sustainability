"""Figures for "Algorithms and Sustainability", lecture 4: segmentation (own work, CC BY 4.0).

Usage:  python3 tools/make_segmentation_figures.py <data folder> lectures/figures
Same data folder as tools/make_stork_figures.py (GPS data of Flack et al. 2016 from the Movebank
Data Repository, doi:10.5441/001/1.78152p3q, CC0; Natural Earth layers). The running example is
Eamy's first autumn migration (9 August to 10 October 2013), one position per day at 12:00 UTC.

Writes the figures of lecture 4 and prints every number quoted on the slides:
  greedy-speed.svg, greedy-speed-solution.svg      greedy segmentation, speed within a factor 2
  greedy-counterexample.svg                        minimum length and range: greedy gets stuck
  start-stop-diagram.svg, start-stop-diagram-dp.svg valid segments, values S, optimal staircase
  geese-overview.svg                               GPS tracks of the 65 geese of Kölzsch et al. (2016), spring
                                                   and autumn (Movebank, doi:10.5441/001/1.31c2v92f, CC0)
  storks-eamy-input.svg                            daily positions and daily distances
  storks-eamy-criteria.svg, ...-criteria-madrid.svg segmentation with the geese criteria
  storks-eamy-startstop.svg                        start-stop diagram of the running example
  storks-eamy-changepoints.svg                     optimal partitioning of the log daily distances
  storks-eamy-hmm-states.svg, ...-hmm-emissions.svg two-state hidden Markov model
  storks-eamy-methods.svg                          criteria, change points and HMM compared

Algorithms (all in this file): greedy segmentation for decreasing monotone criteria; longest valid
segment per start (two pointers); minimum segmentation by dynamic programming over valid segments
(start-stop diagram); smallest enclosing circle on the sphere; headings in an arc with outliers;
optimal partitioning with a penalty per segment (change points); hidden Markov model with Gaussian
emissions (Baum-Welch, Viterbi). Needs: matplotlib, numpy, pandas. Font as in make_figures.py
(LATO_DIR). Runs in about 10 seconds.
"""
import itertools
import os

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- reuse lecture 2's stork tools
_here = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(_here, "make_stork_figures.py"), encoding="utf-8").read()
_src = _src.split("# ---------------------------------------------------------------- main")[0]
exec(compile(_src, "make_stork_figures.py", "exec"))     # defines plt, laea, basemap, save, load_gps, ...

import matplotlib.patches as mpatches                   # noqa: E402
plt.rcParams.update({"mathtext.fontset": "custom", "mathtext.it": "LatoLatin:italic", "mathtext.rm": "LatoLatin",
                     "mathtext.bf": "LatoLatin:bold", "mathtext.cal": "LatoLatin:italic",
                     "mathtext.sf": "LatoLatin", "mathtext.tt": "LatoLatin"})

STOP, FLY = "#0A97D9", "#E8700A"                         # stopover, flight
COL = ["#0A97D9", "#E8700A", "#DD1367", "#3F7E44", "#6250d6"]


def save_opaque(fig, name):
    """As save(), but with a white background (figures stacked on one slide with fragments)."""
    plt.rcParams["savefig.transparent"] = False
    fig.patch.set_facecolor("white")
    save(fig, name)
    plt.rcParams["savefig.transparent"] = True


# ---------------------------------------------------------------- geometry on the sphere
def bearing(lat1, lon1, lat2, lon2):
    """Initial heading in radians, 0 = north, clockwise."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(lon2 - lon1)
    return np.arctan2(np.sin(dl) * np.cos(p2), np.cos(p1) * np.sin(p2) - np.sin(p1) * np.cos(p2) * np.cos(dl))


def aeqd(lat, lon, lat0, lon0):
    """Azimuthal equidistant projection in km: distances from (lat0, lon0) are exact."""
    p, lam = np.radians(lat), np.radians(lon)
    p0, l0 = np.radians(lat0), np.radians(lon0)
    c = np.arccos(np.clip(np.sin(p0) * np.sin(p) + np.cos(p0) * np.cos(p) * np.cos(lam - l0), -1, 1))
    k = np.where(c < 1e-12, 1.0, c / np.sin(np.maximum(c, 1e-12)))
    return (R_EARTH * k * np.cos(p) * np.sin(lam - l0),
            R_EARTH * k * (np.cos(p0) * np.sin(p) - np.sin(p0) * np.cos(p) * np.cos(lam - l0)))


def aeqd_inv(x, y, lat0, lon0):
    p0, l0 = np.radians(lat0), np.radians(lon0)
    rho = float(np.hypot(x, y))
    if rho < 1e-9:
        return lat0, lon0
    c = rho / R_EARTH
    p = np.arcsin(np.cos(c) * np.sin(p0) + y * np.sin(c) * np.cos(p0) / rho)
    lam = l0 + np.arctan2(x * np.sin(c), rho * np.cos(p0) * np.cos(c) - y * np.sin(p0) * np.sin(c))
    return float(np.degrees(p)), float((np.degrees(lam) + 540) % 360 - 180)


def _circle(pts):
    if len(pts) == 1:
        return pts[0], 0.0
    if len(pts) == 2:
        c = (pts[0] + pts[1]) / 2
        return c, float(np.hypot(*(pts[0] - c)))
    (ax, ay), (bx, by), (cx, cy) = pts
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return max((_circle([p, q]) for p, q in itertools.combinations(pts, 2)), key=lambda t: t[1])
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
    c = np.array([ux, uy])
    return c, float(np.hypot(*(pts[0] - c)))


def enclosing_circle(P):
    """Smallest enclosing circle (Welzl's algorithm, iterative)."""
    P = np.asarray(P, float)[np.random.default_rng(1).permutation(len(P))]
    c, r, eps = P[0], 0.0, 1e-7
    for i in range(1, len(P)):
        if np.hypot(*(P[i] - c)) > r + eps:
            c, r = P[i], 0.0
            for j in range(i):
                if np.hypot(*(P[j] - c)) > r + eps:
                    c, r = _circle([P[i], P[j]])
                    for k in range(j):
                        if np.hypot(*(P[k] - c)) > r + eps:
                            c, r = _circle([P[i], P[j], P[k]])
    return c, r


def enclosing_cap(lat, lon):
    """Smallest spherical cap containing the points ((lat, lon) of the centre, radius in km)."""
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    if len(lat) == 1:
        return (float(lat[0]), float(lon[0])), 0.0
    clat = float(np.mean(lat))
    clon = float(np.degrees(np.arctan2(np.sin(np.radians(lon)).mean(), np.cos(np.radians(lon)).mean())))
    for _ in range(10):
        c, _r = enclosing_circle(np.c_[aeqd(lat, lon, clat, clon)])
        clat, clon = aeqd_inv(c[0], c[1], clat, clon)
        if np.hypot(*c) < 0.01:
            break
    return (clat, clon), float(haversine(lat, lon, clat, clon).max())


# ---------------------------------------------------------------- segmentation algorithms
def greedy(values, ok):
    """Greedy segmentation for a decreasing monotone criterion ok(sequence) -> bool:
    extend the current segment as long as the criterion holds. Segments as (first, last) indices."""
    segs, i = [], 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and ok(values[i:j + 2]):
            j += 1
        segs.append((i, j))
        i = j + 1
    return segs


def longest_valid(n, ok_seg):
    """For a decreasing monotone criterion: for each start j the last end i with ok_seg(j, i).
    Two pointers; the end never moves back when the start advances (amortized O(n) tests)."""
    best, i = np.zeros(n, int), 0
    for j in range(n):
        i = max(i, j)
        while i + 1 < n and ok_seg(j, i + 1):
            i += 1
        best[j] = i
    return best


def min_segmentation(n, valid, score=None):
    """Fewest segments [j, i] (consecutive segments share the break point) that cover 0..n-1, each
    valid(j, i). Ties: largest total score(j, i). Dynamic programming over the start-stop diagram:
    S[i] = min over valid [j, i] of S[j] + 1. Returns a list of segments or None."""
    best = [(np.inf, 0.0)] * n
    best[0] = (0, 0.0)
    prev = [-1] * n
    for i in range(1, n):
        for j in range(i):
            if best[j][0] == np.inf or not valid(j, i):
                continue
            cand = (best[j][0] + 1, best[j][1] - (score(j, i) if score else 0.0))
            if cand < best[i]:
                best[i], prev[i] = cand, j
    if best[n - 1][0] == np.inf:
        return None
    segs, i = [], n - 1
    while i > 0:
        segs.append((prev[i], i))
        i = prev[i]
    return segs[::-1]


def arc_counts(h, w, bins=72):
    """For a fixed start, the most headings of h[0..m-1] inside an arc of width w, for every prefix
    length m (histogram with `bins` sectors, circular window)."""
    b = (np.mod(h, 2 * np.pi) / (2 * np.pi) * bins).astype(int) % bins
    onehot = np.zeros((len(h), bins))
    onehot[np.arange(len(h)), b] = 1
    cum = np.cumsum(onehot, axis=0)                              # prefix histograms
    width = int(round(w / (2 * np.pi) * bins))
    ext = np.concatenate([cum, cum[:, :width]], axis=1)
    win = np.cumsum(np.concatenate([np.zeros((len(h), 1)), ext], axis=1), axis=1)
    return (win[:, width:width + bins] - win[:, :bins]).max(axis=1)


def penalized_partition(y, beta):
    """Optimal partitioning (Jackson et al. 2005): split y into segments with constant mean,
    minimizing the squared deviations plus beta per segment. O(n^2) with prefix sums."""
    n = len(y)
    s1, s2 = np.r_[0, np.cumsum(y)], np.r_[0, np.cumsum(y ** 2)]
    F = np.full(n + 1, np.inf)
    F[0] = -beta
    last = np.zeros(n + 1, int)
    for t in range(1, n + 1):
        s = np.arange(t)
        cost = (s2[t] - s2[s]) - (s1[t] - s1[s]) ** 2 / (t - s)
        v = F[s] + cost + beta
        k = int(np.argmin(v))
        F[t], last[t] = v[k], k
    segs, t = [], n
    while t > 0:
        segs.append((last[t], t))
        t = last[t]
    return segs[::-1]


def hmm_fit(x, K=2, iters=300):
    """Hidden Markov model with K states and Gaussian emissions, fitted by Baum-Welch (scaled).
    Returns means, standard deviations, transition matrix, initial distribution, log-likelihood."""
    n = len(x)
    mu = np.quantile(x, np.linspace(0.15, 0.85, K))
    sd = np.full(K, x.std() / K + 1e-6)
    A = np.full((K, K), 0.1 / (K - 1)) + np.eye(K) * (0.9 - 0.1 / (K - 1))
    pi = np.full(K, 1 / K)
    ll_old = -np.inf
    for _ in range(iters):
        B = np.exp(-0.5 * ((x[:, None] - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi)) + 1e-300
        alpha, c = np.zeros((n, K)), np.zeros(n)
        alpha[0] = pi * B[0]
        c[0] = alpha[0].sum()
        alpha[0] /= c[0]
        for t in range(1, n):
            alpha[t] = (alpha[t - 1] @ A) * B[t]
            c[t] = alpha[t].sum()
            alpha[t] /= c[t]
        beta = np.ones((n, K))
        for t in range(n - 2, -1, -1):
            beta[t] = (A @ (B[t + 1] * beta[t + 1])) / c[t + 1]
        gamma = alpha * beta
        gamma /= gamma.sum(axis=1, keepdims=True)
        xi = np.zeros((K, K))
        for t in range(n - 1):
            m = alpha[t][:, None] * A * (B[t + 1] * beta[t + 1])[None, :] / c[t + 1]
            xi += m / m.sum()
        pi, A = gamma[0], xi / xi.sum(axis=1, keepdims=True)
        w = gamma.sum(axis=0)
        mu = (gamma * x[:, None]).sum(axis=0) / w
        sd = np.sqrt((gamma * (x[:, None] - mu) ** 2).sum(axis=0) / w) + 1e-6
        ll = np.log(c).sum()
        if ll - ll_old < 1e-8:
            break
        ll_old = ll
    o = np.argsort(mu)
    return mu[o], sd[o], A[np.ix_(o, o)], pi[o], ll


def viterbi(x, mu, sd, A, pi):
    """Most likely state sequence: V[t, s] = max over s' of V[t-1, s'] + log A[s', s] + log b_s(x_t)."""
    n, K = len(x), len(mu)
    logB = -0.5 * ((x[:, None] - mu) / sd) ** 2 - np.log(sd * np.sqrt(2 * np.pi))
    V, back = np.zeros((n, K)), np.zeros((n, K), int)
    V[0] = np.log(pi + 1e-300) + logB[0]
    for t in range(1, n):
        cand = V[t - 1][:, None] + np.log(A)
        back[t] = np.argmax(cand, axis=0)
        V[t] = cand[back[t], np.arange(K)] + logB[t]
    s = np.zeros(n, int)
    s[-1] = int(np.argmax(V[-1]))
    for t in range(n - 1, 0, -1):
        s[t - 1] = back[t, s[t]]
    return s


# ---------------------------------------------------------------- small examples
SPEEDS = [1, 2, 2, 3, 5, 4, 9, 8, 2, 1, 1]          # km/h per time step; criterion: max <= 2 min
COUNTER = [2, 3, 5, 8]                              # criterion: at least 2 values and max - min <= 4
DIAGRAM = [2, 3, 5, 8, 3, 3, 3, 7]                  # the counterexample, continued (start-stop diagram)


def factor2(v):
    return max(v) <= 2 * min(v)


def range4(v):
    return len(v) >= 2 and max(v) - min(v) <= 4


def fig_greedy():
    segs = greedy(SPEEDS, factor2)
    for solution in (False, True):
        fig, ax = plt.subplots(figsize=(7.2, 3.3))
        x = np.arange(len(SPEEDS))
        cols = [GREY] * len(SPEEDS)
        if solution:
            for k, (i, j) in enumerate(segs):
                for t in range(i, j + 1):
                    cols[t] = COL[k % 2]
                ax.add_patch(mpatches.FancyBboxPatch((i - 0.45, -0.25), j - i + 0.9, max(SPEEDS[i:j + 1]) + 1.45,
                             boxstyle="round,pad=0.02,rounding_size=0.15", fill=False, ec=COL[k % 2], lw=1.6,
                             ls=(0, (4, 3))))
                ax.text((i + j) / 2, max(SPEEDS[i:j + 1]) + 1.4, f"{min(SPEEDS[i:j + 1])}–{max(SPEEDS[i:j + 1])}",
                        ha="center", va="bottom", fontsize=13, color=COL[k % 2])
        ax.bar(x, SPEEDS, color=cols, width=0.62, zorder=2)
        for xi, v in zip(x, SPEEDS):
            ax.text(xi, v + 0.15, str(v), ha="center", va="bottom", fontsize=14, color=INK, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels([str(i + 1) for i in x])
        ax.set_xlabel("time step", fontsize=14, color=INK)
        ax.set_ylabel("speed (km/h)", fontsize=14, color=INK)
        ax.set_ylim(0, 12.4)
        ax.set_yticks([])
        for s in ["top", "right", "left"]:
            ax.spines[s].set_visible(False)
        ax.tick_params(labelsize=13, colors=INK, length=0)
        save_opaque(fig, "greedy-speed-solution.svg" if solution else "greedy-speed.svg")
    return segs


def fig_counterexample():
    """Greedy takes the longest valid first segment and gets stuck; the optimum has two segments."""
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.8))
    first = greedy_first(COUNTER, range4)
    for ax, (title, segs, okk) in zip(axs, [("greedy: longest first segment", [(0, first), (first + 1, len(COUNTER) - 1)],
                                               [True, False]),
                                              ("optimal: two segments", [(0, 1), (2, 3)], [True, True])]):
        x = np.arange(len(COUNTER))
        cols = [GREY] * len(COUNTER)
        for k, ((i, j), ok) in enumerate(zip(segs, okk)):
            col = COL[k % 2] if ok else COL[2]
            for t in range(i, j + 1):
                cols[t] = col
            ax.add_patch(mpatches.FancyBboxPatch((i - 0.42, -0.3), j - i + 0.84, max(COUNTER[i:j + 1]) + 1.6,
                         boxstyle="round,pad=0.02,rounding_size=0.15", fill=False, ec=col, lw=1.6, ls=(0, (4, 3))))
            if not ok:
                ax.text((i + j) / 2, max(COUNTER[i:j + 1]) + 1.5, "too short", ha="center", va="bottom", fontsize=13,
                        color=col)
        ax.bar(x, COUNTER, color=cols, width=0.6, zorder=2)
        for xi, v in zip(x, COUNTER):
            ax.text(xi, v + 0.15, str(v), ha="center", va="bottom", fontsize=14, color=INK)
        ax.set_title(title, fontsize=14, color=INK, pad=6)
        ax.set_ylim(0, 11.6)
        ax.set_xticks(x)
        ax.set_xticklabels([str(i + 1) for i in x])
        ax.set_yticks([])
        for sp in ["top", "right", "left"]:
            ax.spines[sp].set_visible(False)
        ax.tick_params(labelsize=13, colors=INK, length=0)
    fig.tight_layout(w_pad=2)
    save(fig, "greedy-counterexample.svg")


def greedy_first(v, crit):
    """Last index of the longest valid first segment."""
    return max(j for j in range(len(v)) if crit(v[:j + 1]))


def dp_prefix(v, crit):
    """S[e] = fewest segments that partition v[0:e], each satisfying crit (inf if impossible), and the
    optimal segments for the whole sequence. S[e] = min over s < e with crit(v[s:e]) of S[s] + 1."""
    n = len(v)
    S, prev = [0] + [np.inf] * n, [-1] * (n + 1)
    for e in range(1, n + 1):
        for s in range(e):
            if S[s] + 1 < S[e] and crit(v[s:e]):
                S[e], prev[e] = S[s] + 1, s
    segs, e = [], n
    while e > 0 and prev[e] >= 0:
        segs.append((prev[e], e - 1))
        e = prev[e]
    return S, segs[::-1]


def fig_start_stop():
    """Start-stop diagram of DIAGRAM (row: first step, column: last step; white = valid segment),
    then the same with the values S of the dynamic program and the optimal staircase."""
    n = len(DIAGRAM)
    S, segs = dp_prefix(DIAGRAM, range4)
    for with_dp in (False, True):
        fig, ax = plt.subplots(figsize=(5.6, 6.1))
        for i in range(n):
            for j in range(i, n):
                ok = range4(DIAGRAM[i:j + 1])
                ax.add_patch(mpatches.Rectangle((j, n - 1 - i), 1, 1, fc="white" if ok else "#c9c9c6",
                                                ec="#9a9a96", lw=0.8))
        if with_dp:
            for k, (i, j) in enumerate(segs):
                ax.add_patch(mpatches.Rectangle((j + 0.14, n - 1 - i + 0.14), 0.72, 0.72, fc=COL[k % 2], ec="none"))
                if k + 1 < len(segs):
                    i2, j2 = segs[k + 1]
                    ax.annotate("", xy=(j2 + 0.5, n - 1 - i2 + 0.5), xytext=(j + 0.5, n - 1 - i + 0.5),
                                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6, mutation_scale=14,
                                                shrinkA=9, shrinkB=9))
            ax.text(-0.25, -0.75, "$S$", ha="right", va="center", fontsize=15, color=INK)
            for j in range(n):
                val = S[j + 1]
                ax.text(j + 0.5, -0.75, "∞" if val == np.inf else f"{int(val)}", ha="center", va="center",
                        fontsize=15, color=INK if val != np.inf else GREY, fontweight="bold")
        for t, v in enumerate(DIAGRAM):
            ax.text(t + 0.5, n + 0.25, str(v), ha="center", va="bottom", fontsize=14, color=INK)
            ax.text(-0.25, n - 1 - t + 0.5, str(v), ha="right", va="center", fontsize=14, color=INK)
        ax.text(n / 2, n + 0.95, "last step of the segment", ha="center", va="bottom", fontsize=13, color=GREY)
        ax.text(-1.05, n / 2, "first step of the segment", ha="center", va="center", fontsize=13, color=GREY,
                rotation=90)
        ax.set_xlim(-1.4, n + 0.1)
        ax.set_ylim(-1.3, n + 1.6)
        ax.set_aspect("equal")
        ax.axis("off")
        save(fig, "start-stop-diagram-dp.svg" if with_dp else "start-stop-diagram.svg")
    return S, segs


# ---------------------------------------------------------------- the running example
BIRD, NAME = "Eamy (DER AL585)", "Eamy"
FIRST, LAST = "2013-08-09", "2013-10-10"          # one position per day (12:00 UTC), as in lectures 2 and 3
RADIUS, HOURS, ARC, INLIERS = 30.0, 48.0, 1.7, 0.8  # the geese criteria of Alewijnse et al. (2014)
BETA = 3.0                                         # change points: penalty per segment, in (log10 km)^2
MOVING_KM = 20.0                                   # change points: segments with a larger mean are "moving"
MIN_KM = 0.1                                       # daily distances below 100 m count as 100 m (GPS noise)
MAP = (lambda lo, la: laea(lo, la, 1, 41.5)), (-1000, 1060, -900, 960)     # projection as storks-autumn-spring.svg
STATE = {"stop": ("stopover", STOP), "fly": ("flight", FLY)}


def daily_track(gps):
    tr = gps[(gps["bird"] == BIRD) & (gps["t"] >= pd.Timestamp(FIRST, tz="UTC"))
             & (gps["t"] < pd.Timestamp(LAST, tz="UTC") + pd.Timedelta(days=1))]
    return noon_fixes(tr)


def step_labels(n, segs, labels):
    """Label of every daily step (from fix k to fix k+1): the label of the segment that contains it."""
    lab = np.empty(n - 1, dtype=object)
    for (j, i), l in zip(segs, labels):
        lab[j:i] = l
    return lab


def runs(lab):
    """Maximal runs of equal labels: list of (label, first index, last index)."""
    out, k = [], 0
    while k < len(lab):
        m = k
        while m + 1 < len(lab) and lab[m + 1] == lab[k]:
            m += 1
        out.append((lab[k], k, m))
        k = m + 1
    return out


def date_axis(ax, dates, every=7, labels=True):
    ticks = list(range(0, len(dates), every))
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{dates[k].day} {dates[k]:%b}" for k in ticks] if labels else [])
    ax.tick_params(axis="x", labelsize=12.5, colors=INK, length=3, color=GREY)


def legend_states(ax, loc="upper right", fontsize=13, names=None):
    names = names or {k: v[0] for k, v in STATE.items()}
    handles = [mpatches.Patch(color=STATE[k][1], label=names[k]) for k in ("stop", "fly")]
    ax.legend(handles=handles, loc=loc, frameon=False, fontsize=fontsize, handlelength=1.2, handleheight=0.9,
              borderaxespad=0.2)


def fig_track(tr, step, lab=None, stops=(), name="storks-eamy-input.svg", highlight=None):
    """Map of the daily positions and bar chart of the daily distances; coloured by state if lab is given.
    stops: list of (text, x, y, ha, (cx, cy)) labels in map coordinates (km), (cx, cy) = stop centre.
    highlight: (first step, last step, map text, map offset, bar text) to circle a stretch of days."""
    proj, box = MAP
    x, y = proj(tr["lon"].values, tr["lat"].values)
    dates = list(tr["t"].iloc[1:])
    fig = plt.figure(figsize=(12.4, 5.4))
    ax = fig.add_axes([0.0, 0.0, 0.44, 1.0])
    basemap(ax, proj, box, tol=5, lakes=False)
    if lab is None:
        ax.plot(x, y, "-", color=GREY, lw=1.3, zorder=2)
        ax.plot(x, y, "o", color=INK, ms=3.6, mew=0, zorder=3)
    else:
        for k in range(len(x) - 1):
            col = STATE[lab[k]][1]
            ax.plot(x[k:k + 2], y[k:k + 2], "-", color=col, lw=2.2 if lab[k] == "fly" else 1.4, zorder=2,
                    solid_capstyle="round")
        fixlab = np.array(["fly"] * len(x), dtype=object)
        for k in range(len(lab)):
            if lab[k] == "stop":
                fixlab[k] = fixlab[k + 1] = "stop"
        ax.plot(x[fixlab == "fly"], y[fixlab == "fly"], "o", color=FLY, ms=3.6, mew=0.6, mec="white", zorder=3)
        for text, tx, ty, ha, (cx, cy) in stops:
            ax.plot(cx, cy, "o", ms=13, color=STOP, mec="white", mew=1.6, zorder=4)
    ax.plot(x[0], y[0], "o", ms=9, color=INK, mec="white", mew=1.4, zorder=5)
    ax.text(x[0] + 50, y[0] + 45, "Lake Constance,\n9 Aug 2013", fontsize=13.5, color=INK, ha="left", va="bottom",
            path_effects=HALO, zorder=6)
    for text, tx, ty, ha, _c in stops:
        ax.text(tx, ty, text, fontsize=13.5, color=STOP, fontweight="bold", ha=ha, va="center",
                path_effects=HALO, zorder=6, linespacing=1.15)
    scalebar(ax, box[0] + 60, box[3] - 150, 500)

    bx = fig.add_axes([0.53, 0.14, 0.46, 0.80])
    cols = [GREY if lab is None else STATE[l][1] for l in (lab if lab is not None else [None] * len(step))]
    bx.bar(np.arange(len(step)), step, width=0.78, color=cols, zorder=2)
    bx.set_xlim(-0.8, len(step) - 0.2)
    bx.set_ylim(0, 400)
    bx.set_yticks([0, 100, 200, 300, 400])
    bx.grid(axis="y", color="#e2e2df", lw=0.8, zorder=0)
    for sp in ["top", "right", "left"]:
        bx.spines[sp].set_visible(False)
    bx.spines["bottom"].set_color(GREY)
    bx.tick_params(axis="y", labelsize=12.5, colors=INK, length=0)
    date_axis(bx, dates)
    bx.set_ylabel("distance to the previous day's position (km)", fontsize=13, color=INK)
    if lab is not None:
        legend_states(bx)
    if highlight:
        a, b, text, (dx, dy), btext = highlight
        hx, hy = x[a:b + 2].mean(), y[a:b + 2].mean()
        ax.add_patch(mpatches.Circle((hx, hy), 70, fill=False, ec=COL[2], lw=2.2, ls=(0, (3, 2)), zorder=7))
        ax.text(hx + dx, hy + dy, text, fontsize=13.5, color=COL[2], fontweight="bold", ha="right", va="center",
                path_effects=HALO, zorder=7, linespacing=1.15)
        top = max(step[a:b + 1]) + 18
        bx.add_patch(mpatches.FancyBboxPatch((a - 0.55, -6), b - a + 1.1, top + 6, boxstyle="round,pad=0,rounding_size=0.3",
                                             fill=False, ec=COL[2], lw=2.0, ls=(0, (3, 2)), zorder=4, clip_on=False))
        ty = max(step[max(0, a - 2):b + 3]) + 25
        bx.plot([(a + b) / 2, (a + b) / 2], [top, ty - 4], color=COL[2], lw=1.2, zorder=4)
        bx.text((a + b) / 2, ty, btext, fontsize=13, color=COL[2], fontweight="bold", ha="center",
                va="bottom", zorder=4, linespacing=1.15, path_effects=HALO)
    (save_opaque if lab is not None else save)(fig, name)


def fig_methods(tr, step, rows):
    """Daily distances and, below, one coloured strip per method. rows: list of (title, step labels)."""
    dates = list(tr["t"].iloc[1:])
    n = len(step)
    fig, axs = plt.subplots(1 + len(rows), 1, figsize=(12.4, 1.95 + 0.92 * len(rows)), sharex=True,
                            gridspec_kw=dict(height_ratios=[2.0] + [0.62] * len(rows), hspace=0.32))
    ax = axs[0]
    ax.bar(np.arange(n), step, width=0.78, color=GREY, zorder=2)
    ax.set_ylim(0, 400)
    ax.set_yticks([])
    for v in (100, 200, 300, 400):
        ax.axhline(v, color="#e2e2df", lw=0.8, zorder=0)
    ax.text(n - 0.3, 200, "200 km", fontsize=11.5, color=GREY, ha="left", va="center")
    ax.text(n - 0.3, 400, "400 km", fontsize=11.5, color=GREY, ha="left", va="center")
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GREY)
    ax.tick_params(axis="x", length=0)
    ax.text(-1.2, 200, "daily\ndistance", fontsize=13, color=INK, ha="right", va="center", linespacing=1.15)
    for bx, (title, lab) in zip(axs[1:], rows):
        for kind, a, b in runs(lab):
            bx.add_patch(mpatches.Rectangle((a - 0.5, 0), b - a + 1, 1, fc=STATE[kind][1], ec="white", lw=1.2))
        bx.set_ylim(0, 1)
        bx.set_yticks([])
        for sp in ["top", "right", "left", "bottom"]:
            bx.spines[sp].set_visible(False)
        bx.text(-1.2, 0.5, title, fontsize=13, color=INK, ha="right", va="center", linespacing=1.15)
        bx.tick_params(axis="x", length=0)
    axs[-1].set_xlim(-0.6, n - 0.4)
    date_axis(axs[-1], dates)
    axs[-1].tick_params(axis="x", length=0, pad=4)
    handles = [mpatches.Patch(color=STATE[k][1], label=lbl) for k, lbl in
               (("stop", "stopover / stationary"), ("fly", "flight / moving"))]
    axs[0].legend(handles=handles, loc="upper right", frameon=False, fontsize=13, ncol=2, handlelength=1.2,
                  bbox_to_anchor=(1.0, 1.12))
    save(fig, "storks-eamy-methods.svg")


def fig_changepoints(tr, x, segs, lab):
    """Log daily distance with the piecewise-constant fit of optimal partitioning."""
    dates = list(tr["t"].iloc[1:])
    fig, ax = plt.subplots(figsize=(11.6, 4.3))
    ax.plot(np.arange(len(x)), x, "o", color=INK, ms=5, mew=0, zorder=3)
    for (a, b), l in zip(segs, lab):
        m = x[a:b].mean()
        ax.plot([a - 0.45, b - 0.55], [m, m], "-", color=STATE[l][1], lw=4, solid_capstyle="butt", zorder=2)
        if a > 0:
            ax.axvline(a - 0.5, color=GREY, lw=1.0, ls=(0, (3, 3)), zorder=1)
    ax.set_yticks([-1, 0, 1, 2])
    ax.set_yticklabels(["≤ 0.1 km", "1 km", "10 km", "100 km"])
    ax.set_ylim(-1.25, 2.85)
    ax.set_xlim(-0.8, len(x) - 0.2)
    ax.grid(axis="y", color="#e2e2df", lw=0.8, zorder=0)
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GREY)
    ax.tick_params(axis="y", labelsize=12.5, colors=INK, length=0)
    date_axis(ax, dates)
    ax.set_ylabel("daily distance (log scale)", fontsize=13.5, color=INK)
    handles = [mpatches.Patch(color=STATE[k][1], label=lbl) for k, lbl in
               (("stop", f"segment mean below {MOVING_KM:g} km"), ("fly", f"segment mean above {MOVING_KM:g} km"))]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=13, ncol=2, handlelength=1.2,
              bbox_to_anchor=(1.0, 1.0))
    save(fig, "storks-eamy-changepoints.svg")


def fig_hmm(x, mu, sd, A, states):
    """Two figures: the two-state model with its transition probabilities, and the histogram of the log
    daily distances with the fitted emission densities (weighted by how often each state occurs)."""
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0.6, 7.0)
    ax.set_aspect("equal")
    ax.axis("off")
    centres = {"stop": (2.2, 3.0), "fly": (7.8, 3.0)}
    for k, st in enumerate(("stop", "fly")):
        cx, cy = centres[st]
        ax.add_patch(mpatches.Circle((cx, cy), 1.45, fc=STATE[st][1], ec="none", zorder=2))
        ax.text(cx, cy, STATE[st][0], ha="center", va="center", fontsize=16, color="white", fontweight="bold",
                zorder=3)
        ax.add_patch(mpatches.FancyArrowPatch((cx - 0.8, cy + 1.25), (cx + 0.8, cy + 1.25),
                                              connectionstyle="arc3,rad=-1.6", arrowstyle="-|>", mutation_scale=18,
                                              color=INK, lw=1.5, zorder=1))
        ax.text(cx, cy + 3.25, f"{A[k, k]:.2f}", ha="center", va="bottom", fontsize=16, color=INK)
    for (xa, ya), (xb, yb), lbl, ty, va in [((3.75, 3.6), (6.25, 3.6), f"{A[0, 1]:.2f}", 4.35, "bottom"),
                                             ((6.25, 2.4), (3.75, 2.4), f"{A[1, 0]:.2f}", 1.65, "top")]:
        ax.add_patch(mpatches.FancyArrowPatch((xa, ya), (xb, yb), connectionstyle="arc3,rad=-0.25", arrowstyle="-|>",
                                              mutation_scale=18, color=INK, lw=1.5))
        ax.text(5.0, ty, lbl, ha="center", va=va, fontsize=16, color=INK)
    save(fig, "storks-eamy-hmm-states.svg")

    fig, bx = plt.subplots(figsize=(6.6, 3.9))
    edges = np.linspace(-1.25, 2.85, 15)
    bx.hist(x, bins=edges, color="#d4d4d0", zorder=1)
    g = np.linspace(-1.25, 2.85, 300)
    width = edges[1] - edges[0]
    top = 0
    for k, st in enumerate(("stop", "fly")):
        w = np.mean(states == k)
        dens = w * len(x) * width * np.exp(-0.5 * ((g - mu[k]) / sd[k]) ** 2) / (sd[k] * np.sqrt(2 * np.pi))
        bx.plot(g, dens, color=STATE[st][1], lw=3, zorder=2)
        med = f"{10 ** mu[k]:.0f}" if 10 ** mu[k] >= 10 else f"{10 ** mu[k]:.1f}"
        bx.text(mu[k], dens.max() + 0.5, f"{STATE[st][0]}:\nmedian {med} km", ha="center", va="bottom",
                fontsize=15, color=STATE[st][1], fontweight="bold", path_effects=HALO, zorder=3)
        top = max(top, dens.max())
    bx.set_xticks([-1, 0, 1, 2])
    bx.set_xticklabels(["≤ 0.1 km", "1 km", "10 km", "100 km"])
    bx.set_xlim(-1.3, 2.9)
    bx.set_ylim(0, max(bx.get_ylim()[1], top) + 3.6)
    for sp in ["top", "right", "left"]:
        bx.spines[sp].set_visible(False)
    bx.spines["bottom"].set_color(GREY)
    bx.set_yticks([])
    bx.tick_params(axis="x", labelsize=14, colors=INK, length=3, color=GREY)
    bx.set_xlabel("daily distance (log scale)", fontsize=15, color=INK)
    save(fig, "storks-eamy-hmm-emissions.svg")


def fig_start_stop_eamy(tr, stop_ok, fly_ok, segs, labels):
    """The start-stop diagram of the running example: row = first day, column = last day."""
    n = len(tr)
    dates = list(tr["t"])
    fig, ax = plt.subplots(figsize=(6.4, 6.4))
    img = np.full((n, n, 3), 1.0)
    light = lambda hx, f: np.array(matplotlib.colors.to_rgb(hx)) * f + (1 - f)
    for j in range(n):
        for i in range(j + 1, n):
            if stop_ok(j, i):
                img[j, i] = light(STOP, 0.45)
            elif fly_ok(j, i):
                img[j, i] = light(FLY, 0.45)
            else:
                img[j, i] = light("#8e908c", 0.18)
    ax.imshow(img, origin="upper", extent=(-0.5, n - 0.5, n - 0.5, -0.5), interpolation="nearest", zorder=1)
    px, py = [], []
    for (j, i), l in zip(segs, labels):
        ax.add_patch(mpatches.Rectangle((i - 0.5, j - 0.5), 1, 1, fc=STATE[l][1], ec=INK, lw=0.8, zorder=3))
        px += [i, i]
        py += [j, i]
    ax.plot(px[:-1], py[:-1], "-", color=INK, lw=1.2, zorder=2)
    ticks = list(range(0, n, 14))
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{dates[k].day} {dates[k]:%b}" for k in ticks])
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{dates[k].day} {dates[k]:%b}" for k in ticks])
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position("top")
    ax.tick_params(labelsize=12, colors=INK, length=3, color=GREY)
    ax.set_xlabel("last day of the segment", fontsize=13, color=GREY, labelpad=8)
    ax.set_ylabel("first day of the segment", fontsize=13, color=GREY)
    for sp in ax.spines.values():
        sp.set_visible(False)
    handles = [mpatches.Patch(color=light(STOP, 0.45), label="valid stopover"),
               mpatches.Patch(color=light(FLY, 0.45), label="valid flight"),
               mpatches.Patch(color=light("#8e908c", 0.18), label="neither")]
    ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=12.5, handlelength=1.2,
              bbox_to_anchor=(0.0, 0.0))
    save(fig, "storks-eamy-startstop.svg")


GEESE_CSV = os.path.join(data_dir, "koelzsch2016-white-fronted-geese",
                         "Migration timing in white-fronted geese (data from Kölzsch et al. 2016)-gps.csv")
SPRING, AUTUMN = "#3F7E44", "#6250d6"


def fig_geese_map():
    """GPS tracks of the 65 white-fronted geese of Kölzsch et al. (2016), spring and autumn migration
    (Movebank Data Repository, doi:10.5441/001/1.31c2v92f, CC0)."""
    proj = lambda lo, la: laea(lo, la, 32, 61)
    box = (-2300, 1900, -1900, 1650)
    fig, ax = plt.subplots(figsize=(6.0, 4.8))
    basemap(ax, proj, box, tol=12, lakes=True)
    g = pd.read_csv(GEESE_CSV, parse_dates=["timestamp"])
    g = g[g["visible"] == True].sort_values(["individual-local-identifier", "timestamp"])  # noqa: E712
    n_tracks = {"spring-migration": 0, "fall-migration": 0}
    for season, col, z in [("fall-migration", AUTUMN, 2), ("spring-migration", SPRING, 3)]:
        sub = g[g["migration-stage-standard"] == season]
        for (_, year), tr in sub.groupby(["individual-local-identifier", sub["timestamp"].dt.year]):
            if len(tr) < 2:
                continue
            gap = tr["timestamp"].diff().dt.total_seconds().fillna(0) > 10 * 86400     # split at gaps > 10 days
            for _, part in tr.groupby(gap.cumsum()):
                xy = np.array([proj(lo, la) for lo, la in zip(part["location-long"], part["location-lat"])])
                ax.plot(xy[:, 0], xy[:, 1], color=col, lw=0.7, alpha=0.55, zorder=z, solid_capstyle="round")
            n_tracks[season] += 1
    for (lat, lon), text, (dx, dy, ha) in [((52.6, 5.6), "wintering:\nNetherlands,\nnorthern Germany", (-60, -120, "left")),
                                           ((69.1, 49.0), "breeding:\nRussian Arctic,\ne.g. Kolguev Island", (-40, 140, "right"))]:
        x, y = proj(lon, lat)
        ax.plot(x, y, "o", ms=11, color=INK, mec="white", mew=1.8, zorder=6)
        ax.text(x + dx, y + dy, text, fontsize=14, color=INK, ha=ha, va="top" if dy < 0 else "bottom",
                path_effects=HALO, zorder=7, linespacing=1.15)
    ax.text(box[1] - 60, box[2] + 1050, f"spring: 83 days\n{n_tracks['spring-migration']} tracks", fontsize=15,
            color=SPRING, fontweight="bold", ha="right", va="center", path_effects=HALO, zorder=7)
    ax.text(box[1] - 60, box[2] + 560, f"autumn: 42 days\n{n_tracks['fall-migration']} tracks", fontsize=15,
            color=AUTUMN, fontweight="bold", ha="right", va="center", path_effects=HALO, zorder=7)
    scalebar(ax, box[1] - 1080, box[2] + 90, 1000)
    save(fig, "geese-overview.svg")
    print(f"== geese map: {len(g)} GPS fixes of {g['individual-local-identifier'].nunique()} geese;"
          f" tracks drawn: spring {n_tracks['spring-migration']}, autumn {n_tracks['fall-migration']}")


def criteria_valid(P, th):
    """Validity tests of the geese criteria on the daily track (fixes j..i)."""
    n = len(P)
    lat, lon = P[:, 0], P[:, 1]
    hd = bearing(lat[:-1], lon[:-1], lat[1:], lon[1:])
    cache = {}

    def disk(j, i):
        if (j, i) not in cache:
            cache[(j, i)] = enclosing_cap(lat[j:i + 1], lon[j:i + 1])[1] <= RADIUS
        return cache[(j, i)]

    maxdisk = longest_valid(n, disk)
    fly = np.zeros((n, n), bool)
    for j in range(n - 1):
        cnt = arc_counts(hd[j:], ARC)
        fly[j, j + 1:] = cnt >= INLIERS * np.arange(1, n - j)
    stop_ok = lambda j, i: i <= maxdisk[j] and th[i] - th[j] >= HOURS
    fly_ok = lambda j, i: bool(fly[j, i])
    return stop_ok, fly_ok, hd


# ---------------------------------------------------------------- main
segs_g = fig_greedy()
print("== greedy, speeds", SPEEDS, "with max <= 2 min:", " | ".join(str(SPEEDS[i:j + 1]) for i, j in segs_g),
      f"({len(segs_g)} segments)")
fig_counterexample()
f = greedy_first(COUNTER, range4)
print("== counterexample", COUNTER, "(at least 2 values, range <= 4): greedy first segment", COUNTER[:f + 1],
      "leaves", COUNTER[f + 1:], "; optimum", dp_prefix(COUNTER, range4)[1])
S, segs_d = fig_start_stop()
print("== start-stop diagram", DIAGRAM, ": S =", ["inf" if v == np.inf else int(v) for v in S], "; optimal segments",
      [DIAGRAM[i:j + 1] for i, j in segs_d], "; greedy first segment", DIAGRAM[:greedy_first(DIAGRAM, range4) + 1])

fig_geese_map()
gps = load_gps()
tr = daily_track(gps)
P = tr[["lat", "lon"]].values
th = (tr["t"] - tr["t"].iloc[0]).dt.total_seconds().values / 3600
n = len(tr)
step = haversine(P[:-1, 0], P[:-1, 1], P[1:, 0], P[1:, 1])
dates = list(tr["t"])
day = lambda k: f"{dates[k].day} {dates[k]:%b}"
print(f"== {NAME}: {n} daily positions, {day(0)} - {day(n - 1)} 2013; daily distance median {np.median(step):.0f} km, "
      f"max {step.max():.0f} km ({day(int(step.argmax()) + 1)})")
print("   daily distances:", " ".join(f"{v:.0f}" for v in step))

# criteria-based segmentation (geese criteria)
stop_ok, fly_ok, hd = criteria_valid(P, th)
valid = lambda j, i: stop_ok(j, i) or fly_ok(j, i)
segs = min_segmentation(n, valid, score=lambda j, i: (th[i] - th[j]) if stop_ok(j, i) else 0.0)
labels = ["stop" if stop_ok(j, i) else "fly" for j, i in segs]
lab_c = step_labels(n, segs, labels)
print(f"== criteria (disk {RADIUS:g} km for >= {HOURS:g} h, OR {INLIERS:.0%} of headings within {ARC} rad): "
      f"{len(segs)} segments")
for (j, i), l in zip(segs, labels):
    print(f"   {l:4s} {day(j):>6s} - {day(i):>6s}  {i - j:2d} days  ({P[j, 0]:.2f}, {P[j, 1]:.2f}) -> "
          f"({P[i, 0]:.2f}, {P[i, 1]:.2f}), {haversine(P[j, 0], P[j, 1], P[i, 0], P[i, 1]):.0f} km")
ph = runs(lab_c)
print("   phases:", "; ".join(f"{STATE[k][0]} {day(a)} - {day(b + 1)} ({b - a + 1} days)" for k, a, b in ph))
valid_cells = sum(valid(j, i) for j in range(n) for i in range(j + 1, n))
print(f"   start-stop diagram: {n * (n - 1) // 2} cells, {valid_cells} valid")
for k, a, b in ph:                             # the flight that swallowed a short stop
    if k == "fly":
        h = np.degrees(hd[a:b + 1])
        inside = arc_counts(hd[a:b + 1], ARC)[-1]
        print(f"   flight {day(a)} - {day(b + 1)}: {int(inside)} of {b - a + 1} headings in an arc of {ARC} rad; "
              f"daily km {[int(round(v)) for v in step[a:b + 1]]}")

# change points: optimal partitioning of log10 daily distance
x = np.log10(np.maximum(step, MIN_KM))
for beta in (1.0, BETA):
    cps = penalized_partition(x, beta)
    print(f"== change points, penalty {beta:g}: {len(cps)} segments:",
          "; ".join(f"{day(a)}-{day(b)} {10 ** x[a:b].mean():.1f} km" for a, b in cps))
cps = penalized_partition(x, BETA)
cp_lab = ["fly" if 10 ** x[a:b].mean() > MOVING_KM else "stop" for a, b in cps]
lab_cp = np.empty(n - 1, dtype=object)
for (a, b), l in zip(cps, cp_lab):
    lab_cp[a:b] = l

# hidden Markov model with two states on log10 daily distance
mu, sd, A, pi, ll = hmm_fit(x, 2)
states = viterbi(x, mu, sd, A, pi)
lab_h = np.array(["stop" if s == 0 else "fly" for s in states], dtype=object)
print(f"== HMM: medians {10 ** mu[0]:.1f} km / {10 ** mu[1]:.0f} km (sd {sd[0]:.2f} / {sd[1]:.2f} log10 km); "
      f"A = {A.round(2).tolist()}; expected stay {1 / (1 - A[0, 0]):.1f} / {1 / (1 - A[1, 1]):.1f} days; "
      f"log-likelihood {ll:.1f}")
print("   Viterbi:", "; ".join(f"{STATE[k][0]} {day(a)} - {day(b + 1)}" for k, a, b in runs(lab_h)))
for nm, lb in [("change points", lab_cp), ("HMM", lab_h)]:
    print(f"   agreement criteria vs {nm}: {np.mean(lab_c == lb):.0%} of {n - 1} days")
print(f"   agreement change points vs HMM: {np.mean(lab_cp == lab_h):.0%}")

stops = {"near Lleida": (300, 40, "left"), "La Mancha": (-130, -110, "right"), "Morocco": (110, -60, "left")}
fig_track(tr, step)
proj, box = MAP
lab_stops = []
stop_runs = [(a, b) for k, a, b in ph if k == "stop"]
for (a, b), text in zip(stop_runs, stops):
    cx, cy = proj(P[a:b + 2, 1].mean(), P[a:b + 2, 0].mean())
    dx, dy, ha = stops[text]
    label = f"{text}\n{b - a + 1} days" if b + 1 < n - 1 else f"{text}\nfrom {day(a)}"
    lab_stops.append((label, cx + dx, cy + dy, ha, (cx, cy)))
fig_track(tr, step, lab_c, lab_stops, "storks-eamy-criteria.svg")
short = np.array([step[k] < 5 and lab_c[k] == "fly" for k in range(n - 1)], dtype=object)
_, a_m, b_m = max((r for r in runs(short) if r[0]), key=lambda r: r[2] - r[1])   # longest run: near Madrid
print(f"   days labelled flight with < 5 km: {day(a_m + 1)} - {day(b_m + 1)}, at "
      f"({P[a_m + 1, 0]:.2f}, {P[a_m + 1, 1]:.2f}), {haversine(P[a_m + 1, 0], P[a_m + 1, 1], 40.4168, -3.7038):.0f} km "
      f"from the centre of Madrid")
fig_track(tr, step, lab_c, lab_stops, "storks-eamy-criteria-madrid.svg",
          highlight=(a_m, b_m, f"{b_m - a_m + 1} days near Madrid", (-95, 0), f"{b_m - a_m + 1} days\nnear Madrid"))
fig_methods(tr, step, [(f"criteria\n({RADIUS:g} km, {HOURS:g} h, {ARC} rad)", lab_c),
                       (f"change points\n(penalty {BETA:g})", lab_cp),
                       ("hidden Markov\nmodel (2 states)", lab_h)])
fig_changepoints(tr, x, cps, cp_lab)
fig_hmm(x, mu, sd, A, states)
fig_start_stop_eamy(tr, stop_ok, fly_ok, segs, labels)
