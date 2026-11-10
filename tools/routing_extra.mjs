// Extra numbers for lecture 5: street names along the fast and the quiet route, the weighted sums
// lambda*time + (1-lambda)*quiet, and all Pareto-optimal routes (time, quiet) with Martins' algorithm.
// Usage: node tools/routing_extra.mjs static/routing-demo  -> prints and writes extra.json
import fs from 'node:fs'; import zlib from 'node:zlib'; import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const dir = process.argv[2] || 'static/routing-demo';
const R = require(path.resolve(dir, 'routing.js'));
const D = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(dir, 'dortmund-graph.json.gz'))));
const G = R.makeGraph(D);
const { segOff, segXY, segName, names } = D;
const segLen = s => { let L = 0; for (let k = segOff[s] + 1; k < segOff[s + 1]; k++) L += Math.hypot(segXY[2*k]-segXY[2*k-2], segXY[2*k+1]-segXY[2*k-1]); return L; };
const piece = e => { const s = G.sg[e]; return s >= 0 ? s : -s - 1; };
function edgesOf(pathNodes, w) { const es = []; for (let i = 0; i + 1 < pathNodes.length; i++) { const u = pathNodes[i], v = pathNodes[i+1]; let b = -1; for (let e = G.off[u]; e < G.off[u+1]; e++) if (G.to[e] === v && (b < 0 || w[e] < w[b])) b = e; es.push(b); } return es; }
function describe(es) {
  let L = 0, busy = 0, t = 0, q = 0; const byName = new Map();
  for (const e of es) { const s = piece(e), l = segLen(s); L += l; t += G.w.fast[e]; q += G.w.quiet[e];
    if (G.w.quiet[e] >= 1.5 * G.w.fast[e]) busy += l;
    const nm = names[segName[s]] || '(unnamed path)'; byName.set(nm, (byName.get(nm) || 0) + l); }
  const top = [...byName.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, v]) => `${k} ${(v/1000).toFixed(2)} km`);
  return { min: +(t/600).toFixed(1), km: +(L/1000).toFixed(2), busyKm: +(busy/1000).toFixed(2), quietCost: +(q/600).toFixed(1), streets: top };
}
const P = Object.fromEntries(Object.entries(D.places).map(([k, v]) => [k, v.node]));
const out = {};
for (const [a, b] of [['hbf', 'phoenix'], ['tu', 'phoenix']]) {
  const s = P[a], t = P[b];
  const f = R.dijkstra(G, s, t, 'fast'), q = R.dijkstra(G, s, t, 'quiet');
  const res = { fast: describe(edgesOf(f.path, G.w.fast)), quiet: describe(edgesOf(q.path, G.w.quiet)) };
  // weighted sums
  const seen = new Map();
  for (let i = 0; i <= 100; i++) {
    const lam = i / 100, w = new Float64Array(G.m);
    for (let e = 0; e < G.m; e++) w[e] = lam * G.w.fast[e] + (1 - lam) * G.w.quiet[e];
    G.w.mix = w;
    const r = R.dijkstra(G, s, t, 'mix');
    const es = edgesOf(r.path, w);
    let tt = 0, qq = 0; for (const e of es) { tt += G.w.fast[e]; qq += G.w.quiet[e]; }
    const key = tt + ',' + qq;
    if (!seen.has(key)) seen.set(key, { lambdaFrom: lam, time: tt, quiet: qq });
  }
  res.weighted = [...seen.values()];
  // Martins: label setting with Pareto sets (time, quiet), pruning by the target's labels
  const t0 = Date.now();
  const labels = Array.from({ length: G.n }, () => []);    // settled labels per node: [t, q]
  const heap = new R.Heap(1 << 16);                         // key: t + q * 1e-7 (lexicographic), payload index
  const L = [];                                             // all labels: [node, t, q, parent]
  const dominated = (list, t_, q_) => list.some(([a, b]) => a <= t_ && b <= q_);
  L.push([s, 0, 0, -1]); heap.push(0, 0);
  let settledLabels = 0;
  while (heap.n > 0) {
    const id = heap.pop(); const [u, tu, qu] = L[id];
    if (dominated(labels[u], tu, qu)) continue;
    if (dominated(labels[t], tu, qu)) continue;            // target pruning
    labels[u].push([tu, qu, id]); settledLabels++;
    if (u === t) continue;
    for (let e = G.off[u]; e < G.off[u + 1]; e++) {
      const v = G.to[e], nt = tu + G.w.fast[e], nq = qu + G.w.quiet[e];
      if (dominated(labels[v], nt, nq) || dominated(labels[t], nt, nq)) continue;
      L.push([v, nt, nq, id]); heap.push(nt + nq * 1e-7, L.length - 1);
    }
  }
  const pareto = labels[t].map(([a, b]) => ({ min: +(a / 600).toFixed(2), quietMin: +(b / 600).toFixed(2) }));
  res.pareto = { count: pareto.length, routes: pareto, settledLabels, seconds: (Date.now() - t0) / 1000 };
  out[a + '-' + b] = res;
  console.log(a, '->', b, JSON.stringify(res.fast), '\n   quiet', JSON.stringify(res.quiet));
  console.log('   weighted sums: distinct routes', res.weighted.length, JSON.stringify(res.weighted.map(x => [x.lambdaFrom, +(x.time/600).toFixed(1), +(x.quiet/600).toFixed(1)])));
  console.log('   Pareto:', res.pareto.count, 'routes,', settledLabels, 'labels,', res.pareto.seconds, 's', JSON.stringify(pareto.map(p => [p.min, p.quietMin])));
}
fs.writeFileSync(path.join(dir, 'extra.json'), JSON.stringify(out, null, 1));
