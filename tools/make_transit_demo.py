"""Data for the public transit demo (static/transit-demo) of "Algorithms and Sustainability", lectures 6-7.
Own work, CC BY 4.0.

1) The example of the slides (make_transit_figures.py): real stop names, a simplified network and invented
   times. example.json has exactly the six trips of the slides (13 connections), example-full.json a regular
   timetable 7:00-10:00 on the same network, so that the departure time can be varied. The query of the
   slides (Campus Süd 7:50 -> Essen Hbf) gives the same answers in both: 8:39 with three trips, 9:01 with two.
       python3 tools/make_transit_demo.py example static/transit-demo
2) A real timetable from a GTFS feed (e.g. the German local transport feed of gtfs.de, CC BY 4.0, or VRR
   open data): all stops in a box, all trips of one day, cut to the box; stops merged into stations
   (parent_station), minimum change time 2 min (or from transfers.txt), footpaths between stations closer
   than 250 m (walking 1 m/s).
       python3 tools/make_transit_demo.py gtfs FEED.zip OUT.json.gz --date 20261208 \
               --box 51.40,7.25,51.60,7.65 --name "Dortmund" --source "Dortmund Universität" --target "Dortmund Hbf"
"""
import csv, gzip, io, json, math, sys, zipfile
from collections import defaultdict

BLUE, ORANGE, RED, GREEN, PURPLE = "#0A97D9", "#E8700A", "#DD1367", "#3F7E44", "#6250d6"


def T(s):
    h, m = s.split(":")[:2]
    return int(h) * 60 + int(m)


def example(outdir):
    import os
    stops = [("CS", "Campus Süd", 6.2, 0.0, 0), ("UNI", "Dortmund Universität", 6.2, 1.5, 2),
             ("DO", "Dortmund Hbf", 8.6, 2.6, 5), ("BO", "Bochum Hbf", 2.6, 2.2, 4), ("E", "Essen Hbf", -1.2, 1.5, 4)]
    idx = {s[0]: i for i, s in enumerate(stops)}
    trips = []

    def trip(line, color, seq):          # seq: [(stop, minutes)], arrival = departure except at the ends
        trips.append(dict(line=line, color=color, stops=[idx[s] for s, _ in seq],
                          arr=[t for _, t in seq], dep=[t for _, t in seq]))
    # the six trips of the slides (make_transit_figures.py)
    trip("H-Bahn", ORANGE, [("CS", T("7:56")), ("UNI", T("8:00"))])
    trip("S1", BLUE, [("DO", T("7:52")), ("UNI", T("8:01")), ("BO", T("8:20")), ("E", T("8:41"))])
    trip("S1", BLUE, [("BO", T("7:45")), ("UNI", T("8:04")), ("DO", T("8:12"))])
    trip("S1", BLUE, [("DO", T("8:12")), ("UNI", T("8:21")), ("BO", T("8:40")), ("E", T("9:01"))])
    trip("RE", RED, [("DO", T("8:09")), ("BO", T("8:19")), ("E", T("8:31"))])
    trip("RE", RED, [("DO", T("8:17")), ("BO", T("8:27")), ("E", T("8:39"))])
    slide_trips = trips[:]
    trips.clear()
    for t in range(T("7:06"), T("9:57"), 10):                     # H-Bahn every 10 minutes, 4 minutes
        trip("H-Bahn", ORANGE, [("CS", t), ("UNI", t + 4)])
    for t in range(T("7:03"), T("9:54"), 10):
        trip("H-Bahn", ORANGE, [("UNI", t), ("CS", t + 4)])
    for t in range(T("7:12"), T("9:33"), 20):                     # S1 Dortmund -> Essen every 20 minutes
        trip("S1", BLUE, [("DO", t), ("UNI", t + 9), ("BO", t + 28), ("E", t + 49)])
    for t in range(T("7:04"), T("9:25"), 20):                     # S1 Essen -> Dortmund
        trip("S1", BLUE, [("E", t), ("BO", t + 21), ("UNI", t + 40), ("DO", t + 48)])
    for h in (7, 8, 9):                                           # two RE per hour each way
        for m0, m1 in ((9, 31), (17, 39)):
            t = h * 60 + m0
            trip("RE", RED, [("DO", t), ("BO", t + 10), ("E", t + m1 - m0)])
        for m0 in (20, 28):
            t = h * 60 + m0
            trip("RE", RED, [("E", t), ("BO", t + 12), ("DO", t + 22)])
    full_trips = trips[:]
    for name_, tr, fn in (("the example of the slides", slide_trips, "example.json"),
                          ("the example with a regular timetable 7:00-10:00", full_trips, "example-full.json")):
      D = dict(name=f"Around TU Dortmund: {name_} (real stop names, simplified network, invented times)",
             stops=[dict(name=n, x=x, y=y, change=c, short=sid) for sid, n, x, y, c in stops],
             trips=tr, footpaths=[],
             lines=[dict(name="S1", color=BLUE, path=[[8.6, 2.6], [6.2, 1.5], [2.6, 2.2], [-1.2, 1.5]], label=[4.2, 1.45]),
                    dict(name="RE", color=RED, path=[[8.6, 2.6], [6.0, 3.15], [2.6, 2.2], [-1.2, 1.5]], label=[5.75, 3.35]),
                    dict(name="H-Bahn", color=ORANGE, path=[[6.2, 0.0], [6.2, 1.5]], label=[6.95, 0.75])],
             query=dict(source=idx["CS"], target=idx["E"], time=T("7:50")),
             attribution="Example: real stop names, simplified network, invented times. CC BY 4.0",
             small=True, other="example-full.json" if fn == "example.json" else "example.json",
             otherLabel="full timetable" if fn == "example.json" else "slide example")
      out = os.path.join(outdir, fn)
      with open(out, "w", encoding="utf-8") as f:
          json.dump(D, f, ensure_ascii=False, separators=(",", ":"))
      print("example:", len(tr), "trips,", sum(len(t["stops"]) - 1 for t in tr), "connections ->", out)


def gtfs(feed, out, date, box, name, source, target, change=2, walk=250):
    lat0, lon0, lat1, lon1 = box
    z = zipfile.ZipFile(feed)
    rd = lambda f: csv.DictReader(io.TextIOWrapper(z.open(f), encoding="utf-8-sig"))
    files = set(z.namelist())
    # service days
    from datetime import date as Date
    d = Date(int(date[:4]), int(date[4:6]), int(date[6:]))
    wd = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][d.weekday()]
    active = set()
    if "calendar.txt" in files:
        for r in rd("calendar.txt"):
            if r["start_date"] <= date <= r["end_date"] and r[wd] == "1":
                active.add(r["service_id"])
    if "calendar_dates.txt" in files:
        for r in rd("calendar_dates.txt"):
            if r["date"] == date:
                (active.add if r["exception_type"] == "1" else active.discard)(r["service_id"])
    # stops in the box, merged into stations
    st, parent = {}, {}
    for r in rd("stops.txt"):
        la, lo = float(r["stop_lat"] or 0), float(r["stop_lon"] or 0)
        st[r["stop_id"]] = (r["stop_name"], la, lo)
        if r.get("parent_station"):
            parent[r["stop_id"]] = r["parent_station"]
    def station(sid):
        while sid in parent and parent[sid] in st:
            sid = parent[sid]
        return sid
    inbox = {sid for sid, (n, la, lo) in st.items() if lat0 <= la <= lat1 and lon0 <= lo <= lon1}
    # routes: line name and colour
    routes = {}
    for r in rd("routes.txt"):
        col = r.get("route_color") or ""
        routes[r["route_id"]] = ((r.get("route_short_name") or r.get("route_long_name") or "?").strip(),
                                 "#" + col if len(col) == 6 else None, r.get("route_type", "3"))
    trip_route = {}
    for r in rd("trips.txt"):
        if r["service_id"] in active:
            trip_route[r["trip_id"]] = r["route_id"]
    # stop times of these trips (streamed; the file is large)
    times = defaultdict(list)
    for r in rd("stop_times.txt"):
        tid = r["trip_id"]
        if tid in trip_route and r["stop_id"] in inbox:
            a, dpt = r["arrival_time"] or r["departure_time"], r["departure_time"] or r["arrival_time"]
            if a and dpt:
                times[tid].append((int(r["stop_sequence"]), station(r["stop_id"]), T(a), T(dpt)))
    # stations used, local metres (equirectangular around the box centre)
    used = sorted({s for v in times.values() for _, s, _, _ in v})
    sidx = {s: i for i, s in enumerate(used)}
    cla, clo = (lat0 + lat1) / 2, (lon0 + lon1) / 2
    kx, ky = 111320 * math.cos(math.radians(cla)), 110540
    stops = []
    for s in used:
        n, la, lo = st[s]
        stops.append(dict(name=n, x=round((lo - clo) * kx), y=round((la - cla) * ky), change=change))
    default_cols = {"0": "#E8700A", "1": "#0A97D9", "2": "#DD1367", "3": "#6250d6", "900": "#E8700A"}
    trips, lines = [], {}
    for tid, v in times.items():
        v.sort()
        seq = [v[0]]
        for x in v[1:]:                                  # merge consecutive calls at the same station
            if x[1] == seq[-1][1]:
                seq[-1] = (seq[-1][0], x[1], seq[-1][2], x[3])
            else:
                seq.append(x)
        # cut where the trip leaves the box (a gap in the stop sequence is fine: it is the same trip)
        if len(seq) < 2:
            continue
        ln, col, rt = routes[trip_route[tid]]
        col = col or default_cols.get(rt, "#6250d6")
        trips.append(dict(line=ln, color=col, stops=[sidx[s] for _, s, _, _ in seq],
                          arr=[a for _, _, a, _ in seq], dep=[d_ for _, _, _, d_ in seq]))
        lines.setdefault(ln, col)
    # footpaths between nearby stations
    foot = []
    cell = defaultdict(list)
    for i, s in enumerate(stops):
        cell[(s["x"] // walk, s["y"] // walk)].append(i)
    for i, s in enumerate(stops):
        cx, cy = s["x"] // walk, s["y"] // walk
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in cell.get((cx + dx, cy + dy), []):
                    if j > i:
                        dist = math.hypot(stops[j]["x"] - s["x"], stops[j]["y"] - s["y"])
                        if dist <= walk:
                            foot.append([i, j, max(1, math.ceil(dist / 60))])
    def find(nm):
        for i, s in enumerate(stops):
            if s["name"] == nm:
                return i
        return 0
    D = dict(name=name, stops=stops, trips=trips, footpaths=foot, lines=[],
             query=dict(source=find(source), target=find(target), time=T("7:50")),
             attribution=f"Timetable: GTFS feed {feed.split('/')[-1]}, {date}", small=False)
    with gzip.open(out, "wt", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, separators=(",", ":"))
    nconn = sum(len(t["stops"]) - 1 for t in trips)
    print(f"{name}: {len(stops)} stations, {len(trips)} trips, {nconn} connections, {len(foot)} footpaths -> {out}")


if __name__ == "__main__":
    if sys.argv[1] == "example":
        example(sys.argv[2])
    else:
        args = sys.argv[2:]
        opt = {a[2:]: args[i + 1] for i, a in enumerate(args) if a.startswith("--")}
        gtfs(args[0], args[1], opt.get("date", "20261208"), [float(x) for x in opt.get("box", "51.40,7.25,51.60,7.65").split(",")],
             opt.get("name", "GTFS"), opt.get("source", ""), opt.get("target", ""))
