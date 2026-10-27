"""Figures for "Algorithms and Sustainability", energy-efficient algorithms (own work, CC BY 4.0).

Usage:  python3 tools/make_energy_figures.py lectures/figures
Small constructed examples only (no data needed). The farm day profile is invented for illustration
(not measured, not real prices).

Writes:
  yds-step-0..3.svg        YDS (Yao, Demers, Shenker 1995) on four jobs: jobs, then the speed profile round by round
  farm-day.svg             a sunny day on a farm: PV surplus and electricity price per hour
  farm-day-solution.svg    the same, with the cheapest three-hour window for the feed mill (50 kW)
  ski-rental.svg           ski rental: cost of "rent until the rent paid equals the price" against the optimum
and prints the numbers quoted on the slides.
Needs: matplotlib, numpy. Font as in make_figures.py (LATO_DIR).
"""
import os
import re
import sys
from fractions import Fraction as Fr

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
    FAMILY = "DejaVu Sans"
plt.rcParams.update({"font.family": FAMILY, "font.size": 15, "svg.fonttype": "path", "savefig.transparent": False,
                     "svg.hashsalt": "aus-2627-energy", "mathtext.fontset": "custom",
                     "mathtext.it": f"{FAMILY}:italic", "mathtext.rm": FAMILY, "mathtext.bf": f"{FAMILY}:bold",
                     "mathtext.cal": f"{FAMILY}:italic", "mathtext.sf": FAMILY, "mathtext.tt": FAMILY})
if FAMILY != "LatoLatin":
    plt.rcParams["mathtext.fontset"] = "dejavusans"      # without LATO_DIR: default fonts (figures differ slightly)
INK, GREY, LIGHT = "#282a2e", "#8e908c", "#d9d9d6"
BLUE, ORANGE, RED, GREEN, PURPLE = "#0A97D9", "#E8700A", "#DD1367", "#3F7E44", "#6250d6"
WHITE, PALEBLUE, PALEORANGE = "#ffffff", "#e7f4fb", "#fbe0c6"
JOBCOL = {"J1": BLUE, "J2": ORANGE, "J3": GREEN, "J4": PURPLE}


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


def style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(GREY)
    ax.tick_params(colors=GREY, labelsize=13)


# ---------------------------------------------------------------- 1) YDS
JOBS = {"J1": (0, 8, 4), "J2": (2, 6, 6), "J3": (5, 10, 3), "J4": (9, 12, 2)}   # release, deadline, work
ALPHA = 3


def yds(jobs):
    """Yao-Demers-Shenker with exact fractions. Works on the original time line by keeping a set of
    blocked intervals instead of compressing time. Returns the rounds: (interval set, jobs, speed)."""
    left = dict(jobs)
    blocked = []                                   # list of (a, b) in original time

    def free_length(a, b):
        L = Fr(b - a)
        for x, y in blocked:
            L -= max(Fr(0), Fr(min(b, y)) - Fr(max(a, x)))
        return L

    rounds = []
    while left:
        times = sorted({t for r, d, w in left.values() for t in (r, d)})
        best = None
        for i, a in enumerate(times):
            for b in times[i + 1:]:
                inside = [j for j, (r, d, w) in left.items() if a <= r and d <= b]
                if not inside:
                    continue
                L = free_length(a, b)
                if L <= 0:
                    continue
                dens = Fr(sum(left[j][2] for j in inside)) / L
                if best is None or dens > best[0]:
                    best = (dens, a, b, inside)
        dens, a, b, inside = best
        # the free parts of [a, b]
        parts, cur = [], Fr(a)
        for x, y in sorted(blocked):
            if y <= cur or x >= b:
                continue
            if x > cur:
                parts.append((cur, Fr(x)))
            cur = max(cur, Fr(y))
        if cur < b:
            parts.append((cur, Fr(b)))
        rounds.append(dict(interval=(a, b), parts=parts, jobs=sorted(inside), speed=dens))
        blocked.append((a, b))
        for j in inside:
            del left[j]
    return rounds


def edf_pieces(rounds, jobs):
    """Within each round, run the jobs of the round at the round's speed in EDF order on its free parts."""
    pieces = []
    for rd in rounds:
        s = rd["speed"]
        queue = sorted(rd["jobs"], key=lambda j: jobs[j][1])
        rem = {j: Fr(jobs[j][2]) for j in queue}
        for a, b in rd["parts"]:
            t = a
            while t < b and any(rem[j] > 0 for j in queue):
                avail = [j for j in queue if rem[j] > 0 and jobs[j][0] <= t]
                if not avail:
                    nxt = min(Fr(jobs[j][0]) for j in queue if rem[j] > 0)
                    t = min(max(t, nxt), b)
                    continue
                j = min(avail, key=lambda x: jobs[x][1])
                dt = min(rem[j] / s, b - t)
                pieces.append((j, t, t + dt, s))
                rem[j] -= dt * s
                t += dt
    return pieces


def fig_yds():
    rounds = yds(JOBS)
    pieces = edf_pieces(rounds, JOBS)
    energy = sum((b - a) * s ** ALPHA for _, a, b, s in pieces)
    print("== YDS example: jobs (release, deadline, work)", JOBS)
    for k, rd in enumerate(rounds, 1):
        print(f"   round {k}: interval {rd['interval']}, free parts {[(float(a), float(b)) for a, b in rd['parts']]}, "
              f"jobs {rd['jobs']}, speed {rd['speed']} = {float(rd['speed']):.3f}")
    print("   EDF pieces:", [(j, round(float(a), 3), round(float(b), 3), str(s)) for j, a, b, s in pieces])
    print(f"   energy with P(s) = s^3: {float(energy):.2f} (exact {energy});",
          f"constant speed 15/12 would need {float(Fr(15, 12) ** 3 * 12):.2f} but misses J2's deadline")
    T = 12
    for k in range(len(rounds) + 1):
        fig, (ax, bx) = plt.subplots(2, 1, figsize=(9.0, 5.6), gridspec_kw=dict(height_ratios=[1.05, 1]),
                                     sharex=True)
        for i, (j, (r, d, w)) in enumerate(JOBS.items()):
            y = 3 - i
            done = any(j in rd["jobs"] for rd in rounds[:k])
            cur = k > 0 and j in rounds[k - 1]["jobs"]
            col = JOBCOL[j]
            ax.add_patch(mpatches.FancyBboxPatch((r, y - 0.32), d - r, 0.64, boxstyle="round,pad=0.0,rounding_size=0.12",
                                                 fc=col if cur else (LIGHT if done else WHITE),
                                                 ec=col, lw=2.2, alpha=0.9 if cur else 1.0))
            ax.text(r - 0.15, y, j, ha="right", va="center", fontsize=17, color=col, fontweight="bold")
            ax.text((r + d) / 2, y, f"work {w}", ha="center", va="center", fontsize=16,
                    color=WHITE if cur else (GREY if done else INK))
        if k:
            a, b = rounds[k - 1]["interval"]
            ax.axvspan(a, b, color=PALEORANGE, alpha=0.55, zorder=0)
        ax.set_ylim(-0.7, 3.7)
        ax.set_yticks([])
        style(ax)
        ax.spines["left"].set_visible(False)
        # speed profile
        for j, a, b, s in pieces:
            rnd = next(i for i, rd in enumerate(rounds) if j in rd["jobs"])
            if rnd < k:
                bx.add_patch(mpatches.Rectangle((float(a), 0), float(b - a), float(s), fc=JOBCOL[j],
                                                ec=WHITE, lw=1.5, alpha=0.95 if rnd == k - 1 else 0.55))
        for rd in rounds[:k]:
            for a, b in rd["parts"]:
                s = rd["speed"]
                lab = f"{s.numerator}/{s.denominator}" if s.denominator != 1 else f"{s.numerator}"
                bx.text(float(a + b) / 2, float(s) + 0.06, lab, ha="center", va="bottom", fontsize=17, color=INK)
        bx.set_ylim(0, 1.95)
        bx.set_xlim(-1.2, T + 0.2)
        bx.set_xticks(range(0, T + 1, 2))
        bx.set_ylabel("speed", fontsize=16, color=INK)
        bx.set_xlabel("time", fontsize=16, color=INK)
        style(bx)
        bx.tick_params(labelsize=14.5)
        if k == 0:
            bx.text(6, 1.0, "speed profile: built round by round", ha="center", va="center", fontsize=16, color=GREY)
        fig.tight_layout(h_pad=0.6)
        save(fig, f"yds-step-{k}.svg")
    return rounds, pieces, energy


# ---------------------------------------------------------------- 2) the farm: PV surplus and prices (invented)
H = np.arange(24)


def farm_profile():
    g = np.array([70 * max(0.0, np.sin(np.pi * (h + 0.5 - 6.5) / 14)) ** 1.2 for h in H])   # sun 6:30-20:30
    base = 12 + 10 * ((H >= 5) & (H <= 7)) + 10 * ((H >= 16) & (H <= 18))
    surplus = np.maximum(g - base, 0)
    buy = 30 + 8 * np.exp(-((H - 8) / 1.5) ** 2) + 12 * np.exp(-((H - 19) / 1.5) ** 2) - 6 * np.exp(-((H - 13) / 2.5) ** 2)
    feed = np.full(24, 7.0)
    return np.round(g, 1), base, np.round(surplus, 1), np.round(buy, 1), feed


MILL_KW, MILL_H, WINDOW = 50, 3, (6, 20)


def mill_cost(surplus, buy, feed, start):
    cost = 0.0
    for h in range(start, start + MILL_H):
        x = MILL_KW
        own = min(x, surplus[h])
        cost += own * feed[h] + (x - own) * buy[h]           # lost feed-in for own power, price for the rest
    return cost / 100                                        # in euro


def fig_farm():
    g, base, surplus, buy, feed = farm_profile()
    costs = {s: mill_cost(surplus, buy, feed, s) for s in range(WINDOW[0], WINDOW[1] - MILL_H + 1)}
    best = min(costs, key=costs.get)
    worst = max(costs, key=costs.get)
    print("== Farm example (invented): PV surplus kW per hour", {int(h): float(surplus[h]) for h in H if surplus[h] > 0})
    print("   buy price ct/kWh", {int(h): float(buy[h]) for h in H}, "; feed-in 7 ct/kWh")
    print(f"   mill {MILL_KW} kW for {MILL_H} hours between 6 and 20: cost (euro) by start hour",
          {s: round(float(c), 2) for s, c in costs.items()})
    print(f"   best start {best}:00 ({costs[best]:.2f} euro), worst start {worst}:00 ({costs[worst]:.2f} euro), "
          f"all from the grid from 17:00 to 20:00 would be {MILL_KW * MILL_H * buy[17:20].mean() / 100:.2f} euro")
    for solution in (False, True):
        fig, (ax, bx) = plt.subplots(2, 1, figsize=(7.6, 5.6), sharex=True, gridspec_kw=dict(height_ratios=[1.1, 1]))
        ax.bar(H + 0.5, surplus, width=0.85, color="#f6c75a", edgecolor="none")
        ax.axhline(MILL_KW, color=INK, lw=1.2, ls=(0, (4, 3)))
        ax.text(0.3, MILL_KW + 1.5, f"mill: {MILL_KW} kW", fontsize=16, color=INK, va="bottom")
        ax.set_ylabel("PV surplus (kW)", fontsize=16, color=INK)
        ax.set_ylim(0, 70)
        style(ax)
        bx.plot(H + 0.5, buy, color=RED, lw=2.6, marker="o", ms=4)
        bx.plot(H + 0.5, feed, color=GREEN, lw=2.2, ls=(0, (5, 3)))
        bx.text(23.8, buy[23] + 1.2, "buy", color=RED, fontsize=16, ha="right", va="bottom")
        bx.text(23.8, feed[23] + 1.2, "sell", color=GREEN, fontsize=16, ha="right", va="bottom")
        bx.set_ylabel("ct/kWh", fontsize=16, color=INK)
        bx.set_ylim(0, 48)
        bx.set_xlim(0, 24)
        bx.set_xticks(range(0, 25, 6))
        bx.set_xticklabels([f"{h}:00" for h in range(0, 25, 6)])
        ax.tick_params(labelsize=14.5)
        bx.tick_params(labelsize=14.5)
        style(bx)
        for a in (ax, bx):
            a.axvspan(0, WINDOW[0], color=LIGHT, alpha=0.35, lw=0)
            a.axvspan(WINDOW[1], 24, color=LIGHT, alpha=0.35, lw=0)
        if solution:
            for a in (ax, bx):
                a.axvspan(best, best + MILL_H, color=PALEBLUE, alpha=0.9, lw=0, zorder=0)
            ax.text(best + MILL_H / 2, 64, f"{best}:00–{best + MILL_H}:00: €{costs[best]:.2f}", ha="center",
                    va="center", fontsize=16, color=BLUE, fontweight="bold")
            ax.text(worst + MILL_H / 2 + 1.0, 38, f"from {worst}:00:\n€{costs[worst]:.2f}", ha="center", va="center",
                    fontsize=15, color=RED)
        fig.tight_layout(h_pad=0.5)
        save(fig, "farm-day-solution.svg" if solution else "farm-day.svg")
    return costs, best, worst


# ---------------------------------------------------------------- 3) ski rental
def fig_ski(rent=50, buy=500, days=20):
    d = np.arange(1, days + 1)
    opt = np.minimum(rent * d, buy)
    k = buy // rent                                      # buy on day k: after k - 1 days of renting
    online = np.where(d < k, rent * d, rent * (k - 1) + buy)
    ratio = online / opt
    print(f"== ski rental: rent {rent}, buy {buy}; break-even strategy buys on day {k}; worst ratio "
          f"{ratio.max():.2f} at {int(d[ratio.argmax()])} days (= 2 - 1/{k})")
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    ax.plot(d, opt, color=BLUE, lw=2.8, marker="o", ms=5, label="optimum (knows the days)")
    ax.plot(d, online, color=ORANGE, lw=2.8, marker="s", ms=5, label=f"rent, buy on day {k}")
    ax.annotate(f"worst case:\n{int(online[k - 1])} vs {int(opt[k - 1])}", xy=(k, online[k - 1]),
                xytext=(k + 3.0, online[k - 1] - 330), fontsize=16, color=INK,
                arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.3))
    ax.set_xlabel("ski days (unknown in advance)", fontsize=16, color=INK)
    ax.set_ylabel("cost (€)", fontsize=16, color=INK)
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.set_ylim(0, 1150)
    ax.legend(frameon=False, fontsize=15, loc="upper left")
    style(ax)
    ax.tick_params(labelsize=14.5)
    fig.tight_layout()
    save(fig, "ski-rental.svg")


if __name__ == "__main__":
    fig_yds()
    fig_farm()
    fig_ski()
