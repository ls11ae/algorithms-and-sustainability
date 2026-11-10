/* Interactive route planning demo on the Dortmund bicycle network (lecture 5, Algorithms and
   Sustainability). Own work, CC BY 4.0; map data (c) OpenStreetMap contributors, ODbL 1.0.
   URL parameters: algo=dijkstra|bidir|astar|alt|ch|compare  metric=fast|quiet  s=, t= (place or node id)
   state=final|start|anim  ui=full|legend|none  speed=<factor>  view=x0,y0,x1,y1 (metres) */
(async function () {
  'use strict';
  const R = window.Routing;
  const P = new URLSearchParams(location.search);
  const COL = { blue: '#0A97D9', orange: '#E8700A', green: '#3F7E44', red: '#DD1367', ink: '#282a2e',
                grey: '#8e908c' };
  const NAMES = { dijkstra: 'Dijkstra', bidir: 'Bidirectional Dijkstra', astar: 'A* (straight line)',
                  alt: 'ALT (A*, landmarks)', ch: 'Contraction hierarchies', compare: 'Fast vs quiet' };
  const RATE = { dijkstra: 140, bidir: 140, astar: 140, alt: 140, ch: 1.5 };   // nodes per frame
  const ui = P.get('ui') || 'full';
  document.body.classList.add(ui === 'none' ? 'noui' : ui === 'legend' ? 'legend' : ui === 'compact' ? 'compact' : 'fullui');
  if (P.get('algos')) {                         // only some algorithm buttons (e.g. algos=astar,alt)
    const keep = P.get('algos').split(',');
    for (const b of document.querySelectorAll('[data-algo]')) if (!keep.includes(b.dataset.algo)) b.remove();
    document.body.classList.add('algosfilter');
  }
  const $ = id => document.getElementById(id);

  // ------------------------------------------------------------ data
  async function loadGz(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(url + ': HTTP ' + r.status);
    const buf = new Uint8Array(await r.arrayBuffer());
    if (buf[0] !== 0x1f || buf[1] !== 0x8b)          // the server has already unpacked it
      return JSON.parse(new TextDecoder().decode(buf));
    if (typeof DecompressionStream === 'undefined') throw new Error('this browser cannot unpack gzip data');
    const stream = new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'));
    return JSON.parse(await new Response(stream).text());
  }
  let D, C;
  try {
    [D, C] = await Promise.all([loadGz('dortmund-graph.json.gz'), loadGz('dortmund-ch.json.gz')]);
  } catch (e) {
    $('loading').textContent = 'Could not load the data (' + e.message + '). Open the page via a web server.';
    return;
  }
  const G = R.makeGraph(D);
  const CH = R.loadCH(C, G);
  const n = G.n, segOff = Int32Array.from(D.segOff), segXY = Int32Array.from(D.segXY), segCls = Uint8Array.from(D.segCls);
  const nSeg = segCls.length;
  const segLen = new Float64Array(nSeg);
  for (let s = 0; s < nSeg; s++) {
    let L = 0;
    for (let k = segOff[s] + 1; k < segOff[s + 1]; k++)
      L += Math.hypot(segXY[2 * k] - segXY[2 * k - 2], segXY[2 * k + 1] - segXY[2 * k - 1]);
    segLen[s] = L;
  }
  const byCls = [[], [], [], []];
  for (let s = 0; s < nSeg; s++) byCls[segCls[s]].push(s);
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (let i = 0; i < n; i++) {
    if (G.x[i] < x0) x0 = G.x[i]; if (G.x[i] > x1) x1 = G.x[i];
    if (G.y[i] < y0) y0 = G.y[i]; if (G.y[i] > y1) y1 = G.y[i];
  }
  // grid for "nearest node"
  const CELL = 150, gw = Math.ceil((x1 - x0) / CELL) + 1, gh = Math.ceil((y1 - y0) / CELL) + 1;
  const cellOf = (x, y) => Math.min(gh - 1, Math.max(0, Math.floor((y - y0) / CELL))) * gw +
                           Math.min(gw - 1, Math.max(0, Math.floor((x - x0) / CELL)));
  const cellStart = new Int32Array(gw * gh + 1), cellNodes = new Int32Array(n);
  for (let i = 0; i < n; i++) cellStart[cellOf(G.x[i], G.y[i]) + 1]++;
  for (let c = 0; c < gw * gh; c++) cellStart[c + 1] += cellStart[c];
  { const f = cellStart.slice(0, gw * gh); for (let i = 0; i < n; i++) cellNodes[f[cellOf(G.x[i], G.y[i])]++] = i; }
  function nearest(x, y) {
    const cx = Math.floor((x - x0) / CELL), cy = Math.floor((y - y0) / CELL);
    let best = -1, bd = Infinity;
    for (let r = 0; r < 60 && (best < 0 || (r - 1) * CELL < Math.sqrt(bd)); r++) {
      for (let j = cy - r; j <= cy + r; j++) for (let i = cx - r; i <= cx + r; i++) {
        if (i < 0 || j < 0 || i >= gw || j >= gh) continue;
        if (Math.max(Math.abs(i - cx), Math.abs(j - cy)) !== r) continue;
        const c = j * gw + i;
        for (let k = cellStart[c]; k < cellStart[c + 1]; k++) {
          const v = cellNodes[k], d = (G.x[v] - x) ** 2 + (G.y[v] - y) ** 2;
          if (d < bd) { bd = d; best = v; }
        }
      }
    }
    return best;
  }

  // ------------------------------------------------------------ view and canvases
  const cv = { base: $('base'), search: $('search'), top: $('top') };
  const ctx = { base: cv.base.getContext('2d'), search: cv.search.getContext('2d'), top: cv.top.getContext('2d') };
  let W = 0, H = 0, dpr = 1;
  const view = { cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, scale: 1 };
  function fit(bx0, by0, bx1, by1) {
    view.cx = (bx0 + bx1) / 2; view.cy = (by0 + by1) / 2;
    view.scale = Math.min(W / (bx1 - bx0), H / (by1 - by0)) * 0.97;
  }
  const SX = x => (x - view.cx) * view.scale + W / 2;
  const SY = y => H / 2 - (y - view.cy) * view.scale;
  function resize(refit) {
    dpr = window.devicePixelRatio || 1;
    W = window.innerWidth; H = window.innerHeight;
    for (const k of Object.keys(cv)) {
      cv[k].width = Math.round(W * dpr); cv[k].height = Math.round(H * dpr);
      ctx[k].setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    if (refit) {
      const v = (P.get('view') || '').split(',').map(Number);
      if (v.length === 4 && v.every(isFinite)) fit(v[0], v[1], v[2], v[3]); else fit(x0, y0, x1, y1);
    }
  }
  const lineScale = () => Math.max(0.6, Math.min(2.5, view.scale * 40));   // thicker lines when zoomed in

  function addPiece(c, s, reverse) {
    const a = segOff[s], b = segOff[s + 1];
    c.moveTo(SX(segXY[2 * a]), SY(segXY[2 * a + 1]));
    for (let k = a + 1; k < b; k++) c.lineTo(SX(segXY[2 * k]), SY(segXY[2 * k + 1]));
  }
  function pieceOf(e) { const s = G.sg[e]; return s >= 0 ? s : -s - 1; }

  function drawBase() {
    const c = ctx.base, ls = lineScale();
    c.fillStyle = '#ffffff'; c.fillRect(0, 0, W, H);
    c.lineCap = 'round'; c.lineJoin = 'round';
    const styles = [[3, '#e1e3e5', 0.55], [0, '#cfd2d6', 0.7], [2, '#bcd8be', 0.9], [1, '#aeb2b8', 1.5]];
    for (const [cls, col, lw] of styles) {
      c.beginPath();
      for (const s of byCls[cls]) addPiece(c, s);
      c.strokeStyle = col; c.lineWidth = lw * ls; c.stroke();
    }
  }

  // ------------------------------------------------------------ state
  const st = {
    algo: P.get('algo') || 'dijkstra', metric: P.get('metric') || 'fast',
    s: -1, t: -1, res: null, shown: 0, anim: false, speed: parseFloat(P.get('speed') || '1'),
    tables: {}, compare: null,
  };
  const placeNode = v => (D.places[v] ? D.places[v].node : (v !== null && v !== '' && isFinite(+v) ? +v : -1));
  st.s = placeNode(P.get('s') || 'tu');
  st.t = placeNode(P.get('t') || 'phoenix');

  function tablesFor(metric) {
    if (!st.tables[metric]) st.tables[metric] = R.landmarkTables(G, CH.landmarks, metric);
    return st.tables[metric];
  }
  function edgesOfPath(path, metric) {
    const w = G.w[metric], es = [];
    for (let i = 0; i + 1 < path.length; i++) {
      const u = path[i], v = path[i + 1];
      let best = -1;
      for (let e = G.off[u]; e < G.off[u + 1]; e++) if (G.to[e] === v && (best < 0 || w[e] < w[best])) best = e;
      es.push(best);
    }
    return es;
  }
  function routeInfo(edges, metric) {
    let len = 0, busy = 0, time = 0;
    for (const e of edges) {
      const L = segLen[pieceOf(e)];
      len += L; time += G.w.fast[e];
      if (G.w.quiet[e] >= 1.5 * G.w.fast[e]) busy += L;
    }
    return { km: len / 1000, busyKm: busy / 1000, min: time / 600 };
  }
  function compute() {
    const { algo, metric, s, t } = st;
    if (s < 0 || t < 0) { st.res = null; return; }
    let r;
    if (algo === 'dijkstra') r = R.dijkstra(G, s, t, metric);
    else if (algo === 'bidir') r = R.bidirectional(G, s, t, metric);
    else if (algo === 'astar') r = R.astar(G, s, t, metric);
    else if (algo === 'alt') r = R.alt(G, s, t, metric, tablesFor(metric));
    else if (algo === 'ch') {
      if (metric !== 'fast') { st.res = { note: 'The contraction hierarchy was computed for travel time only. Another weight needs a new preprocessing (or a customizable CH).' }; return; }
      r = R.chQuery(CH, s, t);
      r.edges = r.origEdges;
    } else if (algo === 'compare') {
      const f = R.dijkstra(G, s, t, 'fast'), q = R.dijkstra(G, s, t, 'quiet');
      const fe = edgesOfPath(f.path, 'fast'), qe = edgesOfPath(q.path, 'quiet');
      st.res = { compare: true, fast: { edges: fe, info: routeInfo(fe) }, quiet: { edges: qe, info: routeInfo(qe) },
                 settled: 0, order: new Int32Array(0), side: new Uint8Array(0) };
      return;
    }
    if (!r.edges) r.edges = edgesOfPath(r.path, metric);
    r.info = routeInfo(r.edges);
    st.res = r;
  }

  // ------------------------------------------------------------ drawing the search
  function drawSearch(k0, k1) {
    const r = st.res;
    if (!r || !r.order) return;
    const c = ctx.search, ls = lineScale();
    c.lineCap = 'round'; c.lineJoin = 'round';
    for (const side of [0, 1]) {
      c.beginPath();
      const sc = new Path2D();
      let anySc = false;
      for (let i = k0; i < k1; i++) {
        if (r.side[i] !== side) continue;
        const u = r.order[i];
        if (st.algo === 'ch') {                  // the two upward search trees
          const e = side === 0 ? r.pF[u] : r.pB[u];
          if (e >= 0) {
            if (e < G.m) addPiece(c, pieceOf(e));
            else { sc.moveTo(SX(G.x[CH.eFrom[e]]), SY(G.y[CH.eFrom[e]])); sc.lineTo(SX(G.x[CH.eTo[e]]), SY(G.y[CH.eTo[e]])); anySc = true; }
          }
        } else if (side === 0) {
          for (let e = G.off[u]; e < G.off[u + 1]; e++) addPiece(c, pieceOf(e));
        } else {
          for (let j = G.roff[u]; j < G.roff[u + 1]; j++) addPiece(c, pieceOf(G.redge[j]));
        }
      }
      const col = side === 0 ? COL.blue : COL.orange;
      c.strokeStyle = col; c.globalAlpha = st.algo === 'ch' ? 0.95 : 0.7;
      c.lineWidth = (st.algo === 'ch' ? 2.2 : 1.25) * ls; c.stroke();
      if (anySc) {
        c.setLineDash([6, 4]); c.lineWidth = 1.6 * Math.min(1.5, ls); c.globalAlpha = 0.9; c.stroke(sc); c.setLineDash([]);
      }
      c.globalAlpha = 1;
      if (st.algo === 'ch') {               // settled nodes as dots
        c.fillStyle = col;
        for (let i = k0; i < k1; i++) {
          if (r.side[i] !== side) continue;
          const u = r.order[i];
          c.beginPath(); c.arc(SX(G.x[u]), SY(G.y[u]), 2.6 * Math.min(1.6, ls), 0, 2 * Math.PI); c.fill();
        }
      }
    }
  }
  function drawRoute(c, edges, col, lw) {
    const ls = Math.min(1.6, lineScale());
    c.lineCap = 'round'; c.lineJoin = 'round';
    c.beginPath();
    for (const e of edges) addPiece(c, pieceOf(e));
    c.strokeStyle = '#ffffff'; c.lineWidth = (lw + 3) * ls; c.stroke();
    c.strokeStyle = col; c.lineWidth = lw * ls; c.stroke();
  }
  function label(c, text, x, y, opts) {
    opts = opts || {};
    c.font = `${opts.bold ? '700 ' : ''}${opts.size || 13}px Lato, LatoLatin, Helvetica, Arial, sans-serif`;
    c.textAlign = opts.align || 'left'; c.textBaseline = 'middle';
    c.lineWidth = 4; c.strokeStyle = 'rgba(255,255,255,0.95)'; c.strokeText(text, x, y);
    c.fillStyle = opts.color || COL.ink; c.fillText(text, x, y);
  }
  function marker(c, v, txt) {
    const x = SX(G.x[v]), y = SY(G.y[v]);
    c.beginPath(); c.arc(x, y, 8, 0, 2 * Math.PI);
    c.fillStyle = COL.ink; c.fill(); c.lineWidth = 2.5; c.strokeStyle = '#ffffff'; c.stroke();
    c.font = '700 11px Lato, LatoLatin, Helvetica, Arial, sans-serif';
    c.fillStyle = '#ffffff'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(txt, x, y + 0.5);
  }
  function drawTop() {
    const c = ctx.top;
    c.clearRect(0, 0, W, H);
    const r = st.res, done = r && !st.anim;
    if (done && r.compare) {
      drawRoute(c, r.quiet.edges, COL.green, 4.5);
      drawRoute(c, r.fast.edges, COL.blue, 3);
    } else if (done && r.edges && r.edges.length) {
      drawRoute(c, r.edges, COL.ink, 3.5);
    }
    if (st.algo === 'alt' && CH.landmarks) {
      for (const L of CH.landmarks) {
        const x = SX(G.x[L]), y = SY(G.y[L]);
        c.beginPath(); c.moveTo(x, y - 8); c.lineTo(x + 8, y); c.lineTo(x, y + 8); c.lineTo(x - 8, y); c.closePath();
        c.fillStyle = COL.red; c.fill(); c.lineWidth = 2; c.strokeStyle = '#ffffff'; c.stroke();
      }
    }
    for (const [key, p] of Object.entries(D.places)) {
      if (key === 'city' || key === 'stadium') continue;
      const v = p.node;
      if (v === st.s || v === st.t) continue;
      const x = SX(G.x[v]), y = SY(G.y[v]);
      c.beginPath(); c.arc(x, y, 3, 0, 2 * Math.PI); c.fillStyle = COL.ink; c.fill();
      label(c, p.label, x + 6, y - 9, { size: ui === 'compact' ? 14 : 12, color: '#4d4f53' });
    }
    if (st.s >= 0) marker(c, st.s, 's');
    if (st.t >= 0) marker(c, st.t, 't');
    const nameOf = v => { for (const p of Object.values(D.places)) if (p.node === v) return p.label; return null; };
    const fs = ui === 'compact' ? 15 : 13;
    if (st.s >= 0 && nameOf(st.s)) label(c, nameOf(st.s), SX(G.x[st.s]) - 12, SY(G.y[st.s]) + 16, { bold: true, align: 'right', size: fs });
    if (st.t >= 0 && nameOf(st.t)) label(c, nameOf(st.t), SX(G.x[st.t]) + 12, SY(G.y[st.t]) + 16, { bold: true, size: fs });
  }
  function redrawAll() {
    drawBase();
    ctx.search.clearRect(0, 0, W, H);
    if (st.res && st.res.order) drawSearch(0, Math.floor(st.shown));
    drawTop();
    updateStats();
  }

  // ------------------------------------------------------------ text
  const fmt = x => Math.round(x).toLocaleString('en-US');
  function updateStats() {
    const r = st.res;
    let html = `<b>${NAMES[st.algo]}</b>` + (st.algo === 'compare' ? '' : ` · weight: ${st.metric === 'fast' ? 'travel time' : 'quiet'}`);
    let leg = '';
    if (r && r.note) html += `<br>${r.note}`;
    else if (r && r.compare) {
      const f = r.fast.info, q = r.quiet.info;
      const line = (col, name, i) => `<span class="key" style="background:${col}"></span>${name}: <b>${i.min.toFixed(1)} min</b>, ${i.km.toFixed(1)} km, ${i.busyKm.toFixed(1)} km on busy roads`;
      html += `<br>${line(COL.blue, 'fastest', f)}<br>${line(COL.green, 'quieter', q)}`;
      const nm = v => { for (const p of Object.values(D.places)) if (p.node === v) return p.label; return 'node ' + v; };
      leg = `<b>${nm(st.s)} → ${nm(st.t)} by bike</b><br>${line(COL.blue, 'fastest', f)}<br>${line(COL.green, 'quieter', q)}`;
    } else if (r) {
      const k = Math.floor(st.shown);
      html += `<br>settled nodes: <b>${fmt(k)}</b>` + (st.anim ? '' : ` of ${fmt(G.n)}`);
      if (!st.anim && r.info) html += `<br>route: <b>${r.info.min.toFixed(1)} min</b> · ${r.info.km.toFixed(1)} km`;
      if (st.algo === 'ch') html += `<br><span class="hint">preprocessing: ${fmt(CH.nShortcuts)} shortcuts; dashed: shortcuts in the two search trees</span>`;
      if (st.algo === 'alt') html += `<br><span class="hint">${CH.landmarks.length} landmarks (red), chosen farthest first</span>`;
      const keys = st.algo === 'bidir' || st.algo === 'ch'
        ? `<span class="key" style="background:${COL.blue}"></span>from s &nbsp;<span class="key" style="background:${COL.orange}"></span>from t` + (st.algo === 'ch' ? ' &nbsp;dashed: shortcuts' : '')
        : `<span class="key" style="background:${COL.blue}"></span>searched streets`;
      leg = `<b>${NAMES[st.algo]}</b><br>settled nodes: <b>${fmt(k)}</b> of ${fmt(G.n)}<br>${keys}` +
            (st.algo === 'alt' ? ` &nbsp;<span style="color:${COL.red}">◆</span> landmarks` : '');
    }
    $('stats').innerHTML = html;
    $('legend').innerHTML = leg;
    for (const b of document.querySelectorAll('[data-algo]')) b.classList.toggle('on', b.dataset.algo === st.algo);
    for (const b of document.querySelectorAll('[data-metric]')) b.classList.toggle('on', b.dataset.metric === st.metric);
    for (const b of document.querySelectorAll('[data-speed]')) b.classList.toggle('on', +b.dataset.speed === st.speed);
  }

  // ------------------------------------------------------------ running
  let raf = 0;
  function run(animated) {
    cancelAnimationFrame(raf);
    compute();
    ctx.search.clearRect(0, 0, W, H);
    const r = st.res;
    if (!r || !r.order || !animated || r.settled === 0) {
      st.anim = false; st.shown = r && r.order ? r.settled : 0;
      if (r && r.order) drawSearch(0, r.settled);
      drawTop(); updateStats(); return;
    }
    st.anim = true; st.shown = 0; drawTop();
    const rate = (RATE[st.algo] || 100) * st.speed;
    const step = () => {
      const k0 = Math.floor(st.shown);
      st.shown = Math.min(r.settled, st.shown + rate);
      const k1 = Math.floor(st.shown);
      drawSearch(k0, k1);
      if (k1 >= r.settled) { st.anim = false; drawTop(); }
      updateStats();
      if (st.anim) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
  }
  function clearSearch() {
    cancelAnimationFrame(raf); st.anim = false; st.res = null; st.shown = 0;
    ctx.search.clearRect(0, 0, W, H); drawTop(); updateStats();
  }

  // ------------------------------------------------------------ interaction
  for (const b of document.querySelectorAll('[data-algo]')) b.onclick = () => { st.algo = b.dataset.algo; run(st.algo !== 'compare'); };
  for (const b of document.querySelectorAll('[data-metric]')) b.onclick = () => { st.metric = b.dataset.metric; run(false); };
  for (const b of document.querySelectorAll('[data-speed]')) b.onclick = () => { st.speed = +b.dataset.speed; updateStats(); };
  $('run').onclick = () => run(true);
  $('instant').onclick = () => run(false);
  $('clear').onclick = clearSearch;
  $('more').onclick = () => { document.body.classList.toggle('compact'); };

  let down = null, dragged = false, nextIsT = false;
  cv.top.addEventListener('pointerdown', ev => { down = { x: ev.clientX, y: ev.clientY, cx: view.cx, cy: view.cy }; dragged = false; cv.top.setPointerCapture(ev.pointerId); });
  cv.top.addEventListener('pointermove', ev => {
    if (!down) return;
    const dx = ev.clientX - down.x, dy = ev.clientY - down.y;
    if (!dragged && Math.hypot(dx, dy) < 5) return;
    dragged = true;
    view.cx = down.cx - dx / view.scale; view.cy = down.cy + dy / view.scale;
    redrawAll();
  });
  cv.top.addEventListener('pointerup', ev => {
    if (down && !dragged) {
      const x = (ev.clientX - W / 2) / view.scale + view.cx, y = view.cy - (ev.clientY - H / 2) / view.scale;
      const v = nearest(x, y);
      if (ev.shiftKey || nextIsT) { st.t = v; nextIsT = false; run(st.algo !== 'compare'); }
      else { st.s = v; st.t = -1; nextIsT = true; clearSearch(); }
    }
    down = null;
  });
  cv.top.addEventListener('wheel', ev => {
    ev.preventDefault();
    const f = Math.exp(-ev.deltaY * 0.0015);
    const mx = (ev.clientX - W / 2) / view.scale + view.cx, my = view.cy - (ev.clientY - H / 2) / view.scale;
    view.scale *= f;
    view.cx = mx - (ev.clientX - W / 2) / view.scale; view.cy = my + (ev.clientY - H / 2) / view.scale;
    redrawAll();
  }, { passive: false });
  window.addEventListener('keydown', ev => {
    // embedded in the slides: pass the navigation keys on to reveal.js (its postMessage API)
    const nav = { ArrowRight: 'next', PageDown: 'next', ' ': 'next', ArrowLeft: 'prev', PageUp: 'prev' };
    if (nav[ev.key] && window.parent !== window) {
      ev.preventDefault();
      window.parent.postMessage(JSON.stringify({ method: nav[ev.key], args: [] }), '*');
      return;
    }
    if (ev.key === 'r' || ev.key === 'Enter') run(true);
    if (ev.key === '0') { resize(true); redrawAll(); }
  });
  let rt = 0;
  window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { resize(true); redrawAll(); }, 120); });

  // ------------------------------------------------------------ start
  try { await document.fonts.load('13px Lato'); await document.fonts.load('700 13px Lato'); } catch (e) { /* fallback font */ }
  $('loading').remove();
  resize(true);
  drawBase();
  const state = P.get('state') || 'final';
  if (state === 'start') { drawTop(); updateStats(); }
  else run(state === 'anim');
  window.demoReady = true;
})();
