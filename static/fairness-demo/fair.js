/* Algorithms for the fairness demo of "Algorithms and Sustainability" (lectures 10 and 11). Own work, CC BY 4.0.
   Runs in the browser (window.Fair) and in Node. The town is the constructed example of the slides
   (tools/make_fairness_figures.py), the wallboxes the example of tools/make_sharing_figures.py. */
(function (root) {
  'use strict';
  const TOWN = {
    A: [[0.8, 1.2], [1.4, 2.4], [0.6, 3.3], [1.9, 1.0], [2.3, 3.0], [1.2, 4.4], [2.0, 5.2], [2.9, 2.0], [0.4, 5.6], [3.0, 4.2], [6.6, 1.0], [7.9, 5.4]],
    B: [[7.4, 1.4], [8.6, 2.2], [9.4, 1.0], [7.8, 3.2], [9.2, 3.6], [8.4, 4.4], [6.8, 2.6], [9.6, 5.0], [6.4, 4.6], [8.8, 6.0], [1.6, 6.3], [3.6, 0.8]],
  };
  function town() {
    const pts = [...TOWN.A.map(p => ({ x: p[0], y: p[1], g: 0 })), ...TOWN.B.map(p => ({ x: p[0], y: p[1], g: 1 }))];
    return pts;
  }
  const dist = (p, q) => Math.hypot(p.x - q.x, p.y - q.y);
  function assign(pts, centres) {                 // nearest centre (ties: lower index)
    return pts.map(p => { let b = 0; centres.forEach((c, i) => { if (dist(p, pts[c]) < dist(p, pts[centres[b]]) - 1e-12) b = i; }); return b; });
  }
  function radiusOf(pts, centres, asg) { return Math.max(...pts.map((p, i) => dist(p, pts[centres[asg[i]]]))); }
  function balance(pts, members) {
    const a = members.filter(i => pts[i].g === 0).length, b = members.length - a;
    return a === 0 || b === 0 ? 0 : Math.min(a / b, b / a);
  }
  function clusterStats(pts, centres, asg) {
    return centres.map((c, k) => { const m = pts.map((p, i) => i).filter(i => asg[i] === k); return { centre: c, members: m, balance: balance(pts, m),
      radius: Math.max(0, ...m.map(i => dist(pts[i], pts[c]))) }; });
  }
  // Gonzalez: farthest first, starting at `first`; returns the picks in order
  function gonzalez(pts, k, first) {
    const C = [first || 0];
    while (C.length < k) {
      let best = -1, bd = -1;
      pts.forEach((p, i) => { const d = Math.min(...C.map(c => dist(p, pts[c]))); if (d > bd + 1e-12) { bd = d; best = i; } });
      C.push(best);
    }
    return C;
  }
  function combos(n, k, f) {                      // all k-subsets of 0..n-1
    const a = [];
    (function rec(s) { if (a.length === k) { f(a.slice()); return; } for (let i = s; i < n; i++) { a.push(i); rec(i + 1); a.pop(); } })(0);
  }
  function optimalKCenter(pts, k) {
    let best = null;
    combos(pts.length, k, cs => { const r = Math.max(...pts.map(p => Math.min(...cs.map(c => dist(p, pts[c]))))); if (!best || r < best.r - 1e-12) best = { r, cs }; });
    return best;
  }
  // bipartite matching (Kuhn) between groups: ok(a, b) -> boolean; returns map a -> b or null
  function matching(na, nb, ok) {
    const mb = new Array(nb).fill(-1);
    const aug = (a, seen) => { for (let b = 0; b < nb; b++) if (ok(a, b) && !seen[b]) { seen[b] = true; if (mb[b] < 0 || aug(mb[b], seen)) { mb[b] = a; return true; } } return false; };
    for (let a = 0; a < na; a++) if (!aug(a, new Array(nb).fill(false))) return null;
    const ma = new Array(na); mb.forEach((a, b) => { ma[a] = b; }); return ma;
  }
  // min-cost perfect matching (Hungarian algorithm, square cost matrix)
  function hungarian(cost) {
    const n = cost.length, INF = 1e18, u = new Array(n + 1).fill(0), v = new Array(n + 1).fill(0), p = new Array(n + 1).fill(0), way = new Array(n + 1).fill(0);
    for (let i = 1; i <= n; i++) {
      p[0] = i; let j0 = 0; const minv = new Array(n + 1).fill(INF), used = new Array(n + 1).fill(false);
      do {
        used[j0] = true; const i0 = p[j0]; let delta = INF, j1 = 0;
        for (let j = 1; j <= n; j++) if (!used[j]) { const cur = cost[i0 - 1][j - 1] - u[i0] - v[j]; if (cur < minv[j]) { minv[j] = cur; way[j] = j0; } if (minv[j] < delta) { delta = minv[j]; j1 = j; } }
        for (let j = 0; j <= n; j++) if (used[j]) { u[p[j]] += delta; v[j] -= delta; } else minv[j] -= delta;
        j0 = j1;
      } while (p[j0] !== 0);
      do { const j1 = way[j0]; p[j0] = p[j1]; j0 = j1; } while (j0);
    }
    const ans = new Array(n); for (let j = 1; j <= n; j++) ans[p[j] - 1] = j - 1; return ans;
  }
  // fairlets for balance 1 (equal group sizes): bottleneck perfect matching A-B, then the shortest total among those
  function fairlets(pts) {
    const IA = pts.map((p, i) => i).filter(i => pts[i].g === 0), IB = pts.map((p, i) => i).filter(i => pts[i].g === 1);
    if (IA.length !== IB.length) return null;
    const cand = [...new Set(IA.flatMap(a => IB.map(b => dist(pts[a], pts[b]))))].sort((x, y) => x - y);
    let lo = 0, hi = cand.length - 1;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (matching(IA.length, IB.length, (a, b) => dist(pts[IA[a]], pts[IB[b]]) <= cand[mid] + 1e-12)) hi = mid; else lo = mid + 1; }
    const t = cand[lo];
    const m = hungarian(IA.map(a => IB.map(b => (dist(pts[a], pts[b]) <= t + 1e-12 ? dist(pts[a], pts[b]) : 1e6))));
    return { t, pairs: IA.map((a, i) => [a, IB[m[i]]]) };
  }
  // fair clustering from fairlets (as on the slides): the best k-center of one representative per fairlet (its
  // group-A family), whole fairlets to the centre nearest to the representative
  function fairletClustering(pts, k, F) {
    const reps = F.pairs.map(([a]) => a);
    const sub = reps.map(i => pts[i]);
    const C = optimalKCenter(sub, k).cs.map(j => reps[j]);
    const asg = new Array(pts.length);
    for (const [a, b] of F.pairs) {
      let best = 0; C.forEach((c, i) => { if (dist(pts[a], pts[c]) < dist(pts[a], pts[C[best]]) - 1e-12) best = i; });
      asg[a] = best; asg[b] = best;
    }
    return { centres: C, asg };
  }
  // exact fair k-center (balance 1), centres among the families, each centre in its own cluster
  function optimalFair(pts, k) {
    const IA = pts.map((p, i) => i).filter(i => pts[i].g === 0), IB = pts.map((p, i) => i).filter(i => pts[i].g === 1);
    if (IA.length !== IB.length) return null;
    let best = null;
    combos(pts.length, k, cs => {
      let cand = [...new Set(pts.flatMap(p => cs.map(c => dist(p, pts[c]))))].sort((x, y) => x - y);
      if (best) cand = cand.filter(r => r < best.r - 1e-12);
      if (!cand.length) return;
      const usable = (a, b) => { const own = [a, b].filter(x => cs.includes(x)); return own.length === 2 ? [] : own.length ? own : cs; };
      const feas = R => matching(IA.length, IB.length, (i, j) => usable(IA[i], IB[j]).some(c => dist(pts[IA[i]], pts[c]) <= R + 1e-12 && dist(pts[IB[j]], pts[c]) <= R + 1e-12));
      if (!feas(cand[cand.length - 1])) return;
      let lo = 0, hi = cand.length - 1;
      while (lo < hi) { const mid = (lo + hi) >> 1; if (feas(cand[mid])) hi = mid; else lo = mid + 1; }
      const R = cand[lo], m = feas(R);
      const asg = new Array(pts.length);
      m.forEach((j, i) => { const a = IA[i], b = IB[j]; const cc = usable(a, b).filter(c => dist(pts[a], pts[c]) <= R + 1e-12 && dist(pts[b], pts[c]) <= R + 1e-12);
        const c = cc.reduce((x, y) => (Math.max(dist(pts[a], pts[y]), dist(pts[b], pts[y])) < Math.max(dist(pts[a], pts[x]), dist(pts[b], pts[x])) ? y : x)); asg[a] = asg[b] = cs.indexOf(c); });
      best = { r: R, cs, asg };
    });
    return best;
  }
  // individual fairness (Jung, Kannan, Lutz 2020): r(x) = radius of the smallest ball around x with n/k points
  function neighbourhoodRadius(pts, k) {
    const need = Math.ceil(pts.length / k);
    return pts.map(p => pts.map(q => dist(p, q)).sort((a, b) => a - b)[need - 1]);
  }

  // ---------------------------------------------------------------- sharing a congested connection
  const WALLBOX = { cap: 30, names: ['A', 'B', 'C', 'D', 'E'], demand: [3.7, 7.4, 11.0, 11.0, 22.0] };
  function waterFilling(d, cap) {                 // the uniform rule: x_i = min(d_i, level)
    const total = d.reduce((s, x) => s + x, 0);
    if (total <= cap) return { x: d.slice(), level: Math.max(...d) };
    const order = d.map((x, i) => i).sort((i, j) => d[i] - d[j]);
    let left = cap, k = d.length, level = 0;
    const x = new Array(d.length).fill(0);
    for (let pos = 0; pos < order.length; pos++) {
      const i = order[pos], share = left / (k - pos);
      if (d[i] <= share) { x[i] = d[i]; left -= d[i]; }
      else { level = share; for (let q = pos; q < order.length; q++) x[order[q]] = share; break; }
    }
    return { x, level };
  }
  function proportional(d, cap) { const t = d.reduce((s, x) => s + x, 0); return d.map(x => (t <= cap ? x : x * cap / t)); }
  function equalSplit(d, cap) { return waterFilling(d.map(() => Infinity), cap).x.map((x, i) => Math.min(x, d[i])); }
  const jain = x => { const s = x.reduce((a, b) => a + b, 0), q = x.reduce((a, b) => a + b * b, 0); return q > 0 ? s * s / (x.length * q) : 1; };

  const Fair = { town, dist, assign, radiusOf, balance, clusterStats, gonzalez, optimalKCenter, fairlets, fairletClustering,
                 optimalFair, neighbourhoodRadius, WALLBOX, waterFilling, proportional, equalSplit, jain };
  if (typeof module !== 'undefined' && module.exports) module.exports = Fair;
  else root.Fair = Fair;
})(typeof window !== 'undefined' ? window : globalThis);
