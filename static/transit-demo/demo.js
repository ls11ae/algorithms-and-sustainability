/* Interactive public transit demo (lectures 6 and 7, Algorithms and Sustainability). Own work, CC BY 4.0.
   URL parameters: algo=csa|raptor  data=<json or json.gz, default example.json>  s=, t= (stop index)
   time=H:MM (departure)  state=start|final  ui=full|compact  speed=<factor>
   The example: real stop names, a simplified network and invented times (tools/make_transit_demo.py). */
(async function () {
  'use strict';
  const T = window.Transit, P = new URLSearchParams(location.search), $ = id => document.getElementById(id);
  const COL = { blue: '#0A97D9', orange: '#E8700A', green: '#3F7E44', red: '#DD1367', ink: '#282a2e', grey: '#8e908c',
                light: '#d9d9d6' };
  const ui = P.get('ui') || 'full';
  if (ui === 'compact') document.body.classList.add('compact');
  const FONT = 'Lato, LatoLatin, Helvetica, Arial, sans-serif';

  async function load(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(url + ': HTTP ' + r.status);
    const buf = new Uint8Array(await r.arrayBuffer());
    if (buf[0] === 0x1f && buf[1] === 0x8b) {
      const s = new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'));
      return JSON.parse(await new Response(s).text());
    }
    return JSON.parse(new TextDecoder().decode(buf));
  }
  let D;
  try { D = await load(P.get('data') || 'example.json'); }
  catch (e) { $('loading').textContent = 'Could not load the timetable (' + e.message + '). Open the page via a web server.'; return; }
  const N = T.prepare(D), S = D.stops.length, small = !!D.small || S <= 40;
  const parseT = s => { const [h, m] = s.split(':').map(Number); return h * 60 + m; };
  const st = {
    algo: P.get('algo') || 'csa',
    s: P.get('s') !== null ? +P.get('s') : D.query.source,
    t: P.get('t') !== null ? +P.get('t') : D.query.target,
    time: P.get('time') ? parseT(P.get('time')) : D.query.time,
    res: null, steps: [], k: 0, anim: false, speed: parseFloat(P.get('speed') || '1'),
  };
  $('attrib').textContent = D.attribution || '';
  if (D.other) {
    const b = $('other'); b.style.display = ''; b.textContent = D.otherLabel || 'other timetable';
    b.onclick = () => { const q = new URLSearchParams(location.search); q.set('data', D.other); q.set('algo', st.algo); q.delete('state'); q.delete('k'); location.search = q.toString(); };
  }
  const name = p => D.stops[p].name, short = p => D.stops[p].short || D.stops[p].name;
  const lineOf = c => D.trips[c.trip].line;
  const dirOf = ri => name(N.routes[ri].stops[N.routes[ri].stops.length - 1]);

  // ------------------------------------------------------------ layout and map transform
  const cv = $('map'), ctx = cv.getContext('2d');
  let W = 0, H = 0, MW = 0, dpr = 1, SW = 380;
  let sx = 1, ox = 0, oy = 0;
  let bx0 = Infinity, by0 = Infinity, bx1 = -Infinity, by1 = -Infinity;
  for (const s of D.stops) { bx0 = Math.min(bx0, s.x); bx1 = Math.max(bx1, s.x); by0 = Math.min(by0, s.y); by1 = Math.max(by1, s.y); }
  for (const l of D.lines || []) for (const [x, y] of l.path) { bx0 = Math.min(bx0, x); bx1 = Math.max(bx1, x); by0 = Math.min(by0, y); by1 = Math.max(by1, y); }
  function resize() {
    dpr = window.devicePixelRatio || 1; W = window.innerWidth; H = window.innerHeight;
    SW = Math.round(Math.min(ui === 'compact' ? 430 : 400, Math.max(300, W * 0.4)));
    MW = W - SW;
    $('side').style.width = SW + 'px';
    cv.style.width = MW + 'px'; cv.style.height = H + 'px';
    cv.width = Math.round(MW * dpr); cv.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const padX = small ? 95 : 30, padT = small ? 70 : 30, padB = small ? 75 : 40;
    sx = Math.min((MW - 2 * padX) / Math.max(1e-9, bx1 - bx0), (H - padT - padB) / Math.max(1e-9, by1 - by0));
    ox = MW / 2 - (bx0 + bx1) / 2 * sx; oy = padT + (H - padT - padB) / 2 + (by0 + by1) / 2 * sx;
  }
  const X = x => ox + x * sx, Y = y => oy - y * sx;

  // ------------------------------------------------------------ running the algorithms
  function compute() {
    if (st.algo === 'csa') {
      const r = T.csa(N, st.s, st.time, st.t, small);
      st.res = r; st.steps = r.trace;
      r.journey = isFinite(r.arr[st.t]) ? T.csaJourney(N, r, st.s, st.t) : null;
    } else {
      const r = T.raptor(N, st.s, st.time, st.t, 8);
      st.res = r; st.steps = [];
      for (const rd of r.rounds) for (const sc of rd.scans) st.steps.push(Object.assign({ k: rd.k }, sc));
      r.journeys = r.pareto.map(p => ({ k: p.k, arr: p.arr, legs: T.raptorJourney(N, r, st.s, st.t, p.k) }));
    }
  }
  // the state after the first k steps: arrival per stop (CSA) or per round (RAPTOR)
  function stateAt(k) {
    const arr = new Float64Array(S).fill(Infinity), when = new Int32Array(S).fill(-1), round = new Int32Array(S).fill(-1);
    arr[st.s] = st.time; round[st.s] = 0;
    for (let i = 0; i < k && i < st.steps.length; i++) {
      for (const [p, a] of st.steps[i].imp || []) if (a < arr[p]) { arr[p] = a; when[p] = i; round[p] = st.steps[i].k || 0; }
    }
    return { arr, when, round };
  }

  // ------------------------------------------------------------ drawing
  function arrow(x0, y0, x1, y1, col, lw) {
    const a = Math.atan2(y1 - y0, x1 - x0), L = Math.hypot(x1 - x0, y1 - y0), r = small ? 15 : 4;
    const ax = x0 + Math.cos(a) * r, ay = y0 + Math.sin(a) * r, bx = x1 - Math.cos(a) * r, by = y1 - Math.sin(a) * r;
    if (L < 2 * r) return;
    ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by);
    ctx.strokeStyle = col; ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.stroke();
    const h = small ? 13 : 6;
    ctx.beginPath(); ctx.moveTo(bx, by);
    ctx.lineTo(bx - h * Math.cos(a - 0.45), by - h * Math.sin(a - 0.45));
    ctx.lineTo(bx - h * Math.cos(a + 0.45), by - h * Math.sin(a + 0.45)); ctx.closePath();
    ctx.fillStyle = col; ctx.fill();
  }
  function text(t, x, y, o) {
    o = o || {};
    ctx.font = `${o.bold ? '700 ' : ''}${o.size || 15}px ${FONT}`;
    ctx.textAlign = o.align || 'center'; ctx.textBaseline = o.base || 'middle';
    if (!o.nohalo) { ctx.lineWidth = 4; ctx.strokeStyle = 'rgba(255,255,255,0.95)'; ctx.lineJoin = 'round'; ctx.strokeText(t, x, y); }
    ctx.fillStyle = o.color || COL.ink; ctx.fillText(t, x, y);
  }
  // label positions for the small example (above or below the stop)
  // name: below / above / lower left; arrival time: right or below the stop
  const labelPos = p => {
    const s = D.stops[p];
    if (s.short === 'CS') return { side: 'below', time: 'right' };
    if (s.short === 'UNI') return { side: 'lowerleft', time: 'right' };
    return { side: 'above', time: 'below' };
  };
  function draw() {
    ctx.clearRect(0, 0, MW, H);
    ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, MW, H);
    const now = stateAt(st.k), cur = st.k > 0 ? st.steps[st.k - 1] : null;
    // lines
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    if (D.lines && D.lines.length) {
      for (const l of D.lines) {
        ctx.beginPath(); l.path.forEach(([x, y], i) => (i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y))));
        ctx.strokeStyle = l.color; ctx.globalAlpha = 0.3; ctx.lineWidth = 9; ctx.stroke(); ctx.globalAlpha = 1;
        if (l.label) text(l.name, X(l.label[0]), Y(l.label[1]), { bold: true, size: 17, color: l.color });
      }
    } else {
      ctx.globalAlpha = 0.18; ctx.lineWidth = 1;
      for (const r of N.routes) {
        ctx.beginPath(); r.stops.forEach((p, i) => (i ? ctx.lineTo(X(D.stops[p].x), Y(D.stops[p].y)) : ctx.moveTo(X(D.stops[p].x), Y(D.stops[p].y))));
        ctx.strokeStyle = r.color || COL.grey; ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    // the journey(s) at the end
    const done = st.k >= st.steps.length && st.steps.length > 0;
    const legsToDraw = [];
    if (done && st.algo === 'csa' && st.res.journey) legsToDraw.push([st.res.journey, COL.ink]);
    if (done && st.algo === 'raptor') st.res.journeys.forEach((j, i) => j.legs && legsToDraw.push([j.legs, i === st.res.journeys.length - 1 ? COL.ink : COL.green]));
    for (const [legs, col] of legsToDraw) for (const L of legs) {
      if (L.walk) continue;
      const tr = D.trips[L.trip], i0 = tr.stops.indexOf(L.from), i1 = tr.stops.lastIndexOf(L.to);
      for (let i = i0; i < i1; i++) {
        const a = D.stops[tr.stops[i]], b = D.stops[tr.stops[i + 1]];
        arrow(X(a.x), Y(a.y), X(b.x), Y(b.y), col, small ? 4.5 : 3);
      }
    }
    // the current step
    if (cur && !done) {
      if (st.algo === 'csa') {
        const c = N.conns[cur.ci], a = D.stops[c.from], b = D.stops[c.to];
        const col = cur.status === 'improves' ? COL.blue : cur.status === 'stop' ? COL.red : cur.status === 'unreachable' || cur.status === 'early' ? '#b9bcc0' : COL.orange;
        arrow(X(a.x), Y(a.y), X(b.x), Y(b.y), col, small ? 6 : 3);
      } else if (!cur.walk) {
        const R = N.routes[cur.route];
        for (let i = cur.from; i + 1 < R.stops.length; i++) {
          const a = D.stops[R.stops[i]], b = D.stops[R.stops[i + 1]];
          arrow(X(a.x), Y(a.y), X(b.x), Y(b.y), COL.orange, small ? 6 : 3);
        }
      }
    }
    // stops
    const tMax = Math.max(st.time + 1, ...Array.from(now.arr).filter(isFinite));
    for (let p = 0; p < S; p++) {
      const s = D.stops[p], x = X(s.x), y = Y(s.y), reached = isFinite(now.arr[p]);
      if (small) {
        ctx.beginPath(); ctx.arc(x, y, 11, 0, 2 * Math.PI);
        ctx.fillStyle = p === st.s || p === st.t ? COL.ink : reached ? '#e7f4fb' : '#ffffff'; ctx.fill();
        ctx.lineWidth = 2.5; ctx.strokeStyle = reached ? COL.blue : COL.ink; if (p === st.s || p === st.t) ctx.strokeStyle = COL.ink; ctx.stroke();
        if (p === st.s || p === st.t) text(p === st.s ? 's' : 't', x, y + 0.5, { bold: true, size: 13, color: '#ffffff', nohalo: true });
        const L = labelPos(p);
        if (L.side === 'above') {
          text(s.name, x, y - 17, { size: 16, base: 'bottom' });
          if (s.change) text(`change ${s.change} min`, x, y - 37, { size: 12, color: COL.grey, base: 'bottom' });
        } else if (L.side === 'below') {
          text(s.name, x, y + 17, { size: 16, base: 'top' });
          if (s.change) text(`change ${s.change} min`, x, y + 37, { size: 12, color: COL.grey, base: 'top' });
        } else {
          text(s.name, x - 14, y + 16, { size: 16, align: 'right', base: 'top' });
          if (s.change) text(`change ${s.change} min`, x - 14, y + 36, { size: 12, color: COL.grey, align: 'right', base: 'top' });
        }
        if (reached) {
          const fresh = cur && now.when[p] === st.k - 1;
          const lbl = st.algo === 'raptor' && now.round[p] > 0 ? `${T.hm(now.arr[p])} (${now.round[p]} trip${now.round[p] > 1 ? 's' : ''})` : T.hm(now.arr[p]);
          if (L.time === 'right') text(lbl, x + 17, y, { bold: true, size: 17, color: fresh ? COL.orange : COL.blue, align: 'left' });
          else text(lbl, x, y + 18, { bold: true, size: 17, color: fresh ? COL.orange : COL.blue, base: 'top' });
        }
      } else {
        let col = '#c9cbce';
        if (reached) { const f = Math.min(1, (now.arr[p] - st.time) / Math.max(30, tMax - st.time)); col = `hsl(${200 - 170 * f}, 75%, ${45 + 10 * f}%)`; }
        ctx.beginPath(); ctx.arc(x, y, reached ? 2.6 : 1.6, 0, 2 * Math.PI); ctx.fillStyle = col; ctx.fill();
      }
    }
    if (!small) for (const p of [st.s, st.t]) if (p >= 0) {
      const x = X(D.stops[p].x), y = Y(D.stops[p].y);
      ctx.beginPath(); ctx.arc(x, y, 7, 0, 2 * Math.PI); ctx.fillStyle = COL.ink; ctx.fill();
      text(name(p), x + 10, y - 12, { bold: true, size: 13, align: 'left' });
    }
  }

  // ------------------------------------------------------------ the list on the right
  const statusText = (e) => {
    const c = N.conns[e.ci];
    if (e.status === 'stop') return 'departs after the arrival at t: stop';
    if (e.status === 'early') return `departs before ${T.hm(st.time)}`;
    if (e.status === 'unreachable') {
      const a = stateAt(st.steps.indexOf(e)).arr[c.from];
      return isFinite(a) ? `not reachable: at ${short(c.from)} ${T.hm(a)} + ${c.from === st.s ? 0 : D.stops[c.from].change} min change` : `not reachable: ${short(c.from)} not reached yet`;
    }
    const how = e.board ? 'board' : 'stay on the trip';
    if (e.status === 'improves') return `${how}; ${short(c.to)}: ${T.hm(c.arr)}`;
    return `${how}; no improvement at ${short(c.to)}`;
  };
  function renderList() {
    const L = $('list'), k = st.k;
    let html = '';
    if (st.algo === 'csa') {
      const tr = st.steps, lo = small ? 0 : Math.max(0, k - 12), hi = small ? tr.length : Math.min(tr.length, k + 18);
      if (lo > 0) html += `<div class="hint" style="padding:2px 10px">… ${lo} connections scanned before</div>`;
      for (let i = lo; i < hi; i++) {
        const e = tr[i], c = N.conns[e.ci], cls = i < k ? (e.status === 'improves' ? 'conn improves' : e.status === 'stop' ? 'conn stop' : 'conn done') : 'conn';
        html += `<div class="${cls}${i === k - 1 ? ' cur' : ''}" id="row${i}"><span>${T.hm(c.dep)}</span><span class="what">${lineOf(c)} ${short(c.from)} → ${short(c.to)}</span><span>${T.hm(c.arr)}</span>` +
                (i < k ? `<span class="st">${statusText(e)}</span>` : '') + '</div>';
      }
    } else {
      let lastK = 0;
      for (let i = 0; i < Math.max(k, small ? st.steps.length : k + 3) && i < st.steps.length; i++) {
        const e = st.steps[i];
        if (e.k !== lastK) { html += `<div class="round">Round ${e.k}: journeys with ${e.k} trip${e.k > 1 ? 's' : ''}</div>`; lastK = e.k; }
        if (i >= k) { html += `<div class="scan hint" id="row${i}">${e.walk ? 'footpaths' : `${N.routes[e.route].line} → ${dirOf(e.route)}, from ${short(N.routes[e.route].stops[e.from])}`}</div>`; continue; }
        const imp = (e.imp || []).map(([p, a]) => `${short(p)} ${T.hm(a)}`).join(', ');
        const board = e.walk ? '' : (e.hops.length ? 'board ' + e.hops.map(h => `${T.hm(h.dep)} at ${short(h.stop)}`).join(', then ') : 'no trip to board');
        html += `<div class="scan${i === k - 1 ? ' cur' : ''}" id="row${i}">${e.walk ? 'footpaths' : `<b>${N.routes[e.route].line}</b> → ${dirOf(e.route)}`}: ${board}` +
                (imp ? `<br><span class="imp">improves ${imp}</span>` : '') + '</div>';
      }
    }
    L.innerHTML = html;
    const row = $('row' + (k - 1));
    if (row) row.scrollIntoView({ block: 'nearest' });
    // status and result
    const nSteps = st.steps.length;
    let s = `<b>${st.algo === 'csa' ? 'Connection Scan' : 'RAPTOR'}</b>: ${name(st.s)} → ${name(st.t)}, depart ${T.hm(st.time)}<br>`;
    s += st.algo === 'csa' ? `connections scanned: <b>${Math.min(k, nSteps)}</b> of ${nSteps}${nSteps && st.steps[nSteps - 1].status === 'stop' ? ' (then stop)' : ''}`
                           : `route scans: <b>${Math.min(k, nSteps)}</b> of ${nSteps}${k ? ` · round ${st.steps[Math.min(k, nSteps) - 1].k}` : ''}`;
    $('status').innerHTML = s;
    const R = $('result');
    const done = k >= nSteps && nSteps > 0;
    R.classList.toggle('on', done);
    if (done) {
      const legTxt = legs => legs.map(l => l.walk ? `walk ${l.dur} min to ${short(l.to)}` : `${D.trips[l.trip].line} ${T.hm(l.dep)} ${short(l.from)} → ${short(l.to)} ${T.hm(l.arr)}`).join('<br>');
      if (st.algo === 'csa') {
        const a = st.res.arr[st.t];
        R.innerHTML = isFinite(a) ? `<b>Earliest arrival at ${name(st.t)}: ${T.hm(a)}</b><br>${legTxt(st.res.journey || [])}` : `<b>${name(st.t)} not reachable</b>`;
      } else {
        R.innerHTML = st.res.journeys.length ? '<b>Pareto set: trips × arrival</b>' + st.res.journeys.map(j =>
          `<br><b>${j.k} trip${j.k > 1 ? 's' : ''}: ${T.hm(j.arr)}</b> <span class="hint">(${(j.legs || []).filter(l => !l.walk).map(l => D.trips[l.trip].line).join(', ')})</span>`).join('') : `<b>${name(st.t)} not reachable</b>`;
      }
    }
    for (const b of document.querySelectorAll('[data-algo]')) b.classList.toggle('on', b.dataset.algo === st.algo);
    $('t').value = st.time; $('time').textContent = T.hm(st.time);
  }
  function redraw() { draw(); renderList(); }

  // ------------------------------------------------------------ interaction
  let timer = 0;
  function stop() { clearTimeout(timer); st.anim = false; $('run').textContent = '▶ Run'; }
  function restart(toEnd) { stop(); compute(); st.k = toEnd ? st.steps.length : 0; redraw(); }
  function stepOnce() { if (st.k < st.steps.length) { st.k++; redraw(); } }
  function run() {
    if (st.anim) { stop(); return; }
    if (st.k >= st.steps.length) st.k = 0;
    st.anim = true; $('run').textContent = '❚❚ Pause';
    const per = small ? (st.algo === 'csa' ? 650 : 1100) / st.speed : 30;
    const batch = small ? 1 : Math.max(1, Math.ceil(st.steps.length / 300));
    const tick = () => {
      st.k = Math.min(st.steps.length, st.k + batch); redraw();
      if (st.k < st.steps.length) timer = setTimeout(tick, per); else stop();
    };
    tick();
  }
  for (const b of document.querySelectorAll('[data-algo]')) b.onclick = () => { st.algo = b.dataset.algo; restart(false); };
  $('step').onclick = () => { stop(); stepOnce(); };
  $('run').onclick = run;
  $('final').onclick = () => { stop(); st.k = st.steps.length; redraw(); };
  $('reset').onclick = () => { stop(); st.k = 0; redraw(); };
  $('t').min = Math.max(0, D.query.time - 50); $('t').max = D.query.time + 70;
  $('t').addEventListener('input', () => { st.time = +$('t').value; restart(false); });
  let nextT = false;
  cv.addEventListener('click', ev => {
    const rect = cv.getBoundingClientRect(), mx = ev.clientX - rect.left, my = ev.clientY - rect.top;
    let best = -1, bd = (small ? 30 : 15) ** 2;
    D.stops.forEach((s, p) => { const d = (X(s.x) - mx) ** 2 + (Y(s.y) - my) ** 2; if (d < bd) { bd = d; best = p; } });
    if (best < 0) return;
    if (ev.shiftKey || nextT) { if (best !== st.s) st.t = best; nextT = false; } else { st.s = best; nextT = true; }
    restart(false);
  });
  window.addEventListener('keydown', ev => {
    const nav = { ArrowRight: 'next', PageDown: 'next', ' ': 'next', ArrowLeft: 'prev', PageUp: 'prev' };
    if (nav[ev.key] && window.parent !== window) {
      ev.preventDefault(); window.parent.postMessage(JSON.stringify({ method: nav[ev.key], args: [] }), '*'); return;
    }
    if (ev.key === 's' || ev.key === 'n') { stop(); stepOnce(); }
    if (ev.key === 'r' || ev.key === 'Enter') run();
  });
  let rt = 0;
  window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { resize(); redraw(); }, 120); });

  try { await document.fonts.load(`15px Lato`); await document.fonts.load(`700 15px Lato`); } catch (e) { /* fallback */ }
  $('loading').remove();
  resize(); compute();
  st.k = (P.get('state') || 'start') === 'final' ? st.steps.length : +(P.get('k') || 0);
  redraw();
  window.demoReady = true;
})();
