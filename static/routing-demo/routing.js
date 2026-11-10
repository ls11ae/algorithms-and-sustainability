/* Route planning algorithms for the Dortmund demo of "Algorithms and Sustainability" (lecture 5).
   Own work, CC BY 4.0, Kevin Buchin / TU Dortmund. Runs in the browser (window.Routing) and in Node.

   Graph: compressed adjacency arrays (out-edges: off/to; in-edges built here), weights in deciseconds.
   All searches record the order in which nodes are settled, for the animation, and return
   { dist, path, order, side, settled }. Ties in the priority queue are broken by node id, so every
   run is reproducible (the numbers on the slides come from this file). */
(function (root) {
  'use strict';

  // ------------------------------------------------------------------ priority queue
  class Heap {
    constructor(cap) { this.k = new Float64Array(cap || 1024); this.v = new Int32Array(cap || 1024); this.n = 0; }
    clear() { this.n = 0; }
    less(i, j) { return this.k[i] < this.k[j] || (this.k[i] === this.k[j] && this.v[i] < this.v[j]); }
    swap(i, j) {
      const k = this.k[i]; this.k[i] = this.k[j]; this.k[j] = k;
      const v = this.v[i]; this.v[i] = this.v[j]; this.v[j] = v;
    }
    push(key, node) {
      if (this.n === this.k.length) {
        const k2 = new Float64Array(this.n * 2); k2.set(this.k); this.k = k2;
        const v2 = new Int32Array(this.n * 2); v2.set(this.v); this.v = v2;
      }
      let i = this.n++;
      this.k[i] = key; this.v[i] = node;
      while (i > 0) {
        const p = (i - 1) >> 1;
        if (!this.less(i, p)) break;
        this.swap(i, p); i = p;
      }
    }
    pop() {                        // returns the node; its key is in this.lastKey
      const node = this.v[0];
      this.lastKey = this.k[0];
      this.n--;
      if (this.n > 0) {
        this.k[0] = this.k[this.n]; this.v[0] = this.v[this.n];
        let i = 0;
        for (;;) {
          const l = 2 * i + 1, r = l + 1;
          let s = i;
          if (l < this.n && this.less(l, s)) s = l;
          if (r < this.n && this.less(r, s)) s = r;
          if (s === i) break;
          this.swap(i, s); i = s;
        }
      }
      return node;
    }
    topKey() { return this.k[0]; }
    topNode() { return this.v[0]; }
  }

  // ------------------------------------------------------------------ graph
  function makeGraph(D) {
    const n = D.x.length, m = D.to.length;
    const G = {
      n, m,
      x: Float64Array.from(D.x), y: Float64Array.from(D.y),
      off: Int32Array.from(D.off), to: Int32Array.from(D.to),
      w: { fast: Int32Array.from(D.wt), quiet: Int32Array.from(D.wq) },
      sg: Int32Array.from(D.sg),
      vmax: D.meta.vmax_kmh / 3.6 / 10,           // metres per decisecond
    };
    const from = new Int32Array(m);
    for (let u = 0; u < n; u++) for (let e = G.off[u]; e < G.off[u + 1]; e++) from[e] = u;
    G.from = from;
    // in-edges: roff/redge (the edge index into to/w)
    const roff = new Int32Array(n + 1);
    for (let e = 0; e < m; e++) roff[G.to[e] + 1]++;
    for (let i = 0; i < n; i++) roff[i + 1] += roff[i];
    const fill = roff.slice(0, n), redge = new Int32Array(m);
    for (let e = 0; e < m; e++) redge[fill[G.to[e]]++] = e;
    G.roff = roff; G.redge = redge;
    return G;
  }

  function pathFromParents(G, parentEdge, t) {
    const path = [t];
    let v = t;
    while (parentEdge[v] >= 0) { v = G.from[parentEdge[v]]; path.push(v); }
    return path.reverse();
  }

  function cleanTop(h, done) {      // drop entries of settled nodes from the top of the heap
    while (h.n > 0 && done[h.topNode()]) h.pop();
  }

  // ------------------------------------------------------------------ Dijkstra, A*, ALT
  // pot: null (Dijkstra) or a function v -> lower bound on dist(v, t) (A*)
  function search(G, s, t, metric, pot) {
    const w = G.w[metric], n = G.n;
    const dist = new Float64Array(n).fill(Infinity), parent = new Int32Array(n).fill(-1);
    const done = new Uint8Array(n), order = [];
    const h = new Heap(4096);
    const P = pot || (() => 0);
    dist[s] = 0; h.push(P(s), s);
    while (h.n > 0) {
      const u = h.pop();
      if (done[u]) continue;
      done[u] = 1; order.push(u);
      if (u === t) break;
      const du = dist[u];
      for (let e = G.off[u]; e < G.off[u + 1]; e++) {
        const v = G.to[e], nd = du + w[e];
        if (nd < dist[v]) { dist[v] = nd; parent[v] = e; h.push(nd + P(v), v); }
      }
    }
    return { dist: dist[t], path: t >= 0 && isFinite(dist[t]) ? pathFromParents(G, parent, t) : [],
             order: Int32Array.from(order), side: new Uint8Array(order.length), settled: order.length,
             parent, distArr: dist };
  }

  function dijkstra(G, s, t, metric) { return search(G, s, t, metric, null); }

  function euclidPotential(G, t) {
    const tx = G.x[t], ty = G.y[t], k = 1 / G.vmax;   // decisecond per metre at top speed
    return v => Math.hypot(G.x[v] - tx, G.y[v] - ty) * k;
  }
  function astar(G, s, t, metric) { return search(G, s, t, metric, euclidPotential(G, t)); }

  // full single-source distances (forward from s, or backward to s with reverse = true)
  function allDistances(G, s, metric, reverse) {
    const w = G.w[metric], n = G.n, dist = new Float64Array(n).fill(Infinity), done = new Uint8Array(n);
    const h = new Heap(8192);
    dist[s] = 0; h.push(0, s);
    while (h.n > 0) {
      const u = h.pop();
      if (done[u]) continue;
      done[u] = 1;
      const du = dist[u];
      if (!reverse) {
        for (let e = G.off[u]; e < G.off[u + 1]; e++) {
          const v = G.to[e], nd = du + w[e];
          if (nd < dist[v]) { dist[v] = nd; h.push(nd, v); }
        }
      } else {
        for (let i = G.roff[u]; i < G.roff[u + 1]; i++) {
          const e = G.redge[i], v = G.from[e], nd = du + w[e];
          if (nd < dist[v]) { dist[v] = nd; h.push(nd, v); }
        }
      }
    }
    return dist;
  }

  // landmarks: given node ids; distances from (d(L, v)) and to (d(v, L)) each landmark
  function landmarkTables(G, landmarks, metric) {
    return landmarks.map(L => ({ L, from: allDistances(G, L, metric, false), to: allDistances(G, L, metric, true) }));
  }
  function altPotential(tables, t) {
    const k = tables.length;
    const dLt = tables.map(T => T.from[t]), dtL = tables.map(T => T.to[t]);
    return v => {
      let best = 0;
      for (let i = 0; i < k; i++) {
        const T = tables[i];
        const a = T.to[v] - dtL[i];          // d(v,t) >= d(v,L) - d(t,L)
        const b = dLt[i] - T.from[v];        // d(v,t) >= d(L,t) - d(L,v)
        if (a > best) best = a;
        if (b > best) best = b;
      }
      return best;
    };
  }
  function alt(G, s, t, metric, tables) { return search(G, s, t, metric, altPotential(tables, t)); }

  // farthest-first landmark selection (Gonzalez, lecture 3), graph distances d(L, v) + d(v, L)
  function chooseLandmarks(G, start, k, metric) {
    const L = [];
    const minD = new Float64Array(G.n).fill(Infinity);
    let next = start;
    // first landmark: farthest from the start node
    {
      const a = allDistances(G, start, metric, false), b = allDistances(G, start, metric, true);
      let best = -1;
      for (let v = 0; v < G.n; v++) { const d = a[v] + b[v]; if (d > best) { best = d; next = v; } }
    }
    while (L.length < k) {
      L.push(next);
      const a = allDistances(G, next, metric, false), b = allDistances(G, next, metric, true);
      let best = -1, arg = -1;
      for (let v = 0; v < G.n; v++) {
        const d = a[v] + b[v];
        if (d < minD[v]) minD[v] = d;
        if (minD[v] > best) { best = minD[v]; arg = v; }
      }
      next = arg;
    }
    return L;
  }

  // ------------------------------------------------------------------ bidirectional Dijkstra
  function bidirectional(G, s, t, metric) {
    const w = G.w[metric], n = G.n;
    const dF = new Float64Array(n).fill(Infinity), dB = new Float64Array(n).fill(Infinity);
    const pF = new Int32Array(n).fill(-1), pB = new Int32Array(n).fill(-1);
    const doneF = new Uint8Array(n), doneB = new Uint8Array(n);
    const hF = new Heap(4096), hB = new Heap(4096);
    const order = [], side = [];
    let mu = Infinity, meet = -1;
    dF[s] = 0; hF.push(0, s); dB[t] = 0; hB.push(0, t);
    if (s === t) { mu = 0; meet = s; }
    for (;;) {
      cleanTop(hF, doneF); cleanTop(hB, doneB);
      if (hF.n === 0 || hB.n === 0) break;
      if (hF.topKey() + hB.topKey() >= mu) break;        // stopping criterion
      if (hF.topKey() <= hB.topKey()) {
        const u = hF.pop(); doneF[u] = 1; order.push(u); side.push(0);
        const du = dF[u];
        for (let e = G.off[u]; e < G.off[u + 1]; e++) {
          const v = G.to[e], nd = du + w[e];
          if (nd < dF[v]) { dF[v] = nd; pF[v] = e; hF.push(nd, v); }
          if (dF[v] + dB[v] < mu) { mu = dF[v] + dB[v]; meet = v; }
        }
      } else {
        const u = hB.pop(); doneB[u] = 1; order.push(u); side.push(1);
        const du = dB[u];
        for (let i = G.roff[u]; i < G.roff[u + 1]; i++) {
          const e = G.redge[i], v = G.from[e], nd = du + w[e];
          if (nd < dB[v]) { dB[v] = nd; pB[v] = e; hB.push(nd, v); }
          if (dF[v] + dB[v] < mu) { mu = dF[v] + dB[v]; meet = v; }
        }
      }
    }
    let path = [];
    if (meet >= 0) {
      path = pathFromParents(G, pF, meet);
      let v = meet;
      while (pB[v] >= 0) { v = G.to[pB[v]]; path.push(v); }
    }
    return { dist: mu, path, order: Int32Array.from(order), side: Uint8Array.from(side), settled: order.length, meet };
  }

  // ------------------------------------------------------------------ contraction hierarchies
  // CH = { rank, eFrom, eTo, eW, eC1, eC2, eOrig, upOff, upE, dnOff, dnE }
  //   edges: original (eOrig = graph edge, eC1 = -1) or shortcuts (children eC1, eC2)
  //   upE[upOff[u]..]: edges u -> v with rank[v] > rank[u]   (forward upward search)
  //   dnE[dnOff[u]..]: edges v -> u with rank[v] > rank[u]   (backward upward search from t)
  // compact form (file): rank, shortcuts sFrom/sTo/sW/sC1/sC2, up/down lists; edge ids < m are edges
  // of the graph, ids >= m are shortcuts (id - m). loadCH builds the arrays the query uses.
  function loadCH(C, G) {
    const m = G.m, S = C.sFrom.length, N = m + S;
    const eFrom = new Int32Array(N), eTo = new Int32Array(N), eW = new Int32Array(N),
          eC1 = new Int32Array(N).fill(-1), eC2 = new Int32Array(N).fill(-1), eOrig = new Int32Array(N).fill(-1);
    eFrom.set(G.from); eTo.set(G.to); eW.set(G.w.fast);
    for (let e = 0; e < m; e++) eOrig[e] = e;
    for (let i = 0; i < S; i++) {
      eFrom[m + i] = C.sFrom[i]; eTo[m + i] = C.sTo[i]; eW[m + i] = C.sW[i]; eC1[m + i] = C.sC1[i]; eC2[m + i] = C.sC2[i];
    }
    const I = a => Int32Array.from(a);
    return { rank: I(C.rank), eFrom, eTo, eW, eC1, eC2, eOrig, upOff: I(C.upOff), upE: I(C.upE),
             dnOff: I(C.dnOff), dnE: I(C.dnE), nShortcuts: S, landmarks: C.landmarks };
  }
  function compactCH(CH, m) {
    const ne = CH.eFrom.length, uid = new Int32Array(ne), sIdx = [];
    for (let e = 0; e < ne; e++) {
      if (CH.eC1[e] < 0) uid[e] = CH.eOrig[e];
      else { uid[e] = m + sIdx.length; sIdx.push(e); }
    }
    const pick = (arr, f) => sIdx.map(e => f ? f(arr[e]) : arr[e]);
    return { m, rank: Array.from(CH.rank), sFrom: pick(CH.eFrom), sTo: pick(CH.eTo), sW: pick(CH.eW),
             sC1: pick(CH.eC1, e => uid[e]), sC2: pick(CH.eC2, e => uid[e]),
             upOff: Array.from(CH.upOff), upE: Array.from(CH.upE, e => uid[e]),
             dnOff: Array.from(CH.dnOff), dnE: Array.from(CH.dnE, e => uid[e]) };
  }

  function chQuery(CH, s, t) {
    const n = CH.rank.length;
    const dF = new Float64Array(n).fill(Infinity), dB = new Float64Array(n).fill(Infinity);
    const pF = new Int32Array(n).fill(-1), pB = new Int32Array(n).fill(-1);
    const doneF = new Uint8Array(n), doneB = new Uint8Array(n);
    const hF = new Heap(1024), hB = new Heap(1024);
    const order = [], side = [], relaxed = [];
    let mu = Infinity, meet = -1;
    dF[s] = 0; hF.push(0, s); dB[t] = 0; hB.push(0, t);
    for (;;) {
      cleanTop(hF, doneF); cleanTop(hB, doneB);
      const fOpen = hF.n > 0 && hF.topKey() < mu, bOpen = hB.n > 0 && hB.topKey() < mu;
      if (!fOpen && !bOpen) break;                       // each search stops when its minimum >= mu
      const forward = fOpen && (!bOpen || hF.topKey() <= hB.topKey());
      if (forward) {
        const u = hF.pop(); doneF[u] = 1; order.push(u); side.push(0);
        if (dF[u] + dB[u] < mu) { mu = dF[u] + dB[u]; meet = u; }
        for (let i = CH.upOff[u]; i < CH.upOff[u + 1]; i++) {
          const e = CH.upE[i], v = CH.eTo[e], nd = dF[u] + CH.eW[e];
          relaxed.push(e);
          if (nd < dF[v]) { dF[v] = nd; pF[v] = e; hF.push(nd, v); }
        }
      } else {
        const u = hB.pop(); doneB[u] = 1; order.push(u); side.push(1);
        if (dF[u] + dB[u] < mu) { mu = dF[u] + dB[u]; meet = u; }
        for (let i = CH.dnOff[u]; i < CH.dnOff[u + 1]; i++) {
          const e = CH.dnE[i], v = CH.eFrom[e], nd = dB[u] + CH.eW[e];
          relaxed.push(e);
          if (nd < dB[v]) { dB[v] = nd; pB[v] = e; hB.push(nd, v); }
        }
      }
    }
    // CH path (with shortcuts), then unpacked into original edges
    const chEdges = [];
    if (meet >= 0) {
      let v = meet;
      const front = [];
      while (pF[v] >= 0) { front.push(pF[v]); v = CH.eFrom[pF[v]]; }
      front.reverse();
      v = meet;
      const back = [];
      while (pB[v] >= 0) { back.push(pB[v]); v = CH.eTo[pB[v]]; }
      chEdges.push(...front, ...back);
    }
    const orig = [];                           // unpacked: edges of the original graph
    const unpack = e => { if (CH.eC1[e] < 0) orig.push(CH.eOrig[e]); else { unpack(CH.eC1[e]); unpack(CH.eC2[e]); } };
    chEdges.forEach(unpack);
    return { dist: mu, chEdges, origEdges: orig, order: Int32Array.from(order), side: Uint8Array.from(side),
             settled: order.length, meet, relaxed: Int32Array.from(relaxed), pF, pB };
  }

  // CH preprocessing (Node, a few seconds to minutes). Priority: edge difference + contracted
  // neighbours; witness searches limited to `settleLimit` settled nodes; lazy updates.
  function buildCH(G, metric, opts) {
    opts = opts || {};
    const settleLimit = opts.settleLimit || 100;
    const log = opts.log || (() => {});
    const n = G.n, w0 = G.w[metric];
    // growable edge table
    let cap = G.m * 3, ne = 0;
    let eFrom = new Int32Array(cap), eTo = new Int32Array(cap), eW = new Int32Array(cap),
        eC1 = new Int32Array(cap), eC2 = new Int32Array(cap), eOrig = new Int32Array(cap);
    const grow = () => {
      cap *= 2;
      const g = a => { const b = new Int32Array(cap); b.set(a); return b; };
      eFrom = g(eFrom); eTo = g(eTo); eW = g(eW); eC1 = g(eC1); eC2 = g(eC2); eOrig = g(eOrig);
    };
    // adjacency of the remaining graph: Map neighbour -> edge id (only the best edge per pair)
    const outM = Array.from({ length: n }, () => new Map()), inM = Array.from({ length: n }, () => new Map());
    const addEdge = (a, b, wt, c1, c2, orig) => {
      const old = outM[a].get(b);
      if (old !== undefined && eW[old] <= wt) return old;
      if (ne === cap) grow();
      const e = ne++;
      eFrom[e] = a; eTo[e] = b; eW[e] = wt; eC1[e] = c1; eC2[e] = c2; eOrig[e] = orig;
      outM[a].set(b, e); inM[b].set(a, e);
      return e;
    };
    for (let e = 0; e < G.m; e++) if (G.from[e] !== G.to[e]) addEdge(G.from[e], G.to[e], w0[e], -1, -1, e);
    const allEdges = [];                       // every edge that ends up in the CH
    const contracted = new Uint8Array(n), delNb = new Int32Array(n), rank = new Int32Array(n).fill(-1);

    // witness search workspace
    const wd = new Float64Array(n).fill(Infinity), touched = [];
    const wh = new Heap(1024);
    function witness(u, avoid, maxDist) {      // Dijkstra from u in the remaining graph without `avoid`
      for (const x of touched) wd[x] = Infinity;
      touched.length = 0; wh.clear();
      wd[u] = 0; touched.push(u); wh.push(0, u);
      let settled = 0;
      while (wh.n > 0) {
        const x = wh.pop(), dx = wh.lastKey;
        if (dx > wd[x]) continue;
        if (dx > maxDist || ++settled > settleLimit) break;
        for (const [y, e] of outM[x]) {
          if (y === avoid || contracted[y]) continue;
          const nd = dx + eW[e];
          if (nd < wd[y]) { if (wd[y] === Infinity) touched.push(y); wd[y] = nd; wh.push(nd, y); }
        }
      }
    }
    // shortcuts needed when contracting v: list of [u, w, weight, e1, e2]
    function shortcutsFor(v) {
      const res = [];
      for (const [u, e1] of inM[v]) {
        if (contracted[u]) continue;
        let maxD = 0;
        for (const [x, e2] of outM[v]) if (!contracted[x] && x !== u) maxD = Math.max(maxD, eW[e1] + eW[e2]);
        if (maxD === 0) continue;
        witness(u, v, maxD);
        for (const [x, e2] of outM[v]) {
          if (contracted[x] || x === u) continue;
          const via = eW[e1] + eW[e2];
          if (wd[x] > via) res.push([u, x, via, e1, e2]);
        }
      }
      return res;
    }
    function priority(v) {
      let deg = 0;
      for (const [u] of inM[v]) if (!contracted[u]) deg++;
      for (const [x] of outM[v]) if (!contracted[x]) deg++;
      return 2 * (shortcutsFor(v).length - deg) + delNb[v];
    }
    const pq = new Heap(n + 16), prio = new Float64Array(n);
    for (let v = 0; v < n; v++) { prio[v] = priority(v); pq.push(prio[v], v); }
    log('initial priorities done');
    let next = 0, nShortcuts = 0;
    while (pq.n > 0) {
      const v = pq.pop(), key = pq.lastKey;
      if (contracted[v] || key !== prio[v]) continue;
      const p = priority(v);
      if (p > key && pq.n > 0 && p > pq.topKey()) { prio[v] = p; pq.push(p, v); continue; }
      // contract v
      for (const [u, x, via, e1, e2] of shortcutsFor(v)) {
        const before = ne;
        addEdge(u, x, via, e1, e2, -1);
        if (ne > before) nShortcuts++;
      }
      contracted[v] = 1; rank[v] = next++;
      const nbs = new Set();
      for (const [u] of inM[v]) if (!contracted[u]) nbs.add(u);
      for (const [x] of outM[v]) if (!contracted[x]) nbs.add(x);
      for (const u of nbs) { delNb[u]++; prio[u] = priority(u); pq.push(prio[u], u); }
      if (next % 10000 === 0) log(`contracted ${next}, shortcuts ${nShortcuts}`);
    }
    // the CH contains all edges between nodes (original and shortcuts) that are still the best for
    // their pair; edges are stored once and used upward from the lower endpoint
    const keep = [];
    for (let a = 0; a < n; a++) for (const [, e] of outM[a]) keep.push(e);
    keep.sort((p, q) => p - q);
    const upCnt = new Int32Array(n + 1), dnCnt = new Int32Array(n + 1);
    for (const e of keep) { if (rank[eTo[e]] > rank[eFrom[e]]) upCnt[eFrom[e] + 1]++; else dnCnt[eTo[e] + 1]++; }
    for (let i = 0; i < n; i++) { upCnt[i + 1] += upCnt[i]; dnCnt[i + 1] += dnCnt[i]; }
    const upE = new Int32Array(upCnt[n]), dnE = new Int32Array(dnCnt[n]);
    const fu = upCnt.slice(0, n), fd = dnCnt.slice(0, n);
    for (const e of keep) { if (rank[eTo[e]] > rank[eFrom[e]]) upE[fu[eFrom[e]]++] = e; else dnE[fd[eTo[e]]++] = e; }
    return { rank, eFrom: eFrom.slice(0, ne), eTo: eTo.slice(0, ne), eW: eW.slice(0, ne), eC1: eC1.slice(0, ne),
             eC2: eC2.slice(0, ne), eOrig: eOrig.slice(0, ne), upOff: upCnt, upE, dnOff: dnCnt, dnE,
             nShortcuts, nEdges: keep.length };
  }

  const Routing = { Heap, makeGraph, dijkstra, astar, alt, bidirectional, chQuery, buildCH, loadCH, compactCH,
                    landmarkTables, chooseLandmarks, allDistances, euclidPotential, altPotential };
  if (typeof module !== 'undefined' && module.exports) module.exports = Routing;
  else root.Routing = Routing;
})(typeof window !== 'undefined' ? window : globalThis);
