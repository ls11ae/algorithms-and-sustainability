"""Figures on white stork migration for "Algorithms and Sustainability", lecture 2 (own work, CC BY 4.0).

Usage:  python3 tools/make_stork_figures.py <data folder> lectures/figures [<track folder>]
The data folder (searched recursively; in AuN: movement-analysis/data) holds
  - the GPS data of Flack et al. (2016), Science Advances 2:e1500931, from the Movebank Data
    Repository, doi:10.5441/001/1.78152p3q, licence CC0:
    "MPIO white stork lifetime tracking data (2013-2014)-gps.csv.zip";
  - two Natural Earth 1:50m layers (public domain) as GeoJSON:
    ne_50m_admin_0_countries.geojson and ne_50m_lakes.geojson from
    https://github.com/nvkelso/natural-earth-vector/tree/master/geojson
Writes storks-overview.svg, storks-two-routes.svg, storks-autumn-spring.svg and storks-one-day.svg
and prints the numbers quoted on the slides. With a track folder, it also writes the full-resolution
tracks of the fully tracked storks (first 150 days after departure, one "lat lon" line per fix) for
timing experiments.
Needs: matplotlib, numpy, pandas. Font as in make_figures.py (LATO_DIR).
"""
import functools
import glob
import json
import os
import re
import sys
import zipfile

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib import patheffects
from matplotlib.collections import PolyCollection
import matplotlib.patches

data_dir, out = sys.argv[1], sys.argv[2]
track_dir = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(out, exist_ok=True)
FD = os.environ.get("LATO_DIR", "")
HAVE_LATO = bool(FD) and os.path.exists(os.path.join(FD, "LatoLatin-Regular.ttf"))
if HAVE_LATO:
    for f in ["LatoLatin-Regular.ttf", "LatoLatin-Bold.ttf", "LatoLatin-Italic.ttf"]:
        font_manager.fontManager.addfont(os.path.join(FD, f))
plt.rcParams.update({
    "font.family": "LatoLatin" if HAVE_LATO else "sans-serif", "font.size": 13, "svg.fonttype": "path",
    "savefig.transparent": True, "svg.hashsalt": "aus-2627-storks",
})
INK, GREY = "#282a2e", "#8e908c"
LAND, BORDER = "#ebebe8", "#ffffff"
BLUE, GREEN = "#0A97D9", "#3F7E44"           # track colours as in make_figures.py (SDG 14, SDG 13)
STRATEGY = {                                  # validated as a set (all pairs, white background)
    "crossed the Sahara": "#0A97D9",
    "stayed north of the Sahara": "#E8700A",
    "did not migrate": "#DD1367",
}
R_EARTH = 6371.0
HALO = [patheffects.withStroke(linewidth=3.2, foreground="white")]
POPULATIONS = {"Spain Donana": "Spain", "SWGermany 2013": "SW Germany", "Tunisia": "Tunisia", "Poland": "Poland",
               "Greece Evros Delta": "Greece", "Moscow": "Russia", "Armenia": "Armenia", "Uzbekistan": "Uzbekistan"}
RESIDENT_KM = 150                             # "within a radius of about 150 km" (Flack et al. 2016)


def save(fig, name):
    path = os.path.join(out, name)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.05, metadata={"Date": None})
    plt.close(fig)
    # round path coordinates to 0.01 pt: invisible, but the maps get about 40 % smaller
    num = re.compile(r"-?\d+\.\d+")
    short = lambda m: f"{float(m.group()):.2f}".rstrip("0").rstrip(".")
    with open(path, encoding="utf-8") as f:
        svg = f.read()
    svg = re.sub(r'(\sd=")([^"]*)(")', lambda m: m.group(1) + num.sub(short, m.group(2)) + m.group(3), svg)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)


# ---------------------------------------------------------------- geometry
def laea(lon, lat, lon0, lat0):
    """Lambert azimuthal equal-area projection, in kilometres."""
    lon, lat = np.radians(lon), np.radians(lat)
    l0, p0 = np.radians(lon0), np.radians(lat0)
    k = np.sqrt(2 / (1 + np.sin(p0) * np.sin(lat) + np.cos(p0) * np.cos(lat) * np.cos(lon - l0)))
    x = R_EARTH * k * np.cos(lat) * np.sin(lon - l0)
    y = R_EARTH * k * (np.cos(p0) * np.sin(lat) - np.sin(p0) * np.cos(lat) * np.cos(lon - l0))
    return x, y


def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in km; broadcasts."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    h = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * R_EARTH * np.arcsin(np.sqrt(np.minimum(h, 1.0)))


def dist_matrix(A, B):
    """A, B: arrays of (lat, lon). Returns the matrix of great-circle distances."""
    return haversine(A[:, None, 0], A[:, None, 1], B[None, :, 0], B[None, :, 1])


def discrete_frechet(D):
    """Discrete Fréchet distance and one optimal coupling for a distance matrix D (O(nm))."""
    n, m = D.shape
    C = np.empty_like(D)
    C[0, 0] = D[0, 0]
    C[0, 1:] = np.maximum.accumulate(D[0, 1:].clip(min=D[0, 0]))
    C[1:, 0] = np.maximum.accumulate(D[1:, 0].clip(min=D[0, 0]))
    for i in range(1, n):
        for j in range(1, m):
            C[i, j] = max(D[i, j], min(C[i - 1, j - 1], C[i - 1, j], C[i, j - 1]))
    pairs, i, j = [(n - 1, m - 1)], n - 1, m - 1
    while (i, j) != (0, 0):
        cand = [(p, q) for p, q in [(i - 1, j - 1), (i - 1, j), (i, j - 1)] if p >= 0 and q >= 0]
        i, j = min(cand, key=lambda pq: (C[pq], D[pq]))
        pairs.append((i, j))
    return C[-1, -1], pairs[::-1]


def hausdorff(D):
    """Hausdorff distance and the pair of points that realises it."""
    a, b = D.min(axis=1), D.min(axis=0)
    if a.max() >= b.max():
        i = int(a.argmax())
        return a[i], (i, int(D[i].argmin()))
    j = int(b.argmax())
    return b[j], (int(D[:, j].argmin()), j)


def clip_ring(P, xmin, xmax, ymin, ymax):
    """Sutherland–Hodgman: clip a polygon ring to a rectangle."""
    def clip(P, inside, cut):
        out = []
        for k in range(len(P)):
            cur, prev = P[k], P[k - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(cut(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cut(prev, cur))
        return np.array(out) if out else np.empty((0, 2))

    def cut_x(x0):
        return lambda a, b: np.array([x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0])])

    def cut_y(y0):
        return lambda a, b: np.array([a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0])

    for inside, cut in [(lambda p: p[0] >= xmin, cut_x(xmin)), (lambda p: p[0] <= xmax, cut_x(xmax)),
                        (lambda p: p[1] >= ymin, cut_y(ymin)), (lambda p: p[1] <= ymax, cut_y(ymax))]:
        if len(P) == 0:
            break
        P = clip(P, inside, cut)
    return P


def thin(P, tol):
    """Drop vertices closer than tol (km) to the previously kept one."""
    keep, last = [0], P[0]
    for k in range(1, len(P)):
        if np.hypot(*(P[k] - last)) >= tol:
            keep.append(k)
            last = P[k]
    return P[keep]


def find(pattern):
    hits = sorted(glob.glob(os.path.join(data_dir, "**", pattern), recursive=True))
    if not hits:
        sys.exit(f"{pattern} not found in {data_dir}")
    return hits[0]


@functools.lru_cache(maxsize=None)
def features(name):
    with open(find(name), encoding="utf-8") as f:
        return json.load(f)["features"]


def rings(geom):
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    for poly in polys:
        yield np.array(poly[0], float)          # outer ring only (holes are lakes, drawn separately)


def basemap(ax, proj, box, tol, lakes=True):
    """Countries (light grey, white borders) and large lakes, projected and clipped to box."""
    xmin, xmax, ymin, ymax = box
    polys = []
    for feat in features("ne_50m_admin_0_countries.geojson"):
        for ring in rings(feat["geometry"]):
            x, y = proj(ring[:, 0], ring[:, 1])
            P = np.c_[x, y]
            P = P[np.isfinite(P).all(axis=1)]
            if len(P) < 3 or P[:, 0].max() < xmin or P[:, 0].min() > xmax \
                    or P[:, 1].max() < ymin or P[:, 1].min() > ymax:
                continue
            P = clip_ring(thin(P, tol), xmin - 50, xmax + 50, ymin - 50, ymax + 50)
            if len(P) >= 3:
                polys.append(P)
    ax.add_collection(PolyCollection(polys, facecolor=LAND, edgecolor=BORDER, linewidth=0.6, zorder=0))
    if lakes:
        feats = [ft for ft in features("ne_50m_lakes.geojson") if ft["properties"].get("scalerank", 9) <= 2]
        lp = []
        for feat in feats:
            for ring in rings(feat["geometry"]):
                x, y = proj(ring[:, 0], ring[:, 1])
                P = clip_ring(thin(np.c_[x, y], tol), xmin - 50, xmax + 50, ymin - 50, ymax + 50)
                if len(P) >= 3:
                    lp.append(P)
        ax.add_collection(PolyCollection(lp, facecolor="#ffffff", edgecolor="none", zorder=0.5))
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.axis("off")


def scalebar(ax, x, y, km, label=None):
    ax.plot([x, x + km], [y, y], color=INK, lw=2.4, solid_capstyle="butt", zorder=5)
    ax.text(x + km / 2, y + 0.015 * np.diff(ax.get_ylim())[0], label or f"{km:g} km", ha="center", va="bottom",
            fontsize=13, color=INK)


# ---------------------------------------------------------------- data
def load_gps():
    with zipfile.ZipFile(find("*gps.csv.zip")) as z:
        name = [n for n in z.namelist() if n.endswith(".csv") and not n.startswith("__MACOSX")][0]
        with z.open(name) as f:
            df = pd.read_csv(f, low_memory=False)
    if "visible" in df:
        df = df[df["visible"].astype(str).str.lower() == "true"]
    df = df.rename(columns={"location-long": "lon", "location-lat": "lat", "individual-local-identifier": "bird",
                            "study-specific-measurement": "study"})
    df["pop"] = df["study"].str.replace("LifeTrack White Stork ", "", regex=False).map(POPULATIONS)
    df = df[df["pop"].notna()]                  # the eight juvenile populations (drops one bird tagged in South Africa)
    df["t"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.dropna(subset=["lon", "lat"]).sort_values(["bird", "t"])
    return df[["bird", "pop", "t", "lon", "lat"]].reset_index(drop=True)


def noon_fixes(track):
    """One position per day: the fix closest to 12:00 UTC."""
    d = track.assign(day=track["t"].dt.floor("D"),
                     off=(track["t"].dt.hour * 60 + track["t"].dt.minute - 720).abs())
    return d.loc[d.groupby("day")["off"].idxmin()].drop(columns=["day", "off"]).reset_index(drop=True)


def describe(gps):
    """Per bird: natal site and population, departure, first-winter site, strategy, sampling.

    First winter = median position in December and January after tagging. Within 150 km of the
    nest: did not migrate; south of 20°N: crossed the Sahara; otherwise: stayed north of the Sahara.
    No fix in that period: track ended before winter (the bird died or the tag stopped)."""
    rows = []
    for bird, tr in gps.groupby("bird", sort=False):
        tr = tr.reset_index(drop=True)
        lon0, lat0, t0 = tr.at[0, "lon"], tr.at[0, "lat"], tr.at[0, "t"]
        south = tr[tr["lat"] < lat0 - 0.5]                      # departure as in Flack et al. (2016)
        dep = south["t"].iloc[0] if len(south) else pd.NaT
        y = t0.year
        win = tr[(tr["t"] >= pd.Timestamp(f"{y}-12-01", tz="UTC")) & (tr["t"] < pd.Timestamp(f"{y + 1}-02-01", tz="UTC"))]
        if len(win) == 0:
            strategy, wlon, wlat = "track ended before winter", np.nan, np.nan
        else:
            wlon, wlat = win["lon"].median(), win["lat"].median()
            if haversine(lat0, lon0, wlat, wlon) < RESIDENT_KM:
                strategy = "did not migrate"
            elif wlat < 20:
                strategy = "crossed the Sahara"
            else:
                strategy = "stayed north of the Sahara"
        gap = tr["t"].diff().dt.total_seconds().median() / 60
        rows.append(dict(bird=bird, lon0=lon0, lat0=lat0, t0=t0, pop=tr.at[0, "pop"],
                         departure=dep, wlon=wlon, wlat=wlat, strategy=strategy, n=len(tr),
                         median_gap_min=gap, end=tr["t"].iloc[-1]))
    return pd.DataFrame(rows)


def first_winter(tr, t0):
    """The track from tagging until 31 January of the first winter."""
    return tr[tr["t"] < pd.Timestamp(f"{t0.year + 1}-02-01", tz="UTC")]


# ---------------------------------------------------------------- figures
LEGEND_ORDER = ["crossed the Sahara", "stayed north of the Sahara", "did not migrate", "track ended before winter"]


def fig_overview(gps, info, labels, note=None):
    """First journey of all juveniles until 31 January, coloured by where they spent the winter."""
    proj = lambda lo, la: laea(lo, la, 28, 14)
    fig, ax = plt.subplots(figsize=(6.0, 6.0))
    basemap(ax, proj, (-5100, 3750, -4500, 4900), tol=20)
    for strategy in ["track ended before winter", "crossed the Sahara", "stayed north of the Sahara", "did not migrate"]:
        for _, r in info[info["strategy"] == strategy].iterrows():
            tr = noon_fixes(first_winter(gps[gps["bird"] == r["bird"]], r["t0"]))
            x, y = proj(tr["lon"].values, tr["lat"].values)
            if strategy == "track ended before winter":
                ax.plot(x, y, color=GREY, lw=0.8, alpha=0.8, zorder=1)
                ax.plot(x[-1], y[-1], marker="x", ms=4, mew=1.0, color=GREY, zorder=1)
            else:
                ax.plot(x, y, color=STRATEGY[strategy], lw=1.4, alpha=0.9, zorder=2, solid_joinstyle="round")
            if strategy == "did not migrate":       # residents stay at the nest site: ring around it
                ax.plot(*proj(r["lon0"], r["lat0"]), "o", ms=13, mfc="none", mec=STRATEGY[strategy], mew=2.2, zorder=6)
    for pop, g in info.groupby("pop"):
        x, y = proj(g["lon0"].mean(), g["lat0"].mean())
        ax.plot(x, y, "o", ms=7, color=INK, mec="white", mew=1.2, zorder=5)
        text, dx, dy, ha = labels.get(pop, (pop, 120, 120, "left"))
        ax.text(x + dx, y + dy, text, fontsize=14, color=INK, ha=ha, va="center", zorder=6, path_effects=HALO)
    if note:                                    # annotation of one winter area, e.g. the dumps in Morocco
        (lon, lat), (dx, dy), text = note
        x, y = proj(lon, lat)
        ax.annotate(text, xy=(x, y), xytext=(x + dx, y + dy), fontsize=12.5, color=INK, ha="right", va="center",
                    zorder=6, path_effects=HALO,
                    arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkA=2, shrinkB=3))
    handles = []
    for strategy in LEGEND_ORDER:
        n = int((info["strategy"] == strategy).sum())
        if n == 0:
            continue
        col = GREY if strategy == "track ended before winter" else STRATEGY[strategy]
        if strategy == "did not migrate":
            h = plt.Line2D([], [], ls="none", marker="o", ms=11, mfc="none", mec=col, mew=2.2)
        else:
            h = plt.Line2D([], [], color=col, lw=2.2 if col != GREY else 1.2,
                           marker="x" if col == GREY else None, ms=4, mew=1.0)
        h.set_label(f"{strategy} ({n})")
        handles.append(h)
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(1.0, 0.04), frameon=False,
              fontsize=13, handlelength=1.5, labelspacing=0.5,
              title="first winter\n(December and January)", title_fontsize=13, alignment="left")
    save(fig, "storks-overview.svg")


def route(gps, info, bird, end):
    """Daily positions (12:00 UTC) from the day before departure until `end`."""
    r = info.set_index("bird").loc[bird]
    tr = gps[(gps["bird"] == bird) & (gps["t"] >= r["departure"].floor("D") - pd.Timedelta(days=1))
             & (gps["t"] < pd.Timestamp(end, tz="UTC"))]
    return noon_fixes(tr)


def fig_two_routes(gps, info, panels, end):
    """Pairs of juveniles from the same nest site: how similar are their routes (discrete Fréchet)?

    panels: list of dicts with keys a, b (bird ids), name_a, name_b, off_a, off_b (label offsets in km,
    plus alignment) and off_d (offset of the distance label from the middle of the longest leash)."""
    proj = lambda lo, la: laea(lo, la, -3, 31)
    box = (-1650, 1350, -2150, 2050)
    fig, axs = plt.subplots(1, len(panels), figsize=(4.6 * len(panels), 6.2))
    results = []
    for ax, pn in zip(np.atleast_1d(axs), panels):
        A, B = route(gps, info, pn["a"], end), route(gps, info, pn["b"], end)
        PA, PB = A[["lat", "lon"]].values, B[["lat", "lon"]].values
        D = dist_matrix(PA, PB)
        dF, pairs = discrete_frechet(D)
        dH, _ = hausdorff(D)
        basemap(ax, proj, box, tol=8, lakes=False)
        xa, ya = proj(PA[:, 1], PA[:, 0])
        xb, yb = proj(PB[:, 1], PB[:, 0])
        step = max(1, len(pairs) // 30)
        for p, q in pairs[::step]:
            ax.plot([xa[p], xb[q]], [ya[p], yb[q]], color=GREY, lw=0.8, ls=(0, (2, 2)), zorder=1)
        k = int(np.argmax([D[p, q] for p, q in pairs]))
        p, q = pairs[k]
        ax.plot([xa[p], xb[q]], [ya[p], yb[q]], color=INK, lw=2.6, zorder=4, solid_capstyle="round")
        ax.plot(xb, yb, "-o", color=GREEN, lw=1.8, ms=2.8, zorder=2)
        ax.plot(xa, ya, "-o", color=BLUE, lw=1.8, ms=2.8, zorder=3)
        ax.plot(xa[0], ya[0], "o", ms=8, color=INK, mec="white", mew=1.2, zorder=5)
        ax.text(xa[0] - 90, ya[0] + 60, "start", fontsize=14, color=GREY, ha="right", va="bottom", path_effects=HALO)
        for (x, y), name, col, (dx, dy, ha) in [((xa[-1], ya[-1]), pn["name_a"], BLUE, pn["off_a"]),
                                                ((xb[-1], yb[-1]), pn["name_b"], GREEN, pn["off_b"])]:
            ax.text(x + dx, y + dy, name, fontsize=15, fontweight="bold", color=col, ha=ha, va="center",
                    zorder=6, path_effects=HALO)
        mx, my = (xa[p] + xb[q]) / 2, (ya[p] + yb[q]) / 2
        dx, dy, ha = pn["off_d"]
        ax.annotate(f"Fréchet distance\n{dF:,.0f} km", xy=(mx, my), xytext=(mx + dx, my + dy), fontsize=14.5,
                    color=INK, ha=ha, va="center", zorder=6, path_effects=HALO,
                    arrowprops=None if (dx, dy) == (0, 0) else dict(arrowstyle="-", color=INK, lw=0.8, shrinkB=2))
        results.append(dict(a=pn["a"], b=pn["b"], dF=dF, dH=dH, nA=len(PA), nB=len(PB),
                            leash=(A.iloc[p]["t"], B.iloc[q]["t"])))
    fig.tight_layout(w_pad=0.5)
    save(fig, "storks-two-routes.svg")
    return results


def fig_autumn_spring(gps, bird, autumn, spring, name):
    """One stork, autumn and spring migration: same corridor, opposite direction."""
    tr = gps[gps["bird"] == bird]
    seg = lambda a, b: noon_fixes(tr[(tr["t"] >= pd.Timestamp(a, tz="UTC")) & (tr["t"] < pd.Timestamp(b, tz="UTC"))])
    A, B = seg(*autumn), seg(*spring)
    PA, PB = A[["lat", "lon"]].values, B[["lat", "lon"]].values
    D = dist_matrix(PA, PB)
    dF, pairs = discrete_frechet(D)
    dH, (hi, hj) = hausdorff(D)
    dF_rev, _ = discrete_frechet(dist_matrix(PA, PB[::-1]))
    proj = lambda lo, la: laea(lo, la, 1, 41.5)
    fig, ax = plt.subplots(figsize=(7.4, 7.1))
    basemap(ax, proj, (-1100, 1150, -1060, 1050), tol=5, lakes=False)
    xa, ya = proj(PA[:, 1], PA[:, 0])
    xb, yb = proj(PB[:, 1], PB[:, 0])
    ORANGE = STRATEGY["stayed north of the Sahara"]
    for x, y, col in [(xa, ya, BLUE), (xb, yb, ORANGE)]:
        ax.plot(x, y, "-o", color=col, lw=1.8, ms=2.6, zorder=3)
        steps = np.hypot(np.diff(x), np.diff(y))
        for frac in (0.3, 0.55, 0.8):              # arrowheads on long daily steps: direction of travel
            k = int(frac * len(steps))
            k += int(np.argmax(steps[k:k + 8]))
            ax.add_patch(matplotlib.patches.FancyArrowPatch((x[k], y[k]), (x[k + 1], y[k + 1]), arrowstyle="-|>",
                                                            mutation_scale=20, color=col, lw=0, zorder=4))
    k = int(np.argmax([D[p, q] for p, q in pairs]))
    p, q = pairs[k]
    ax.plot([xa[p], xb[q]], [ya[p], yb[q]], color=INK, lw=2.6, zorder=5, solid_capstyle="round")
    ax.plot([xa[hi], xb[hj]], [ya[hi], yb[hj]], color=INK, lw=2.2, ls=(0, (1.5, 1.2)), zorder=5)
    ax.annotate(f"Fréchet distance\n{dF:,.0f} km", xy=(0.35 * xa[p] + 0.65 * xb[q], 0.35 * ya[p] + 0.65 * yb[q]),
                xytext=(380, 80), fontsize=14.5, color=INK, ha="left", va="center", zorder=6, path_effects=HALO,
                arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkB=2))
    ax.annotate(f"Hausdorff distance\n{dH:,.0f} km", xy=((xa[hi] + xb[hj]) / 2, (ya[hi] + yb[hj]) / 2),
                xytext=(-40, 930), fontsize=14.5, color=INK, ha="right", va="center", zorder=6, path_effects=HALO,
                arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkB=2))
    ax.text(60, -820, f"{name}, autumn 2013:\nsouthward", fontsize=14, fontweight="bold", color=BLUE,
            ha="left", va="center", path_effects=HALO, zorder=6)
    ax.text(-1060, 330, f"{name},\nspring 2014:\nnorthward", fontsize=14, fontweight="bold", color=ORANGE,
            ha="left", va="center", path_effects=HALO, zorder=6)
    save(fig, "storks-autumn-spring.svg")
    return dict(dF=dF, dH=dH, dF_rev=dF_rev, nA=len(PA), nB=len(PB))


def day_track(gps, bird, day):
    t0 = pd.Timestamp(day, tz="UTC")
    return gps[(gps["bird"] == bird) & (gps["t"] >= t0) & (gps["t"] < t0 + pd.Timedelta(days=1))]


def path_km(tr):
    la, lo = tr["lat"].values, tr["lon"].values
    return float(haversine(la[:-1], lo[:-1], la[1:], lo[1:]).sum())


def diameter_km(tr):
    P = tr[["lat", "lon"]].values
    return float(dist_matrix(P, P).max())


def fig_one_day(panels):
    """One day at full resolution (a fix every 5 minutes), side by side, each with its own scale.

    panels: list of (track, title, colour, scale bar in km)."""
    fig, axs = plt.subplots(1, len(panels), figsize=(3.8 * len(panels), 4.4))
    for ax, (tr, title, col, bar) in zip(np.atleast_1d(axs), panels):
        lon0, lat0 = tr["lon"].mean(), tr["lat"].mean()
        x, y = laea(tr["lon"].values, tr["lat"].values, lon0, lat0)
        ax.plot(x, y, "-", color=col, lw=1.1, alpha=0.6, zorder=1)
        ax.plot(x, y, "o", color=col, ms=3.4, mew=0, zorder=2)
        ax.plot(x[0], y[0], "o", ms=8, color="white", mec=INK, mew=1.5, zorder=3)
        r = 0.58 * max(np.ptp(x), np.ptp(y), 1e-3)
        cx, cy = (x.max() + x.min()) / 2, (y.max() + y.min()) / 2
        ax.set_xlim(cx - r, cx + r)
        ax.set_ylim(cy - r, cy + r)
        ax.text(x[0] + 0.06 * r, y[0] - 0.05 * r, "start", fontsize=13, color=GREY, ha="left", va="top",
                path_effects=HALO, zorder=4)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=14.5, color=INK, loc="left", linespacing=1.3)
        scalebar(ax, cx - r + 0.05 * r, cy - r + 0.04 * r, bar)
    fig.tight_layout(w_pad=2.0)
    save(fig, "storks-one-day.svg")


def first_months(gps, info, bird, days=150):
    """Full-resolution track from departure until `days` days later (the window of Flack et al.)."""
    r = info.set_index("bird").loc[bird]
    start = r["departure"] if pd.notna(r["departure"]) else r["t0"]
    tr = gps[(gps["bird"] == bird) & (gps["t"] >= start) & (gps["t"] < start + pd.Timedelta(days=days))]
    return tr


# ---------------------------------------------------------------- main
gps = load_gps()
info = describe(gps)
print(f"{len(info)} juveniles from {info['pop'].nunique()} populations, {len(gps):,} GPS fixes")
print("first winter:", ", ".join(f"{s} {int((info['strategy'] == s).sum())}" for s in LEGEND_ORDER))
print(info.groupby(["pop", "strategy"]).size().unstack(fill_value=0).to_string())

# 1) overview map
north = info[(info["pop"] == "SW Germany") & (info["strategy"] == "stayed north of the Sahara") & (info["wlat"] < 40)]
labels = {"Spain": ("Spain", -150, 60, "right"), "SW Germany": ("SW Germany", -120, 170, "right"),
          "Greece": ("Greece", -120, 210, "right"), "Tunisia": ("Tunisia", 130, 30, "left"),
          "Poland": ("Poland", 130, 60, "left"), "Russia": ("Russia", 130, 60, "left"),
          "Armenia": ("Armenia", 220, 60, "left"), "Uzbekistan": ("Uzbekistan", -60, 340, "center")}
fig_overview(gps, info, labels, ((north["wlon"].mean(), north["wlat"].mean()), (-650, -420), "rubbish dumps\nin Morocco"))
print(f"SW Germany, winter in Morocco: {', '.join(n.split(' (')[0] for n in north['bird'])}")

# 2) route similarity: three juveniles from the same nest site in SW Germany (Lake Constance)
K, E, Y = "Karamell (DER AL582)", "Eamy (DER AL585)", "Yolo (DER AN861)"
panels = [dict(a=K, b=E, name_a="Karamell", name_b="Eamy", off_a=(110, -60, "left"), off_b=(-110, -60, "right"),
               off_d=(380, -330, "left")),
          dict(a=K, b=Y, name_a="Karamell", name_b="Yolo", off_a=(110, -40, "left"), off_b=(110, -40, "left"),
               off_d=(260, 0, "left"))]
for r in fig_two_routes(gps, info, panels, "2014-01-01"):
    print(f"one fix per day until 31 Dec: {r['a'].split(' (')[0]}-{r['b'].split(' (')[0]}: "
          f"Fréchet {r['dF']:,.0f} km, Hausdorff {r['dH']:,.0f} km ({r['nA']} and {r['nB']} days)")

# 2b) the same stork in autumn and spring: Hausdorff ignores the direction, Fréchet does not
r = fig_autumn_spring(gps, K, ("2013-08-10", "2013-10-16"), ("2014-04-05", "2014-06-11"), "Karamell")
print(f"Karamell, autumn 2013 ({r['nA']} days) and spring 2014 ({r['nB']} days): Hausdorff {r['dH']:,.0f} km, "
      f"Fréchet {r['dF']:,.0f} km, Fréchet with the spring route reversed {r['dF_rev']:,.0f} km")

# 3) one day, a fix every 5 minutes
day = "2013-12-12"
a, b = day_track(gps, K, day), day_track(gps, Y, day)
fig_one_day([(a, f"Karamell, Morocco\n{len(a)} fixes, all within {diameter_km(a):.0f} km", BLUE, 0.2),
             (b, f"Yolo, Senegal\n{len(b)} fixes, {path_km(b):.0f} km flown", GREEN, 5)])
print(f"{day}: Karamell {len(a)} fixes, diameter {diameter_km(a):.1f} km, path {path_km(a):.1f} km; "
      f"Yolo {len(b)} fixes, diameter {diameter_km(b):.1f} km, path {path_km(b):.1f} km")
for bird in (K, Y):
    dec = gps[(gps["bird"] == bird) & (gps["t"] >= pd.Timestamp("2013-12-01", tz="UTC"))
              & (gps["t"] < pd.Timestamp("2014-01-01", tz="UTC"))]
    per_day = dec.groupby(dec["t"].dt.floor("D")).apply(path_km)
    print(f"December 2013, {bird.split(' (')[0]}: path per day {per_day.mean():.1f} km on average "
          f"({per_day.min():.1f}-{per_day.max():.1f})")

# 4) size of the full-resolution problem
full = {r["bird"]: first_months(gps, info, r["bird"]) for _, r in info.iterrows()}
full = {k: v for k, v in full.items() if len(v) > 30000}
sizes = sorted(len(v) for v in full.values())
print(f"fully tracked (more than 30,000 fixes in the 150 days after departure): {len(full)} birds, "
      f"{sizes[0]:,}-{sizes[-1]:,} fixes")
print(f"Karamell-Yolo at full resolution: {len(full[K]):,} x {len(full[Y]):,} = {len(full[K]) * len(full[Y]):.3g} "
      f"table entries; all {len(full) * (len(full) - 1) // 2} pairs: "
      f"{sum(len(full[p]) * len(full[q]) for i, p in enumerate(full) for q in list(full)[i + 1:]):.3g}")
if track_dir:
    os.makedirs(track_dir, exist_ok=True)
    for bird, tr in full.items():
        np.savetxt(os.path.join(track_dir, bird.split(" (")[0].replace(" ", "_") + ".txt"),
                   tr[["lat", "lon"]].values, fmt="%.6f")
    print(f"tracks written to {track_dir}")
