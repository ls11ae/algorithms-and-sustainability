"""Generate lecture 2's synthetic time-series chart and introductory route map.

Run from decker/: python tools/make_similarity_figures.py
The route map reuses the existing stork SVG, omitting coupling annotations.
The demand profiles are constructed examples, not measurements.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

figures = Path(__file__).resolve().parents[1] / "lectures" / "figures"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 14,
                     "svg.fonttype": "path", "svg.hashsalt": "aus-time-series"})
hours = list(range(9, 16))
first = [1, 1, 4, 1, 1, 1, 1]
second = [1, 1, 1, 4, 1, 1, 1]
fig, ax = plt.subplots(figsize=(6.0, 3.9))
ax.plot(hours, first, "o-", color="#0A97D9", linewidth=2.4, label="Day A")
ax.plot(hours, second, "s--", color="#E8700A", linewidth=2.4, label="Day B")
ax.set(xlabel="Clock time (hour)", ylabel="Demand (arbitrary units)",
       xticks=hours, yticks=[0, 1, 2, 3, 4], ylim=(-0.1, 4.6))
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.18)
ax.legend(loc="upper right", frameon=False)
fig.tight_layout()
fig.savefig(figures / "time-series-alignment.svg", transparent=True,
            bbox_inches="tight", metadata={"Date": None})
plt.close(fig)

# These groups are the two distance labels and their leader lines.
# Grey dashed connectors and the black longest connector encode the coupling.
ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
ns = {"s": "http://www.w3.org/2000/svg"}
tree = ET.parse(figures / "storks-two-routes.svg")
root = tree.getroot()
removed = []
for parent in root.iter():
    for element in list(parent):
        ident = element.get("id", "")
        styles = [p.get("style", "") for p in element.findall(".//s:path", ns)]
        coupling = ident.startswith("line2d_") and any(
            "stroke-dasharray: 1.6,1.6" in s or
            "stroke: #282a2e; stroke-width: 2.6" in s for s in styles)
        if ident in {"text_4", "text_8", "patch_2", "patch_3"} or coupling:
            parent.remove(element)
            removed.append(ident)
assert {"text_4", "text_8", "patch_2", "patch_3"}.issubset(removed)
tree.write(figures / "storks-two-routes-intro.svg", encoding="utf-8", xml_declaration=True)
print("Generated the synthetic demand chart and introductory route map.")
