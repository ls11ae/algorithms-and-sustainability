"""Figures for "Algorithms and Sustainability", lecture 4: segmentation (own work, CC BY 4.0).

Usage:  python3 tools/make_segmentation_figures.py <data folder> lectures/figures
The data folder is AuN/movement-analysis/data (as for tools/make_stork_figures.py) with
  koelzsch2016-white-fronted-geese/  GPS data of Kölzsch et al. (2016), Movebank Data Repository,
      doi:10.5441/001/1.31c2v92f, CC0; every fix carries the ecologists' label (stopover or flight)
  koelzsch2022-geese-new-year/       GPS data of Kölzsch et al. (2022), Movebank Data Repository,
      doi:10.5441/001/1.g51fs0jv, CC0 (study: Kölzsch et al. 2023): geese of four species around New Year,
      2013/14 to 2020/21
  nasa-gistemp/GLB.Ts+dSST.csv       NASA GISTEMP v4, global annual mean temperature anomalies
  natural-earth/                     Natural Earth 1:50m countries and lakes (public domain)

Writes the figures of lecture 4 and prints every number quoted on the slides:
  greedy-speed.svg, greedy-speed-solution.svg       greedy segmentation, speed within a factor 2
  greedy-counterexample.svg                         minimum length and range: greedy gets stuck
  start-stop-diagram.svg, start-stop-diagram-dp.svg  valid segments, values S, optimal staircase
  start-stop-step-1..6.svg, start-stop-dp-1..8.svg  the same, built step by step and filled column by column
  start-stop-blocks-1..2.svg                        blocks of white cells, one range-minimum query per block
  optimal-partitioning.svg                          sketch of the change-point recurrence (constructed data)
  geese-criteria.svg, criteria-attributes.svg       schematic criteria: stopover and flight of the geese; speed,
                                                    heading, location and duration
  monotone-decreasing.svg, monotone-increasing.svg  schematic: subsegments resp. supersegments stay valid
  greedy-stays-ahead.svg                            greedy vs another valid segmentation of the speeds
  geese-overview.svg                                all GPS tracks of Kölzsch et al. (2016)
  geese-3104-input.svg, geese-3104-experts.svg      running example: goose 3104, spring 2014, distance per
                                                    hour, without and with the ecologists' labels
  geese-3104-criteria.svg, geese-3104-methods.svg  ecologists vs criteria; all three methods
  geese-3104-hmm.svg                                distances per hour with the four fitted emission densities
  geese-3104-hmm-zoom.svg                           four days hour by hour, coloured by the most likely state
  hmm-model.svg                                     schematic: hidden states (a Markov chain) emit the distances
  viterbi-trellis.svg, viterbi-trellis-1..5.svg,    a small Viterbi example (costs: rounded -log probabilities),
  viterbi-trellis-solution.svg                      solved hour by hour, then backtracking
  gistemp-changepoints.svg                          global temperature with continuous piecewise-linear trends
  geese-new-year.svg                                New Year's night: one goose, every fix with its state; share of
                                                    fixes in the flight state, New Year vs other nights

Algorithms (all in this file): greedy for decreasing monotone criteria; longest valid segment per start (two
pointers); fewest segments by dynamic programming over the start-stop diagram (ties: longest stopovers);
smallest enclosing circle (Welzl); headings in an arc with outliers; optimal partitioning with a penalty per
segment; continuous piecewise-linear trends by exhaustive search over the change years; hidden Markov model
with Gaussian emissions on a log scale (Baum-Welch, Viterbi). Needs matplotlib, numpy, pandas; font as in
make_figures.py (LATO_DIR). Runs in about three minutes; the output is byte-reproducible.
"""
import itertools
import os

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- reuse lecture 2's stork tools
_here = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(_here, "make_stork_figures.py"), encoding="utf-8").read()
_src = _src.split("# ---------------------------------------------------------------- main")[0]
exec(compile(_src, "make_stork_figures.py", "exec"))     # defines plt, laea, basemap, save, haversine, ...

import matplotlib.patches as mpatches                   # noqa: E402
plt.rcParams.update({"mathtext.fontset": "custom", "mathtext.it": "LatoLatin:italic", "mathtext.rm": "LatoLatin",
                     "mathtext.bf": "LatoLatin:bold", "mathtext.cal": "LatoLatin:italic",
                     "mathtext.sf": "LatoLatin", "mathtext.tt": "LatoLatin"})

STOP, FLY = "#0A97D9", "#E8700A"                         # stopover / resting, flight
COL = ["#0A97D9", "#E8700A", "#DD1367", "#3F7E44", "#6250d6"]
STATE = {"stop": ("stopover", STOP), "fly": ("flight", FLY)}
HMM_NAMES = ["resting", "moving locally", "local flights", "migratory flight"]
HMM_COLS = ["#0A97D9", "#3F7E44", "#6250d6", "#E8700A"]  # validated as a set (dataviz validator, light mode)
LIGHT_BAND = "#dcebf5"                                   # background of the ecologists' stopovers


def save_opaque(fig, name):
    """As save(), but with a white background (figures stacked on one slide with fragments)."""
    plt.rcParams["savefig.transparent"] = False
    fig.patch.set_facecolor("white")
    save(fig, name)
    plt.rcParams["savefig.transparent"] = True


def clean(ax, left=True):
    for s in ["top", "right"] + (["left"] if left else []):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GREY)
    if not left:
        ax.spines["left"].set_visible(False)


# ---------------------------------------------------------------- geometry
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
    """Smallest enclosing circle (Welzl's algorithm, iterative, fixed random order)."""
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


def disk_radius(lat, lon):
    """Radius (km) of the smallest disk containing the positions, in the azimuthal equidistant projection at
    the first position (for disks of 30 km the distortion is below 0.01 %)."""
    x, y = aeqd(lat, lon, lat[0], lon[0])
    return enclosing_circle(np.c_[x, y])[1]


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


def arc_counts(h, w, bins=1440):
    """For a fixed start, the most headings of h[0..m-1] inside an arc of width w, for every prefix
    length m (histogram with `bins` sectors of 0.25 degrees, circular window). The window has floor(w / sector)
    sectors (1.7 rad: 389 sectors = 97.25 degrees), so every counted set fits into an arc of width w; a window one
    sector wider gives the same segmentation of goose 3104."""
    b = (np.mod(h, 2 * np.pi) / (2 * np.pi) * bins).astype(int) % bins
    onehot = np.zeros((len(h), bins))
    onehot[np.arange(len(h)), b] = 1
    cum = np.cumsum(onehot, axis=0)                              # prefix histograms
    width = int(np.floor(w / (2 * np.pi) * bins))
    ext = np.concatenate([cum, cum[:, :width]], axis=1)
    win = np.cumsum(np.concatenate([np.zeros((len(h), 1)), ext], axis=1), axis=1)
    return (win[:, width:width + bins] - win[:, :bins]).max(axis=1)


def criteria_segmentation(lat, lon, th, radius, hours, arc, inliers):
    """Fewest segments [j, i] (consecutive segments share the break point), each a stopover (smallest disk of
    radius <= radius and duration >= hours) or a flight (>= inliers of the headings within an arc); ties: the
    longest total stopover time. Dynamic programming S[i] = min over valid [j, i] of S[j] + 1 over the
    start-stop diagram, one column at a time (numpy). Returns segments (j, i, kind) and the diagram size."""
    n = len(lat)
    hd = bearing(lat[:-1], lon[:-1], lat[1:], lon[1:])
    maxdisk = longest_valid(n, lambda j, i: disk_radius(lat[j:i + 1], lon[j:i + 1]) <= radius)
    fly = np.zeros((n, n), bool)
    for j in range(n - 1):
        fly[j, j + 1:] = arc_counts(hd[j:], arc) >= inliers * np.arange(1, n - j)
    S, W = np.full(n, np.inf), np.zeros(n)                   # fewest segments, stopover hours (ties)
    S[0] = 0
    prev, kind = np.full(n, -1), np.empty(n, object)
    n_valid = 0
    for i in range(1, n):
        stop = (maxdisk[:i] >= i) & (th[i] - th[:i] >= hours)
        fl = fly[:i, i] & ~stop
        n_valid += int(stop.sum() + fl.sum())
        for ok, k, w in ((stop, "stop", th[i] - th[:i]), (fl, "fly", np.zeros(i))):
            if not ok.any():
                continue
            cs = np.where(ok, S[:i] + 1, np.inf)
            cw = np.where(ok, W[:i] + w, -np.inf)
            b = int(np.lexsort((-cw, cs))[0])
            if (cs[b], -cw[b]) < (S[i], -W[i]):
                S[i], W[i], prev[i], kind[i] = cs[b], cw[b], b, k
    if not np.isfinite(S[-1]):
        return None, n_valid
    segs, i = [], n - 1
    while i > 0:
        segs.append((int(prev[i]), i, kind[i]))
        i = int(prev[i])
    return segs[::-1], n_valid


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


def hmm_fit(x, K, init, iters=400, min_sd=0.1):
    """Hidden Markov model with K states and Gaussian emissions, fitted by Baum-Welch (scaled forward-backward)
    from the given initial means. Standard deviations are kept >= min_sd (otherwise a state can collapse onto
    the many equal values at the GPS noise floor). Returns means, sds, transition matrix, initial distribution,
    log-likelihood; states sorted by mean."""
    n = len(x)
    mu = np.array(init, float)
    sd = np.full(K, max(x.std() / K, min_sd))
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
        sd = np.maximum(np.sqrt((gamma * (x[:, None] - mu) ** 2).sum(axis=0) / w), min_sd)
        ll = np.log(c).sum()
        if ll - ll_old < 1e-7:
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


def greedy_first(v, crit):
    """Last index of the longest valid first segment."""
    return max(j for j in range(len(v)) if crit(v[:j + 1]))


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
        for t, v in enumerate(DIAGRAM):                      # step number (grey) and its speed (black)
            ax.text(t + 0.5, n + 0.1, str(t + 1), ha="center", va="bottom", fontsize=10.5, color=GREY)
            ax.text(t + 0.5, n + 0.5, str(v), ha="center", va="bottom", fontsize=14, color=INK)
            ax.text(-0.12, n - 1 - t + 0.5, str(t + 1), ha="right", va="center", fontsize=10.5, color=GREY)
            ax.text(-0.52, n - 1 - t + 0.5, str(v), ha="right", va="center", fontsize=14, color=INK)
        ax.text(n / 2, n + 1.2, "last step of the segment", ha="center", va="bottom", fontsize=13, color=GREY)
        ax.text(-1.35, n / 2, "first step of the segment", ha="center", va="center", fontsize=13, color=GREY,
                rotation=90)
        ax.set_xlim(-1.7, n + 0.1)
        ax.set_ylim(-1.3, n + 1.85)
        ax.set_aspect("equal")
        ax.axis("off")
        save(fig, "start-stop-diagram-dp.svg" if with_dp else "start-stop-diagram.svg")
    return S, segs


# ---------------------------------------------------------------- schematic figures: criteria, monotonicity, greedy
def _bracket(ax, x0, x1, y, col, lw=2.2, h=0.18, up=True):
    """A bracket from x0 to x1 at height y (ticks pointing down if up, else up)."""
    d = -h if up else h
    ax.plot([x0, x0, x1, x1], [y + d, y, y, y + d], color=col, lw=lw, solid_capstyle="round",
            solid_joinstyle="round", zorder=3)


def _walk(rng, n, step, radius, start=(0.0, 0.0)):
    """A random walk of n positions that stays inside a disk around the origin (schematic stopover)."""
    p, pts = np.array(start, float), []
    while len(pts) < n:
        q = p + rng.normal(0, step, 2)
        if np.hypot(*q) < radius:
            p = q
            pts.append(p)
    return np.array(pts)


def _radius(ax, angle, label, r=1.0):
    """A radius arrow at the given angle, labelled just outside the disk."""
    tip = np.array([np.cos(angle), np.sin(angle)]) * r
    ax.annotate("", xy=tip, xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.3, mutation_scale=11,
                shrinkA=0, shrinkB=0), zorder=4)
    ax.plot([0], [0], "o", color=INK, ms=3, zorder=4)
    ax.text(*(tip * 1.1), label, fontsize=15, color=INK, ha="left", va="top", path_effects=HALO, zorder=5)


def fig_geese_criteria():
    """The two criteria of the geese: a stopover stays within a disk of radius 30 km for at least 48 h; a flight
    has at least 80% of its headings within an arc of 1.7 rad (schematic, not data)."""
    rng = np.random.default_rng(11)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.6, 2.55), gridspec_kw={"width_ratios": [1.0, 1.3]})
    pts = _walk(rng, 60, 0.2, 0.85)
    a1.plot(pts[:, 0], pts[:, 1], "-", color=STOP, lw=0.9, alpha=0.55, zorder=2)
    a1.plot(pts[:, 0], pts[:, 1], "o", color=STOP, ms=3.0, zorder=3)
    t = np.linspace(0, 2 * np.pi, 200)
    a1.plot(np.cos(t), np.sin(t), color=STOP, lw=1.6, ls=(0, (4, 3)), zorder=1)
    _radius(a1, -0.55, "30 km")
    a1.text(0, 1.3, "stopover", fontsize=17, color=STOP, fontweight="bold", ha="center", va="bottom")
    a1.text(0, -1.18, "for at least 48 h", fontsize=15, color=INK, ha="center", va="top")
    a1.set_xlim(-1.3, 1.75)
    a1.set_ylim(-1.6, 1.45)
    # flight: a track whose headings mostly lie in one arc, and the same headings as a fan
    deg = [20, 55, 35, 80, 45, 172, 65, 28, 88, -62]                   # two outliers: 172 and -62 degrees
    head = np.radians(deg)
    lo_a, width = np.radians(2), 1.7                                   # arc from 2 to 99 degrees
    inside = ((head - lo_a) % (2 * np.pi)) <= width
    assert inside.mean() >= 0.8
    xy = np.vstack([[0, 0], np.cumsum(np.c_[np.cos(head), np.sin(head)] * 0.27, axis=0)])
    xy = xy - (xy.min(axis=0) + xy.max(axis=0)) / 2 + np.array([-1.15, -0.1])
    a2.plot(xy[:, 0], xy[:, 1], "o", color=INK, ms=2.6, zorder=4)
    for k in range(len(head)):
        a2.annotate("", xy=xy[k + 1], xytext=xy[k], arrowprops=dict(arrowstyle="-|>", lw=1.6, mutation_scale=10,
                    color=FLY if inside[k] else GREY, shrinkA=2, shrinkB=2), zorder=3)
    c = np.array([0.95, -0.38])
    a2.add_patch(mpatches.Wedge(c, 0.92, np.degrees(lo_a), np.degrees(lo_a + width), fc="#fbe3cf", ec="none",
                                zorder=1))
    for h, ok in zip(head, inside):
        a2.annotate("", xy=c + 0.76 * np.array([np.cos(h), np.sin(h)]), xytext=c,
                    arrowprops=dict(arrowstyle="-|>", lw=1.5, mutation_scale=9, color=FLY if ok else GREY,
                                    shrinkA=0, shrinkB=0), zorder=3)
    a2.text(c[0] + 0.72, c[1] + 0.62, "1.7 rad", fontsize=15, color=INK, ha="left", va="bottom", path_effects=HALO)
    a2.text(-1.15, 0.9, "track", fontsize=14, color=GREY, ha="center", va="bottom")
    a2.text(c[0] + 0.1, 0.9, "its headings", fontsize=14, color=GREY, ha="center", va="bottom")
    a2.text(0.0, 1.3, "flight", fontsize=17, color=FLY, fontweight="bold", ha="center", va="bottom")
    a2.text(0.0, -1.18, "≥ 80% of the headings in the arc", fontsize=15, color=INK, ha="center", va="top")
    a2.set_xlim(-2.25, 2.45)
    a2.set_ylim(-1.6, 1.62)
    a1.set_ylim(-1.6, 1.62)
    for ax in (a1, a2):
        ax.set_aspect("equal")
        ax.axis("off")
    fig.tight_layout(w_pad=0.5)
    save(fig, "geese-criteria.svg")


def fig_criteria_attributes():
    """Four kinds of criteria for a segment: speed range, heading arc, disk, duration (schematic)."""
    rng = np.random.default_rng(5)
    fig, axs = plt.subplots(1, 4, figsize=(12.4, 2.45))
    texts = ["speed:\nhighest ≤ 2 × lowest", "heading:\nwithin an arc $\\alpha$", "location:\nwithin a disk, radius $r$",
             "duration:\nat least $\\Delta t$"]
    # speed
    ax = axs[0]
    v = [3.4, 4.6, 3.9, 6.1, 4.4, 5.3, 3.6]
    ax.bar(np.arange(len(v)), v, width=0.6, color=STOP, zorder=2)
    for y, lab in ((min(v), "lowest"), (2 * min(v), "2 × lowest")):
        ax.plot([-0.5, len(v) - 0.4], [y, y], color=INK, lw=1.0, ls=(0, (3, 2)), zorder=3)
        ax.text(len(v) - 0.2, y, lab, fontsize=14, color=INK, ha="left", va="center")
    ax.set_xlim(-0.6, len(v) + 3.6)
    ax.set_ylim(0, 7.4)
    # heading
    ax = axs[1]
    lo_a, w = np.radians(25), np.radians(97)
    ax.add_patch(mpatches.Wedge((0, 0), 0.92, np.degrees(lo_a), np.degrees(lo_a + w), fc="#d5ecf8", ec="none",
                                zorder=1))
    for h in np.radians([31, 48, 60, 77, 95, 113]):
        ax.annotate("", xy=(0.82 * np.cos(h), 0.82 * np.sin(h)), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="-|>", lw=1.6, mutation_scale=10, color=STOP, shrinkA=0, shrinkB=0))
    arc = np.linspace(lo_a, lo_a + w, 50)
    ax.plot(1.02 * np.cos(arc), 1.02 * np.sin(arc), color=INK, lw=1.0)
    ax.text(1.16 * np.cos(lo_a + w / 2), 1.16 * np.sin(lo_a + w / 2), "$\\alpha$", fontsize=17, color=INK,
            ha="center", va="bottom")
    ax.set_xlim(-1.4, 1.4)
    ax.set_ylim(-0.15, 1.45)
    ax.set_aspect("equal")
    # location
    ax = axs[2]
    pts = _walk(rng, 30, 0.22, 0.8)
    ax.plot(pts[:, 0], pts[:, 1], "-", color=STOP, lw=0.9, alpha=0.6)
    ax.plot(pts[:, 0], pts[:, 1], "o", color=STOP, ms=2.6)
    t = np.linspace(0, 2 * np.pi, 200)
    ax.plot(np.cos(t), np.sin(t), color=INK, lw=1.2, ls=(0, (3, 2)))
    tip = np.array([np.cos(-0.5), np.sin(-0.5)])
    ax.annotate("", xy=tip, xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", lw=1.2, mutation_scale=10, color=INK,
                shrinkA=0, shrinkB=0))
    ax.text(*(tip * 1.13), "$r$", fontsize=17, color=INK, ha="left", va="top")
    ax.set_xlim(-1.5, 1.6)
    ax.set_ylim(-1.15, 1.1)
    ax.set_aspect("equal")
    # duration
    ax = axs[3]
    ts = np.sort(rng.uniform(0, 10, 14))
    ax.plot([0, 10], [0, 0], color=GREY, lw=1.2)
    ax.plot(ts, np.zeros_like(ts), "o", color=STOP, ms=4)
    _bracket(ax, ts[2], ts[11], 0.55, STOP, lw=1.8)
    ax.text((ts[2] + ts[11]) / 2, 0.7, "≥ $\\Delta t$", fontsize=16, color=INK, ha="center", va="bottom")
    ax.text(10.2, 0, "time", fontsize=14, color=GREY, ha="left", va="center")
    ax.set_xlim(-0.5, 12.2)
    ax.set_ylim(-0.6, 1.5)
    for ax in axs:
        ax.axis("off")
    fig.subplots_adjust(wspace=0.25, bottom=0.36, top=0.98, left=0.01, right=0.99)
    for ax, txt in zip(axs, texts):
        box = ax.get_position()
        fig.text((box.x0 + box.x1) / 2, 0.02, txt, fontsize=16.5, color=INK, ha="center", va="bottom",
                 linespacing=1.15)
    save(fig, "criteria-attributes.svg")


def fig_monotone(kind):
    """Decreasing monotone: every subsegment of a valid segment is valid; increasing monotone: every
    supersegment of a valid segment is valid (schematic)."""
    n = 10
    fig, ax = plt.subplots(figsize=(6.0, 1.9))
    ax.plot([-0.3, n - 0.7], [0, 0], color=GREY, lw=1.0, zorder=1)
    ax.plot(np.arange(n), np.zeros(n), "o", color=GREY, ms=5, zorder=2)
    if kind == "decreasing":
        main, others, lab = (1, 8), [(2, 4), (4, 7)], "subsegments"
    else:
        main, others, lab = (4, 6), [(2, 7), (0, 8)], "supersegments"
    _bracket(ax, main[0] - 0.25, main[1] + 0.25, 0.75, STOP, lw=2.6)
    ax.text(n - 0.2, 0.75, "valid segment", fontsize=17, color=STOP, ha="left", va="center", fontweight="bold")
    for k, (a, b) in enumerate(others):
        y = -0.65 - 0.55 * k
        _bracket(ax, a - 0.25, b + 0.25, y, STOP, lw=1.8, up=False)
    ax.text(n - 0.2, -0.65 - 0.55 * (len(others) - 1) / 2, f"{lab}:\nvalid as well", fontsize=17, color=INK,
            ha="left", va="center", linespacing=1.1)
    ax.set_xlim(-0.6, n + 5.2)
    ax.set_ylim(-1.55, 1.05)
    ax.axis("off")
    save(fig, f"monotone-{kind}.svg")


def fig_stays_ahead():
    """Greedy stays ahead on the speeds of slide 10: after k segments, greedy (g_k) is at least as far as any
    other valid segmentation (o_k)."""
    g = greedy(SPEEDS, factor2)                                   # [(0, 2), (3, 5), (6, 7), (8, 10)]
    other = [(0, 1), (2, 3), (4, 5), (6, 7), (8, 10)]             # also valid, five segments
    assert all(factor2(SPEEDS[i:j + 1]) for i, j in other)
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    x = np.arange(len(SPEEDS))
    hs = 0.55 * np.array(SPEEDS)                                  # bars drawn smaller, labelled with the speeds
    ax.bar(x, hs, color="#c9c9c6", width=0.62, zorder=2)
    for xi, v, h in zip(x, SPEEDS, hs):
        ax.text(xi, h + 0.1, str(v), ha="center", va="bottom", fontsize=15, color=INK, zorder=3)
        ax.text(xi, -0.42, str(xi + 1), ha="center", va="center", fontsize=13.5, color=GREY)
    ax.text(-0.85, -0.42, "step", fontsize=13.5, color=GREY, ha="right", va="center")
    rows = [("greedy", g, -2.05, "g"), ("another valid\nsegmentation", other, -3.95, "o")]
    ends = {}
    for name, segs, y, sym in rows:
        for k, (i, j) in enumerate(segs):
            col = COL[k % 2] if sym == "g" else "#7d7f7b"
            for fill in (True, False):
                ax.add_patch(mpatches.FancyBboxPatch((i - 0.4, y - 0.38), j - i + 0.8, 0.76,
                             boxstyle="round,pad=0.02,rounding_size=0.18", fc=col if fill else "none",
                             ec="none" if fill else col, lw=1.5, alpha=(0.22 if sym == "g" else 0.18) if fill else 1,
                             zorder=2 if fill else 3))
            if sym == "g":
                ax.text(j + 0.4, y + 0.48, f"$g_{k + 1}$", fontsize=15.5, color=INK, ha="center", va="bottom")
            else:
                ax.text(j + 0.4, y - 0.5, f"$o_{k + 1}$", fontsize=15.5, color=INK, ha="center", va="top")
            ends[(sym, k)] = j + 0.4
        ax.text(-0.85, y, name, fontsize=15, color=INK, ha="right", va="center", linespacing=1.1)
    for k in range(len(g)):
        ax.annotate("", xy=(ends[("g", k)], -2.48), xytext=(ends[("o", k)], -3.52),
                    arrowprops=dict(arrowstyle="-|>", lw=1.3, mutation_scale=11, color=INK, shrinkA=2, shrinkB=2),
                    zorder=4)
    ax.set_xlim(-4.4, len(SPEEDS) - 0.3)
    ax.set_ylim(-5.1, 6.0)
    ax.axis("off")
    save(fig, "greedy-stays-ahead.svg")



def fig_start_stop_steps():
    """Animation frames for the start-stop diagram of DIAGRAM: start-stop-step-1..6.svg build the diagram (one
    valid cell, one invalid cell, all cells, greedy gets stuck, a staircase); start-stop-dp-1..8.svg fill the values
    S column by column and backtrack the optimal staircase. All frames have the same size (fragments on one slide)."""
    n = len(DIAGRAM)
    S, segs = dp_prefix(DIAGRAM, range4)                         # S[e]: fewest segments for steps 1..e
    valid = {(i, j): range4(DIAGRAM[i:j + 1]) for i in range(n) for j in range(i, n)}
    UNK, BAD = "#efefec", "#c9c9c6"
    inf = lambda v: "∞" if v == np.inf else f"{int(v)}"

    def frame(name, shown=(), focus=None, caption="", stair=None, greedy_cell=None, stuck_row=None, s_upto=None,
              col=None, best=None, cols_done=(), dp=False):
        low = -2.75                                               # room for the values S (slide 17), on every frame
        fig, ax = plt.subplots(figsize=(6.0, 7.3))                # so that the diagram does not move between slides
        ax.add_patch(mpatches.Rectangle((-2.0, low), n + 2.3, n + 2.1 - low, fc="white", ec="none", zorder=0))
        for (i, j), ok in valid.items():
            seen = shown == "all" or (i, j) in shown
            ax.add_patch(mpatches.Rectangle((j, n - 1 - i), 1, 1, fc=("white" if ok else BAD) if seen else UNK,
                                            ec="#9a9a96", lw=0.8, zorder=1))
        if col is not None:                                       # the column of the current step
            ax.add_patch(mpatches.Rectangle((col, n - 1 - col), 1, col + 1, fill=False, ec=STOP, lw=2.6, zorder=4))
            for i in range(col + 1):
                if valid[(i, col)]:
                    v = S[i] + 1
                    ax.text(col + 0.5, n - 1 - i + 0.5, inf(v), ha="center", va="center", fontsize=15,
                            color=INK if i == best else GREY, fontweight="bold" if i == best else "normal", zorder=5)
            if best is not None:
                ax.add_patch(mpatches.Rectangle((col + 0.1, n - 1 - best + 0.1), 0.8, 0.8, fill=False, ec=STOP,
                                                lw=2.2, zorder=5))
        if focus is not None:
            i, j = focus
            c = STOP if valid[focus] else COL[2]
            ax.add_patch(mpatches.Rectangle((j + 0.04, n - 1 - i + 0.04), 0.92, 0.92, fill=False, ec=c, lw=3.2,
                                            zorder=5))
            _bracket(ax, i + 0.1, j + 0.9, n + 1.45, c, lw=2.4, h=0.2)        # the steps of the segment, on top
        if greedy_cell is not None:
            i, j = greedy_cell
            ax.add_patch(mpatches.Rectangle((j + 0.14, n - 1 - i + 0.14), 0.72, 0.72, fc=FLY, ec="none", zorder=5))
        if stuck_row is not None:
            ax.add_patch(mpatches.Rectangle((stuck_row + 0.04, n - 1 - stuck_row + 0.04), n - stuck_row - 0.08,
                                            0.92, fill=False, ec=COL[2], lw=3.0, zorder=5))
        if stair is not None:
            for k, (i, j) in enumerate(stair):
                ax.add_patch(mpatches.Rectangle((j + 0.14, n - 1 - i + 0.14), 0.72, 0.72, fc=COL[k % 2], ec="none",
                                                zorder=5))
                if k + 1 < len(stair):
                    i2, j2 = stair[k + 1]
                    ax.annotate("", xy=(j2 + 0.5, n - 1 - i2 + 0.5), xytext=(j + 0.5, n - 1 - i + 0.5),
                                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.8, mutation_scale=15, shrinkA=10,
                                                shrinkB=10), zorder=6)
        if s_upto is not None:                                    # the values S below the columns
            ax.text(-0.3, -0.7, "$S$", ha="right", va="center", fontsize=17, color=INK)
            for j in range(n):
                if j + 1 <= s_upto or j + 1 in cols_done:
                    val = S[j + 1]
                    ax.text(j + 0.5, -0.7, inf(val), ha="center", va="center", fontsize=17,
                            color=GREY if val == np.inf else INK, fontweight="bold")
        for t, v in enumerate(DIAGRAM):                           # step number (grey) and speed (black)
            ax.text(t + 0.5, n + 0.1, str(t + 1), ha="center", va="bottom", fontsize=12, color=GREY)
            ax.text(t + 0.5, n + 0.5, str(v), ha="center", va="bottom", fontsize=16, color=INK)
            ax.text(-0.12, n - 1 - t + 0.5, str(t + 1), ha="right", va="center", fontsize=12, color=GREY)
            ax.text(-0.55, n - 1 - t + 0.5, str(v), ha="right", va="center", fontsize=16, color=INK)
        ax.text(n / 2, n + 1.75, "last step of the segment", ha="center", va="bottom", fontsize=14, color=GREY)
        ax.text(-1.45, n / 2, "first step of the segment", ha="center", va="center", fontsize=14, color=GREY,
                rotation=90)
        ax.text(n / 2 - 0.5, -1.45 if dp else -0.55, caption, ha="center", va="top", fontsize=16, color=INK,
                linespacing=1.25)
        ax.set_xlim(-2.0, n + 0.3)
        ax.set_ylim(low, n + 2.1)
        ax.set_aspect("equal")
        ax.axis("off")
        save_opaque(fig, name)

    # the concept, step by step
    frame("start-stop-step-1.svg", caption="cell $(i, j)$: the segment\nfrom step $i$ to step $j$")
    frame("start-stop-step-2.svg", shown={(0, 1)}, focus=(0, 1), caption="steps 1–2: speeds 2, 3\nrange 1: valid")
    frame("start-stop-step-3.svg", shown={(0, 1), (0, 3)}, focus=(0, 3),
          caption="steps 1–4: speeds 2, 3, 5, 8\nrange 6: not valid")
    frame("start-stop-step-4.svg", shown="all", caption="white: valid segments\n(a single step is too short)")
    g_end = greedy_first(DIAGRAM, range4)
    frame("start-stop-step-5.svg", shown="all", greedy_cell=(0, g_end), stuck_row=g_end + 1,
          caption=f"greedy: steps 1–{g_end + 1}, then row {g_end + 2}\nhas no white cell: stuck")
    frame("start-stop-step-6.svg", shown="all", stair=segs,
          caption="segmentation = staircase:\n" + ", ".join(f"{i + 1}–{j + 1}" for i, j in segs))
    # the dynamic program, column by column
    frame("start-stop-dp-1.svg", shown="all", s_upto=0, dp=True,
          caption="$S(j)$: fewest segments for steps $1..j$\n$S(0)=0$")
    steps = [(0, None, "column 1: no white cell\n$S(1)=\\infty$"),
             (1, 0, "column 2: start 1\n$S(2)=S(0)+1=1$"),
             (2, 0, "column 3: starts 1, 2\n$S(3)=\\min(S(0)+1,\\ S(1)+1)=1$"),
             (3, 2, "column 4: start 3\n$S(4)=S(2)+1=2$"),
             (4, None, "column 5: no white cell\n$S(5)=\\infty$")]
    for k, (c, b, cap) in enumerate(steps):
        frame(f"start-stop-dp-{k + 2}.svg", shown="all", s_upto=c + 1, col=c, best=b, caption=cap, dp=True)
    frame("start-stop-dp-7.svg", shown="all", s_upto=n, col=n - 1, best=segs[-1][0], dp=True,
          caption="columns 6–8: best start 5\n$S(8)=S(4)+1=3$")
    frame("start-stop-dp-8.svg", shown="all", s_upto=n, stair=segs[::-1], dp=True,
          caption="back from $S(8)$: " + ", ".join(f"{i + 1}–{j + 1}" for i, j in segs[::-1]))


def fig_start_stop_blocks():
    """The idea of the O(n log n) dynamic program (Alewijnse et al. 2014) on the diagram of DIAGRAM, same canvas as
    the frames of fig_start_stop_steps: in every column the white cells form one block (AND of a decreasing and an
    increasing monotone criterion); start-stop-blocks-1.svg outlines the blocks, start-stop-blocks-2.svg shows the
    range-minimum query for the last column. Returns the blocks as (column, first start, last start), 0-based."""
    n = len(DIAGRAM)
    S, segs = dp_prefix(DIAGRAM, range4)
    valid = {(i, j): range4(DIAGRAM[i:j + 1]) for i in range(n) for j in range(i, n)}
    BAD = "#c9c9c6"
    inf = lambda v: "∞" if v == np.inf else f"{int(v)}"
    blocks = []
    for j in range(n):
        i = 0
        while i <= j:
            if valid[(i, j)]:
                a = i
                while i + 1 <= j and valid[(i + 1, j)]:
                    i += 1
                blocks.append((j, a, i))
            i += 1
    jq, aq, bq = blocks[-1]                                       # the query of the last column

    def frame(name, query, caption):
        fig, ax = plt.subplots(figsize=(6.0, 7.3))
        ax.add_patch(mpatches.Rectangle((-2.0, -2.75), n + 2.3, n + 4.85, fc="white", ec="none", zorder=0))
        for (i, j), ok in valid.items():
            ax.add_patch(mpatches.Rectangle((j, n - 1 - i), 1, 1, fc="white" if ok else BAD, ec="#9a9a96", lw=0.8,
                                            zorder=1))
        for j, a, b in blocks:
            hot = query and j == jq
            ax.add_patch(mpatches.FancyBboxPatch((j + 0.12, n - 1 - b + 0.12), 0.76, b - a + 0.76,
                                                 boxstyle="round,pad=0,rounding_size=0.14", fill=False,
                                                 ec=FLY if hot else STOP, lw=3.0, zorder=4))
        ax.text(-0.3, -0.7, "$S$", ha="right", va="center", fontsize=17, color=INK)
        for j in range(n):
            val = S[j + 1]
            ax.text(j + 0.5, -0.7, inf(val), ha="center", va="center", fontsize=17,
                    color=GREY if val == np.inf else INK, fontweight="bold")
        if query:                                                 # S(aq) .. S(bq): under the columns aq-1 .. bq-1
            ax.add_patch(mpatches.FancyBboxPatch((aq - 1 + 0.08, -1.08), bq - aq + 0.84, 0.76, fill=False, ec=FLY,
                                                 lw=3.0, boxstyle="round,pad=0,rounding_size=0.14", zorder=4))
        for t, v in enumerate(DIAGRAM):                           # step number (grey) and speed (black)
            ax.text(t + 0.5, n + 0.1, str(t + 1), ha="center", va="bottom", fontsize=12, color=GREY)
            ax.text(t + 0.5, n + 0.5, str(v), ha="center", va="bottom", fontsize=16, color=INK)
            ax.text(-0.12, n - 1 - t + 0.5, str(t + 1), ha="right", va="center", fontsize=12, color=GREY)
            ax.text(-0.55, n - 1 - t + 0.5, str(v), ha="right", va="center", fontsize=16, color=INK)
        ax.text(n / 2, n + 1.75, "last step of the segment", ha="center", va="bottom", fontsize=14, color=GREY)
        ax.text(-1.45, n / 2, "first step of the segment", ha="center", va="center", fontsize=14, color=GREY,
                rotation=90)
        ax.text(n / 2 - 0.5, -1.45, caption, ha="center", va="top", fontsize=16, color=INK, linespacing=1.25)
        ax.set_xlim(-2.0, n + 0.3)
        ax.set_ylim(-2.75, n + 2.1)
        ax.set_aspect("equal")
        ax.axis("off")
        save_opaque(fig, name)

    frame("start-stop-blocks-1.svg", False,
          f"at most one block of white cells\nper column: {len(blocks)} blocks in total")
    frame("start-stop-blocks-2.svg", True,
          f"column {jq + 1}: starts {aq + 1}–{bq + 1}, one query\n"
          f"$S({jq + 1})=\\min(S({aq}),\\,S({aq + 1}),\\,S({bq}))+1={inf(S[jq + 1])}$")
    return blocks


def fig_optimal_partitioning():
    """Sketch of the recurrence of optimal partitioning: the best cost F(s) for x_1..x_s (computed before) plus the
    last segment x_{s+1}..x_t with its misfit c(s, t) (squared deviations from its mean) and the penalty beta
    (constructed data)."""
    rng = np.random.default_rng(4)
    mu = np.array([1.0] * 9 + [3.6] * 8 + [2.2] * 9)
    x = mu + rng.normal(0, 0.33, len(mu))
    n, s = len(x), 17                                             # last segment: x_18 .. x_26
    fig, ax = plt.subplots(figsize=(8.8, 3.4))
    t = np.arange(1, n + 1)
    ax.axvspan(s + 0.5, n + 0.5, color="#d5ecf8", zorder=0, lw=0)
    for a, b in ((0, 9), (9, s)):                                  # the best segmentation of x_1 .. x_s
        ax.plot([a + 0.6, b + 0.4], [x[a:b].mean()] * 2, color=GREY, lw=2.2, ls=(0, (4, 3)), zorder=2)
    ax.plot(t[:s], x[:s], "o", color=GREY, ms=6.5, zorder=3)
    m = x[s:].mean()
    for i in range(s, n):
        ax.plot([i + 1, i + 1], [m, x[i]], color=STOP, lw=1.4, zorder=2)
    ax.plot([s + 0.6, n + 0.4], [m, m], color=STOP, lw=2.8, zorder=2)
    ax.plot(t[s:], x[s:], "o", color=STOP, ms=6.5, zorder=3)
    top = 6.55
    ax.text((1 + s) / 2, top, "$F(s)$: cheapest for $x_1,\\dots,x_s$\n(computed before)", ha="center", va="top",
            fontsize=18, color=INK, linespacing=1.2)
    ax.text((s + 1 + n) / 2, top, "last segment\n$c(s,t)+\\beta$", ha="center", va="top", fontsize=18,
            color=STOP, fontweight="bold", linespacing=1.2)
    ax.text(n + 0.6, m, "mean", fontsize=16, color=STOP, ha="left", va="center")
    for pos, lab in ((s, "$s$"), (n, "$t$")):
        ax.plot([pos + 0.5, pos + 0.5], [-0.25, 0.05], color=INK, lw=1.2)
        ax.text(pos + 0.5, -0.35, lab, ha="center", va="top", fontsize=19, color=INK)
    ax.plot([0.5, n + 0.5], [0.05, 0.05], color=GREY, lw=1.0)
    ax.set_xlim(0.2, n + 3.0)
    ax.set_ylim(-1.1, 6.6)
    ax.axis("off")
    save(fig, "optimal-partitioning.svg")

# ---------------------------------------------------------------- the geese of Kölzsch et al. (2016)
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


# ---------------------------------------------------------------- the running example: goose 3104, spring 2014
GOOSE, YEAR = "3104", 2014
RADIUS, HOURS, ARC, INLIERS = 30.0, 48.0, 1.7, 0.8   # the geese criteria of Alewijnse et al. (2014)
MIN_KM = 0.1                                         # distances below 100 m per hour count as 100 m (GPS noise)
BETA = 8.0                                           # change points: penalty per segment, in (log10 km)^2
MOVING = 0.0                                         # change points: segment mean of log10 km above 0 (1 km/h) = flight
K_HMM = 4
GOOSE_PROJ = lambda lo, la: laea(lo, la, 27, 60.5)
GOOSE_BOX = (-1640, 1420, -1080, 1250)


def load_goose():
    """All GPS fixes of the goose's spring migration and one position per full hour (the nearest fix within
    20 minutes), with the ecologists' label of that fix."""
    g = pd.read_csv(GEESE_CSV, parse_dates=["timestamp"])
    g = g[(g["visible"] == True) & (g["individual-local-identifier"].astype(str) == GOOSE)       # noqa: E712
          & (g["migration-stage-standard"] == "spring-migration") & (g["timestamp"].dt.year == YEAR)]
    g = g.sort_values("timestamp").set_index("timestamp")
    hours = pd.date_range(g.index[0].ceil("h"), g.index[-1].floor("h"), freq="h")
    idx = g.index.get_indexer(hours, method="nearest", tolerance=pd.Timedelta("20min"))
    H = g.iloc[idx[idx >= 0]].copy()
    H.index = hours[idx >= 0]
    return g, H


def expert_stopovers(g):
    """Runs of fixes labelled 'stopover' in the full-resolution data: (first time, last time, lat, lon)."""
    lab = g["migration-stage"].values
    out = []
    for kind, a, b in runs(list(lab)):
        if kind == "stopover":
            out.append((g.index[a], g.index[b], g["location-lat"].values[a:b + 1].mean(),
                        g["location-long"].values[a:b + 1].mean()))
    return out


def day_axis(ax, t0, days, every=14, labels=True):
    ticks = np.arange(0, days + 0.01, every)
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{(t0 + pd.Timedelta(days=float(d))).day} {(t0 + pd.Timedelta(days=float(d))):%b}"
                        for d in ticks] if labels else [])
    ax.tick_params(axis="x", labelsize=12.5, colors=INK, length=3, color=GREY)


def log_km_axis(ax, label=True):
    ax.set_yticks([-1, 0, 1, 2])
    ax.set_yticklabels(["≤ 0.1 km", "1 km", "10 km", "100 km"])
    ax.set_ylim(-1.35, 2.2)
    ax.grid(axis="y", color="#e2e2df", lw=0.8, zorder=0)
    ax.tick_params(axis="y", labelsize=12.5, colors=INK, length=0)
    if label:
        ax.set_ylabel("distance per hour (log scale)", fontsize=13, color=INK)


def fig_goose(g, H, x, stops, with_labels, name):
    """Map of the hourly positions and the distance per hour over time; with the ecologists' labels if asked."""
    proj, box = GOOSE_PROJ, GOOSE_BOX
    px, py = proj(H["location-long"].values, H["location-lat"].values)
    t0 = H.index[0]
    days = (H.index - t0).total_seconds().values / 86400
    lab = np.where(H["migration-stage"].values[1:] == "stopover", "stop", "fly")
    fig = plt.figure(figsize=(12.6, 5.3))
    ax = fig.add_axes([0.0, 0.0, 0.40, 1.0])
    basemap(ax, proj, box, tol=6, lakes=True)
    if not with_labels:
        ax.plot(px, py, "-", color=INK, lw=1.0, zorder=2, solid_capstyle="round")
    else:
        for kind, a, b in runs(list(lab)):
            ax.plot(px[a:b + 2], py[a:b + 2], "-", color=STATE[kind][1], lw=2.0 if kind == "fly" else 1.0,
                    zorder=2 if kind == "stop" else 3, solid_capstyle="round")
        for k, (ta, tb, la, lo) in enumerate(stops):
            cx, cy = proj(lo, la)
            d = (tb - ta).total_seconds() / 86400
            ax.plot(cx, cy, "o", ms=6 + 1.6 * np.sqrt(d) * 2, color=STOP, mec="white", mew=1.4, alpha=0.9, zorder=4)
    for (lat, lon), text, (dx, dy, ha, va) in [((H["location-lat"].iloc[0], H["location-long"].iloc[0]),
                                                f"Netherlands\n{t0.day} {t0:%b} {t0.year}", (40, -60, "left", "top")),
                                               ((H["location-lat"].iloc[-1], H["location-long"].iloc[-1]),
                                                f"Kolguev Island\n{H.index[-1].day} {H.index[-1]:%b}",
                                                (-60, 40, "right", "bottom"))]:
        cx, cy = proj(lon, lat)
        ax.plot(cx, cy, "o", ms=10, color=INK, mec="white", mew=1.6, zorder=6)
        ax.text(cx + dx, cy + dy, text, fontsize=13.5, color=INK, ha=ha, va=va, path_effects=HALO, zorder=7,
                linespacing=1.15)
    scalebar(ax, box[0] + 60, box[3] - 170, 500)

    bx = fig.add_axes([0.47, 0.13, 0.52, 0.82])
    if with_labels:
        for ta, tb, _la, _lo in stops:
            a, b = (ta - t0).total_seconds() / 86400, (tb - t0).total_seconds() / 86400
            bx.axvspan(a, b, color=LIGHT_BAND, lw=0, zorder=0)
        cols = np.where(lab == "stop", STOP, FLY)
    else:
        cols = np.full(len(x), INK)
    bx.scatter(days[1:], x, s=5, c=cols, lw=0, zorder=2, rasterized=True)
    log_km_axis(bx)
    bx.set_xlim(-0.5, days[-1] + 0.5)
    day_axis(bx, t0, days[-1])
    clean(bx, left=False)
    handles = [mpatches.Patch(color=LIGHT_BAND, label="stopover (ecologists)"),
               plt.Line2D([], [], marker="o", ls="", color=STOP, ms=6, label="hour at a stopover"),
               plt.Line2D([], [], marker="o", ls="", color=FLY, ms=6, label="hour in a flight phase")]
    leg = bx.legend(handles=handles, loc="upper left", frameon=False, fontsize=12.5, ncol=3, handlelength=1.0,
                    bbox_to_anchor=(0.0, 1.11), columnspacing=1.2)
    if not with_labels:                         # same layout as the labelled version, for the overlay on the slide
        for t in leg.get_texts():
            t.set_alpha(0)
        for h in leg.legend_handles:
            h.set_alpha(0)
    (save_opaque if with_labels else save)(fig, name)


def fig_methods(H, x, rows, name):
    """Distance per hour and, below, one strip per method. rows: (title, labels per hour, colours by label)."""
    t0 = H.index[0]
    days = (H.index - t0).total_seconds().values / 86400
    fig, axs = plt.subplots(1 + len(rows), 1, figsize=(12.6, 2.1 + 0.78 * len(rows)), sharex=True,
                            gridspec_kw=dict(height_ratios=[2.2] + [0.55] * len(rows), hspace=0.3))
    ax = axs[0]
    ax.scatter(days[1:], x, s=4, c=INK, lw=0, zorder=2, rasterized=True)
    log_km_axis(ax, label=False)
    clean(ax, left=False)
    ax.tick_params(axis="x", length=0)
    ax.text(-0.5, 2.32, "distance per hour (log scale)", fontsize=12.5, color=GREY, ha="left", va="bottom")
    for bx, (title, lab, colours) in zip(axs[1:], rows):
        for kind, a, b in runs(list(lab)):
            bx.add_patch(mpatches.Rectangle((days[a + 1] - 1 / 48, 0), days[b + 1] - days[a + 1] + 1 / 24, 1,
                                            fc=colours[kind], ec="none"))
        bx.set_ylim(0, 1)
        bx.set_yticks([])
        for sp in ["top", "right", "left", "bottom"]:
            bx.spines[sp].set_visible(False)
        bx.text(-2.0, 0.5, title, fontsize=13, color=INK, ha="right", va="center", linespacing=1.12)
        bx.tick_params(axis="x", length=0)
    axs[-1].set_xlim(-0.5, days[-1] + 0.5)
    day_axis(axs[-1], t0, days[-1])
    axs[-1].tick_params(axis="x", length=0, pad=4)
    handles = [mpatches.Patch(color=STOP, label="stopover"), mpatches.Patch(color=FLY, label="flight")]
    axs[0].legend(handles=handles, loc="upper right", frameon=False, fontsize=12.5, ncol=len(handles),
                  handlelength=1.1, bbox_to_anchor=(1.0, 1.18), columnspacing=1.1)
    save(fig, name)


def fig_hmm(x, mu, sd, states):
    """Histogram of the log distances per hour with the K fitted emission densities (weighted by how often
    each state occurs in the Viterbi path). The tall bar at the noise floor is cut and labelled."""
    fig, bx = plt.subplots(figsize=(8.6, 4.2))
    edges = np.linspace(-1.1, 2.2, 34)
    counts, _, _ = bx.hist(np.maximum(x, -1.0), bins=edges, color="#d4d4d0", zorder=1)
    cap = 150
    width = edges[1] - edges[0]
    g = np.linspace(-1.1, 2.2, 600)
    for k in range(len(mu)):
        w = np.mean(states == k)
        dens = w * len(x) * width * np.exp(-0.5 * ((g - mu[k]) / sd[k]) ** 2) / (sd[k] * np.sqrt(2 * np.pi))
        bx.plot(g, dens, color=HMM_COLS[k], lw=2.6, zorder=2)
        peak = w * len(x) * width / (sd[k] * np.sqrt(2 * np.pi))
        med = 10 ** mu[k]
        txt = "≤ 0.1" if med < 0.15 else (f"{med:.1f}" if med < 10 else f"{med:.0f}")
        if k == 0:
            bx.text(-0.55, 92, f"{HMM_NAMES[k]}\n{txt} km/h", fontsize=13.5, color=HMM_COLS[k], fontweight="bold",
                    ha="left", va="bottom", path_effects=HALO, zorder=4, linespacing=1.1)
        else:
            bx.text(mu[k], min(peak, cap) + 6, f"{HMM_NAMES[k]}\n{txt} km/h", fontsize=13.5, color=HMM_COLS[k],
                    fontweight="bold", ha="center", va="bottom", path_effects=HALO, zorder=4, linespacing=1.1)
    bx.text(-0.55, cap * 0.97, f"{int(counts.max()):,} hours below 0.13 km (bar cut)", fontsize=12.5, color=INK,
            ha="left", va="top", path_effects=HALO, zorder=4)
    bx.set_ylim(0, cap)
    bx.set_xlim(-1.15, 2.25)
    bx.set_xticks([-1, 0, 1, 2])
    bx.set_xticklabels(["≤ 0.1 km", "1 km", "10 km", "100 km"])
    bx.set_yticks([])
    clean(bx, left=False)
    bx.tick_params(axis="x", labelsize=13, colors=INK, length=3, color=GREY)
    bx.set_xlabel("distance per hour (log scale)", fontsize=13.5, color=INK)
    save(fig, "geese-3104-hmm.svg")


def fig_hmm_zoom(H, x, states, first, last):
    """Four days hour by hour: distance per hour coloured by the Viterbi state, and the states as a strip."""
    t = H.index[1:]
    m = (t >= pd.Timestamp(first)) & (t <= pd.Timestamp(last))
    tt = (t[m] - pd.Timestamp(first)).total_seconds().values / 3600
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(11.4, 4.2), sharex=True,
                                 gridspec_kw=dict(height_ratios=[3.2, 0.5], hspace=0.12))
    for k in range(len(HMM_NAMES)):
        sel = states[m] == k
        ax.plot(tt[sel], x[m][sel], "o", color=HMM_COLS[k], ms=6.5, mew=0.8, mec="white", zorder=3,
                label=HMM_NAMES[k])
    ax.plot(tt, x[m], "-", color="#c4c4c0", lw=1.0, zorder=2)
    log_km_axis(ax)
    clean(ax, left=False)
    ax.tick_params(axis="x", length=0)
    ax.legend(loc="upper left", frameon=False, fontsize=12.5, ncol=4, handletextpad=0.2, columnspacing=1.2,
              bbox_to_anchor=(0.0, 1.16))
    for kind, a, b in runs(list(states[m])):
        bx.add_patch(mpatches.Rectangle((tt[a] - 0.5, 0), tt[b] - tt[a] + 1, 1, fc=HMM_COLS[kind], ec="white", lw=0.6))
    bx.set_ylim(0, 1)
    bx.set_yticks([])
    for sp in ["top", "right", "left", "bottom"]:
        bx.spines[sp].set_visible(False)
    ticks = np.arange(0, tt[-1] + 0.1, 12)
    bx.set_xticks(ticks)
    bx.set_xticklabels([f"{(pd.Timestamp(first) + pd.Timedelta(hours=float(h))).day} "
                        f"{(pd.Timestamp(first) + pd.Timedelta(hours=float(h))):%b %H:%M}" for h in ticks])
    bx.tick_params(axis="x", labelsize=12, colors=INK, length=3, color=GREY)
    bx.set_xlim(-1, tt[-1] + 1)
    bx.set_xlabel("UTC", fontsize=12, color=GREY)
    save(fig, "geese-3104-hmm-zoom.svg")


HMM_EX_STATES = ["rest", "rest", "flight", "flight", "rest"]      # schematic example of slide 21 (not the
HMM_EX_OBS = ["0.1 km", "0.4 km", "52 km", "38 km", "0.2 km"]     # Viterbi exercise, which has its own values)
HMM_EX_STAY = 0.9                                                # probability to stay in the state for another hour


def fig_hmm_model():
    """Schematic of a hidden Markov model with the states rest and flight: hidden states form a Markov chain, hour by
    hour; each state emits the distance of its hour, drawn from its own distribution (right; schematic, not fitted)."""
    cols = {"rest": STOP, "flight": FLY}
    fig = plt.figure(figsize=(13.4, 3.5))
    ax = fig.add_axes([0.0, 0.0, 0.71, 1.0])
    X = [1.75 * k for k in range(len(HMM_EX_STATES))]
    ys, yo = 1.7, 0.35
    for k, (st, ob) in enumerate(zip(HMM_EX_STATES, HMM_EX_OBS)):
        x = X[k]
        ax.text(x, 2.42, f"hour {k + 1}", ha="center", va="center", fontsize=14, color=GREY)
        ax.add_patch(mpatches.FancyBboxPatch((x - 0.55, ys - 0.26), 1.1, 0.52, fc=cols[st], ec="none", zorder=3,
                                             boxstyle="round,pad=0,rounding_size=0.24"))
        ax.text(x, ys, st, ha="center", va="center", fontsize=17, color="white", fontweight="bold", zorder=4)
        ax.annotate("", xy=(x, yo + 0.27), xytext=(x, ys - 0.28),
                    arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.6, mutation_scale=16, shrinkA=0, shrinkB=0))
        ax.add_patch(mpatches.FancyBboxPatch((x - 0.62, yo - 0.25), 1.24, 0.5, fc="#f1f1ee", ec="#c9c9c6", lw=1.0,
                                             zorder=3, boxstyle="round,pad=0,rounding_size=0.12"))
        ax.text(x, yo, ob, ha="center", va="center", fontsize=17, color=INK, zorder=4)
        if k + 1 < len(X):
            p = HMM_EX_STAY if HMM_EX_STATES[k + 1] == st else 1 - HMM_EX_STAY
            ax.annotate("", xy=(X[k + 1] - 0.6, ys), xytext=(x + 0.6, ys),
                        arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.8, mutation_scale=16, shrinkA=0, shrinkB=0))
            ax.text((x + X[k + 1]) / 2, ys + 0.12, f"{p:g}", ha="center", va="bottom", fontsize=15, color=INK)
    ax.text(-0.85, ys, "hidden state\n(not observed)", ha="right", va="center", fontsize=15, color=INK,
            linespacing=1.2)
    ax.text(-0.85, yo, "observed:\ndistance per hour", ha="right", va="center", fontsize=15, color=INK,
            linespacing=1.2)
    ax.set_xlim(-3.3, X[-1] + 0.75)
    ax.set_ylim(-0.05, 2.65)
    ax.set_aspect("equal")
    ax.axis("off")
    bx = fig.add_axes([0.765, 0.2, 0.225, 0.56])                 # the distribution of the distance in each state
    g = np.linspace(-1.4, 2.4, 400)
    for st, mu, sd in [("rest", np.log10(0.2), 0.33), ("flight", np.log10(45), 0.3)]:
        dens = np.exp(-0.5 * ((g - mu) / sd) ** 2)
        bx.fill_between(g, dens, color=cols[st], alpha=0.18, lw=0)
        bx.plot(g, dens, color=cols[st], lw=2.6)
        bx.text(mu, 1.06, st, ha="center", va="bottom", fontsize=15, color=cols[st], fontweight="bold")
    bx.set_xlim(-1.4, 2.4)
    bx.set_ylim(0, 1.32)
    bx.set_xticks([-1, 0, 1, 2])
    bx.set_xticklabels(["0.1 km", "1 km", "10 km", "100 km"])
    bx.set_yticks([])
    clean(bx, left=False)
    bx.tick_params(axis="x", labelsize=13, colors=INK, length=3, color=GREY)
    bx.set_title("distance per hour, by state", fontsize=15, color=INK, pad=6)
    save(fig, "hmm-model.svg")


# ---------------------------------------------------------------- Viterbi: a small example
V_OBS = ["0.2 km", "45 km", "3 km", "60 km", "0.3 km"]
V_EMIT = {"rest": [0, 8, 1, 8, 0], "flight": [5, 0, 2, 0, 5]}   # cost of each observation in each state
V_SWITCH = 2                                                   # cost of a change of state; staying costs 0


def viterbi_costs():
    """Min-cost path through the trellis (costs = rounded -log probabilities): V[t][s], the chosen predecessor
    back[t][s] and the best path."""
    states = ["rest", "flight"]
    V = [{s: V_EMIT[s][0] for s in states}]
    back = [{}]
    for t in range(1, len(V_OBS)):
        V.append({})
        back.append({})
        for s in states:
            best = min(states, key=lambda r: (V[t - 1][r] + (0 if r == s else V_SWITCH), r != s))
            V[t][s] = V[t - 1][best] + (0 if best == s else V_SWITCH) + V_EMIT[s][t]
            back[t][s] = best
    s = min(states, key=lambda r: V[-1][r])
    path = [s]
    for t in range(len(V_OBS) - 1, 0, -1):
        s = back[t][s]
        path.append(s)
    return V, back, path[::-1]


def fig_trellis_frames():
    """The Viterbi example as fragments of one slide, all frames of the same size: viterbi-trellis.svg (the exercise),
    viterbi-trellis-1..5.svg (hour by hour: the cheapest cost to reach each node, the chosen predecessor, the
    computation below) and viterbi-trellis-solution.svg (back from the cheapest end)."""
    V, back, path = viterbi_costs()
    states = ["rest", "flight"]
    ys = {"rest": 1.0, "flight": 0.0}
    cols = {"rest": STOP, "flight": FLY}
    n = len(V_OBS)
    sw = lambda r, s: 0 if r == s else V_SWITCH

    def frame(name, upto, caption, solution=False):
        fig, ax = plt.subplots(figsize=(10.2, 4.65))
        ax.add_patch(mpatches.Rectangle((-1.3, -1.12), n + 2.15, 3.27, fc="white", ec="none", zorder=0))
        if upto and not solution:                                 # the column computed in this frame
            ax.add_patch(mpatches.FancyBboxPatch((upto - 1.38, -0.62), 0.76, 2.74, fc="#f2eee4", ec="none",
                                                 zorder=0.5, boxstyle="round,pad=0,rounding_size=0.12"))
        for t in range(n - 1):
            for r in states:
                for s in states:
                    chosen = t + 1 < upto and back[t + 1][s] == r
                    if solution and chosen and path[t] == r and path[t + 1] == s:
                        c, lw, z = INK, 4.2, 2
                    elif chosen:
                        c, lw, z = ("#9a9a96" if solution else INK), 2.2, 1.5
                    else:
                        c, lw, z = "#d4d4d0", 1.3, 1
                    ax.plot([t, t + 1], [ys[r], ys[s]], "-", color=c, lw=lw, zorder=z, solid_capstyle="round")
        for t in range(n):
            ax.text(t, 1.62, V_OBS[t], ha="center", va="center", fontsize=17, color=INK)
            ax.text(t, 1.93, f"hour {t + 1}", ha="center", va="center", fontsize=14, color=GREY)
            for s in states:
                ax.add_patch(mpatches.Circle((t, ys[s]), 0.22, fc=cols[s], ec="white", lw=2, zorder=3))
                ax.text(t, ys[s], str(V_EMIT[s][t]), ha="center", va="center", fontsize=18, color="white",
                        fontweight="bold", zorder=4)
                if t < upto:
                    ax.text(t + 0.27, ys[s] + (0.2 if s == "rest" else -0.2), str(V[t][s]), ha="left",
                            va="bottom" if s == "rest" else "top", fontsize=17, color=INK, fontweight="bold",
                            path_effects=HALO, zorder=5)
        for s in states:
            ax.text(-0.42, ys[s], s, ha="right", va="center", fontsize=17, color=cols[s], fontweight="bold")
        ax.text(n - 1 + 0.45, 0.5, f"cost of a step:\nstay 0 ≈ $-\\ln 0.9$\nswitch {V_SWITCH} ≈ $-\\ln 0.1$", ha="left",
                va="center", fontsize=15, color=INK, linespacing=1.4)
        ax.text((n - 1) / 2, -0.88, caption, ha="center", va="center", fontsize=16.5, color=INK)
        ax.set_xlim(-1.3, n + 0.85)
        ax.set_ylim(-1.12, 2.15)
        ax.set_aspect("equal")
        ax.axis("off")
        save_opaque(fig, name)

    frame("viterbi-trellis.svg", 0, "in a node: the cost of that hour's distance in that state")
    frame("viterbi-trellis-1.svg", 1,
          f"hour 1: only the cost of the distance, rest {V[0]['rest']}, flight {V[0]['flight']}")
    for t in range(1, n):
        terms = {s: ", ".join(f"{V[t - 1][r]} + {sw(r, s)}" for r in states) for s in states}
        frame(f"viterbi-trellis-{t + 1}.svg", t + 1, f"hour {t + 1}: " + ",   ".join(
            f"{s} min({terms[s]}) + {V_EMIT[s][t]} = {V[t][s]}" for s in states))
    frame("viterbi-trellis-solution.svg", n,
          f"back from the cheapest end ({V[n - 1][path[-1]]}): " + ", ".join(path), solution=True)
    return V, path


# ---------------------------------------------------------------- global temperature (NASA GISTEMP v4)
GISTEMP = os.path.join(data_dir, "nasa-gistemp", "GLB.Ts+dSST.csv")
LAST_YEAR = 2025


def joinpoint_fit(t, y, taus):
    """Least-squares continuous piecewise-linear fit with slope changes at taus: SSE, fitted values, slopes."""
    X = np.column_stack([np.ones(len(t)), t - 1950] + [np.maximum(t - tau, 0) for tau in taus])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    fit = X @ coef
    r = y - fit
    return float(r @ r), fit, np.cumsum(coef[1:])


def best_joinpoints(t, y, k, step=1, gap=10, lo=1890, hi=2015):
    """Exhaustive search over change years in [lo, hi] (every `step` years, at least `gap` years apart). With
    step > 1, the coarse optimum is then improved year by year: move one change year at a time to its best
    position (all years), until nothing improves (a local optimum on the full grid)."""
    best = (np.inf, ())
    for taus in itertools.combinations(range(lo, hi + 1, step), k):
        if k > 1 and min(np.diff(taus)) < gap:
            continue
        s = joinpoint_fit(t, y, taus)[0]
        if s < best[0]:
            best = (s, taus)
    improved = step > 1
    while improved:
        improved = False
        for c in range(k):
            for year in range(lo, hi + 1):
                taus = tuple(sorted(best[1][:c] + (year,) + best[1][c + 1:]))
                if len(set(taus)) < k or (k > 1 and min(np.diff(taus)) < gap):
                    continue
                s = joinpoint_fit(t, y, taus)[0]
                if s < best[0] - 1e-12:
                    best, improved = (s, taus), True
    return best


def fig_temperature():
    T = pd.read_csv(GISTEMP, skiprows=1, na_values="***")[["Year", "J-D"]].dropna()
    T = T[T["Year"] <= LAST_YEAR]
    t, y = T["Year"].values.astype(float), T["J-D"].values.astype(float)
    n = len(y)
    fits = {}
    for k, step in ((0, 1), (1, 1), (2, 1), (3, 1), (4, 2)):
        s, taus = (joinpoint_fit(t, y, ())[0], ()) if k == 0 else best_joinpoints(t, y, k, step)
        bic = n * np.log(s / n) + (2 + 2 * k + 1) * np.log(n)        # iid Gaussian errors
        fits[k] = (s, taus, bic)
        slopes = joinpoint_fit(t, y, taus)[2] * 10
        print(f"   {k} change points {[int(v) for v in taus]}: SSE {s:.3f}, BIC (independent errors) {bic:.1f}, "
              f"slopes per decade {' '.join(f'{v:+.3f}' for v in slopes)}")
    taus3 = fits[3][1]
    s3, fit3, sl3 = joinpoint_fit(t, y, taus3)
    for extra in (1998, 2012):
        s, _f, sl = joinpoint_fit(t, y, tuple(sorted(taus3 + (extra,))))
        bic = n * np.log(s / n) + (2 + 2 * 4 + 1) * np.log(n)
        print(f"   three change points + {extra}: SSE {s:.3f} (gain {s3 - s:.3f}), BIC {bic:.1f} vs {fits[3][2]:.1f};"
              f" last slope {sl[-1] * 10:+.3f} per decade")
    for a, b in ((1998, 2012), (1970, 1997)):
        m = (t >= a) & (t <= b)
        print(f"   least-squares trend {a}-{b}: {np.polyfit(t[m], y[m], 1)[0] * 10:+.3f} °C per decade")

    fig, ax = plt.subplots(figsize=(11.0, 4.5))
    ax.plot(t, y, "o", color="#9a9a96", ms=4.2, mew=0, zorder=2)
    bounds = [t[0]] + list(taus3) + [t[-1]]
    segcols = [GREY, COL[2], GREY, COL[2]]
    for k in range(len(bounds) - 1):
        m = (t >= bounds[k]) & (t <= bounds[k + 1])
        ax.plot(t[m], fit3[m], "-", color=segcols[k], lw=3.2, zorder=3, solid_capstyle="round")
        xm = (bounds[k] + bounds[k + 1]) / 2
        ym = np.interp(xm, t, fit3)
        ax.text(xm, ym + (0.17 if k != 2 else 0.19), f"{sl3[k] * 10:+.2f} °C\nper decade".replace("-", "−"),
                ha="center",
                va="bottom", fontsize=13, color=segcols[k] if k % 2 else INK, fontweight="bold",
                path_effects=HALO, zorder=5, linespacing=1.1)
    for tau in taus3:
        ax.axvline(tau, color=GREY, lw=1.0, ls=(0, (3, 3)), zorder=1)
        ax.text(tau, -0.6, f"{int(tau)}", ha="center", va="bottom", fontsize=13, color=INK, zorder=5,
                bbox=dict(fc="white", ec="none", pad=1.5))
    s4, fit4, sl4 = joinpoint_fit(t, y, tuple(sorted(taus3 + (2012,))))
    m = t >= 2000
    ax.plot(t[m], fit4[m], "--", color=INK, lw=1.6, zorder=4, dashes=(4, 3))
    ax.text(2014.5, fit4[t == 2012][0] + 0.48, "with a change\nin 2012?", ha="right", va="bottom", fontsize=12.5,
            color=INK, path_effects=HALO, zorder=5, linespacing=1.1)
    ax.set_xlim(1876, 2029)
    ax.set_ylim(-0.66, 1.42)
    ax.set_yticks([-0.5, 0, 0.5, 1.0])
    ax.set_yticklabels(["−0.5 °C", "0 °C", "+0.5 °C", "+1.0 °C"])
    ax.grid(axis="y", color="#e2e2df", lw=0.8, zorder=0)
    clean(ax, left=False)
    ax.tick_params(labelsize=12.5, colors=INK, length=0)
    ax.set_ylabel("deviation from 1951–1980", fontsize=13, color=INK)
    save(fig, "gistemp-changepoints.svg")
    return t, y, fits


# ---------------------------------------------------------------- geese around New Year (Kölzsch et al. 2023)
NY_CSV = os.path.join(data_dir, "koelzsch2022-geese-new-year", "Goose flight around New Year in W-Europe 2014-2021.csv")
NY_FIT_TRACKS = 120                                    # tracks drawn at random (fixed seed) for fitting the model
NY_OTHER = [f"12-{d}" for d in range(20, 31)] + [f"01-{d:02d}" for d in range(2, 10)]   # other evenings


def new_year():
    g = pd.read_csv(NY_CSV, parse_dates=["timestamp"], low_memory=False)
    g = g[(g["visible"] == True) & g["ground-speed"].notna()]                                # noqa: E712
    g = g.sort_values(["individual-local-identifier", "timestamp"]).reset_index(drop=True)
    g["track"] = g["individual-local-identifier"].astype(str) + "/" + g["comments"].astype(str)
    x = np.log10(np.maximum(g["ground-speed"].values, 0.1))                                # m/s, floor 0.1
    tracks = np.array(sorted(g["track"].unique()))
    pick = np.random.default_rng(2).choice(tracks, NY_FIT_TRACKS, replace=False)
    sub = g["track"].isin(pick).values
    mu, sd, A, pi, ll = max((hmm_fit(x[sub], 3, init, iters=150) for init in ([-1.0, -0.4, 1.1], [-0.9, -0.2, 1.2])),
                            key=lambda r: r[4])
    states = np.zeros(len(g), int)
    for _trk, grp in g.groupby("track", sort=False):
        ii = grp.index.values
        states[ii] = viterbi(x[ii], mu, sd, A, pi)
    g["state"] = states
    g["fly"] = (states == 2).astype(int)
    local = g["timestamp"] + pd.Timedelta(hours=1)                                         # CET = UTC + 1
    g["bin"] = local.dt.hour + (local.dt.minute // 30) * 0.5
    g["evening"] = (local - pd.Timedelta(hours=12)).dt.strftime("%m-%d")
    g["season"] = (local - pd.Timedelta(hours=12) - pd.Timedelta(days=100)).dt.year       # 2020 = 2020/21
    return g, (mu, sd, A, pi, ll), sub.sum()


NY_SPECIES = [("Anser fabalis", "bean"), ("Anser albifrons", "white-fronted"), ("Branta leucopsis", "barnacle"),
              ("Anser brachyrhynchus", "pink-footed")]
NY_STATES = [("resting", "#0A97D9"), ("slow", "#3F7E44"), ("flight", "#E8700A")]   # as for goose 3104
NY_EXAMPLE = "3G/2018"                                 # a pink-footed goose, a fix every 10 to 20 minutes


def fig_new_year(g):
    """Left: one goose on New Year's night (NY_EXAMPLE): the GPS speed of every fix, coloured by its state, and the
    states as a strip. Right: share of all fixes in the flight state per half hour, New Year's night against the
    other nights. Returns the half hours, both shares and the number of fixes of the example."""
    order = [h + m for h in list(range(18, 24)) + list(range(0, 7)) for m in (0, 0.5)][:-1]
    nye, other = g["evening"] == "12-31", g["evening"].isin(NY_OTHER)
    share = lambda mask: [100 * g.loc[mask & (g["bin"] == b), "fly"].mean() for b in order]
    a, b = share(nye), share(other)
    fig = plt.figure(figsize=(12.8, 4.6))
    rx = fig.add_axes([0.07, 0.31, 0.38, 0.52])
    sx = fig.add_axes([0.07, 0.15, 0.38, 0.08])
    ax = fig.add_axes([0.555, 0.15, 0.445, 0.68])
    # left: one goose, every fix with its state
    shifted = g["timestamp"] + pd.Timedelta(hours=1) - pd.Timedelta(hours=12)        # CET, minus 12 h
    h = (shifted - shifted.dt.normalize()).dt.total_seconds() / 3600 - 6               # hours since 18:00
    ex = g[nye & (g["track"] == NY_EXAMPLE) & (h >= 0) & (h <= 12.5)]
    hh, st = h[ex.index].values, ex["state"].values
    v = np.maximum(ex["ground-speed"].values, 0.1)
    rx.plot(hh, v, "-", color="#c4c4c0", lw=1.0, zorder=2)
    for k, (name, col) in enumerate(NY_STATES):
        sel = st == k
        rx.plot(hh[sel], v[sel], "o", color=col, ms=7, mec="white", mew=0.8, zorder=3)
        sx.broken_barh([(hh[q], min(hh[q + 1] - hh[q] if q + 1 < len(hh) else 0.5, 0.5))
                        for q in range(len(hh)) if st[q] == k], (0, 1), facecolors=col, lw=0)
    for axx in (rx, sx):
        axx.axvline(6, color=GREY, lw=1.0, ls=(0, (3, 3)), zorder=1)
        axx.set_xlim(-0.2, 12.7)
    rx.set_yscale("log")
    rx.set_ylim(0.07, 40)
    rx.set_yticks([0.1, 1, 10])
    rx.set_yticklabels(["≤ 0.1", "1", "10"])
    rx.minorticks_off()
    rx.set_xticks([])
    rx.grid(axis="y", color="#e2e2df", lw=0.8, zorder=0)
    clean(rx, left=False)
    rx.spines["bottom"].set_visible(False)
    rx.tick_params(labelsize=12.5, colors=INK, length=0)
    rx.set_ylabel("speed (m/s)", fontsize=13, color=INK)
    sp = dict(NY_SPECIES)[ex["individual-taxon-canonical-name"].iloc[0]]
    season = int(ex["season"].iloc[0])
    rx.set_title(f"one goose ({sp}, {season}/{season + 1 - 2000:02d}): every GPS fix gets a state", fontsize=14,
                 color=INK, loc="left", pad=28)
    for k, (name, col) in enumerate(NY_STATES):
        rx.plot([0.15 + 2.9 * k], [62], "o", color=col, ms=9, clip_on=False)
        rx.text(0.55 + 2.9 * k, 62, name, fontsize=12.5, color=INK, va="center", clip_on=False)
    sx.set_ylim(0, 1)
    sx.set_yticks([])
    for sp_ in ["top", "right", "left", "bottom"]:
        sx.spines[sp_].set_visible(False)
    sx.set_xticks(range(0, 13, 2))
    sx.set_xticklabels([f"{(18 + t) % 24:02d}:00" for t in range(0, 13, 2)])
    sx.tick_params(labelsize=12.5, colors=INK, length=3, color=GREY)
    sx.set_xlabel("local time (CET)", fontsize=13, color=INK)
    # right: share of the fixes in the flight state
    xs = np.arange(len(order))
    ax.plot(xs, b, "-o", color=GREY, lw=2.2, ms=4.5, zorder=2)
    ax.plot(xs, a, "-o", color=COL[2], lw=2.6, ms=5, zorder=3)
    k0 = order.index(0.0)
    ax.annotate(f"{a[k0]:.0f} %", xy=(k0, a[k0]), xytext=(k0 + 1.6, a[k0] + 2), fontsize=15, color=COL[2],
                fontweight="bold", va="center", arrowprops=dict(arrowstyle="-", color=COL[2], lw=1.2))
    ax.text(xs[-1], a[-1] + 2.5, "New Year's night", fontsize=13.5, color=COL[2], fontweight="bold", ha="right",
            va="bottom", path_effects=HALO)
    ax.text(xs[1] - 0.4, b[1] - 1.0, "other nights (20 Dec – 9 Jan)", fontsize=13.5, color=GREY, fontweight="bold",
            ha="left", va="top", path_effects=HALO)
    ax.axvline(order.index(0.0), color=GREY, lw=1.0, ls=(0, (3, 3)), zorder=1)
    ax.set_xticks(xs[::4])
    ax.set_xticklabels([f"{int(order[k]):02d}:00" for k in range(0, len(order), 4)])
    ax.set_ylim(0, 50)
    ax.set_yticks([0, 10, 20, 30, 40, 50])
    ax.set_yticklabels([f"{v} %" for v in (0, 10, 20, 30, 40, 50)])
    ax.grid(axis="y", color="#e2e2df", lw=0.8, zorder=0)
    clean(ax, left=False)
    ax.tick_params(labelsize=12.5, colors=INK, length=0)
    ax.set_xlabel("local time (CET)", fontsize=13, color=INK)
    ax.set_title(f"share of fixes in the flight state, all {g['track'].nunique()} tracks", fontsize=14, color=INK,
                 loc="left", pad=26)
    save(fig, "geese-new-year.svg")
    return order, a, b, len(hh)


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
fig_start_stop_steps()
blocks = fig_start_stop_blocks()
print("   blocks of white cells (column: starts):", "; ".join(f"{j + 1}: {a + 1}-{b + 1}" for j, a, b in blocks))
fig_optimal_partitioning()
fig_geese_criteria()
fig_criteria_attributes()
fig_monotone("decreasing")
fig_monotone("increasing")
fig_stays_ahead()
fig_hmm_model()

# --- goose 3104
g, H = load_goose()
lat, lon = H["location-lat"].values, H["location-long"].values
th = (H.index - H.index[0]).total_seconds().values / 3600
d = haversine(lat[:-1], lon[:-1], lat[1:], lon[1:])
x = np.log10(np.maximum(d, MIN_KM))
expert = np.where(H["migration-stage"].values[1:] == "stopover", "stop", "fly")    # label of each hour (step)
stops = expert_stopovers(g)
dur = (g.index[-1] - g.index[0]).total_seconds() / 86400
stop_days = sum((b - a).total_seconds() for a, b, _, _ in stops) / 86400
print(f"== goose {GOOSE}, spring {YEAR}: {len(g)} GPS fixes ({g.index[0]:%d %b %H:%M} - {g.index[-1]:%d %b %H:%M}),"
      f" {dur:.1f} days, {haversine(g['location-lat'].iloc[0], g['location-long'].iloc[0], g['location-lat'].iloc[-1], g['location-long'].iloc[-1]):.0f} km"
      f" in a straight line; {len(H)} hourly positions; median fix interval "
      f"{np.median(np.diff(g.index.values).astype('timedelta64[s]').astype(float)) / 60:.0f} min")
print(f"   ecologists: {len(stops)} stopovers, {stop_days:.1f} days ({stop_days / dur:.0%} of the time):")
for a, b, la, lo in stops:
    print(f"     {a:%d %b %H:%M} - {b:%d %b %H:%M}  {(b - a).total_seconds() / 86400:5.1f} days at ({la:.2f}, {lo:.2f})")
print(f"   hours <= 0.1 km: {np.mean(d < MIN_KM):.0%}; total distance between hourly positions {d.sum():.0f} km;"
      f" hours with more than 30 km: {(d > 30).sum()}; fastest hour {d.max():.0f} km ({H.index[int(np.argmax(d))]:%d %b %H:%M})")
_fl = runs(list(g["migration-stage"].values))[1]                  # first flight phase of the ecologists
_a, _b = g.iloc[_fl[1]], g.iloc[_fl[2]]
print(f"   first flight (ecologists' label): {g.index[_fl[1]]:%d %b %H:%M} - {g.index[_fl[2]]:%d %b %H:%M}, "
      f"{(g.index[_fl[2]] - g.index[_fl[1]]).total_seconds() / 3600:.1f} h, "
      f"{haversine(_a['location-lat'], _a['location-long'], _b['location-lat'], _b['location-long']):.0f} km "
      f"in a straight line ({_fl[0]})")
fig_goose(g, H, x, stops, False, "geese-3104-input.svg")
fig_goose(g, H, x, stops, True, "geese-3104-experts.svg")

# criteria
segs, n_valid = criteria_segmentation(lat, lon, th, RADIUS, HOURS, ARC, INLIERS)
lab_c = np.empty(len(H) - 1, object)
for j, i, k in segs:
    lab_c[j:i] = k
ph = runs(list(lab_c))
n_cells = len(H) * (len(H) - 1) // 2
print(f"== criteria (disk {RADIUS:g} km for >= {HOURS:g} h, OR {INLIERS:.0%} of headings within {ARC} rad): "
      f"{len(segs)} segments, {len(ph)} phases; start-stop diagram {n_cells:,} cells, {n_valid:,} valid; "
      f"agreement with the ecologists {np.mean(lab_c == expert):.1%} of {len(expert)} hours")
for kind, a, b in ph:
    print(f"     {kind:4s} {H.index[a]:%d %b %H:%M} - {H.index[b + 1]:%d %b %H:%M}  {(b - a + 1) / 24:5.1f} days, "
          f"{sum(1 for j, i, k in segs if j >= a and i <= b + 1)} segments")
dis = lab_c != expert                                    # where the criteria and the ecologists disagree
print(f"     disagreement: {dis.sum()} hours; runs:", "; ".join(
    f"{H.index[a]:%d %b %H:%M} - {H.index[b + 1]:%d %b %H:%M} ({b - a + 1} h, ecologists {expert[a]}, "
    f"{d[a:b + 1].sum():.0f} km)" for kind, a, b in runs(list(np.where(dis, "D", "A"))) if kind == "D"))
for kind, a, b in ph:                                    # stopovers that the criteria split into several segments
    parts = [(j, i) for j, i, k in segs if k == "stop" and j >= a and i <= b + 1]
    if len(parts) > 1:
        cen = [(lat[j:i + 1].mean(), lon[j:i + 1].mean()) for j, i in parts]
        print(f"     stopover {H.index[a]:%d %b} - {H.index[b + 1]:%d %b} split: "
              + ", ".join(f"{H.index[j]:%d %b %H:%M} - {H.index[i]:%d %b %H:%M} ({(th[i] - th[j]) / 24:.1f} days, "
                          f"disk radius {disk_radius(lat[j:i + 1], lon[j:i + 1]):.1f} km)" for j, i in parts)
              + "; mean positions " + ", ".join(f"{haversine(*cen[k], *cen[k + 1]):.0f} km" for k in range(len(cen) - 1))
              + " apart")

# change points on log10 km per hour
cps = penalized_partition(x, BETA)
lab_cp = np.empty(len(x), object)
for a, b in cps:
    lab_cp[a:b] = "fly" if x[a:b].mean() > MOVING else "stop"
print(f"== change points, penalty {BETA:g}: {len(cps)} segments, agreement {np.mean(lab_cp == expert):.1%}; "
      f"penalty 3: {len(penalized_partition(x, 3.0))} segments, 20: {len(penalized_partition(x, 20.0))}")

# hidden Markov model, four states
fits = [hmm_fit(x, K_HMM, np.quantile(x, [0.3, 0.75, 0.93, 0.99]) + 0.05 * k, min_sd=0.15) for k in range(3)]
mu, sd, A, pi, ll = max(fits, key=lambda r: r[4])
st = viterbi(x, mu, sd, A, pi)
lab_h = np.where(st == K_HMM - 1, "fly", "stop")
print(f"== HMM with {K_HMM} states: log-likelihood {ll:.1f} (starts: {', '.join(f'{r[4]:.1f}' for r in fits)})")
for k in range(K_HMM):
    print(f"     {HMM_NAMES[k]:17s} median {10 ** mu[k]:6.2f} km/h (sd {sd[k]:.2f} log10), stays {A[k, k]:.2f}"
          f" (expected stay {1 / (1 - A[k, k]):.1f} h), Viterbi {np.mean(st == k):5.1%} of hours")
print("     transition matrix:", np.round(A, 2).tolist())
fl = st == K_HMM - 1
print(f"   migratory flight: {fl.sum()} hours, {d[fl].sum():.0f} km; {np.mean(expert[fl] == 'fly'):.0%} of them in the"
      f" ecologists' flight phases; agreement (migratory flight vs rest) {np.mean(lab_h == expert):.1%}")
for K in (2, 3, 5):
    r = max((hmm_fit(x, K, np.quantile(x, np.linspace(0.3, 0.99, K)) + 0.05 * k, min_sd=0.15) for k in range(3)),
            key=lambda r: r[4])
    print(f"   K = {K}: log-likelihood {r[4]:.1f}, BIC {-2 * r[4] + (K * K + 2 * K - 1) * np.log(len(x)):.1f}, medians "
          f"{' '.join(f'{10 ** m:.2f}' for m in r[0])} km/h")
print(f"   K = 4: log-likelihood {ll:.1f}, BIC {-2 * ll + (K_HMM ** 2 + 2 * K_HMM - 1) * np.log(len(x)):.1f}")
fig_hmm(x, mu, sd, st)
fig_hmm_zoom(H, x, st, "2014-04-24 12:00", "2014-04-28 12:00")
z = (H.index[1:] >= pd.Timestamp("2014-04-24 12:00")) & (H.index[1:] <= pd.Timestamp("2014-04-28 12:00"))
print("   24 Apr 12:00 - 28 Apr 12:00:", " ".join(f"{HMM_NAMES[k]} {np.sum(st[z] == k)} h" for k in range(K_HMM)),
      f"; migratory flight covers {d[z & fl].sum():.0f} km of {d[z].sum():.0f} km")
two = {"stop": STOP, "fly": FLY}
rows = [("ecologists\n(by hand)", expert, two), (f"criteria\n({RADIUS:g} km, {HOURS:g} h; {ARC} rad)", lab_c, two),
        (f"change points\n(penalty {BETA:g})", lab_cp, two), ("hidden Markov model\n(migratory flight)", lab_h, two)]
fig_methods(H, x, rows[:2], "geese-3104-criteria.svg")
fig_methods(H, x, rows, "geese-3104-methods.svg")
print(f"   agreement criteria vs change points {np.mean(lab_c == lab_cp):.1%}, criteria vs HMM {np.mean(lab_c == lab_h):.1%},"
      f" change points vs HMM {np.mean(lab_cp == lab_h):.1%}")

# Viterbi example
V, path = fig_trellis_frames()
print("== Viterbi example: observations", V_OBS, "; V =", [{s: v for s, v in col.items()} for col in V],
      "; best path", path, f"cost {min(V[-1].values())}")
cheap = sum(min(V_EMIT[s][t] for s in V_EMIT) for t in range(len(V_OBS)))
print(f"   without switching costs: path {[min(V_EMIT, key=lambda s: V_EMIT[s][t]) for t in range(len(V_OBS))]}"
      f" with cost {cheap}; with 4 switches that path costs {cheap + 4 * V_SWITCH}")

# global temperature
print("== global temperature (NASA GISTEMP v4, annual means 1880-%d), continuous piecewise-linear trends:" % LAST_YEAR)
fig_temperature()

# New Year
ny, (mu3, sd3, A3, pi3, ll3), n_fit = new_year()
print(f"== New Year: {len(ny):,} GPS fixes with ground speed, {ny['track'].nunique()} tracks (goose/season), "
      f"{ny['individual-local-identifier'].nunique()} geese; species {ny['individual-taxon-canonical-name'].value_counts().to_dict()}")
print(f"   HMM (3 states, fitted on {n_fit:,} fixes of {NY_FIT_TRACKS} tracks): medians "
      f"{' '.join(f'{10 ** m:.2f}' for m in mu3)} m/s, stays {np.round(np.diag(A3), 2).tolist()};"
      f" flight state {ny['fly'].mean():.1%} of all fixes")
order, a_ny, b_ny, n_rows = fig_new_year(ny)
print(f"   left panel: goose {NY_EXAMPLE}, {n_rows} fixes between 18:00 and 06:30 on New Year's night")
for bb in (23.5, 0.0, 0.5, 1.0, 2.0):
    k = order.index(bb)
    print(f"   {int(bb):02d}:{int(60 * (bb % 1)):02d} CET: New Year {a_ny[k]:.1f} %, other nights {b_ny[k]:.1f} %")
mid = (ny["evening"] == "12-31") & (ny["bin"] == 0.0)
for key, grp in ny[mid].groupby("individual-taxon-canonical-name"):
    print(f"   00:00-00:30 on New Year's night, {key}: {grp['fly'].mean():.0%} of {len(grp)} fixes")
for key, grp in ny[mid].groupby("season"):
    print(f"   00:00-00:30 on New Year's night {key}/{key + 1 - 2000:02d}: {grp['fly'].mean():.0%} of {len(grp)} fixes")
