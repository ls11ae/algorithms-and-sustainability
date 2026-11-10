"""Pareto front of the Dortmund example (lecture 5, outlook): all Pareto-optimal bicycle routes from
Dortmund Hbf to the Phoenix-See for (travel time, quiet), and those found by weighted sums.
Own work, CC BY 4.0. Data: static/routing-demo/extra.json from tools/routing_extra.mjs
(OpenStreetMap data, (c) OpenStreetMap contributors, ODbL).
Usage: python3 tools/make_routing_pareto.py static/routing-demo/extra.json lectures/figures
"""
import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

src, out = sys.argv[1], sys.argv[2]
FD = os.environ.get("LATO_DIR", "")
if FD and os.path.exists(os.path.join(FD, "LatoLatin-Regular.ttf")):
    for f in ["LatoLatin-Regular.ttf", "LatoLatin-Bold.ttf", "LatoLatin-Italic.ttf"]:
        font_manager.fontManager.addfont(os.path.join(FD, f))
    FAMILY = "LatoLatin"
else:
    FAMILY = "sans-serif"
plt.rcParams.update({"font.family": FAMILY, "font.size": 14, "svg.fonttype": "path",
                     "svg.hashsalt": "aus-2627-routing-pareto"})
INK, GREY, BLUE, GREEN = "#282a2e", "#8e908c", "#0A97D9", "#3F7E44"

d = json.load(open(src))["hbf-phoenix"]
P = sorted((p["min"], p["quietMin"]) for p in d["pareto"]["routes"])
Wt = sorted({(round(w["time"] / 600, 2), round(w["quiet"] / 600, 2)) for w in d["weighted"]})
fig, ax = plt.subplots(figsize=(6.4, 4.2))
ax.plot([p[0] for p in P], [p[1] for p in P], "o", ms=4.5, color=GREY, label=f"Pareto-optimal: {len(P)}", zorder=2)
ax.plot([w[0] for w in Wt], [w[1] for w in Wt], "-", color=BLUE, lw=1.2, alpha=0.6, zorder=1)
ax.plot([w[0] for w in Wt], [w[1] for w in Wt], "o", ms=7.5, color=BLUE, mfc="none", mew=2,
        label=f"found by a weighted sum: {len(Wt)}", zorder=3)
f, q = P[0], P[-1]
ax.annotate("fastest", f, xytext=(12, -4), textcoords="offset points", color=INK, va="center")
ax.annotate("quietest", q, xytext=(-10, 16), textcoords="offset points", color=INK, ha="right")
ax.set_xlabel("travel time (min)")
ax.set_ylabel("quiet weight (min)")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.legend(frameon=False, loc="upper right")
ax.set_title("Dortmund Hbf to the Phoenix-See by bike", fontsize=14, color=INK, loc="left")
path = os.path.join(out, "dortmund-pareto.svg")
fig.savefig(path, bbox_inches="tight", pad_inches=0.06, metadata={"Date": None})
num = re.compile(r"-?\d+\.\d+")
svg = open(path, encoding="utf-8").read()
svg = re.sub(r'(\sd=")([^"]*)(")', lambda m: m.group(1) + num.sub(lambda k: f"{float(k.group()):.2f}".rstrip("0").rstrip("."), m.group(2)) + m.group(3), svg)
open(path, "w", encoding="utf-8").write(svg)
on_front = sum(1 for w in Wt if any(abs(w[0] - p[0]) < 0.006 and abs(w[1] - p[1]) < 0.006 for p in P))
print(f"Pareto-optimal {len(P)}, weighted sums {len(Wt)} (on the front: {on_front}), fastest {f}, quietest {q}")
