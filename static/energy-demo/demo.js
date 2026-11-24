/* Interactive demos for lecture 9 (energy-efficient algorithms), Algorithms and Sustainability. CC BY 4.0.
   URL parameters: mode=mill|yds|power  ui=full|compact  modes=0 (hide the mode buttons)
   mill: start=<hour>  state=final (show the cheapest window and all costs)
   yds: k=<rounds shown> (default: all)  avr=1 (show the online AVR profile)  alpha=2|3
   power: long=<share of long idle periods, 0..1>  n=<periods>  beta=<wake-up energy, J>  state=final */
(function () {
  'use strict';
  const E = window.Energy, P = new URLSearchParams(location.search), $ = id => document.getElementById(id);
  const COL = { blue: '#0A97D9', orange: '#E8700A', green: '#3F7E44', red: '#DD1367', purple: '#6250d6', ink: '#282a2e',
                grey: '#8e908c', light: '#d9d9d6', sun: '#F2B705', paleSun: '#FBE7A1' };
  const JOBCOL = [COL.blue, COL.orange, COL.green, COL.purple, COL.red, '#1b998b', '#a2672e', '#5c6f8a'];
  const FONT = 'Lato, LatoLatin, Helvetica, Arial, sans-serif';
  const ui = P.get('ui') || 'full';
  if (ui === 'compact') document.body.classList.add('compact');
  if (P.get('modes') === '0') { $('modes').classList.add('hide'); $('modesep').classList.add('hide'); }
  const cv = $('cv'), c = cv.getContext('2d');
  let W = 0, H = 0, TOP = 0, dpr = 1;
  const fs = ui === 'compact' ? 15 : 14;
  function resize() {
    dpr = window.devicePixelRatio || 1;
    TOP = $('bar').offsetHeight;
    W = window.innerWidth; H = window.innerHeight - TOP;
    cv.style.top = TOP + 'px'; cv.style.width = W + 'px'; cv.style.height = H + 'px';
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function text(t, x, y, o) {
    o = o || {};
    c.font = `${o.bold ? '700 ' : ''}${o.size || fs}px ${FONT}`;
    c.textAlign = o.align || 'left'; c.textBaseline = o.base || 'middle';
    if (o.halo) { c.lineWidth = 4; c.strokeStyle = 'rgba(255,255,255,0.95)'; c.lineJoin = 'round'; c.strokeText(t, x, y); }
    c.fillStyle = o.color || COL.ink; c.fillText(t, x, y);
  }
  function axisLine(x0, y0, x1, y1) { c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1, y1); c.strokeStyle = '#b9bcc0'; c.lineWidth = 1; c.stroke(); }
  const euro = x => '€' + x.toFixed(2);
  const fr = f => (f.d === 1 ? String(f.n) : `${f.n}/${f.d}`);
  let mode = P.get('mode') || 'mill', timer = 0;
  const stopTimer = () => { clearInterval(timer); timer = 0; };
  function btn(label, fn, cls) { const b = document.createElement('button'); b.textContent = label; b.onclick = fn; if (cls) b.className = cls; $('ctl').appendChild(b); return b; }
  function sep() { const s = document.createElement('span'); s.className = 'sep'; $('ctl').appendChild(s); }

  // ============================================================ 1) the feed mill
  const F = E.farm();
  const mill = { start: P.get('start') !== null ? +P.get('start') : 8, tried: new Map(), best: -1 };
  const millStarts = []; for (let s = F.window[0]; s <= F.window[1] - F.hours; s++) millStarts.push(s);
  function millSetup() {
    btn('▶ Try all windows', () => {
      stopTimer(); mill.tried.clear(); mill.best = -1; let i = 0;
      timer = setInterval(() => {
        if (i >= millStarts.length) { stopTimer(); mill.best = bestStart(); mill.start = mill.best; draw(); return; }
        mill.start = millStarts[i++]; mill.tried.set(mill.start, E.millCost(F, mill.start).cost); draw();
      }, 420);
    }, 'run');
    btn('Cheapest', () => { stopTimer(); for (const s of millStarts) mill.tried.set(s, E.millCost(F, s).cost); mill.best = bestStart(); mill.start = mill.best; draw(); });
    btn('Reset', () => { stopTimer(); mill.tried.clear(); mill.best = -1; mill.start = 8; draw(); });
    if (P.get('state') === 'final') { for (const s of millStarts) mill.tried.set(s, E.millCost(F, s).cost); mill.best = bestStart(); mill.start = mill.best; }
    else mill.tried.set(mill.start, E.millCost(F, mill.start).cost);
  }
  const bestStart = () => millStarts.reduce((b, s) => (E.millCost(F, s).cost < E.millCost(F, b).cost ? s : b), millStarts[0]);
  let millGeo = null;
  function drawMill() {
    const L = 58, R = 58, T = 34, h1 = Math.round(H * 0.56), x0 = L, x1 = W - R;
    const X = h => x0 + (h / 24) * (x1 - x0), YK = kw => T + h1 - (kw / 80) * h1, YP = ct => T + h1 - (ct / 50) * h1;
    millGeo = { X, YK, x0, x1, T, h1 };
    // axes
    axisLine(x0, T + h1, x1, T + h1); axisLine(x0, T, x0, T + h1); axisLine(x1, T, x1, T + h1);
    for (let h = 0; h <= 24; h += 3) text(`${h}:00`, X(h), T + h1 + 12, { align: 'center', color: COL.grey, size: fs - 1 });
    for (let kw = 0; kw <= 80; kw += 20) { text(String(kw), x0 - 6, YK(kw), { align: 'right', color: COL.grey, size: fs - 1 }); }
    for (let ct = 0; ct <= 50; ct += 10) { text(String(ct), x1 + 6, YP(ct), { color: COL.grey, size: fs - 1 }); }
    text('kW', x0 - 6, T - 14, { align: 'right', color: COL.grey, size: fs - 1 });
    text('ct/kWh', x1 + 6, T - 14, { color: COL.grey, size: fs - 1 });
    // PV surplus (bars) and the mill block
    for (let h = 0; h < 24; h++) {
      if (F.surplus[h] <= 0) continue;
      c.fillStyle = COL.paleSun; c.fillRect(X(h) + 1, YK(F.surplus[h]), X(h + 1) - X(h) - 2, YK(0) - YK(F.surplus[h]));
    }
    const s = mill.start;
    for (let h = s; h < s + F.hours; h++) {
      const own = Math.min(F.kw, F.surplus[h]);
      c.fillStyle = 'rgba(242, 183, 5, 0.85)'; c.fillRect(X(h) + 1, YK(own), X(h + 1) - X(h) - 2, YK(0) - YK(own));
      if (own < F.kw) { c.fillStyle = 'rgba(221, 19, 103, 0.55)'; c.fillRect(X(h) + 1, YK(F.kw), X(h + 1) - X(h) - 2, YK(own) - YK(F.kw)); }
    }
    c.strokeStyle = COL.orange; c.lineWidth = 3; c.strokeRect(X(s), YK(F.kw), X(s + F.hours) - X(s), YK(0) - YK(F.kw));
    text('feed mill 50 kW · 3 h  ↔ drag', X(s + F.hours / 2), YK(F.kw) - 12, { align: 'center', bold: true, color: COL.orange, halo: true });
    // prices
    c.beginPath(); for (let h = 0; h < 24; h++) (h ? c.lineTo : c.moveTo).call(c, X(h + 0.5), YP(F.buy[h]));
    c.strokeStyle = COL.red; c.lineWidth = 2.6; c.stroke();
    for (let h = 0; h < 24; h++) { c.beginPath(); c.arc(X(h + 0.5), YP(F.buy[h]), 2.6, 0, 2 * Math.PI); c.fillStyle = COL.red; c.fill(); }
    c.beginPath(); c.moveTo(X(0), YP(7)); c.lineTo(X(24), YP(7)); c.setLineDash([6, 4]); c.strokeStyle = COL.green; c.lineWidth = 2; c.stroke(); c.setLineDash([]);
    text('buy', X(23.9), YP(F.buy[23]) - 12, { align: 'right', color: COL.red, bold: true, halo: true });
    text('sell (feed-in) 7 ct', X(23.9), YP(7) - 11, { align: 'right', color: COL.green, bold: true, halo: true });
    text('PV surplus', X(16.5), YK(F.surplus[16]) - 12, { align: 'center', color: '#a07800', bold: true, halo: true });
    c.fillStyle = 'rgba(242, 183, 5, 0.85)'; c.fillRect(x0 + 12, T + 6, 14, 12); text('own solar power', x0 + 32, T + 12, { size: fs - 1 });
    c.fillStyle = 'rgba(221, 19, 103, 0.55)'; c.fillRect(x0 + 12, T + 26, 14, 12); text('bought from the grid', x0 + 32, T + 32, { size: fs - 1 });
    // cost bars by start hour
    const b0 = T + h1 + 44, bh = H - b0 - 34;
    const maxC = 55, Yc = v => b0 + bh - (v / maxC) * bh;
    axisLine(x0, b0 + bh, x1, b0 + bh);
    text('cost by start hour', x0, b0 - 8, { color: COL.grey, size: fs - 1 });
    for (const st of millStarts) {
      const v = mill.tried.get(st);
      const bx = X(st) + 3, bw = X(st + 1) - X(st) - 6;
      if (v === undefined) { c.strokeStyle = '#e1e3e5'; c.strokeRect(bx, b0 + bh - 2, bw, 2); continue; }
      c.fillStyle = st === mill.best ? COL.green : st === mill.start ? COL.orange : '#c4c7cb';
      c.fillRect(bx, Yc(v), bw, b0 + bh - Yc(v));
      text(v.toFixed(2), bx + bw / 2, Yc(v) - 9, { align: 'center', size: fs - 3, color: st === mill.best ? COL.green : COL.ink });
    }
    for (const st of millStarts) text(`${st}`, X(st + 0.5), b0 + bh + 11, { align: 'center', size: fs - 2, color: COL.grey });
    const m = E.millCost(F, s);
    $('info').innerHTML = `<b>${s}:00–${s + F.hours}:00</b>: own solar ${m.own.toFixed(0)} kWh (lost feed-in ${euro(m.ownC)}) + grid ${m.grid.toFixed(0)} kWh (${euro(m.gridC)}) = <b>${euro(m.cost)}</b>` +
                       (mill.best >= 0 ? ` · cheapest: <b style="color:${COL.green}">${mill.best}:00</b>` : '');
  }
  function millDrag(ev, kind) {
    if (!millGeo) return;
    const r = cv.getBoundingClientRect(), mx = ev.clientX - r.left;
    const h = (mx - millGeo.x0) / (millGeo.x1 - millGeo.x0) * 24;
    const s = Math.max(F.window[0], Math.min(F.window[1] - F.hours, Math.round(h - F.hours / 2)));
    if (s !== mill.start || kind === 'down') { stopTimer(); mill.start = s; mill.tried.set(s, E.millCost(F, s).cost); draw(); }
  }

  // ============================================================ 2) YDS
  const defJobs = [{ name: 'J1', r: 0, d: 8, w: 4 }, { name: 'J2', r: 2, d: 6, w: 6 }, { name: 'J3', r: 5, d: 10, w: 3 }, { name: 'J4', r: 9, d: 12, w: 2 }];
  const Y = { jobs: defJobs.map(j => Object.assign({}, j)), T: 12, k: -1, avr: P.get('avr') === '1', alpha: +(P.get('alpha') || 3), rounds: [], pieces: [] };
  function ydsCompute() { Y.rounds = E.yds(Y.jobs); Y.pieces = E.edfPieces(Y.rounds, Y.jobs); if (Y.k < 0 || Y.k > Y.rounds.length) Y.k = Y.rounds.length; }
  function ydsSetup() {
    btn('Step', () => { stopTimer(); Y.k = Math.min(Y.rounds.length, Y.k + 1); draw(); });
    btn('▶ Run', () => { stopTimer(); Y.k = 0; draw(); timer = setInterval(() => { Y.k++; draw(); if (Y.k >= Y.rounds.length) stopTimer(); }, 1300); }, 'run');
    btn('Reset', () => { stopTimer(); Y.k = 0; draw(); });
    sep();
    const a = btn('online: AVR', () => { Y.avr = !Y.avr; a.classList.toggle('on', Y.avr); draw(); }); a.classList.toggle('on', Y.avr);
    btn('random jobs', () => {
      stopTimer();
      let x = Date.now() % 100000 + 7;
      const rnd = n => { x = (x * 48271) % 2147483647; return x % n; };
      Y.jobs = [];
      for (let i = 0; i < 5; i++) { const r = rnd(9), d = Math.min(12, r + 2 + rnd(6)); Y.jobs.push({ name: 'J' + (i + 1), r, d, w: 1 + rnd(6) }); }
      Y.k = -1; ydsCompute(); draw();
    });
    btn('example', () => { stopTimer(); Y.jobs = defJobs.map(j => Object.assign({}, j)); Y.k = -1; ydsCompute(); draw(); });
    ydsCompute();
    if (P.get('k') !== null) Y.k = Math.min(Y.rounds.length, +P.get('k'));
  }
  let ydsGeo = null, drag = null;
  function drawYds() {
    const L = 70, R = 30, T = 26, n = Y.jobs.length, rowH = Math.min(36, (H * 0.48) / n), top1 = T;
    const x0 = L, x1 = W - R, X = t => x0 + (t / Y.T) * (x1 - x0);
    const k = Y.k, cur = k > 0 ? Y.rounds[k - 1] : null;
    // current interval
    if (cur) { const [a, b] = cur.interval; c.fillStyle = 'rgba(232, 112, 10, 0.10)'; c.fillRect(X(a), top1 - 8, X(b) - X(a), n * rowH + 8); }
    const doneJobs = new Set(Y.rounds.slice(0, k).flatMap(r => r.jobs)), curJobs = new Set(cur ? cur.jobs : []);
    Y.jobs.forEach((j, i) => {
      const y = top1 + i * rowH, col = JOBCOL[i % JOBCOL.length], h = rowH * 0.62;
      const fill = curJobs.has(i) ? col : doneJobs.has(i) ? '#e4e5e7' : '#ffffff';
      c.fillStyle = fill; c.fillRect(X(j.r), y, X(j.d) - X(j.r), h);
      c.strokeStyle = col; c.lineWidth = 2.2; c.strokeRect(X(j.r), y, X(j.d) - X(j.r), h);
      text(`${j.name}: work ${j.w}`, X(j.r) + 6, y + h / 2, { bold: true, color: curJobs.has(i) ? '#ffffff' : doneJobs.has(i) ? COL.grey : COL.ink, size: fs - 1 });
      text(j.name, x0 - 10, y + h / 2, { align: 'right', color: col, bold: true });
    });
    // speed profile
    const b0 = top1 + n * rowH + 30, bh = H - b0 - 40;
    const maxS = Math.max(1.6, ...Y.rounds.map(r => r.speed.v), ...(Y.avr ? E.avr(Y.jobs).map(s => s.s) : [0])) * 1.12;
    const YS = s => b0 + bh - (s / maxS) * bh;
    axisLine(x0, b0 + bh, x1, b0 + bh); axisLine(x0, b0, x0, b0 + bh);
    for (let t = 0; t <= Y.T; t += 2) text(String(t), X(t), b0 + bh + 12, { align: 'center', color: COL.grey, size: fs - 1 });
    text('time', x0, b0 + bh + 28, { color: COL.grey, size: fs - 1 });
    text('speed', x0 - 10, b0 + 6, { align: 'right', color: COL.grey, size: fs - 1 });
    for (let s = 0.5; s < maxS; s += 0.5) text(s % 1 ? '' : String(s), x0 - 6, YS(s), { align: 'right', color: COL.grey, size: fs - 2 });
    for (const p of Y.pieces) {
      if (p.round >= k) continue;
      c.globalAlpha = p.round === k - 1 ? 0.95 : 0.55;
      c.fillStyle = JOBCOL[p.job % JOBCOL.length]; c.fillRect(X(p.a), YS(p.s), X(p.b) - X(p.a), YS(0) - YS(p.s));
      c.globalAlpha = 1; c.strokeStyle = '#ffffff'; c.lineWidth = 1.5; c.strokeRect(X(p.a), YS(p.s), X(p.b) - X(p.a), YS(0) - YS(p.s));
    }
    Y.rounds.slice(0, k).forEach(rd => { for (const [a, b] of rd.parts) text(fr(rd.speed), X((a + b) / 2), YS(rd.speed.v) - 11, { align: 'center', bold: true, size: fs + 1 }); });
    if (Y.avr) {
      const segs = E.avr(Y.jobs);
      c.beginPath(); let last = null;
      for (const sg of segs) { if (!last || last.b !== sg.a) c.moveTo(X(sg.a), YS(0)); c.lineTo(X(sg.a), YS(sg.s)); c.lineTo(X(sg.b), YS(sg.s)); last = sg; }
      if (last) c.lineTo(X(last.b), YS(0));
      c.strokeStyle = COL.ink; c.lineWidth = 2; c.setLineDash([6, 4]); c.stroke(); c.setLineDash([]);
      text('AVR (online)', X(segs.length ? segs[0].a : 0) + 4, YS(segs.length ? segs[0].s : 0) - 10, { size: fs - 1, halo: true });
    }
    ydsGeo = { X, x0, x1, top1, rowH, n };
    const Eyds = E.energyOf(Y.pieces, Y.alpha), Eavr = E.avr(Y.jobs).reduce((s, g) => s + (g.b - g.a) * Math.pow(g.s, Y.alpha), 0);
    let msg;
    if (k === 0) msg = 'Step: find the interval with the highest density (work inside / free length)';
    else if (cur) msg = `round ${k}: [${cur.interval[0]}, ${cur.interval[1]}], ${cur.jobs.map(j => Y.jobs[j].name).join(', ')}: work ${cur.jobs.reduce((s, j) => s + Y.jobs[j].w, 0)} / free length ${cur.parts.reduce((s, [a, b]) => s + b - a, 0)} = speed <b>${fr(cur.speed)}</b>`;
    if (k >= Y.rounds.length) msg = (msg ? msg + ' · ' : '') + `energy ∑ s<sup>${Y.alpha}</sup>·Δt: <b>YDS ${Eyds.toFixed(2)}</b>` + (Y.avr ? `, AVR ${Eavr.toFixed(2)} (×${(Eavr / Eyds).toFixed(2)})` : '');
    $('info').innerHTML = msg + (k < Y.rounds.length ? '' : ' · drag the ends of the jobs');
  }
  function ydsHit(mx, my) {
    if (!ydsGeo) return null;
    const { X, top1, rowH, n } = ydsGeo;
    const i = Math.floor((my - top1) / rowH);
    if (i < 0 || i >= n) return null;
    const j = Y.jobs[i], dl = Math.abs(mx - X(j.r)), dr = Math.abs(mx - X(j.d));
    if (Math.min(dl, dr) < 12) return { i, end: dl < dr ? 'r' : 'd' };
    if (mx > X(j.r) && mx < X(j.d)) return { i, end: 'move', off: mx };
    return null;
  }
  function ydsDrag(mx) {
    const { x0, x1 } = ydsGeo, t = Math.round((mx - x0) / (x1 - x0) * Y.T), j = Y.jobs[drag.i];
    if (drag.end === 'r') j.r = Math.max(0, Math.min(j.d - 1, t));
    else if (drag.end === 'd') j.d = Math.min(Y.T, Math.max(j.r + 1, t));
    else { const dt = Math.round((mx - drag.off) / (x1 - x0) * Y.T); if (dt) { const len = j.d - j.r; j.r = Math.max(0, Math.min(Y.T - len, j.r + dt)); j.d = j.r + len; drag.off += dt / Y.T * (x1 - x0); } }
    Y.k = -1; ydsCompute(); draw();
  }

  // ============================================================ 3) power-down = ski rental
  const PW = { beta: +(P.get('beta') || 10), long: P.get('long') !== null ? +P.get('long') : 0.3, n: +(P.get('n') || 60), seed: 7, k: 0, adversary: false, L: [] };
  const STRATS = [['opt', 'offline optimum', COL.green], ['never', 'never sleep', COL.grey], ['always', 'sleep at once', COL.purple],
                  ['breakeven', 'sleep after β (2-competitive)', COL.blue], ['random', 'randomised (e/(e−1) ≈ 1.58)', COL.orange]];
  function pwGen() { PW.L = PW.adversary ? Array(PW.n).fill(PW.beta * 1.001) : E.idlePeriods(PW.n, PW.long, PW.seed); }
  function pwSetup() {
    btn('Step', () => { stopTimer(); PW.k = Math.min(PW.n, PW.k + 1); draw(); });
    btn('▶ Run', () => { stopTimer(); if (PW.k >= PW.n) PW.k = 0; timer = setInterval(() => { PW.k++; draw(); if (PW.k >= PW.n) stopTimer(); }, 110); }, 'run');
    btn('Result', () => { stopTimer(); PW.k = PW.n; draw(); });
    btn('Reset', () => { stopTimer(); PW.k = 0; draw(); });
    sep();
    const lab = document.createElement('span'); lab.className = 'lbl'; lab.textContent = 'long idle periods'; $('ctl').appendChild(lab);
    const sl = document.createElement('input'); sl.type = 'range'; sl.min = 0; sl.max = 1; sl.step = 0.05; sl.value = PW.long; $('ctl').appendChild(sl);
    sl.oninput = () => { PW.long = +sl.value; PW.adversary = false; adv.classList.remove('on'); pwGen(); draw(); };
    const adv = btn('adversary', () => { PW.adversary = !PW.adversary; adv.classList.toggle('on', PW.adversary); pwGen(); PW.k = PW.n; draw(); });
    pwGen();
    PW.k = P.get('state') === 'final' ? PW.n : 0;
  }
  function drawPower() {
    const L = 40, R = 30, T = 30, x0 = L, x1 = W - R, beta = PW.beta;
    // the idle periods as bars (capped at 4 beta)
    const h1 = Math.round(H * 0.36), cap = 4 * beta;
    const bw = (x1 - x0) / PW.n, Yl = v => T + h1 - (Math.min(v, cap) / cap) * h1;
    axisLine(x0, T + h1, x1, T + h1);
    c.beginPath(); c.moveTo(x0, Yl(beta)); c.lineTo(x1, Yl(beta)); c.setLineDash([5, 4]); c.strokeStyle = COL.blue; c.lineWidth = 1.5; c.stroke(); c.setLineDash([]);
    text('β: break-even (idle energy = wake-up energy)', x1, Yl(beta) - 10, { align: 'right', color: COL.blue, size: fs - 2, halo: true });
    text('idle periods (length, s)', x0, T - 14, { color: COL.grey, size: fs - 1 });
    for (let i = 0; i < PW.n; i++) {
      const v = PW.L[i], done = i < PW.k;
      c.fillStyle = done ? (v > beta ? '#9ec9e3' : '#c4c7cb') : '#eceeef';
      c.fillRect(x0 + i * bw + 1, Yl(v), Math.max(1, bw - 2), T + h1 - Yl(v));
      if (v > cap) text('↑', x0 + (i + 0.5) * bw, T + 6, { align: 'center', size: fs - 3, color: COL.grey });
    }
    if (PW.k > 0 && PW.k <= PW.n) { const i = PW.k - 1; c.strokeStyle = COL.orange; c.lineWidth = 2; c.strokeRect(x0 + i * bw + 0.5, Yl(PW.L[i]) - 1, bw - 1, T + h1 - Yl(PW.L[i]) + 1); }
    // totals
    const tot = {}; for (const [k] of STRATS) tot[k] = 0;
    for (let i = 0; i < PW.k; i++) for (const [k] of STRATS) tot[k] += E.PD[k](PW.L[i], beta);
    const b0 = T + h1 + 40, rowH = Math.min(40, (H - b0 - 20) / STRATS.length), maxT = Math.max(1, ...Object.values(tot));
    const lw = 250, bx0 = x0 + lw, bx1 = x1 - 120;
    text(`energy after ${PW.k} of ${PW.n} idle periods (idle 1 W, sleep 0 W, wake-up β = ${beta} J)`, x0, b0 - 14, { color: COL.grey, size: fs - 1 });
    STRATS.forEach(([k, name, col], i) => {
      const y = b0 + i * rowH, v = tot[k], w = (v / maxT) * (bx1 - bx0);
      text(name, bx0 - 10, y + rowH * 0.4, { align: 'right', bold: k === 'opt' });
      c.fillStyle = col; c.fillRect(bx0, y + rowH * 0.12, w, rowH * 0.56);
      const ratio = tot.opt > 0 ? v / tot.opt : 0;
      text(`${v.toFixed(0)} J` + (k !== 'opt' && tot.opt > 0 ? `  (×${ratio.toFixed(2)})` : ''), bx0 + w + 8, y + rowH * 0.4, { size: fs - 1 });
    });
    const cur = PW.k > 0 ? PW.L[PW.k - 1] : null;
    $('info').innerHTML = cur === null ? 'Step: the next idle period; nobody knows its length in advance (except the offline optimum)'
      : `idle period ${PW.k}: <b>${cur.toFixed(1)} s</b> ` + (cur > beta ? `(longer than β = ${beta} s: sleeping would have paid off)` : `(shorter than β: stay awake)`);
  }

  // ============================================================ common
  function draw() {
    c.clearRect(0, 0, W, H); c.fillStyle = '#ffffff'; c.fillRect(0, 0, W, H);
    if (mode === 'mill') drawMill(); else if (mode === 'yds') drawYds(); else drawPower();
    for (const b of document.querySelectorAll('[data-mode]')) b.classList.toggle('on', b.dataset.mode === mode);
  }
  function setMode(m) {
    stopTimer(); mode = m; $('ctl').innerHTML = ''; $('info').innerHTML = '';
    if (m === 'mill') millSetup(); else if (m === 'yds') ydsSetup(); else pwSetup();
    resize(); draw();
  }
  for (const b of document.querySelectorAll('[data-mode]')) b.onclick = () => setMode(b.dataset.mode);
  cv.addEventListener('pointerdown', ev => {
    const r = cv.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top;
    if (mode === 'mill') { drag = { mill: true }; millDrag(ev, 'down'); cv.setPointerCapture(ev.pointerId); }
    else if (mode === 'yds') { const h = ydsHit(mx, my); if (h) { stopTimer(); drag = h; cv.setPointerCapture(ev.pointerId); } }
  });
  cv.addEventListener('pointermove', ev => {
    if (!drag) return;
    const r = cv.getBoundingClientRect();
    if (drag.mill) millDrag(ev, 'move'); else ydsDrag(ev.clientX - r.left);
  });
  cv.addEventListener('pointerup', () => { drag = null; });
  window.addEventListener('keydown', ev => {
    const nav = { ArrowRight: 'next', PageDown: 'next', ' ': 'next', ArrowLeft: 'prev', PageUp: 'prev' };
    if (nav[ev.key] && window.parent !== window) { ev.preventDefault(); window.parent.postMessage(JSON.stringify({ method: nav[ev.key], args: [] }), '*'); }
  });
  let rt = 0;
  window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { resize(); draw(); }, 120); });
  (async () => {
    try { await document.fonts.load(`${fs}px Lato`); await document.fonts.load(`700 ${fs}px Lato`); } catch (e) { /* fallback */ }
    setMode(mode);
    window.demoReady = true;
  })();
})();
