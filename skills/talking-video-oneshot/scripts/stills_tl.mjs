// usage: node scripts/stills_tl.mjs <outDir> <timelineSrc (relative to public/)> <name:frame> [name:frame ...]  -> outDir/<name>.png  (Main composition, bundles once)
import { bundle } from '@remotion/bundler';
import { openBrowser, renderStill, selectComposition } from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';
const [outDir, timelineSrc, ...specs] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const serveUrl = await bundle({ entryPoint: path.resolve('src/index.ts'), publicDir: path.resolve('public') });
const inputProps = { timelineSrc };
const puppeteerInstance = await openBrowser('chrome'); // one browser for all stills: its HTTP cache keeps the ~180 Google Font files after the first load
let comp;
for (let attempt = 1; attempt <= 5 && !comp; attempt++) {
  try { comp = await selectComposition({ serveUrl, id: 'Main', inputProps, puppeteerInstance, timeoutInMilliseconds: 240000 }); }
  catch (e) { console.log('retry selectComposition', attempt, String(e.message).slice(0, 120)); if (attempt === 5) throw e; }
}
for (const sp of specs) {
  const [name, f] = sp.split(':');
  for (let attempt = 1; attempt <= 4; attempt++) { // Google Fonts fetches are occasionally slow -> retry
    try {
      await renderStill({ composition: comp, serveUrl, frame: Number(f), inputProps, output: path.join(outDir, `${name}.png`), imageFormat: 'png', puppeteerInstance, timeoutInMilliseconds: 240000 });
      console.log('done', name); break;
    } catch (e) { console.log('retry', name, attempt, String(e.message).slice(0, 120)); if (attempt === 4) throw e; }
  }
}
await puppeteerInstance.close({ silent: true });
