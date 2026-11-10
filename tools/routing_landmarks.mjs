// Where do the landmarks of the Dortmund routing demo lie, and which of them give the ALT bound?
// (Lecture 5, slide "A* and ALT on the map of Dortmund".)
// Usage: node tools/routing_landmarks.mjs static/routing-demo    (after tools/routing_prep.mjs)
// Reads dortmund-graph.json.gz and the landmarks in stats.json; prints, for each landmark, its
// position in the bounding box of the graph (0 = west/south, 1 = east/north), and for the query
// TU Dortmund -> Phoenix-See (travel time) how many settled nodes of ALT get their best bound from
// each landmark, and the bounds at the start compared with the true travel time.
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

const dir = process.argv[2] || 'static/routing-demo';
const R = require(path.resolve(dir, 'routing.js'));
const D = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(dir, 'dortmund-graph.json.gz'))).toString('utf8'));
const G = R.makeGraph(D);
const L = JSON.parse(fs.readFileSync(path.join(dir, 'stats.json'), 'utf8')).landmarks;

let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
for (let v = 0; v < G.n; v++) {
  x0 = Math.min(x0, G.x[v]); x1 = Math.max(x1, G.x[v]); y0 = Math.min(y0, G.y[v]); y1 = Math.max(y1, G.y[v]);
}
const rel = v => [(G.x[v] - x0) / (x1 - x0), (G.y[v] - y0) / (y1 - y0)];
const fmt = ([a, b]) => `east ${a.toFixed(2)}, north ${b.toFixed(2)}`;
const s = D.places.tu.node, t = D.places.phoenix.node;
console.log(`landmarks in the order farthest first chose them (TU Dortmund: ${fmt(rel(s))}):`);
L.forEach((l, i) => console.log(`  ${i + 1}. node ${l}: ${fmt(rel(l))}`));

const tables = R.landmarkTables(G, L, 'fast');
const dLt = tables.map(T => T.from[t]), dtL = tables.map(T => T.to[t]);
const bound = (v, i) => Math.max(tables[i].to[v] - dtL[i], dLt[i] - tables[i].from[v]);
const best = v => {
  let b = 0, arg = -1;
  for (let i = 0; i < L.length; i++) { const x = bound(v, i); if (x > b) { b = x; arg = i; } }
  return [b, arg];
};
const res = R.alt(G, s, t, 'fast', tables);
const count = new Array(L.length).fill(0);
let none = 0;
for (const v of res.order) { const [, arg] = best(v); if (arg < 0) none++; else count[arg]++; }
const n = res.order.length;
console.log(`\nALT TU Dortmund -> Phoenix-See: ${n} settled nodes; best bound from landmark:`);
count.forEach((c, i) => { if (c) console.log(`  ${i + 1}. ${c} nodes (${(100 * c / n).toFixed(1)} %)`); });
if (none) console.log(`  no positive bound: ${none}`);
const min = ds => (ds / 600).toFixed(1);       // weights are in deciseconds
const [hs, arg] = best(s);
console.log(`\nbound at the start: ALT ${min(hs)} min (landmark ${arg + 1}), straight line ` +
            `${min(R.euclidPotential(G, t)(s))} min; true travel time ${min(res.dist)} min`);
