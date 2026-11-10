// Preprocessing for the Dortmund routing demo (lecture 5): contraction hierarchy and landmarks,
// checks against Dijkstra, and the numbers quoted on the slides.
// Usage: node tools/routing_prep.mjs static/routing-demo     (after tools/make_routing_demo.py)
// Writes static/routing-demo/dortmund-ch.json.gz and static/routing-demo/stats.json.
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

const dir = process.argv[2] || 'static/routing-demo';
const R = require(path.resolve(dir, 'routing.js'));
const D = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(dir, 'dortmund-graph.json.gz'))).toString('utf8'));
const G = R.makeGraph(D);
const t0 = Date.now();
const log = msg => console.log(`[${((Date.now() - t0) / 1000).toFixed(1)} s] ${msg}`);
log(`graph ${G.n} nodes, ${G.m} edges`);

// ---- contraction hierarchy for travel time
const tc = Date.now();
const CH0 = R.buildCH(G, 'fast', { settleLimit: 100, log });
const chSeconds = (Date.now() - tc) / 1000;
const compact = R.compactCH(CH0, G.m);
const CH = R.loadCH(compact, G);            // the checks below use exactly what the demo loads
CH.nShortcuts = CH0.nShortcuts; CH.nEdges = CH0.nEdges;
log(`CH: ${CH.nShortcuts} shortcuts added, ${CH.nEdges} edges in the hierarchy, ${chSeconds.toFixed(1)} s`);

// ---- landmarks (farthest first from TU Dortmund), 8 for travel time
const tu = D.places.tu.node, phoenix = D.places.phoenix.node;
const landmarks = R.chooseLandmarks(G, tu, 8, 'fast');
log(`landmarks ${landmarks.join(', ')}`);
const tables = R.landmarkTables(G, landmarks, 'fast');

// ---- checks: random pairs, every method must give the Dijkstra distance
let seed = 12345;
const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
let bad = 0;
const sums = { dijkstra: 0, bidirectional: 0, astar: 0, alt: 0, ch: 0 };
const PAIRS = 300;
for (let i = 0; i < PAIRS; i++) {
  const s = Math.floor(rnd() * G.n), t = Math.floor(rnd() * G.n);
  const d = R.dijkstra(G, s, t, 'fast');
  const b = R.bidirectional(G, s, t, 'fast');
  const a = R.astar(G, s, t, 'fast');
  const l = R.alt(G, s, t, 'fast', tables);
  const c = R.chQuery(CH, s, t);
  // unpacked CH path must have the right length and be a path from s to t
  let len = 0, ok = true, cur = s;
  for (const e of c.origEdges) { if (G.from[e] !== cur) ok = false; cur = G.to[e]; len += G.w.fast[e]; }
  if (s !== t && cur !== t) ok = false;
  for (const [name, r] of [['bidirectional', b], ['astar', a], ['alt', l], ['ch', c]]) {
    if (r.dist !== d.dist) { bad++; console.log('MISMATCH', name, s, t, r.dist, d.dist); }
  }
  if (!ok || len !== d.dist) { bad++; console.log('CH unpack mismatch', s, t, len, d.dist); }
  sums.dijkstra += d.settled; sums.bidirectional += b.settled; sums.astar += a.settled; sums.alt += l.settled; sums.ch += c.settled;
}
log(`checked ${PAIRS} random pairs: ${bad} mismatches`);
const avg = Object.fromEntries(Object.entries(sums).map(([k, v]) => [k, Math.round(v / PAIRS)]));
log(`average settled nodes: ${JSON.stringify(avg)}`);

// ---- the running example: TU Dortmund -> Phoenix-See
const scen = {};
const timeIt = (f, reps = 5) => { const t = performance.now(); let r; for (let i = 0; i < reps; i++) r = f(); return [r, (performance.now() - t) / reps]; };
const [dj, tDj] = timeIt(() => R.dijkstra(G, tu, phoenix, 'fast'));
const [bi, tBi] = timeIt(() => R.bidirectional(G, tu, phoenix, 'fast'));
const [as, tAs] = timeIt(() => R.astar(G, tu, phoenix, 'fast'));
const [al, tAl] = timeIt(() => R.alt(G, tu, phoenix, 'fast', tables));
const [ch, tCh] = timeIt(() => R.chQuery(CH, tu, phoenix), 50);
const [qu, tQu] = timeIt(() => R.dijkstra(G, tu, phoenix, 'quiet'));
for (const [k, r, ms] of [['dijkstra', dj, tDj], ['bidirectional', bi, tBi], ['astar', as, tAs], ['alt', al, tAl], ['ch', ch, tCh]]) {
  scen[k] = { settled: r.settled, dist_ds: r.dist, minutes: +(r.dist / 600).toFixed(1), ms: +ms.toFixed(2) };
}
log(`TU -> Phoenix-See: ${JSON.stringify(scen)}`);

const stats = {
  osm_base: D.meta.osm_base, nodes: G.n, edges: G.m, km: D.meta.km,
  ch: { shortcuts: CH.nShortcuts, edges: CH.nEdges, seconds: +chSeconds.toFixed(1), settleLimit: 100 },
  landmarks, check: { pairs: PAIRS, mismatches: bad, avgSettled: avg },
  tuPhoenix: scen, quiet: { settled: qu.settled, dist_ds: qu.dist },
};
fs.writeFileSync(path.join(dir, 'stats.json'), JSON.stringify(stats, null, 1));
compact.landmarks = landmarks;
const json = JSON.stringify(compact);
fs.writeFileSync(path.join(dir, 'dortmund-ch.json.gz'), zlib.gzipSync(Buffer.from(json, 'utf8'), { level: 9 }));
log(`wrote dortmund-ch.json.gz (${(json.length / 1e6).toFixed(1)} MB JSON, ${(fs.statSync(path.join(dir, 'dortmund-ch.json.gz')).size / 1e6).toFixed(1)} MB compressed) and stats.json`);
