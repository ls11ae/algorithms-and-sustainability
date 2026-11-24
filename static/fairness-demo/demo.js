/* Interactive demos for lectures 10 and 11 (fairness), Algorithms and Sustainability. CC BY 4.0.
   URL parameters: mode=cluster|share  ui=full|compact  modes=0 (hide the mode buttons)
   cluster: show=town|kcenter|gonzalez|fairlets|fair  k=<2..5>  radius=1 (individual fairness radii)
   share: rule=prop|water|equal  cap=<kW>  d=<demands, comma-separated>  state=final */
(function () {
  'use strict';
  const F = window.Fair, P = new URLSearchParams(location.search), $ = id => document.getElementById(id);
  const COL = { blue: '#0A97D9', orange: '#E8700A', green: '#3F7E44', red: '#DD1367', purple: '#6250d6', ink: '#282a2e',
                grey: '#8e908c', light: '#d9d9d6' };
  const CL = [COL.green, COL.purple, COL.red, '#1b998b', '#a2672e'];
  const GA = COL.blue, GB = COL.orange;           // the two groups
  const FONT = 'Lato, LatoLatin, Helvetica, Arial, sans-serif';
  const ui = P.get('ui') || 'full';
  if (ui === 'compact') document.body.classList.add('compact');
  if (P.get('modes') === '0') { $('modes').classList.add('hide'); $('modesep').classList.add('hide'); }
  const cv = $('cv'), c = cv.getContext('2d');
  let W = 0, H = 0, TOP = 0, dpr = 1;
  const fs = ui === 'compact' ? 15 : 14;
  function resize() {
    dpr = window.devicePixelRatio || 1; TOP = $('bar').offsetHeight;
    W = window.innerWidth; H = window.innerHeight - TOP;
    cv.style.top = TOP + 'px'; cv.style.width = W + 'px'; cv.style.height = H + 'px';
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); c.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function text(t, x, y, o) {
    o = o || {};
    c.font = `${o.bold ? '700 ' : ''}${o.size || fs}px ${FONT}`;
    c.textAlign = o.align || 'left'; c.textBaseline = o.base || 'middle';
    if (o.halo) { c.lineWidth = 4; c.strokeStyle = 'rgba(255,255,255,0.95)'; c.lineJoin = 'round'; c.strokeText(t, x, y); }
    c.fillStyle = o.color || COL.ink; c.fillText(t, x, y);
  }
  let mode = P.get('mode') || 'cluster', timer = 0;
  const stopTimer = () => { clearInterval(timer); timer = 0; };
  function btn(label, fn, cls) { const b = document.createElement('button'); b.textContent = label; b.onclick = fn; if (cls) b.className = cls; $('ctl').appendChild(b); return b; }
  function sep() { const s = document.createElement('span'); s.className = 'sep'; $('ctl').appendChild(s); }

  // ============================================================ 1) fair clustering in the constructed town
  const K = { pts: F.town(), k: +(P.get('k') || 3), show: P.get('show') || 'kcenter', radius: P.get('radius') === '1', anim: -1, res: null };
  const showBtns = {};
  function clusterCompute() {
    const pts = K.pts, k = K.k;
    if (K.show === 'kcenter') { const o = F.optimalKCenter(pts, k); K.res = { centres: o.cs, asg: F.assign(pts, o.cs), title: `optimal ${k}-center` }; }
    else if (K.show === 'gonzalez') { const g = F.gonzalez(pts, k, 0); K.res = { centres: g, asg: F.assign(pts, g), title: `Gonzalez (farthest first) from family 1`, order: true }; }
    else if (K.show === 'fairlets') {
      const fl = F.fairlets(pts);
      if (!fl) { K.res = { note: 'Fairlets with balance 1 need equally many families in both groups.' }; return; }
      const fc = F.fairletClustering(pts, k, fl);
      K.res = { centres: fc.centres, asg: fc.asg, pairs: fl.pairs, bottleneck: fl.t, title: `fairlets, then the best ${k}-center of the fairlets` };
    } else if (K.show === 'fair') {
      const o = F.optimalFair(pts, k);
      K.res = o ? { centres: o.cs, asg: o.asg, title: `best clustering with balance 1 (exact)` } : { note: 'no clustering with balance 1 (the groups need equal sizes)' };
    } else K.res = { title: 'the town: two groups of families' };
    if (K.res.centres) { K.res.stats = F.clusterStats(pts, K.res.centres, K.res.asg); K.res.r = Math.max(...K.res.stats.map(s => s.radius)); }
  }
  function clusterSetup() {
    for (const [key, label] of [['town', 'town'], ['kcenter', 'optimal k-center'], ['gonzalez', 'Gonzalez'], ['fairlets', 'fairlets'], ['fair', 'fair optimum']])
      showBtns[key] = btn(label, () => { stopTimer(); K.show = key; clusterCompute(); if (key === 'gonzalez') animateGonzalez(); else draw(); });
    sep();
    const lab = document.createElement('span'); lab.className = 'lbl'; lab.textContent = 'k ='; $('ctl').appendChild(lab);
    for (const k of [2, 3, 4]) btn(String(k), () => { K.k = k; clusterCompute(); draw(); }).dataset.k = k;
    sep();
    const rb = btn('neighbourhood radius r(x)', () => { K.radius = !K.radius; rb.classList.toggle('on', K.radius); draw(); }); rb.classList.toggle('on', K.radius);
    btn('reset town', () => { K.pts = F.town(); clusterCompute(); draw(); });
    clusterCompute();
  }
  function animateGonzalez() {
    K.anim = 1; draw();
    timer = setInterval(() => { K.anim++; draw(); if (K.anim >= K.k) { stopTimer(); K.anim = -1; draw(); } }, 1000);
  }
  let geo = null, dragI = -1;
  function drawCluster() {
    const pts = K.pts, pad = 36, x0 = 70, y0 = 20, w = W - x0 - 330, h = H - y0 - 30;
    const sx = Math.min(w / 10, h / 7), X = x => x0 + x * sx, Y = y => y0 + h - y * sx + (h - 7 * sx) * -0.5 * 0;
    geo = { X, Y, sx };
    // grid (km)
    c.strokeStyle = '#eef0f2'; c.lineWidth = 1;
    for (let x = 0; x <= 10; x++) { c.beginPath(); c.moveTo(X(x), Y(0)); c.lineTo(X(x), Y(7)); c.stroke(); }
    for (let y = 0; y <= 7; y++) { c.beginPath(); c.moveTo(X(0), Y(y)); c.lineTo(X(10), Y(y)); c.stroke(); }
    text('1 km', X(0), Y(0) + 14, { size: fs - 2, color: COL.grey });
    const R = K.res || {};
    const kShown = K.anim > 0 ? K.anim : (R.centres ? R.centres.length : 0);
    const centres = R.centres ? R.centres.slice(0, kShown) : [];
    const asg = K.anim > 0 ? F.assign(pts, centres) : R.asg;
    // neighbourhood radii
    if (K.radius) {
      const rr = F.neighbourhoodRadius(pts, K.k);
      pts.forEach((p, i) => {                      // only the families without a school within r(x)
        const ok = !centres.length || Math.min(...centres.map(cc => F.dist(p, pts[cc]))) <= rr[i] + 1e-9;
        if (ok && centres.length) return;
        c.beginPath(); c.arc(X(p.x), Y(p.y), rr[i] * sx, 0, 2 * Math.PI);
        c.strokeStyle = centres.length ? 'rgba(221,19,103,0.7)' : 'rgba(40,42,46,0.18)'; c.lineWidth = centres.length ? 1.8 : 1; c.stroke();
      });
    }
    // cluster radii (around each centre: its farthest member)
    if (centres.length && asg) centres.forEach((cc, k) => {
      const r = Math.max(0, ...pts.map((p, i) => (asg[i] === k ? F.dist(p, pts[cc]) : 0)));
      c.beginPath(); c.arc(X(pts[cc].x), Y(pts[cc].y), r * sx, 0, 2 * Math.PI);
      c.fillStyle = CL[k % CL.length] + '14'; c.fill();
      c.setLineDash([6, 4]); c.strokeStyle = CL[k % CL.length]; c.lineWidth = 1.6; c.stroke(); c.setLineDash([]);
    });
    if (R.pairs && K.anim < 0) for (const [a, b] of R.pairs) { c.beginPath(); c.moveTo(X(pts[a].x), Y(pts[a].y)); c.lineTo(X(pts[b].x), Y(pts[b].y)); c.strokeStyle = '#9a9da1'; c.lineWidth = 1.4; c.stroke(); }
    // families: group A circles, group B triangles; fill = cluster colour
    pts.forEach((p, i) => {
      const x = X(p.x), y = Y(p.y), col = asg && centres.length ? CL[asg[i] % CL.length] : (p.g ? GB : GA);
      c.beginPath();
      if (p.g === 0) c.arc(x, y, 7.5, 0, 2 * Math.PI); else { c.moveTo(x, y - 9); c.lineTo(x + 8.5, y + 6); c.lineTo(x - 8.5, y + 6); c.closePath(); }
      c.fillStyle = col; c.fill(); c.lineWidth = 2.2; c.strokeStyle = p.g ? GB : GA; c.stroke();
    });
    centres.forEach((cc, k) => { const x = X(pts[cc].x), y = Y(pts[cc].y); c.lineWidth = 3; c.strokeStyle = COL.ink; c.strokeRect(x - 12, y - 12, 24, 24); text(String(k + 1), x + 14, y - 14, { bold: true, halo: true }); });
    // side panel
    const px = W - 310;
    let y = 30;
    text(R.title || '', px, y, { bold: true }); y += 26;
    if (R.note) { text(R.note, px, y, { color: COL.red }); }
    text('● group A    ▲ group B    □ school (centre)', px, y, { size: fs - 1, color: COL.grey }); y += 26;
    if (R.stats && K.anim < 0) {
      R.stats.forEach((s, k) => {
        const a = s.members.filter(i => pts[i].g === 0).length, b = s.members.length - a;
        c.fillStyle = CL[k % CL.length]; c.fillRect(px, y - 7, 14, 14);
        text(`school ${k + 1}: ${a} A + ${b} B, balance ${s.balance.toFixed(2)}`, px + 22, y, { size: fs }); y += 24;
      });
      y += 4;
      text(`radius (longest way): ${R.r.toFixed(2)} km`, px, y, { bold: true }); y += 24;
      text(`minimum balance: ${Math.min(...R.stats.map(s => s.balance)).toFixed(2)}`, px, y, { bold: true }); y += 24;
      if (R.bottleneck) { text(`longest fairlet pair: ${R.bottleneck.toFixed(2)} km`, px, y, { size: fs - 1, color: COL.grey }); y += 22; }
      if (K.radius) {
        const rr = F.neighbourhoodRadius(pts, K.k), bad = pts.filter((p, i) => Math.min(...R.centres.map(cc => F.dist(p, pts[cc]))) > rr[i] + 1e-9).length;
        text(`r(x): ${bad} famil${bad === 1 ? 'y has' : 'ies have'} no school within r(x)`, px, y, { size: fs - 1, color: bad ? COL.red : COL.green }); y += 22;
      }
    } else if (K.anim > 0) text(`pick ${K.anim}: the family farthest from all picked schools`, px, y, { size: fs });
    for (const [key, b] of Object.entries(showBtns)) b.classList.toggle('on', key === K.show);
    for (const b of document.querySelectorAll('[data-k]')) b.classList.toggle('on', +b.dataset.k === K.k);
    $('info').innerHTML = 'Drag a family to move it; the clustering is computed again.';
  }

  // ============================================================ 2) sharing a congested connection (lecture 11)
  const S = { cap: +(P.get('cap') || F.WALLBOX.cap), d: P.get('d') ? P.get('d').split(',').map(Number) : F.WALLBOX.demand.slice(),
              names: F.WALLBOX.names.slice(), rule: P.get('rule') || 'water', level: -1 };
  const ruleBtns = {};
  function alloc(rule, d) { return rule === 'prop' ? F.proportional(d, S.cap) : rule === 'equal' ? F.equalSplit(d, S.cap) : F.waterFilling(d, S.cap).x; }
  function shareSetup() {
    for (const [key, label] of [['prop', 'in proportion to demand'], ['water', 'max-min fair (water-filling)'], ['equal', 'equal split']])
      ruleBtns[key] = btn(label, () => { stopTimer(); S.rule = key; S.level = -1; draw(); });
    btn('▶ fill', () => {
      stopTimer(); S.rule = 'water'; S.level = 0;
      const final = F.waterFilling(S.d, S.cap).level;
      timer = setInterval(() => { S.level = Math.min(final, S.level + final / 40); draw(); if (S.level >= final) { stopTimer(); S.level = -1; draw(); } }, 40);
    }, 'run');
    sep();
    const lab = document.createElement('span'); lab.className = 'lbl'; lab.textContent = 'capacity'; $('ctl').appendChild(lab);
    const sl = document.createElement('input'); sl.type = 'range'; sl.min = 10; sl.max = 60; sl.step = 0.5; sl.value = S.cap; $('ctl').appendChild(sl);
    const cl = document.createElement('span'); cl.className = 'lbl'; $('ctl').appendChild(cl);
    const upd = () => { cl.textContent = `${S.cap.toFixed(1)} kW`; };
    sl.oninput = () => { S.cap = +sl.value; upd(); draw(); }; upd();
    btn('reset', () => { S.d = F.WALLBOX.demand.slice(); S.cap = F.WALLBOX.cap; sl.value = S.cap; upd(); draw(); });
  }
  let sgeo = null, dragS = -1;
  function drawShare() {
    const n = S.d.length, x0 = 80, x1 = W - 360, y0 = 30, h = H - y0 - 50;
    const maxD = Math.max(25, ...S.d) * 1.1, Yk = v => y0 + h - (v / maxD) * h, bw = (x1 - x0) / n;
    sgeo = { x0, bw, Yk, maxD, y0, h };
    c.strokeStyle = '#b9bcc0'; c.lineWidth = 1; c.beginPath(); c.moveTo(x0, y0 + h); c.lineTo(x1, y0 + h); c.stroke();
    for (let v = 0; v <= maxD; v += 5) { text(String(v), x0 - 8, Yk(v), { align: 'right', size: fs - 2, color: COL.grey }); c.strokeStyle = '#f0f1f2'; c.beginPath(); c.moveTo(x0, Yk(v)); c.lineTo(x1, Yk(v)); c.stroke(); }
    text('kW', x0 - 8, y0 - 14, { align: 'right', size: fs - 2, color: COL.grey });
    const water = F.waterFilling(S.d, S.cap);
    const x = S.level >= 0 ? S.d.map(d => Math.min(d, S.level)) : alloc(S.rule, S.d);
    S.d.forEach((d, i) => {
      const bx = x0 + i * bw + bw * 0.18, ww = bw * 0.64;
      c.fillStyle = 'rgba(10,151,217,0.85)'; c.fillRect(bx, Yk(x[i]), ww, Yk(0) - Yk(x[i]));
      c.strokeStyle = COL.ink; c.lineWidth = 2; c.setLineDash([5, 3]); c.strokeRect(bx, Yk(d), ww, Yk(0) - Yk(d)); c.setLineDash([]);
      c.fillStyle = COL.ink; c.fillRect(bx + ww / 2 - 10, Yk(d) - 3, 20, 6);              // handle: drag the demand
      text(`${x[i].toFixed(2)}`, bx + ww / 2, Yk(x[i]) + 14, { align: 'center', bold: true, color: '#ffffff' });
      text(`wants ${d.toFixed(1)}`, bx + ww / 2, Yk(d) - 14, { align: 'center', size: fs - 1, halo: true });
      text(`wallbox ${S.names[i]}`, bx + ww / 2, y0 + h + 16, { align: 'center', bold: true });
    });
    if (S.rule === 'water' || S.level >= 0) {
      const L = S.level >= 0 ? S.level : water.level;
      if (L > 0 && L < maxD) { c.beginPath(); c.moveTo(x0, Yk(L)); c.lineTo(x1, Yk(L)); c.strokeStyle = COL.blue; c.lineWidth = 2; c.setLineDash([8, 4]); c.stroke(); c.setLineDash([]);
        text(`water level ${L.toFixed(2)} kW`, x1, Yk(L) - 10, { align: 'right', color: COL.blue, bold: true, halo: true }); }
    }
    // side panel
    const px = W - 330, tot = x.reduce((a, b) => a + b, 0), totD = S.d.reduce((a, b) => a + b, 0);
    let y = 40;
    const names = { prop: 'In proportion to demand', water: 'Max-min fair (water-filling)', equal: 'Equal split' };
    text(names[S.level >= 0 ? 'water' : S.rule], px, y, { bold: true }); y += 28;
    text(`connection: ${S.cap.toFixed(1)} kW, demand ${totD.toFixed(1)} kW`, px, y); y += 24;
    text(`distributed: ${tot.toFixed(1)} kW`, px, y); y += 24;
    text(`Jain's index: ${F.jain(x).toFixed(3)}`, px, y); y += 24;
    text(`smallest share of the own demand: ${Math.min(...x.map((v, i) => v / S.d[i])).toFixed(2)}`, px, y); y += 34;
    text('Drag the black handle of a wallbox:', px, y, { size: fs - 1, color: COL.grey }); y += 20;
    text('who gains by asking for more?', px, y, { size: fs - 1, color: COL.grey });
    for (const [key, b] of Object.entries(ruleBtns)) b.classList.toggle('on', key === S.rule && S.level < 0);
    $('info').innerHTML = S.rule === 'water' ? 'Water-filling: raise one level for everybody; a wallbox gets its demand or the level, whichever is smaller.'
      : S.rule === 'prop' ? 'Proportional: everybody gets the same fraction of the own demand; asking for more always pays off.'
      : 'Equal split: everybody gets capacity / 5 (at most the own demand); unused power is not passed on.';
  }

  // ============================================================ common
  function draw() {
    c.clearRect(0, 0, W, H); c.fillStyle = '#ffffff'; c.fillRect(0, 0, W, H);
    if (mode === 'cluster') drawCluster(); else drawShare();
    for (const b of document.querySelectorAll('[data-mode]')) b.classList.toggle('on', b.dataset.mode === mode);
  }
  function setMode(m) { stopTimer(); mode = m; $('ctl').innerHTML = ''; $('info').innerHTML = ''; if (m === 'cluster') clusterSetup(); else shareSetup(); resize(); draw(); }
  for (const b of document.querySelectorAll('[data-mode]')) b.onclick = () => setMode(b.dataset.mode);
  cv.addEventListener('pointerdown', ev => {
    const r = cv.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top;
    if (mode === 'cluster' && geo) {
      let best = -1, bd = 14 * 14;
      K.pts.forEach((p, i) => { const d = (geo.X(p.x) - mx) ** 2 + (geo.Y(p.y) - my) ** 2; if (d < bd) { bd = d; best = i; } });
      if (best >= 0) { dragI = best; cv.setPointerCapture(ev.pointerId); }
    } else if (mode === 'share' && sgeo) {
      const i = Math.floor((mx - sgeo.x0) / sgeo.bw);
      if (i >= 0 && i < S.d.length && Math.abs(my - sgeo.Yk(S.d[i])) < 16) { dragS = i; cv.setPointerCapture(ev.pointerId); }
    }
  });
  cv.addEventListener('pointermove', ev => {
    const r = cv.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top;
    if (dragI >= 0) {
      const p = K.pts[dragI]; p.x = Math.max(0, Math.min(10, (mx - geo.X(0)) / geo.sx)); p.y = Math.max(0, Math.min(7, (geo.Y(0) - my) / geo.sx));
      clusterCompute(); draw();
    } else if (dragS >= 0) {
      const v = (sgeo.y0 + sgeo.h - my) / sgeo.h * sgeo.maxD;
      S.d[dragS] = Math.max(0.5, Math.min(60, Math.round(v * 10) / 10)); draw();
    }
  });
  cv.addEventListener('pointerup', () => { dragI = -1; dragS = -1; });
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
