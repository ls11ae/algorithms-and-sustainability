"""Dortmund bicycle network from OpenStreetMap for lecture 5 (route planning), own work, CC BY 4.0.

Usage:  python3 tools/make_routing_demo.py <dortmund-highways.osm.gz> static/routing-demo

Reads the street network (downloaded with AuN/routenplanung/get_dortmund_osm.py), builds the junction
graph for a simple bicycle profile and writes static/routing-demo/dortmund-graph.json.gz, the data of the
interactive demo. Contraction hierarchies and landmarks are added by
tools/routing_prep.mjs (Node); the images for the PDF come from tools/routing_shots.mjs.

Bicycle profile (a model for teaching, not a real cycling profile):
  * travel time: 18 km/h on roads and cycleways, slower on living streets, tracks, paths and
    unpaved or cobbled surfaces, 5 km/h where the bike has to be pushed (footways, pedestrian zones);
    motorways, motor roads, steps and roads where bicycles are not allowed are left out;
    one-way streets count unless cyclists may ride both ways (oneway:bicycle=no, contraflow lanes).
  * quiet: travel time times a stress factor of the road (3 on primary roads, 2.2 secondary,
    1.6 tertiary, 1.2 unclassified, 1 elsewhere), reduced by cycle lanes or tracks and by 30 km/h.
The graph keeps the largest strongly connected component; nodes are junctions, edges are the street
pieces between them (with their shape for drawing).

Data (c) OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright).
The exported graph is a derived database and is therefore also available under the ODbL.
"""
import gzip
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

LAT0, LON0 = 51.49, 7.43            # projection centre (TU Dortmund / city centre)
KX = math.cos(math.radians(LAT0)) * 111319.49
KY = 111132.95
VMAX_KMH = 18.0                     # fastest speed in the profile (used by the A* potential)

EXCLUDE = {"motorway", "motorway_link", "construction", "proposed", "abandoned", "platform", "bus_stop",
           "raceway", "elevator", "rest_area", "services", "steps", "corridor", "bus_guideway", "escape",
           "bridleway", "via_ferrata", "emergency_bay", "busway", "planned", "disused", "razed", "no"}
BICYCLE_OK = {"yes", "designated", "permissive", "official"}
UNPAVED = {"gravel", "ground", "dirt", "earth", "grass", "sand", "mud", "unpaved", "pebblestone",
           "woodchips", "grass_paver", "rock"}
SMOOTH_UNPAVED = {"compacted", "fine_gravel"}
COBBLES = {"sett", "cobblestone", "unhewn_cobblestone", "paving_stones:lanes"}
STRESS = {"primary": 3.0, "primary_link": 3.0, "trunk": 3.0, "trunk_link": 3.0,
          "secondary": 2.2, "secondary_link": 2.2, "tertiary": 1.6, "tertiary_link": 1.6,
          "unclassified": 1.2}
# drawing classes: 0 minor, 1 main road, 2 cycleway, 3 path/track/footway
MAIN = {"primary", "primary_link", "trunk", "trunk_link", "secondary", "secondary_link", "tertiary",
        "tertiary_link"}


def profile(t):
    """Returns (speed_kmh, forward, backward, stress, draw_class) or None if bicycles cannot use the way."""
    hw = t.get("highway")
    if hw is None or hw in EXCLUDE or t.get("area") == "yes":
        return None
    bic = t.get("bicycle")
    if bic in ("no", "use_sidepath"):
        return None
    if t.get("motorroad") == "yes" or (hw in ("trunk", "trunk_link") and bic not in BICYCLE_OK):
        return None
    if t.get("access") in ("no", "private") and bic not in BICYCLE_OK:
        return None
    if hw == "footway" and t.get("footway") in ("sidewalk", "crossing", "traffic_island") and bic not in BICYCLE_OK:
        return None                     # sidewalks run next to the road the bike uses
    push = False
    if hw == "cycleway":
        v, cls = 18.0, 2
    elif hw in ("footway", "pedestrian"):
        if bic in BICYCLE_OK:
            v, cls = (16.0 if bic == "designated" else 14.0), (2 if bic == "designated" else 3)
            if hw == "pedestrian":
                v = 10.0
        else:
            v, cls, push = 5.0, 3, True
    elif hw == "path":
        v, cls = (16.0, 2) if bic == "designated" else (12.0, 3)
    elif hw == "track":
        v, cls = {"grade1": 16.0, "grade2": 14.0}.get(t.get("tracktype"), 12.0), 3
    elif hw == "living_street":
        v, cls = 10.0, 0
    elif hw == "service":
        v, cls = (12.0 if t.get("service") in ("parking_aisle", "driveway", "drive-through") else 16.0), 0
    else:
        v, cls = 18.0, (1 if hw in MAIN else 0)
    if bic == "dismount":
        v, push = 5.0, True
    surf = t.get("surface")
    if not push:
        if surf in UNPAVED:
            v *= 0.8
        elif surf in SMOOTH_UNPAVED:
            v *= 0.9
        elif surf in COBBLES:
            v *= 0.75
    # one-way streets
    fwd = bwd = True
    if not push:
        ow = t.get("oneway", "yes" if t.get("junction") in ("roundabout", "circular") else "no")
        contraflow = (t.get("oneway:bicycle") == "no" or t.get("cycleway", "").startswith("opposite")
                      or t.get("cycleway:left:oneway") == "no" or t.get("cycleway:right:oneway") == "no"
                      or t.get("cycleway:both:oneway") == "no")
        if ow in ("yes", "true", "1") and not contraflow:
            bwd = False
        elif ow == "-1" and not contraflow:
            fwd = False
    # stress factor for the "quiet" weight
    base = STRESS.get(hw, 1.0)
    f = base
    if base > 1.0:
        infra = " ".join(t.get(k, "") for k in ("cycleway", "cycleway:both", "cycleway:right", "cycleway:left"))
        if "track" in infra:
            f = 1 + (base - 1) * 0.2
        elif "lane" in infra or "share_busway" in infra:
            f = 1 + (base - 1) * 0.5
        ms = t.get("maxspeed", "")
        if ms.isdigit() and int(ms) <= 30:
            f = min(f, 1 + (base - 1) * 0.5)
    if t.get("bicycle_road") == "yes" or t.get("cyclestreet") == "yes":
        f, cls = 1.0, 2
    return v, fwd, bwd, f, cls


# ---------------------------------------------------------------- read OSM XML
ways, coords = [], {}
osm_base = ""
with gzip.open(src, "rb") as fh:
    for ev, el in ET.iterparse(fh, events=("end",)):
        if el.tag == "way":
            tags = {c.get("k"): c.get("v") for c in el if c.tag == "tag"}
            nds = [int(c.get("ref")) for c in el if c.tag == "nd"]
            p = profile(tags)
            if p is not None and len(nds) >= 2:
                ways.append((int(el.get("id")), nds, p, tags.get("name", "")))
            el.clear()
        elif el.tag == "node":
            coords[int(el.get("id"))] = (float(el.get("lat")), float(el.get("lon")))
            el.clear()
        elif el.tag == "meta":
            osm_base = el.get("osm_base", "")
print(f"usable ways {len(ways)}, OSM nodes {len(coords)}, OSM base {osm_base}")


def proj(nid):
    lat, lon = coords[nid]
    return (lon - LON0) * KX, (lat - LAT0) * KY


# junctions: endpoints of usable ways and nodes shared by two usable ways (or visited twice)
use = {}
for _, nds, _, _ in ways:
    for k, nid in enumerate(nds):
        use[nid] = use.get(nid, 0) + (2 if k in (0, len(nds) - 1) else 1)
junction = {nid for nid, c in use.items() if c >= 2}

# segments between junctions
segs = []        # (a, b, [node ids], length_m, speed, fwd, bwd, stress, cls, name)
for wid, nds, (v, fwd, bwd, f, cls), name in ways:
    nds = [n for n in nds if n in coords]
    start = 0
    for k in range(1, len(nds)):
        if nds[k] in junction or k == len(nds) - 1:
            piece = nds[start:k + 1]
            if len(piece) >= 2 and piece[0] != piece[-1]:
                pts = [proj(n) for n in piece]
                length = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
                segs.append((piece[0], piece[-1], piece, length, v, fwd, bwd, f, cls, name))
            start = k
print(f"segments {len(segs)}")

# directed edges; weights in deciseconds, rounded up, and never below the straight-line time at
# VMAX_KMH between the exported (rounded) node coordinates: then the A* potential
# h(v) = straight-line distance(v, t) / VMAX is consistent for both weights.
def pxy(nid_):
    x, y = proj(nid_)
    return round(x, 1), round(y, 1)


out_edges = {}
for si, (a, b, piece, length, v, fwd, bwd, f, cls, name) in enumerate(segs):
    (ax, ay), (bx, by) = pxy(a), pxy(b)
    length_ = max(length, math.hypot(ax - bx, ay - by))
    t = max(1, math.ceil(length_ / (v / 3.6) * 10 - 1e-9))
    q = max(t, math.ceil(t * f - 1e-9))
    if fwd:
        out_edges.setdefault(a, []).append((b, t, q, si, 1))
    if bwd:
        out_edges.setdefault(b, []).append((a, t, q, si, -1))


# largest strongly connected component (iterative Tarjan)
def tarjan(nodes, adj):
    index, low, onstack, stack, comps = {}, {}, set(), [], []
    counter = 0
    for root in nodes:
        if root in index:
            continue
        work = [(root, 0)]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        onstack.add(root)
        while work:
            v, i = work[-1]
            nbrs = adj.get(v, [])
            if i < len(nbrs):
                work[-1] = (v, i + 1)
                w = nbrs[i][0]
                if w not in index:
                    index[w] = low[w] = counter
                    counter += 1
                    stack.append(w)
                    onstack.add(w)
                    work.append((w, 0))
                elif w in onstack:
                    low[v] = min(low[v], index[w])
            else:
                work.pop()
                if work:
                    u = work[-1][0]
                    low[u] = min(low[u], low[v])
                if low[v] == index[v]:
                    comp = []
                    while True:
                        w = stack.pop()
                        onstack.discard(w)
                        comp.append(w)
                        if w == v:
                            break
                    comps.append(comp)
    return comps


allnodes = sorted(set(out_edges) | {e[0] for es in out_edges.values() for e in es})
comps = tarjan(allnodes, out_edges)
big = max(comps, key=len)
keep = set(big)
print(f"junction nodes {len(allnodes)}, largest SCC {len(big)} ({len(comps)} components)")

# renumber nodes spatially (sorted by x then y) so that the output is reproducible
order = sorted(keep, key=lambda n: (round(proj(n)[0], 1), round(proj(n)[1], 1), n))
nid = {n: i for i, n in enumerate(order)}
n = len(order)
X = [pxy(o)[0] for o in order]
Y = [pxy(o)[1] for o in order]


# segments used by kept edges; geometry simplified (Douglas-Peucker, 2 m)
def simplify(pts, eps=2.0):
    if len(pts) <= 2:
        return pts
    keep_i = [False] * len(pts)
    keep_i[0] = keep_i[-1] = True
    st = [(0, len(pts) - 1)]
    while st:
        i, j = st.pop()
        (x1, y1), (x2, y2) = pts[i], pts[j]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1e-9
        best, bk = -1.0, -1
        for k in range(i + 1, j):
            d = abs(dy * (pts[k][0] - x1) - dx * (pts[k][1] - y1)) / L
            if d > best:
                best, bk = d, k
        if best > eps:
            keep_i[bk] = True
            st += [(i, bk), (bk, j)]
    return [p for p, k in zip(pts, keep_i) if k]


seg_used = sorted({e[3] for a in keep for e in out_edges.get(a, []) if e[0] in keep})
seg_new = {s: i for i, s in enumerate(seg_used)}
seg_off, seg_xy, seg_cls, seg_name, names = [0], [], [], [], {"": 0}
total_len = 0.0
for s in seg_used:
    a, b, piece, length, v, fwd, bwd, f, cls, name = segs[s]
    seg_name.append(names.setdefault(name, len(names)))
    pts = simplify([proj(p) for p in piece])
    for (x, y) in pts:
        seg_xy += [round(x), round(y)]
    seg_off.append(len(seg_xy) // 2)
    seg_cls.append(cls)
    total_len += length

# CSR adjacency (out-edges), sorted by target for reproducibility
off, to, wt, wq, sg = [0], [], [], [], []
for i, o in enumerate(order):
    es = sorted((nid[e[0]], e[1], e[2], seg_new[e[3]] * e[4] if e[4] > 0 else -seg_new[e[3]] - 1)
                for e in out_edges.get(o, []) if e[0] in keep)
    for (j, t, q, s) in es:
        to.append(j)
        wt.append(t)
        wq.append(q)
        sg.append(s)          # >= 0: segment drawn forward; < 0: segment -s-1 drawn backward
    off.append(len(to))
m = len(to)
print(f"graph: {n} nodes, {m} directed edges, {len(seg_used)} street pieces, {total_len / 1000:.0f} km")

# named places (snapped to the nearest node of the graph)
PLACES = [("tu", "TU Dortmund", 51.49250, 7.41420),
          ("phoenix", "Phoenix-See", 51.48720, 7.50460),
          ("hbf", "Dortmund Hbf", 51.51780, 7.45940),
          ("stadium", "Westfalenstadion", 51.49260, 7.45190),
          ("city", "Reinoldikirche", 51.51360, 7.46800)]
places = {}
for key, label, lat, lon in PLACES:
    px, py = (lon - LON0) * KX, (lat - LAT0) * KY
    best = min(range(n), key=lambda i: (X[i] - px) ** 2 + (Y[i] - py) ** 2)
    places[key] = {"label": label, "node": best, "d": round(math.hypot(X[best] - px, Y[best] - py))}
print("places:", {k: (v["node"], v["d"]) for k, v in places.items()})

data = {
    "meta": {"source": "OpenStreetMap", "osm_base": osm_base,
             "license": "Data (c) OpenStreetMap contributors, ODbL 1.0",
             "profile": "bicycle, 18 km/h max; quiet = time x stress factor",
             "vmax_kmh": VMAX_KMH, "n": n, "m": m, "km": round(total_len / 1000, 1),
             "proj": {"lat0": LAT0, "lon0": LON0, "kx": round(KX, 3), "ky": KY}},
    "x": X, "y": Y, "off": off, "to": to, "wt": wt, "wq": wq, "sg": sg,
    "segOff": seg_off, "segXY": seg_xy, "segCls": seg_cls, "segName": seg_name,
    "names": sorted(names, key=names.get), "places": places,
}
raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
target = os.path.join(out, "dortmund-graph.json.gz")
with open(target, "wb") as fh:                       # gzip without time stamp: reproducible bytes
    with gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0, compresslevel=9) as gz:
        gz.write(raw)
print("wrote", target, len(raw) // 1000, "kB JSON,", os.path.getsize(target) // 1000, "kB compressed")
