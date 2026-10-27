"""Figures for "Algorithms and Sustainability", lecture 3: clustering (own work, CC BY 4.0).

Usage:  python3 tools/make_clustering_figures.py <data folder> lectures/figures
Same data folder as tools/make_stork_figures.py (GPS data of Flack et al. 2016 from the Movebank
Data Repository, doi:10.5441/001/1.78152p3q, CC0; Natural Earth layers). The drawing functions and
the data loading are taken from that script.

Writes the figures of lecture 3 and prints every number quoted on the slides:
  clustering-points-curves.svg       four kinds of clustering in movement data (schematic)
  storks-routes.svg                  the 34 autumn routes (input)
  storks-winter-kcenter-1..4.svg     Gonzalez on the first-winter sites, one centre per step
  gonzalez-exercise(-solution).svg   small example to work by hand
  kcenter-proof.svg                  why Gonzalez is a 2-approximation (schematic)
  route-simplification.svg           optimal 6-vertex simplification of one route (discrete Fréchet)
  storks-klcenter-1..5.svg           Gonzalez with simplification, (k, l) = (5, 6), one step each
  klcenter-radius.svg                radius after k steps, l = 6

Algorithms (all in this file): discrete Fréchet distance (dynamic program over anti-diagonals),
smallest enclosing circle (Welzl) in an azimuthal equidistant projection, optimal l-vertex
simplification under the discrete Fréchet distance (consecutive groups, greedy check, binary
search on the radius), Gonzalez's farthest-first traversal. Distances are great-circle distances.
Needs: matplotlib, numpy, pandas. Font as in make_figures.py (LATO_DIR). Runs in about 2 minutes.
"""
import itertools
import os
import sys

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- reuse lecture 2's stork tools
_here = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(_here, "make_stork_figures.py"), encoding="utf-8").read()
_src = _src.split("# ---------------------------------------------------------------- main")[0]
exec(compile(_src, "make_stork_figures.py", "exec"))     # defines plt, laea, basemap, save, load_gps, ...

import matplotlib.patches as mpatches                   # noqa: E402
plt.rcParams.update({"mathtext.fontset": "custom", "mathtext.it": "LatoLatin:italic", "mathtext.rm": "LatoLatin",
                     "mathtext.bf": "LatoLatin:bold"})

COL = ["#0A97D9", "#E8700A", "#DD1367", "#3F7E44", "#6250d6"]   # validated as a set; maps carry direct labels
LIGHT, PALE = "#d9d9d6", "#d6ecf8"
OVERVIEW = (lambda lo, la: laea(lo, la, 28, 14)), (-5100, 3750, -4500, 4900)   # as storks-overview.svg


# ---------------------------------------------------------------- algorithms
def frechet(D):
    """Discrete Fréchet distance for a distance matrix D, filled anti-diagonal by anti-diagonal."""
    n, m = D.shape
    C = np.full((n, m), np.inf)
    C[0, 0] = D[0, 0]
    for d in range(1, n + m - 1):
        i = np.arange(max(0, d - m + 1), min(n, d + 1))
        j = d - i
        best = np.full(len(i), np.inf)
        a = (i > 0) & (j > 0)
        best[a] = C[i[a] - 1, j[a] - 1]
        a = i > 0
        best[a] = np.minimum(best[a], C[i[a] - 1, j[a]])
        a = j > 0
        best[a] = np.minimum(best[a], C[i[a], j[a] - 1])
        C[i, j] = np.maximum(D[i, j], best)
    return C


def frechet_coupling(D):
    """Value and one optimal coupling (backtracking as in make_stork_figures.discrete_frechet)."""
    C = frechet(D)
    n, m = D.shape
    pairs, i, j = [(n - 1, m - 1)], n - 1, m - 1
    while (i, j) != (0, 0):
        cand = [(p, q) for p, q in [(i - 1, j - 1), (i - 1, j), (i, j - 1)] if p >= 0 and q >= 0]
        i, j = min(cand, key=lambda pq: (C[pq], D[pq]))
        pairs.append((i, j))
    return C[-1, -1], pairs[::-1]


def dF(A, B):
    return frechet(dist_matrix(A, B))[-1, -1]


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
    """Circle through 1, 2 or 3 points (smallest circle for two points)."""
    if len(pts) == 1:
        return pts[0], 0.0
    if len(pts) == 2:
        c = (pts[0] + pts[1]) / 2
        return c, float(np.hypot(*(pts[0] - c)))
    (ax, ay), (bx, by), (cx, cy) = pts
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:                                   # collinear: the widest pair
        return max((_circle([p, q]) for p, q in itertools.combinations(pts, 2)), key=lambda t: t[1])
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
    c = np.array([ux, uy])
    return c, float(np.hypot(*(pts[0] - c)))


def enclosing_circle(P):
    """Smallest enclosing circle of points P (n x 2), Welzl's algorithm in iterative form."""
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
    """Smallest spherical cap containing the points: enclosing circle in an azimuthal equidistant
    projection, re-centred at the circle's centre until the centre stays put (then all distances
    to the centre are exact). Returns ((lat, lon), radius in km)."""
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    if len(lat) == 1:
        return (float(lat[0]), float(lon[0])), 0.0
    clat = float(np.mean(lat))
    clon = float(np.degrees(np.arctan2(np.sin(np.radians(lon)).mean(), np.cos(np.radians(lon)).mean())))
    for _ in range(10):
        c, _r = enclosing_circle(np.c_[aeqd(lat, lon, clat, clon)])
        clat, clon = aeqd_inv(c[0], c[1], clat, clon)
        if np.hypot(*c) < 0.01:                          # moved less than 10 m
            break
    return (clat, clon), float(haversine(lat, lon, clat, clon).max())


def simplify(P, ell):
    """Optimal simplification with at most ell vertices under the discrete Fréchet distance, vertices
    anywhere. Optimal couplings can be taken to split P into at most ell groups of consecutive
    points, each matched to one vertex; the best vertex for a group is the centre of its smallest
    enclosing cap. So: minimize the largest cap radius over partitions into <= ell groups.
    Greedy check for a given radius (a group is extended while it fits), binary search on the radius.
    Returns (vertices as (lat, lon) array, error in km, groups as (first, last) index pairs)."""
    cache = {}

    def cap(i, j):
        if (i, j) not in cache:
            cache[(i, j)] = enclosing_cap(P[i:j + 1, 0], P[i:j + 1, 1])
        return cache[(i, j)]

    def greedy(eps):
        groups, i, n = [], 0, len(P)
        while i < n:
            lo, step = i, 1                              # galloping, then binary search for the end
            while lo + step < n and cap(i, lo + step)[1] <= eps:
                lo += step
                step *= 2
            hi = min(n - 1, lo + step)                   # the group ends somewhere in lo..hi
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if cap(i, mid)[1] <= eps:
                    lo = mid
                else:
                    hi = mid - 1
            groups.append((i, lo))
            i = lo + 1
            if len(groups) > ell:
                return None
        return groups

    lo, hi = 0.0, cap(0, len(P) - 1)[1]
    best = [(0, len(P) - 1)]
    while hi - lo > 0.5:                                 # to 0.5 km
        mid = (lo + hi) / 2
        g = greedy(mid)
        if g is None:
            lo = mid
        else:
            hi, best = mid, g
    verts = np.array([cap(i, j)[0] for i, j in best])
    return verts, max(cap(i, j)[1] for i, j in best), best


def gonzalez(dist_to, n, k, first):
    """Farthest-first traversal: dist_to(c) gives the distances of all n objects to centre c.
    Returns the chosen objects, the radius after each step, the assignment and the distances."""
    chosen, d = [first], dist_to(first).copy()
    assign, radii = np.zeros(n, int), [float(d.max())]
    for _ in range(1, k):
        nxt = int(np.argmax(d))
        chosen.append(nxt)
        dn = dist_to(nxt)
        assign[dn < d] = len(chosen) - 1
        d = np.minimum(d, dn)
        radii.append(float(d.max()))
    return chosen, radii, assign, d


def geocircle(lat, lon, r, n=181):
    """Points at great-circle distance r (km) around (lat, lon)."""
    p1, l1, delta = np.radians(lat), np.radians(lon), r / R_EARTH
    b = np.linspace(0, 2 * np.pi, n)
    p2 = np.arcsin(np.sin(p1) * np.cos(delta) + np.cos(p1) * np.sin(delta) * np.cos(b))
    l2 = l1 + np.arctan2(np.sin(b) * np.sin(delta) * np.cos(p1), np.cos(delta) - np.sin(p1) * np.sin(p2))
    return np.degrees(p2), np.degrees(l2)


def name(bird):
    return bird.split(" (")[0]


def km(x):
    return f"{x:,.0f} km"


# ---------------------------------------------------------------- figures
def badge(ax, x, y, text, col, size=13, z=8):
    ax.text(x, y, text, fontsize=size, fontweight="bold", color="white", ha="center", va="center", zorder=z,
            bbox=dict(boxstyle="circle,pad=0.25", fc=col, ec="white", lw=1.2))


def fig_points_curves():
    """Four kinds of clustering in movement data, schematic (synthetic data)."""
    rng = np.random.default_rng(7)
    fig, axs = plt.subplots(1, 4, figsize=(15.6, 4.3))
    for ax in axs:
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 8.2)
        ax.set_aspect("equal")
        ax.axis("off")
    # (a) one track: excursions from a central place; the fixes at the nest form a cluster
    ax = axs[0]
    nest = np.array([4.6, 4.4])
    pts = [nest + rng.normal(0, 0.18, 2)]
    for ang in [0.4, 2.0, 3.5, 5.1]:
        tip = nest + 3.4 * np.array([np.cos(ang), np.sin(ang)])
        t = np.linspace(0, 1, 9)[1:]
        bend = np.array([-np.sin(ang), np.cos(ang)])
        out = nest + np.outer(t, tip - nest) + np.outer(np.sin(np.pi * t), bend) * 0.9
        pts += list(out + rng.normal(0, 0.08, out.shape))
        back = (nest + np.outer(t, tip - nest) - np.outer(np.sin(np.pi * t), bend) * 0.5)[::-1]
        pts += list(back + rng.normal(0, 0.08, back.shape))
        pts += list(nest + rng.normal(0, 0.16, (7, 2)))
    P = np.array(pts)
    inside = np.hypot(*(P - nest).T) < 0.6
    ax.plot(P[:, 0], P[:, 1], "-", color=GREY, lw=0.8, alpha=0.7, zorder=1)
    ax.plot(P[~inside, 0], P[~inside, 1], "o", color=GREY, ms=3, zorder=2)
    ax.plot(P[inside, 0], P[inside, 1], "o", color=COL[0], ms=4, zorder=3)
    ax.add_patch(mpatches.Circle(nest, 0.75, fill=False, ec=COL[0], lw=1.8, ls=(0, (3, 2)), zorder=4))
    # (b) many animals: stationary fixes of several tracks around one place
    ax = axs[1]
    spot = np.array([5.4, 3.6])
    for s, (x0, y0) in enumerate([(0.6, 7.4), (9.4, 7.6), (0.8, 0.9), (9.3, 1.2), (5.0, 7.9)]):
        t = np.linspace(0, 1, 10)
        path = np.c_[x0 + t * (spot[0] - x0), y0 + t * (spot[1] - y0)] + np.c_[np.sin(3 * t) * 0.4, np.cos(4 * t) * 0.3] * (1 - t)[:, None]
        ax.plot(path[:, 0], path[:, 1], "-", color=GREY, lw=0.9, alpha=0.8, zorder=1)
        ax.plot(path[:-1, 0], path[:-1, 1], "o", color=GREY, ms=3, zorder=2)
        st = spot + rng.normal(0, 0.22, (5, 2))
        ax.plot(st[:, 0], st[:, 1], "o", color=COL[1], ms=4, zorder=3)
    ax.add_patch(mpatches.Circle(spot, 0.85, fill=False, ec=COL[1], lw=1.8, ls=(0, (3, 2)), zorder=4))
    # (c) whole tracks: two groups of similar routes, each with a simple representative
    ax = axs[2]
    x = np.linspace(0.5, 9.5, 24)
    for grp, (base, amp, col) in enumerate([(5.6, 1.1, COL[0]), (2.4, -0.9, COL[3])]):
        for s in range(4):
            wig = rng.normal(0, 0.16, len(x)).cumsum() * 0.45
            wig -= np.linspace(wig[0], wig[-1], len(x)) * 0.6
            y = base + (amp + rng.normal(0, 0.35)) * np.sin((x - 0.5) / 9 * np.pi) + wig + rng.normal(0, 0.25)
            ax.plot(x, y, "-", color=col, lw=1.1, alpha=0.75, zorder=1)
        rx = np.array([0.5, 3.5, 6.5, 9.5])
        ry = base + amp * np.sin((rx - 0.5) / 9 * np.pi)
        ax.plot(rx, ry, "-o", color="white", lw=5, ms=8, zorder=2)
        ax.plot(rx, ry, "-o", color=col, lw=2.6, ms=6, mec="white", mew=1, zorder=3)
    # (d) parts of tracks: different routes share a corridor in the middle
    ax = axs[3]
    corr = np.c_[np.linspace(3.6, 6.4, 8), np.linspace(3.6, 4.6, 8)]
    for s, ((x0, y0), (x1, y1)) in enumerate([((0.4, 7.5), (9.6, 7.3)), ((0.5, 0.6), (9.5, 0.9)),
                                              ((0.3, 4.6), (9.7, 2.0)), ((2.0, 7.9), (8.2, 0.3))]):
        a = np.c_[np.linspace(x0, corr[0, 0], 7), np.linspace(y0, corr[0, 1], 7)]
        b = np.c_[np.linspace(corr[-1, 0], x1, 7), np.linspace(corr[-1, 1], y1, 7)]
        a[1:-1] += rng.normal(0, 0.22, (5, 2))
        b[1:-1] += rng.normal(0, 0.22, (5, 2))
        mid = corr + rng.normal(0, 0.07, corr.shape)
        path = np.r_[a[:-1], mid, b[1:]]
        ax.plot(path[:, 0], path[:, 1], "-", color=GREY, lw=1.0, alpha=0.8, zorder=1)
        ax.plot(mid[:, 0], mid[:, 1], "-", color=COL[4], lw=2.0, alpha=0.9, zorder=2)
    ax.add_patch(mpatches.FancyBboxPatch((3.3, 3.1), 3.4, 2.0, boxstyle="round,pad=0.1,rounding_size=0.8",
                                         fill=False, ec=COL[4], lw=1.8, ls=(0, (3, 2)), zorder=3))
    for ax, (t1, t2) in zip(axs, [("points of one track", "nest, roost, dead bird"),
                                  ("points of many tracks", "vultures at a carcass"),
                                  ("whole tracks", "typical routes"),
                                  ("parts of tracks", "shared corridors")]):
        ax.text(5, -0.5, t1, fontsize=17, fontweight="bold", color=INK, ha="center", va="top")
        ax.text(5, -1.55, t2, fontsize=15, color=INK, ha="center", va="top")
        ax.set_ylim(-2.4, 8.2)
    fig.tight_layout(w_pad=1.5)
    save(fig, "clustering-points-curves.svg")


def origins(ax, proj, info, labels):
    for pop, g in info.groupby("pop"):
        x, y = proj(g["lon0"].mean(), g["lat0"].mean())
        ax.plot(x, y, "o", ms=6.5, color=INK, mec="white", mew=1.2, zorder=6)
        if pop in labels:
            text, dx, dy, ha = labels[pop]
            ax.text(x + dx, y + dy, text, fontsize=13, color=INK, ha=ha, va="center", zorder=7, path_effects=HALO)


ORIGIN_LABELS = {"Spain": ("Spain", -130, 40, "right"), "SW Germany": ("SW Germany", -120, 150, "right"),
                 "Greece": ("Greece", -110, 190, "right"), "Tunisia": ("Tunisia", 120, 20, "left"),
                 "Poland": ("Poland", 120, 50, "left"), "Russia": ("Russia", 120, 50, "left"),
                 "Armenia": ("Armenia", 160, 60, "left")}


def fig_routes(routes, mig):
    proj, box = OVERVIEW
    fig, ax = plt.subplots(figsize=(6.0, 6.0))
    basemap(ax, proj, box, tol=20)
    for P in routes:
        x, y = proj(P[:, 1], P[:, 0])
        ax.plot(x, y, color=INK, lw=0.9, alpha=0.55, zorder=2, solid_joinstyle="round")
    origins(ax, proj, mig, ORIGIN_LABELS)
    for (lat, lon), text, (dx, dy, ha) in [((36.0, -5.6), "Strait of\nGibraltar", (-420, -420, "right")),
                                          ((41.1, 29.0), "Bosporus", (330, -420, "left"))]:
        x, y = proj(lon, lat)
        ax.annotate(text, xy=(x, y), xytext=(x + dx, y + dy), fontsize=12.5, color=INK, ha=ha, va="center",
                    zorder=7, path_effects=HALO, arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkB=3))
    ax.text(box[0] + 150, box[2] + 250, f"{len(routes)} juveniles,\none position per day\nuntil 31 December",
            fontsize=13, color=INK, ha="left", va="bottom", path_effects=HALO, zorder=7)
    save(fig, "storks-routes.svg")


def fig_winter_sites(win):
    proj, box = OVERVIEW
    x, y = proj(win["wlon"].values, win["wlat"].values)
    fig, ax = plt.subplots(figsize=(6.0, 6.0))
    basemap(ax, proj, box, tol=20)
    ax.plot(x, y, "o", ms=6.5, color=INK, mec="white", mew=0.9, zorder=4)
    ax.text(box[0] + 150, box[2] + 250, f"{len(win)} juveniles:\nwhere they spent\ntheir first winter",
            fontsize=13, color=INK, ha="left", va="bottom", path_effects=HALO, zorder=7)
    save(fig, "storks-winter-sites.svg")


def fig_winter_steps(win, D, chosen, radii, place):
    """Gonzalez on the first-winter sites; one figure per step (centres 1..k, current radius)."""
    proj, box = OVERVIEW
    lat, lon = win["wlat"].values, win["wlon"].values
    x, y = proj(lon, lat)
    for k in range(1, len(chosen)):
        C = chosen[:k]
        d = D[C].min(axis=0)
        assign = np.array(C)[D[C].argmin(axis=0)]
        far = int(np.argmax(d))
        fig, ax = plt.subplots(figsize=(6.0, 6.0))
        fig.patch.set_facecolor("white")
        basemap(ax, proj, box, tol=20)
        for ci, c in enumerate(C):
            cl, co = geocircle(lat[c], lon[c], d.max())
            cx, cy = proj(co, cl)
            ok = np.isfinite(cx) & np.isfinite(cy)
            ax.plot(cx[ok], cy[ok], color=COL[ci], lw=1.4, ls=(0, (4, 3)), zorder=2)
            mem = assign == c
            ax.plot(x[mem], y[mem], "o", ms=6, color=COL[ci], mec="white", mew=0.8, zorder=4)
        c_near = assign[far]
        ax.plot([x[far], x[c_near]], [y[far], y[c_near]], color=INK, lw=2.2, zorder=5)
        ax.plot(x[far], y[far], "o", ms=13, mfc="none", mec=INK, mew=2.2, zorder=6)
        mx, my = (x[far] + x[c_near]) / 2, (y[far] + y[c_near]) / 2
        ux, uy = x[far] - x[c_near], y[far] - y[c_near]
        nx, ny = -uy / np.hypot(ux, uy), ux / np.hypot(ux, uy)       # unit normal of the line
        if ny < 0 or (abs(ny) < 0.2 and nx < 0):
            nx, ny = -nx, -ny                                          # put the label above or right of it
        ha = "left" if nx > 0.3 else ("right" if nx < -0.3 else "center")
        ax.text(mx + 160 * nx, my + 160 * ny, f"{d.max():,.0f} km", fontsize=14, fontweight="bold", color=INK,
                ha=ha, va="bottom" if ha == "center" else "center", path_effects=HALO, zorder=7)
        for ci, c in enumerate(C):
            badge(ax, x[c], y[c], str(ci + 1), COL[ci])
            if c in place:
                text, dx, dy, ha = place[c]
                ax.text(x[c] + dx, y[c] + dy, text, fontsize=13, color=INK, ha=ha, va="center", zorder=7,
                        path_effects=HALO)
        ax.text(box[0] + 150, box[3] - 200, f"k = {k}\nr = {d.max():,.0f} km", fontsize=16, color=INK,
                ha="left", va="top", zorder=9, path_effects=HALO, linespacing=1.4)
        save_opaque(fig, f"storks-winter-kcenter-{k}.svg")


def save_opaque(fig, name):
    """As save(), but with a white background (the step figures are stacked on one slide)."""
    plt.rcParams["savefig.transparent"] = False
    fig.patch.set_facecolor("white")
    save(fig, name)
    plt.rcParams["savefig.transparent"] = True


EX = {"a": (1, 2), "b": (0, 3), "c": (2, 4), "d": (8, 1), "e": (9, 3), "f": (10, 2), "g": (4, 8), "h": (5, 9)}


def fig_exercise():
    """Gonzalez by hand: eight points on a grid, start at a."""
    names = list(EX)
    P = np.array([EX[n] for n in names], float)
    D = np.hypot(*(P[:, None, :] - P[None, :, :]).transpose(2, 0, 1))
    chosen, radii, assign, d = gonzalez(lambda i: D[i], len(P), 3, 0)
    for solution in (False, True):
        fig, ax = plt.subplots(figsize=(5.6, 5.0))
        ax.set_xlim(-1.6, 13.0)
        ax.set_ylim(-0.9, 11.6)
        ax.set_aspect("equal")
        ax.set_xticks(range(0, 11))
        ax.set_yticks(range(0, 10))
        ax.grid(True, color="#e3e3e0", lw=0.8)
        ax.tick_params(length=0, labelsize=11, colors=GREY)
        for s in ax.spines.values():
            s.set_visible(False)
        for i, n in enumerate(names):
            col = COL[[0, 1, 3][assign[i]]] if solution else INK
            ax.plot(*P[i], "o", ms=9, color=col, mec="white", mew=1.2, zorder=4)
            ax.text(P[i, 0] + 0.42, P[i, 1] + 0.42, n, fontsize=16, fontweight="bold", color=col, zorder=5,
                    path_effects=HALO)
        if not solution:
            ax.plot(*P[0], "s", ms=17, mfc="none", mec=INK, mew=2, zorder=3)
            ax.text(P[0, 0] + 0.1, P[0, 1] - 0.95, "start", fontsize=13, color=GREY, ha="center", zorder=5)
        else:
            r = radii[-1]
            for ci, c in enumerate(chosen):
                col = COL[[0, 1, 3][ci]]
                ax.add_patch(mpatches.Circle(P[c], r, fill=False, ec=col, lw=1.4, ls=(0, (4, 3)), zorder=2))
                ax.plot(*P[c], "s", ms=17, mfc="none", mec=col, mew=2.2, zorder=3)
            for i in np.where(np.isclose(d, r))[0]:
                c = chosen[assign[i]]
                ax.plot([P[i, 0], P[c, 0]], [P[i, 1], P[c, 1]], color=INK, lw=2.0, zorder=3)
            ax.text(2.6, 2.6, "√5 ≈ 2.24", fontsize=14, color=INK, ha="left", va="center", path_effects=HALO, zorder=6)
        save(fig, "gonzalez-exercise-solution.svg" if solution else "gonzalez-exercise.svg")
    return names, chosen, radii, D


def fig_proof():
    """k + 1 points with pairwise distance > 2 r*, but only k optimal discs of radius r*."""
    rng = np.random.default_rng(3)
    fig, ax = plt.subplots(figsize=(5.2, 3.5))
    ax.set_xlim(0, 10.5)
    ax.set_ylim(0, 6.9)
    ax.set_aspect("equal")
    ax.axis("off")
    discs = [np.array([2.0, 4.3]), np.array([5.6, 2.0]), np.array([8.6, 4.3])]
    for c in discs:
        ax.add_patch(mpatches.Circle(c, 1.55, fc="#f2f2f0", ec=GREY, lw=1.4, ls=(0, (4, 3)), zorder=1))
        pts = c + rng.uniform(-1.0, 1.0, (7, 2)) * 0.95
        pts = pts[np.hypot(*(pts - c).T) < 1.4]
        ax.plot(pts[:, 0], pts[:, 1], "o", color=GREY, ms=4.5, zorder=2)
    G = {"$p_1$": discs[0] + [-0.7, 0.75], "$p_2$": discs[1] + [0.85, -0.6], "$p_3$": discs[2] + [0.4, 0.95],
         "$p_4$": discs[0] + [0.85, -0.85]}
    for lbl, p in G.items():
        ax.plot(*p, "o", color=INK, ms=8, zorder=4)
        ax.text(p[0] + 0.18, p[1] + 0.18, lbl, fontsize=19, color=INK, zorder=5, path_effects=HALO)
    a, b = G["$p_1$"], G["$p_4$"]
    ax.plot([a[0], b[0]], [a[1], b[1]], color=COL[2], lw=2.6, zorder=3)
    ax.text((a[0] + b[0]) / 2 - 1.05, (a[1] + b[1]) / 2 - 0.55, "$\\leq 2r^{\\ast}$", fontsize=19, fontweight="bold",
            color=COL[2], zorder=5, path_effects=HALO)
    c = discs[1]
    ax.annotate("", xy=(c[0] - 1.55, c[1]), xytext=(c[0], c[1]),
                arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.2, mutation_scale=12))
    ax.text(c[0] - 0.8, c[1] + 0.12, "$r^{\\ast}$", fontsize=18, color=GREY, ha="center", va="bottom", path_effects=HALO)
    ax.text(5.25, 6.55, "k = 3 optimal clusters, radius $r^{\\ast}$", fontsize=16, color=GREY, ha="center")
    save(fig, "kcenter-proof.svg")


def fig_simplification(P, verts, groups, err, label):
    """One route, its groups of consecutive positions, their enclosing caps and the simplification."""
    lat0, lon0 = float(np.mean(P[:, 0])), float(np.mean(P[:, 1]))
    proj = lambda lo, la: laea(lo, la, lon0, lat0)
    x, y = proj(P[:, 1], P[:, 0])
    pad = 700
    box = (x.min() - 2900, x.max() + pad + 300, y.min() - pad, y.max() + pad)
    fig, ax = plt.subplots(figsize=(6.6, 7.0))
    basemap(ax, proj, box, tol=10, lakes=True)
    ax.plot(x, y, "-", color=GREY, lw=0.9, alpha=0.8, zorder=1)
    for gi, (i, j) in enumerate(groups):
        col = COL[0] if gi % 2 == 0 else COL[1]
        ax.plot(x[i:j + 1], y[i:j + 1], "o", ms=3.3, color=col, zorder=3)
        (clat, clon), r = enclosing_cap(P[i:j + 1, 0], P[i:j + 1, 1])
        cl, co = geocircle(clat, clon, r)
        cx, cy = proj(co, cl)
        ax.plot(cx, cy, color=col, lw=1.3, ls=(0, (4, 3)), zorder=2)
    vx, vy = proj(verts[:, 1], verts[:, 0])
    ax.plot(vx, vy, "-", color="white", lw=5.5, zorder=4)
    ax.plot(vx, vy, "-o", color=INK, lw=2.6, ms=7, mec="white", mew=1.2, zorder=5)
    ax.text(box[0] + 100, box[3] - 150, f"{label}:\n{len(P)} daily positions,\nsimplified to {len(verts)} vertices",
            fontsize=13.5, color=INK, ha="left", va="top", path_effects=HALO, zorder=7, linespacing=1.35)
    ax.text(box[0] + 100, box[2] + 120, f"error = largest\nradius: {err:,.0f} km", fontsize=13.5, color=INK,
            ha="left", va="bottom", path_effects=HALO, zorder=7, linespacing=1.35)
    save(fig, "route-simplification.svg")


CLUSTER_LABELS = {"Karamell": ("western flyway\n(SW Germany)", -260, 80, "right"),
                  "Pelopidas": ("eastern flyway\nto southern Africa", 260, 120, "left"),
                  "BraveHeart": ("Armenia to\nthe Middle East", 230, -60, "left"),
                  "Silvia": ("eastern flyway\nto the Sahel", 1500, 450, "left"),
                  "C708": ("Spain, Tunisia\nto the Sahel", -700, -1050, "right")}


def fig_klcenter_steps(routes, mig, chosen, Q, dq, ell):
    """Gonzalez with simplified centres on the routes, one figure per step; the last one is labelled."""
    proj, box = OVERVIEW
    xy = [proj(P[:, 1], P[:, 0]) for P in routes]
    for k in range(1, len(chosen) + 1):
        d = np.min(dq[:k], axis=0)
        assign = np.argmin(dq[:k], axis=0)
        far = int(np.argmax(d))
        fig, ax = plt.subplots(figsize=(6.0, 6.0))
        basemap(ax, proj, box, tol=20)
        for i, (x, y) in enumerate(xy):
            if i != far:
                ax.plot(x, y, color=COL[assign[i]], lw=0.9, alpha=0.5, zorder=2, solid_joinstyle="round")
        if k < len(chosen):
            x, y = xy[far]
            ax.plot(x, y, color=INK, lw=1.9, zorder=3, solid_joinstyle="round")
            line = plt.Line2D([], [], color=INK, lw=1.9, label="farthest route:\nthe next centre")
            ax.legend(handles=[line], loc="lower left", frameon=False, fontsize=12.5, handlelength=1.6,
                      handletextpad=0.5, borderaxespad=0.3)
        else:
            x, y = xy[far]
            ax.plot(x, y, color=COL[assign[far]], lw=0.9, alpha=0.5, zorder=2)
        for ci in range(k):
            vx, vy = proj(Q[ci][:, 1], Q[ci][:, 0])
            ax.plot(vx, vy, "-", color="white", lw=6, zorder=4, solid_joinstyle="round")
            ax.plot(vx, vy, "-o", color=COL[ci], lw=3.0, ms=6, mec="white", mew=1.0, zorder=5,
                    solid_joinstyle="round")
            badge(ax, vx[-1], vy[-1], str(ci + 1), COL[ci], size=12, z=8)
            if k == len(chosen):
                text, dx, dy, ha = CLUSTER_LABELS.get(name(mig.at[chosen[ci], "bird"]), ("", 0, 0, "left"))
                ax.text(vx[-1] + dx, vy[-1] + dy, text, fontsize=13, fontweight="bold", color=COL[ci], ha=ha,
                        va="center", zorder=9, path_effects=HALO, linespacing=1.2)
        ax.text(box[0] + 150, box[3] - 200, f"k = {k}, ℓ = {ell}\nr = {d.max():,.0f} km", fontsize=16,
                color=INK, ha="left", va="top", zorder=9, path_effects=HALO, linespacing=1.4)
        save_opaque(fig, f"storks-klcenter-{k}.svg")


def fig_radius(radii, ell, mark):
    fig, ax = plt.subplots(figsize=(4.8, 3.3))
    ks = np.arange(1, len(radii) + 1)
    ax.plot(ks, radii, "-", color=COL[0], lw=2, zorder=2)
    ax.plot(ks, radii, "o", color=COL[0], ms=8, mec="white", mew=1.5, zorder=3)
    ax.plot(mark, radii[mark - 1], "o", ms=15, mfc="none", mec=INK, mew=2, zorder=4)
    ax.text(mark + 0.25, radii[mark - 1] + 450, f"k = {mark}: {radii[mark - 1]:,.0f} km", fontsize=15, color=INK,
            ha="left", va="bottom", path_effects=HALO)
    ax.set_xticks(ks)
    ax.set_ylim(0, max(radii) * 1.12)
    ax.set_yticks(range(0, int(max(radii) * 1.12), 2000))
    ax.set_yticklabels([f"{v:,}" for v in range(0, int(max(radii) * 1.12), 2000)])
    ax.grid(axis="y", color="#e3e3e0", lw=0.8)
    ax.set_axisbelow(True)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.set_xlabel("k (number of representative routes)", fontsize=15, color=INK)
    ax.set_ylabel("radius (km)", fontsize=15, color=INK)
    ax.tick_params(labelsize=14, colors=INK)
    ax.text(0.98, 0.95, f"ℓ = {ell}", transform=ax.transAxes, fontsize=15, color=GREY, ha="right", va="top")
    save(fig, "klcenter-radius.svg")


def band(ax, P, r, col):
    """Region within distance r of the polyline P: a line of width 2r in data units, round caps and joins."""
    ax.figure.canvas.draw()
    (x0, _), (x1, _) = ax.transData.transform([(0, 0), (2 * r, 0)])
    ax.plot(P[:, 0], P[:, 1], "-", color=col, lw=(x1 - x0) * 72 / ax.figure.dpi, solid_capstyle="round",
            solid_joinstyle="round", zorder=0)


def to_polyline(p, P):
    """Euclidean distance from the point p to the polyline P."""
    A, AB = P[:-1], P[1:] - P[:-1]
    t = np.clip(((p - A) * AB).sum(1) / np.maximum((AB * AB).sum(1), 1e-12), 0, 1)
    return float(np.hypot(*(A + t[:, None] * AB - p).T).min())


def fig_points_to_curves():
    """From points to curves (schematic, synthetic data): a centre point and radius r; an input curve as centre,
    with its detour; a centre curve with few vertices. Shaded: everything within distance r of the centre."""
    rng = np.random.default_rng(5)
    fig, axs = plt.subplots(1, 3, figsize=(13.2, 3.0))
    for ax in axs:
        ax.set_xlim(0, 10)
        ax.set_ylim(-0.9, 6.6)
        ax.set_aspect("equal")
        ax.axis("off")
    fig.tight_layout(w_pad=1.0)                          # before band(), which needs the final scale
    # (a) points: the centre is an input point
    ax = axs[0]
    c = np.array([5.0, 3.0])
    P = c + rng.normal(0, 0.95, (10, 2))
    r = float(np.hypot(*(P - c).T).max())
    far = P[np.argmax(np.hypot(*(P - c).T))]
    ax.add_patch(mpatches.Circle(c, r, fc=PALE, ec="none", zorder=0))
    ax.plot(P[:, 0], P[:, 1], "o", color=GREY, ms=7, mec="white", mew=1, zorder=2)
    ax.plot([c[0], far[0]], [c[1], far[1]], color=INK, lw=1.8, zorder=3)
    ax.plot(*c, "o", color=COL[0], ms=12, mec="white", mew=1.5, zorder=4)
    mid, u = (c + far) / 2, (far - c) / np.hypot(*(far - c))
    ax.text(*(mid + 0.42 * np.array([-u[1], u[0]])), "$r$", fontsize=19, color=INK, ha="center", va="center",
            zorder=5, path_effects=HALO)
    # (b) and (c): five curves; (b) one of them, with a loop, is the centre; (c) a centre with four vertices
    x = np.linspace(0.5, 9.5, 13)
    base = lambda x: 2.4 + 1.6 * np.sin((x - 0.5) / 9 * np.pi)
    curves = [np.c_[x + rng.normal(0, 0.06, len(x)), base(x) + off + rng.normal(0, 0.13, len(x))]
              for off in (-0.75, -0.38, 0.0, 0.38, 0.75)]
    C = curves[2]
    k = 8                                                # a loop after vertex k, like circling in one area
    ang = np.linspace(-np.pi / 2, 1.5 * np.pi, 11)[1:-1]
    loop = C[k] + np.array([0.15, 0.62]) + 0.62 * np.c_[np.cos(ang), np.sin(ang)]
    C = np.r_[C[:k + 1], loop, C[k + 1:]]
    S = np.c_[[0.5, 3.4, 6.6, 9.5], base(np.array([0.5, 3.4, 6.6, 9.5]))]
    for ax, centre, others, ms, mew in [(axs[1], C, [Q for i, Q in enumerate(curves) if i != 2], 4, 0),
                                        (axs[2], S, curves, 9, 1)]:
        r = max(to_polyline(p, centre) for Q in others for p in Q)
        band(ax, centre, r, PALE)
        for Q in others:
            ax.plot(Q[:, 0], Q[:, 1], "-o", color=GREY, lw=1.2, ms=3, zorder=2)
        ax.plot(centre[:, 0], centre[:, 1], "-", color="white", lw=5.5, zorder=3, solid_joinstyle="round")
        ax.plot(centre[:, 0], centre[:, 1], "-o", color=COL[0], lw=2.8, ms=ms, mec="white", mew=mew, zorder=4,
                solid_joinstyle="round")
        p0 = centre[0]
        ax.plot([p0[0], p0[0]], [p0[1], p0[1] - r], color=INK, lw=1.8, zorder=5)
        ax.text(p0[0] - 0.3, p0[1] - r / 2, "$r$", fontsize=19, color=INK, ha="right", va="center", zorder=5,
                path_effects=HALO)
    for ax, text in zip(axs, ["centre: an input point", "centre: an input trajectory", "centre: at most ℓ vertices"]):
        ax.text(5, 0.45, text, fontsize=24, color=INK, ha="center", va="top")
    save(fig, "points-to-curves.svg")


def fig_why3():
    """Why Gonzalez with simplification gives 3 r* (schematic; points stand for curves): p_i and p_j share an
    optimal cluster, q_i is the simplification of p_i, and p_j is at least r away from q_i."""
    fig, ax = plt.subplots(figsize=(5.4, 3.7))
    ax.set_xlim(-0.35, 5.25)
    ax.set_ylim(0.35, 4.7)
    ax.set_aspect("equal")
    ax.axis("off")
    c, R = np.array([3.2, 2.55]), 1.55
    ax.add_patch(mpatches.Circle(c, R, fc="#f2f2f0", ec=GREY, lw=1.4, ls=(0, (4, 3)), zorder=1))
    ax.text(c[0], c[1] + R + 0.12, "an optimal cluster, radius $r^{\\ast}$", fontsize=16, color=GREY, ha="center",
            va="bottom")
    pi, pj, qi = np.array([2.3, 3.25]), np.array([4.0, 1.7]), np.array([0.85, 2.8])
    for (a, b), col, text, at, ha in [((pi, qi), COL[0], "$\\leq r^{\\ast}$", (1.45, 3.35), "center"),
                                      ((pi, pj), COL[2], "$\\leq 2r^{\\ast}$", (3.42, 2.72), "left"),
                                      ((qi, pj), COL[1], "$\\geq r$", (2.3, 1.98), "center")]:
        ax.plot([a[0], b[0]], [a[1], b[1]], color=col, lw=2.8, zorder=3, solid_capstyle="round")
        ax.text(*at, text, fontsize=19, fontweight="bold", color=col, ha=ha, va="center", zorder=6,
                path_effects=HALO)
    for p, lbl, (dx, dy, ha) in [(pi, "$p_i$", (0.12, 0.2, "left")), (pj, "$p_j$", (0.18, -0.05, "left"))]:
        ax.plot(*p, "o", color=INK, ms=10, mec="white", mew=1.2, zorder=5)
        ax.text(p[0] + dx, p[1] + dy, lbl, fontsize=20, color=INK, ha=ha, va="center", zorder=6, path_effects=HALO)
    ax.plot(*qi, "s", color=COL[0], ms=11, mec="white", mew=1.2, zorder=5)
    ax.text(qi[0] - 0.2, qi[1], "$q_i$", fontsize=20, color=COL[0], ha="right", va="center", zorder=6,
            path_effects=HALO)
    ax.text(-0.3, 0.55, "points stand for curves", fontsize=15, color=GREY, ha="left", va="center", style="italic")
    save(fig, "klcenter-proof.svg")


BOTTLENECKS = {"Strait of Gibraltar": (36.0, -5.6), "Levant": (32.0, 35.5)}   # Levant: Jordan valley
NEAR_KM = 100


def near_km(P, lat0, lon0):
    """Smallest distance in km from (lat0, lon0) to the route P (lat, lon), in an azimuthal equidistant projection
    centred there: exact for the positions, close enough for the segments between two daily positions."""
    x, y = aeqd(P[:, 0], P[:, 1], lat0, lon0)
    return to_polyline(np.zeros(2), np.c_[x, y])


def fig_bottlenecks(routes, Q, assign, through, place):
    """The routes in their clusters, the representative routes and two bottlenecks with the number of routes."""
    proj, box = OVERVIEW
    fig, ax = plt.subplots(figsize=(6.0, 6.0))
    basemap(ax, proj, box, tol=20)
    for i, P in enumerate(routes):
        x, y = proj(P[:, 1], P[:, 0])
        ax.plot(x, y, color=COL[assign[i]], lw=0.9, alpha=0.5, zorder=2, solid_joinstyle="round")
    for ci, V in enumerate(Q):
        vx, vy = proj(V[:, 1], V[:, 0])
        ax.plot(vx, vy, "-", color="white", lw=6, zorder=4, solid_joinstyle="round")
        ax.plot(vx, vy, "-o", color=COL[ci], lw=3.0, ms=6, mec="white", mew=1.0, zorder=5, solid_joinstyle="round")
    for nm, (lat, lon) in BOTTLENECKS.items():
        x, y = proj(lon, lat)
        ax.plot(x, y, "o", ms=24, mfc="none", mec=INK, mew=2.4, zorder=9)
        dx, dy, ha = place[nm]
        ax.annotate(f"{nm}:\n{len(through[nm])} of {len(routes)} routes", xy=(x, y), xytext=(x + dx, y + dy), fontsize=14,
                    fontweight="bold", color=INK, ha=ha, va="center", zorder=10, path_effects=HALO,
                    linespacing=1.25, arrowprops=dict(arrowstyle="-", color=INK, lw=1.2, shrinkA=2, shrinkB=10))
    ax.text(box[0] + 150, box[2] + 250, f"{len(routes)} routes in {len(Q)} clusters\nwith their representatives",
            fontsize=14, color=INK, ha="left", va="bottom", zorder=9, path_effects=HALO, linespacing=1.35)
    save_opaque(fig, "storks-bottlenecks.svg")


# ---------------------------------------------------------------- main
gps = load_gps()
info = describe(gps)
print(f"{len(info)} juveniles; first winter known for {int(info['wlat'].notna().sum())}")

# 1) schematics
fig_points_curves()
fig_points_to_curves()

# 2) points: the first-winter sites, Gonzalez starting at Karamell
win = info[info["wlat"].notna()].reset_index(drop=True)
W = win[["wlat", "wlon"]].values
DW = dist_matrix(W, W)
wnames = [name(b) for b in win["bird"]]
chosen, radii, assign, d = gonzalez(lambda i: DW[i], len(W), 6, wnames.index("Karamell"))
print("winter sites, Gonzalez from Karamell:", " -> ".join(f"{wnames[c]} ({win.at[c, 'pop']})" for c in chosen))
print("  radius after k = 1..6:", ", ".join(km(r) for r in radii))
for k in (3, 4, 5):
    best = min((DW[list(C)].min(axis=0).max(), C) for C in itertools.combinations(range(len(W)), k))
    lb = min(DW[a, b] for a, b in itertools.combinations(chosen[:k + 1], 2)) / 2
    print(f"  k = {k}: Gonzalez {km(radii[k - 1])}; best with centres at winter sites {km(best[0])} "
          f"({', '.join(wnames[c] for c in best[1])}); any centres: at least {km(lb)}")
place = {wnames.index("Karamell"): ("Morocco", -300, 0, "right"),
         wnames.index("Pelopidas"): ("South Africa", 270, 0, "left"),
         wnames.index("Halim"): ("Uzbekistan", -300, 0, "right"),
         wnames.index("DER AR446"): ("Sudan", 270, 0, "left")}
fig_winter_sites(win)
fig_winter_steps(win, DW, chosen[:5], radii, place)

# 3) exercise and proof figure
names_ex, ch_ex, r_ex, D_ex = fig_exercise()
print("exercise: start a ->", " -> ".join(names_ex[c] for c in ch_ex), "; radius after k=1..3:",
      ", ".join(f"{r:.2f}" for r in r_ex))
fig_proof()
fig_why3()

# 4) routes: juveniles that migrated and were tracked into the winter; daily positions from the day
#    before departure until 31 December 2013 (as in lecture 2)
mig = info[info["strategy"].isin(["crossed the Sahara", "stayed north of the Sahara"])].reset_index(drop=True)
routes = [route(gps, info, b, "2014-01-01")[["lat", "lon"]].values for b in mig["bird"]]
names_r = [name(b) for b in mig["bird"]]
print(f"routes: {len(routes)}, {min(map(len, routes))}-{max(map(len, routes))} daily positions")
fig_routes(routes, mig)
F = np.zeros((len(routes), len(routes)))
for a, b in itertools.combinations(range(len(routes)), 2):
    F[a, b] = F[b, a] = dF(routes[a], routes[b])
ch0, r0, _, _ = gonzalez(lambda i: F[i], len(routes), 6, names_r.index("Karamell"))
print("routes, Gonzalez with input routes as centres:", " -> ".join(names_r[c] for c in ch0))
print("  radius after k = 1..6:", ", ".join(km(r) for r in r0))

# 5) (k, l)-center: Gonzalez with simplified centres, l = 6, k up to 8 for the radius plot
ELL, K = 6, 5
first = names_r.index("Karamell")
chosen_r, Q, dq, rad_r, simp_err = [], [], [], [], []
cur = np.full(len(routes), np.inf)
p = first
for step in range(8):
    verts, err, groups = simplify(routes[p], ELL)
    dist = np.array([dF(R, verts) for R in routes])
    chosen_r.append(p)
    Q.append(verts)
    dq.append(dist)
    simp_err.append(err)
    cur = np.minimum(cur, dist)
    rad_r.append(float(cur.max()))
    p = int(np.argmax(cur))
print(f"(k, l)-center, l = {ELL}, Gonzalez with simplification from Karamell:")
for k in range(8):
    print(f"  k = {k + 1}: centre {names_r[chosen_r[k]]} ({mig.at[chosen_r[k], 'pop']}, "
          f"{len(routes[chosen_r[k]])} positions, simplification error {km(simp_err[k])}); radius {km(rad_r[k])}")
dq = np.array(dq)
far = int(np.argmax(np.min(dq[:K], axis=0)))
lb = min(F[a, b] for a, b in itertools.combinations(chosen_r[:K + 1], 2)) / 2
s_all = [simplify(R, ELL)[1] for R in routes]
print(f"  k = {K}: radius {km(rad_r[K - 1])} (farthest: {names_r[far]}); lower bound for the optimum: "
      f"max(half the smallest distance among the {K + 1} chosen routes = {km(lb)}, largest simplification "
      f"error of any route = {km(max(s_all))}); ratio at most {rad_r[K - 1] / max(lb, max(s_all)):.2f}")
assign_r = np.argmin(dq[:K], axis=0)
for ci in range(K):
    print(f"  cluster {ci + 1} ({names_r[chosen_r[ci]]}): " +
          ", ".join(f"{names_r[i]} [{mig.at[i, 'pop']}]" for i in np.where(assign_r == ci)[0]))
fig_klcenter_steps(routes, mig, chosen_r[:K], Q[:K], dq[:K], ELL)
fig_radius(rad_r, ELL, K)
near = {nm: np.array([near_km(R, lat, lon) for R in routes]) for nm, (lat, lon) in BOTTLENECKS.items()}
through = {nm: np.where(d <= NEAR_KM)[0] for nm, d in near.items()}
for nm, d in near.items():
    sel = through[nm]
    print(f"  {nm}: {len(sel)} of {len(routes)} routes pass within {NEAR_KM} km (within 150 / 200 km: "
          f"{int((d <= 150).sum())} / {int((d <= 200).sum())}); by cluster at k = {K}: " +
          ", ".join(f"{ci + 1}: {int((assign_r[sel] == ci).sum())} of {int((assign_r == ci).sum())}"
                    for ci in range(K) if (assign_r[sel] == ci).any()))
fig_bottlenecks(routes, Q[:K], assign_r, through, {"Strait of Gibraltar": (-200, 1350, "center"),
                                                   "Levant": (1000, -750, "left")})
for ell in (4, 8):
    cur2, p2 = np.full(len(routes), np.inf), first
    for step in range(K):
        v = simplify(routes[p2], ell)[0]
        cur2 = np.minimum(cur2, np.array([dF(R, v) for R in routes]))
        p2 = int(np.argmax(cur2))
    print(f"  l = {ell}: radius with k = {K}: {km(cur2.max())}")

# 6) simplification of one route
pel = names_r.index("Pelopidas")
verts, err, groups = simplify(routes[pel], ELL)
print(f"Pelopidas: {len(routes[pel])} positions, {ELL}-vertex simplification error {km(err)}, groups "
      + ", ".join(f"{i}-{j}" for i, j in groups))
fig_simplification(routes[pel], verts, groups, err, "Pelopidas, Greece to South Africa")
