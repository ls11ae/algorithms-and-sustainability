/* Algorithms for the energy demo of "Algorithms and Sustainability" (lecture 9). Own work, CC BY 4.0.
   Runs in the browser (window.Energy) and in Node. The farm day is invented (as on the slides,
   tools/make_energy_figures.py); YDS works with exact fractions when all times are integers. */
(function (root) {
  'use strict';

  // ---------------------------------------------------------------- the farm (invented numbers)
  const r1 = x => Math.round(x * 10) / 10;
  function farm() {
    const g = [], base = [], surplus = [], buy = [], feed = [];
    for (let h = 0; h < 24; h++) {
      const s = Math.sin(Math.PI * (h + 0.5 - 6.5) / 14);
      g.push(r1(70 * Math.pow(Math.max(0, s), 1.2)));
      base.push(12 + ((h >= 5 && h <= 7) || (h >= 16 && h <= 18) ? 10 : 0));
      surplus.push(r1(Math.max(70 * Math.pow(Math.max(0, s), 1.2) - base[h], 0)));
      buy.push(r1(30 + 8 * Math.exp(-(((h - 8) / 1.5) ** 2)) + 12 * Math.exp(-(((h - 19) / 1.5) ** 2)) - 6 * Math.exp(-(((h - 13) / 2.5) ** 2))));
      feed.push(7);
    }
    return { g, base, surplus, buy, feed, kw: 50, hours: 3, window: [6, 20] };
  }
  // cost (euro) of running the mill from `start` for F.hours hours: lost feed-in for own power, price for the rest
  function millCost(F, start) {
    let own = 0, grid = 0, ownC = 0, gridC = 0;
    for (let h = start; h < start + F.hours; h++) {
      const o = Math.min(F.kw, F.surplus[h]);
      own += o; grid += F.kw - o; ownC += o * F.feed[h]; gridC += (F.kw - o) * F.buy[h];
    }
    return { own, grid, ownC: ownC / 100, gridC: gridC / 100, cost: (ownC + gridC) / 100 };
  }

  // ---------------------------------------------------------------- YDS (Yao, Demers, Shenker 1995)
  const gcd = (a, b) => { a = Math.abs(a); b = Math.abs(b); while (b) [a, b] = [b, a % b]; return a || 1; };
  function frac(n, d) { const g = gcd(n, d); return { n: n / g, d: d / g, v: n / d }; }
  // jobs: [{name, r, d, w}] with integer r < d and w > 0. Rounds: interval, free parts, jobs, speed.
  function yds(jobs) {
    let left = jobs.map((j, i) => i);
    const blocked = [], rounds = [];
    const free = (a, b) => { let L = b - a; for (const [x, y] of blocked) L -= Math.max(0, Math.min(b, y) - Math.max(a, x)); return L; };
    while (left.length) {
      const times = [...new Set(left.flatMap(i => [jobs[i].r, jobs[i].d]))].sort((a, b) => a - b);
      let best = null;
      for (let i = 0; i < times.length; i++) for (let k = i + 1; k < times.length; k++) {
        const a = times[i], b = times[k];
        const inside = left.filter(j => a <= jobs[j].r && jobs[j].d <= b);
        if (!inside.length) continue;
        const L = free(a, b);
        if (L <= 0) continue;
        const W = inside.reduce((s, j) => s + jobs[j].w, 0);
        if (!best || W * best.L > best.W * L || (W * best.L === best.W * L && b - a < best.b - best.a)) best = { a, b, inside, W, L };
      }
      const { a, b, inside, W, L } = best;
      const parts = [];
      let cur = a;
      for (const [x, y] of [...blocked].sort((p, q) => p[0] - q[0])) {
        if (y <= cur || x >= b) continue;
        if (x > cur) parts.push([cur, x]);
        cur = Math.max(cur, y);
      }
      if (cur < b) parts.push([cur, b]);
      rounds.push({ interval: [a, b], parts, jobs: inside.slice().sort((p, q) => p - q), speed: frac(W, L) });
      blocked.push([a, b]);
      left = left.filter(j => !inside.includes(j));
    }
    return rounds;
  }
  function edfPieces(rounds, jobs) {               // run each round's jobs in EDF order on its free parts
    const pieces = [];
    rounds.forEach((rd, k) => {
      const s = rd.speed.v, rem = new Map(rd.jobs.map(j => [j, jobs[j].w]));
      for (const [a, b] of rd.parts) {
        let t = a, guard = 0;
        while (t < b - 1e-12 && [...rem.values()].some(x => x > 1e-12) && guard++ < 1000) {
          const avail = rd.jobs.filter(j => rem.get(j) > 1e-12 && jobs[j].r <= t + 1e-12);
          if (!avail.length) {
            const nxt = Math.min(...rd.jobs.filter(j => rem.get(j) > 1e-12).map(j => jobs[j].r));
            t = Math.min(Math.max(t, nxt), b); continue;
          }
          const j = avail.reduce((p, q) => (jobs[q].d < jobs[p].d ? q : p));
          const dt = Math.min(rem.get(j) / s, b - t);
          pieces.push({ job: j, a: t, b: t + dt, s, round: k });
          rem.set(j, rem.get(j) - dt * s); t += dt;
        }
      }
    });
    return pieces;
  }
  const energyOf = (pieces, alpha) => pieces.reduce((E, p) => E + (p.b - p.a) * Math.pow(p.s, alpha), 0);
  // AVR (Average Rate, online): every job runs at its density w/(d - r) during its whole window
  function avr(jobs) {
    const ts = [...new Set(jobs.flatMap(j => [j.r, j.d]))].sort((a, b) => a - b), segs = [];
    for (let i = 0; i + 1 < ts.length; i++) {
      const a = ts[i], b = ts[i + 1];
      const s = jobs.reduce((x, j) => x + (j.r <= a && b <= j.d ? j.w / (j.d - j.r) : 0), 0);
      if (s > 0) segs.push({ a, b, s });
    }
    return segs;
  }

  // ---------------------------------------------------------------- power-down = ski rental
  // idle period of length L (s), idle power 1 W, sleeping 0 W, waking up costs beta (J)
  const PD = {
    opt: (L, beta) => Math.min(L, beta),
    never: (L) => L,
    always: (L, beta) => beta,
    breakeven: (L, beta) => (L <= beta ? L : 2 * beta),
    // randomised: sleep after x with density e^(x/beta)/(beta (e-1)) on [0, beta]: expected cost e/(e-1) * OPT
    random: (L, beta) => {
      const e = Math.E, l = Math.min(L, beta);
      // E[cost] = int_0^l (x + beta) p(x) dx + L * P(x > L)   (for L < beta)  ;  = int_0^beta (x + beta) p(x) dx  for L >= beta
      const F = x => (Math.exp(x / beta) - 1) / (e - 1);                       // P(threshold <= x)
      const intXp = x => ((x - beta) * Math.exp(x / beta) + beta) / (e - 1);   // int_0^x y p(y) dy
      return intXp(l) + beta * F(l) + (L < beta ? L * (1 - F(L)) : 0);
    },
  };
  // a reproducible random sequence of idle periods: a mix of short and long ones
  function idlePeriods(n, longShare, seed) {
    let x = seed || 12345;
    const rnd = () => { x ^= x << 13; x ^= x >>> 17; x ^= x << 5; return ((x >>> 0) % 1e9) / 1e9; };
    const out = [];
    for (let i = 0; i < n; i++) {
      const long = rnd() < longShare;
      const mean = long ? 40 : 3;
      out.push(Math.max(0.05, -mean * Math.log(1 - rnd())));
    }
    return out;
  }

  const Energy = { farm, millCost, yds, edfPieces, energyOf, avr, PD, idlePeriods, frac };
  if (typeof module !== 'undefined' && module.exports) module.exports = Energy;
  else root.Energy = Energy;
})(typeof window !== 'undefined' ? window : globalThis);
