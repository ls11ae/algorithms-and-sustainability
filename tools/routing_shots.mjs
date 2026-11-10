// Static images of the Dortmund routing demo for the PDF version of lecture 5 (and as fallback).
// Usage (after `decker html`, so that public/ has the demo and the fonts):
//   node tools/routing_shots.mjs public lectures/figures
// Needs Playwright with Chromium, and Python with Pillow for the 64-colour palette PNGs.
// Each image is the demo in "legend" mode at the size of the iframe on the slide (680 x 520 CSS
// pixels), rendered at device scale factor 2.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

import { execFileSync } from 'node:child_process';
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

const WIDE = '-8800,-7200,9200,8300';          // TU and the whole Dijkstra search
const ALL = '-9700,-8600,10700,9300';           // the whole network, with all landmarks
const CITY = '-300,-1700,7300,4400';            // Hbf to Phoenix-See
const SHOTS = [
  ['dortmund-fast-quiet', `algo=compare&s=hbf&t=phoenix&view=${CITY}`],
  ['dortmund-dijkstra', `algo=dijkstra&view=${WIDE}`],
  ['dortmund-bidirectional', `algo=bidir&view=${WIDE}`],
  ['dortmund-astar', `algo=astar&view=${WIDE}`],
  ['dortmund-alt', `algo=alt&view=${ALL}`],
  ['dortmund-ch', `algo=ch&view=${WIDE}`],
];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 680, height: 520 }, deviceScaleFactor: 2 });
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
for (const [name, q] of SHOTS) {
  await page.goto(`http://localhost:${port}/static/routing-demo/index.html?ui=legend&${q}`);
  await page.waitForFunction(() => window.demoReady === true, null, { timeout: 60000 });
  await page.waitForTimeout(200);
  const file = path.join(outDir, name + '.png');
  await page.screenshot({ path: file });
  execFileSync('python3', ['-c', 'import sys; from PIL import Image; im = Image.open(sys.argv[1]).convert("RGB"); ' +
    'im.quantize(colors=64, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(sys.argv[1], optimize=True)', file]);
  const legend = await page.$eval('#legend', el => el.innerText.replace(/\s+/g, ' '));
  console.log(name, '|', legend);
}
await browser.close();
server.close();
// the PDF shows A* and ALT side by side
execFileSync('python3', ['-c', 'import sys; from PIL import Image; a, b = (Image.open(f).convert("RGB") for f in sys.argv[1:3]); ' +
  'c = Image.new("RGB", (a.width + b.width + 20, a.height), "white"); c.paste(a, (0, 0)); c.paste(b, (a.width + 20, 0)); ' +
  'c.quantize(colors=64, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(sys.argv[3], optimize=True)',
  path.join(outDir, 'dortmund-astar.png'), path.join(outDir, 'dortmund-alt.png'), path.join(outDir, 'dortmund-astar-alt.png')]);
if (errors.length) { console.error('page errors:', errors); process.exit(1); }
