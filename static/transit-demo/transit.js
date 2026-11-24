/* Public transit routing for the demo of "Algorithms and Sustainability" (lectures 6 and 7).
   Own work, CC BY 4.0, Kevin Buchin / TU Dortmund. Runs in the browser (window.Transit) and in Node.

   Data: stops [{name, x, y, change}] (change = minimum change time in minutes), trips
   [{line, color, stops: [stop index], arr: [min], dep: [min]}], optional footpaths [[a, b, minutes]].
   Times are minutes after midnight. Connection Scan (Dibbelt et al. 2018) and RAPTOR (Delling, Pajor,
   Werneck 2015) record traces for the animation: what happened at each connection, in each round. */
(function (root) {
  'use strict';

  function prepare(D) {
    const S = D.stops.length;
    const conns = [];                          // elementary connections, sorted by departure
    D.trips.forEach((tr, ti) => {
      for (let i = 0; i + 1 < tr.stops.length; i++)
        conns.push({ trip: ti, i, from: tr.stops[i], to: tr.stops[i + 1], dep: tr.dep[i], arr: tr.arr[i + 1] });
    });
    conns.sort((a, b) => a.dep - b.dep || a.arr - b.arr || a.trip - b.trip || a.i - b.i);
    const foot = Array.from({ length: S }, () => []);
    for (const [a, b, d] of D.footpaths || []) { foot[a].push([b, d]); foot[b].push([a, d]); }
    // routes: trips with the same stop sequence, sorted by departure at the first stop
    const byKey = new Map();
    D.trips.forEach((tr, ti) => {
      const key = tr.stops.join(',');
      if (!byKey.has(key)) byKey.set(key, { stops: tr.stops, trips: [], line: tr.line, color: tr.color });
      byKey.get(key).trips.push(ti);
    });
    const routes = [...byKey.values()];
    for (const r of routes) r.trips.sort((a, b) => D.trips[a].dep[0] - D.trips[b].dep[0]);
    const routesAt = Array.from({ length: S }, () => []);
    routes.forEach((r, ri) => r.stops.forEach((p, i) => { if (i + 1 < r.stops.length) routesAt[p].push([ri, i]); }));
    return { D, S, conns, foot, routes, routesAt };
  }
  const changeAt = (N, p, source) => (p === source ? 0 : N.D.stops[p].change || 0);

  // ---------------------------------------------------------------- Connection Scan, earliest arrival
  function csa(N, source, t0, target, fromStart) {
    const { D, S, conns, foot } = N;
    const arr = new Float64Array(S).fill(Infinity), inLeg = new Array(S).fill(null);
    const enter = new Int32Array(D.trips.length).fill(-1);   // connection where we board the trip
    arr[source] = t0;
    for (const [b, d] of foot[source]) if (t0 + d < arr[b]) { arr[b] = t0 + d; inLeg[b] = { walk: true, from: source, dur: d }; }
    const trace = [];
    let first = 0;                             // the first connection departing at t0 or later
    while (first < conns.length && conns[first].dep < t0) first++;
    if (fromStart) for (let ci = 0; ci < first; ci++) trace.push({ ci, status: 'early' });   // small examples: show them
    for (let ci = first; ci < conns.length; ci++) {
      const c = conns[ci];
      if (target >= 0 && c.dep >= arr[target]) { trace.push({ ci, status: 'stop' }); break; }
      const onboard = enter[c.trip] >= 0;
      const boardable = arr[c.from] + changeAt(N, c.from, source) <= c.dep;
      if (!onboard && !boardable) { trace.push({ ci, status: 'unreachable' }); continue; }
      if (!onboard) enter[c.trip] = ci;
      let status = 'nothing';
      const imp = [];
      if (c.arr < arr[c.to]) {
        arr[c.to] = c.arr; inLeg[c.to] = { trip: c.trip, enter: enter[c.trip], exit: ci };
        status = 'improves'; imp.push([c.to, c.arr]);
        for (const [b, d] of foot[c.to]) if (c.arr + d < arr[b]) { arr[b] = c.arr + d; inLeg[b] = { walk: true, from: c.to, dur: d }; imp.push([b, c.arr + d]); }
      }
      trace.push({ ci, status, board: !onboard, imp });
    }
    return { arr, inLeg, trace, first };
  }
  function csaJourney(N, res, source, target) {   // legs from source to target
    const legs = [];
    let p = target, guard = 0;
    while (p !== source && res.inLeg[p] && guard++ < 1000) {
      const L = res.inLeg[p];
      if (L.walk) { legs.push({ walk: true, from: L.from, to: p, dur: L.dur }); p = L.from; continue; }
      const a = N.conns[L.enter], b = N.conns[L.exit];
      legs.push({ trip: L.trip, from: a.from, to: b.to, dep: a.dep, arr: b.arr, enter: L.enter, exit: L.exit });
      p = a.from;
    }
    return p === source ? legs.reverse() : null;
  }

  // ---------------------------------------------------------------- RAPTOR, rounds = trips
  function raptor(N, source, t0, target, K) {
    const { D, S, routes, routesAt, foot } = N;
    K = K || 8;
    const tau = [new Float64Array(S).fill(Infinity)];
    const best = new Float64Array(S).fill(Infinity);
    const par = [new Array(S).fill(null)];
    tau[0][source] = t0; best[source] = t0;
    let marked = new Set([source]);
    for (const [b, d] of foot[source]) if (t0 + d < tau[0][b]) { tau[0][b] = t0 + d; best[b] = t0 + d; par[0][b] = { walk: true, from: source, dur: d }; marked.add(b); }
    const rounds = [];
    for (let k = 1; k <= K && marked.size; k++) {
      tau.push(Float64Array.from(tau[k - 1])); par.push(new Array(S).fill(null));
      const Q = new Map();                       // route -> earliest marked position
      for (const p of marked) for (const [ri, i] of routesAt[p]) if (!Q.has(ri) || i < Q.get(ri)) Q.set(ri, i);
      const newly = new Set(), scans = [];
      for (const [ri, i0] of Q) {
        const R = routes[ri], seq = R.stops;
        let cur = -1, boardAt = -1;
        const hops = [], imp = [];
        for (let i = i0; i < seq.length; i++) {
          const p = seq[i];
          if (cur >= 0) {
            const a = D.trips[cur].arr[i];
            if (a < Math.min(best[p], target >= 0 ? best[target] : Infinity)) {
              tau[k][p] = a; best[p] = a; newly.add(p); imp.push([p, a]);
              par[k][p] = { trip: cur, from: seq[boardAt], to: p, dep: D.trips[cur].dep[boardAt], arr: a, round: k - 1 };
            }
          }
          if (i + 1 < seq.length && tau[k - 1][p] < Infinity) {     // can we catch an earlier trip here?
            const ready = tau[k - 1][p] + changeAt(N, p, source);
            let lo = 0, hi = R.trips.length;               // first trip of the route that departs >= ready
            while (lo < hi) { const mid = (lo + hi) >> 1; if (D.trips[R.trips[mid]].dep[i] >= ready) hi = mid; else lo = mid + 1; }
            if (lo < R.trips.length) {
              const tj = R.trips[lo], dep = D.trips[tj].dep[i];
              if (cur < 0 || dep < D.trips[cur].dep[i]) { cur = tj; boardAt = i; hops.push({ trip: tj, stop: p, dep }); }
            }
          }
        }
        scans.push({ route: ri, from: i0, hops, imp });
      }
      // footpaths after the round
      const wimp = [];
      for (const p of [...newly]) for (const [b, d] of foot[p]) {
        if (tau[k][p] + d < Math.min(best[b], tau[k][b])) { tau[k][b] = tau[k][p] + d; best[b] = tau[k][b]; par[k][b] = { walk: true, from: p, dur: d }; newly.add(b); wimp.push([b, tau[k][b]]); }
      }
      if (wimp.length) scans.push({ walk: true, imp: wimp });
      rounds.push({ k, scans, improved: [...newly] });
      marked = newly;
    }
    // Pareto set at the target: (number of trips, arrival)
    const pareto = [];
    if (target >= 0) for (let k = 1; k < tau.length; k++) {
      const a = tau[k][target];
      if (a < Infinity && (pareto.length === 0 || a < pareto[pareto.length - 1].arr)) pareto.push({ k, arr: a });
    }
    return { tau, par, rounds, pareto };
  }
  function raptorJourney(N, res, source, target, k) {
    const legs = [];
    let p = target, guard = 0;
    while (p !== source && k >= 0 && guard++ < 100) {
      let L = res.par[k][p];
      while (!L && k > 0 && res.tau[k][p] === res.tau[k - 1][p]) { k--; L = res.par[k][p]; }
      if (!L) return null;
      if (L.walk) { legs.push({ walk: true, from: L.from, to: p, dur: L.dur }); p = L.from; continue; }
      legs.push({ trip: L.trip, from: L.from, to: p, dep: L.dep, arr: L.arr });
      p = L.from; k = L.round;
    }
    return p === source ? legs.reverse() : null;
  }

  function hm(t) {
    if (!isFinite(t)) return '–';
    t = Math.round(t);
    return Math.floor(t / 60) % 24 + ':' + String(t % 60).padStart(2, '0');
  }
  const Transit = { prepare, csa, csaJourney, raptor, raptorJourney, hm };
  if (typeof module !== 'undefined' && module.exports) module.exports = Transit;
  else root.Transit = Transit;
})(typeof window !== 'undefined' ? window : globalThis);
