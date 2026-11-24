// Static images of the live demos of lectures 6, 7, 9, 10 and 11 for the PDF versions of the slides.
// Usage (after `decker html`, so that public/ has the demos and the fonts):
//   node tools/demo_shots.mjs public lectures/figures
// Needs Playwright with Chromium, and Python with Pillow for the 64-colour palette PNGs. The size of each
// image is the size of the iframe on the slide (1260 x 450 CSS pixels for the full-width demos), rendered
// at device scale factor 2. The routing images of lecture 5 come from tools/routing_shots.mjs.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const [rootDir = 'public', outDir = 'lectures/figures'] = process.argv.slice(2);
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.gz': 'application/gzip', '.json': 'application/json',
                '.css': 'text/css', '.woff2': 'font/woff2', '.ttf': 'font/ttf' };
const server = http.createServer((req, res) => {
  const f = path.join(rootDir, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  fs.readFile(f, (err, data) => {
    if (err) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' });
    res.end(data);
  });
});
await new Promise(r => server.listen(0, r));
const port = server.address().port;
const VIEW = '-1500,-1000,8000,4900';               // Hbf to Phoenix-See with room for the chart
const WIDE = [1260, 450];
const SHOTS = [
  ['dortmund-lambda', `static/routing-demo/index.html?ui=legend&algo=lambda&lam=0.5&s=hbf&t=phoenix&view=${VIEW}`, WIDE],
  ['dortmund-martins', `static/routing-demo/index.html?ui=legend&algo=mcdijkstra&s=hbf&t=phoenix&view=${VIEW}`, WIDE],
  ['transit-csa', 'static/transit-demo/index.html?ui=compact&algo=csa&state=final', WIDE],
  ['transit-raptor', 'static/transit-demo/index.html?ui=compact&algo=raptor&state=final', WIDE],
  ['energy-yds', 'static/energy-demo/index.html?ui=compact&modes=0&mode=yds&avr=1', WIDE],
  ['energy-power', 'static/energy-demo/index.html?ui=compact&modes=0&mode=power&state=final', WIDE],
  ['fair-live', 'static/fairness-demo/index.html?ui=compact&modes=0&mode=cluster&show=fair', WIDE],
  ['share-live', 'static/fairness-demo/index.html?ui=compact&modes=0&mode=share&rule=water', WIDE],
];
const browser = await chromium.launch();
const errors = [];
for (const [name, url, [w, h]] of SHOTS) {
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
  page.on('pageerror', e => errors.push(name + ': ' + String(e)));
  await page.goto(`http://localhost:${port}/${url}`);
  await page.waitForFunction(() => window.demoReady === true, null, { timeout: 90000 });
  await page.waitForTimeout(300);
  const file = path.join(outDir, name + '.png');
  await page.screenshot({ path: file });
  execFileSync('python3', ['-c', 'import sys; from PIL import Image; im = Image.open(sys.argv[1]).convert("RGB"); ' +
    'im.quantize(colors=64, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(sys.argv[1], optimize=True)', file]);
  const info = await page.evaluate(() => { const el = document.getElementById('legend') || document.getElementById('info') || document.getElementById('status');
    return el ? el.innerText.replace(/\s+/g, ' ').slice(0, 160) : ''; });
  console.log(name, '|', info);
  await page.close();
}
await browser.close();
server.close();
if (errors.length) { console.error('page errors:', errors); process.exit(1); }
