// 用法（在 <工程目录> 下执行）:
//   node talking-video-oneshot/scripts/stills_timeline.mjs <timelineSrc> <outDir> <frame,frame,...>
// 例: node …/stills_timeline.mjs projects/demo/timeline.json out/demo/stills 45,300,620
// 只打包一次，对 Main 合成按给定 timeline 出多张 PNG：<outDir>/f<帧号>.png。不修改工程 src/ 与 scripts/。
import path from 'node:path';
import fs from 'node:fs';
import { createRequire } from 'node:module';
// 脚本在 Skill 目录里，依赖要从当前工程（cwd）解析
const req = createRequire(path.resolve('package.json'));
const { bundle } = req('@remotion/bundler');
const { renderStill, selectComposition } = req('@remotion/renderer');
const [timelineSrc, outDir, frames] = process.argv.slice(2);
if (!timelineSrc || !outDir || !frames) { console.error('usage: stills_timeline.mjs <timelineSrc> <outDir> <f1,f2,...>'); process.exit(1); }
fs.mkdirSync(outDir, { recursive: true });
const serveUrl = await bundle({ entryPoint: path.resolve('src/index.ts'), publicDir: path.resolve('public') });
const inputProps = { timelineSrc };
const comp = await selectComposition({ serveUrl, id: 'Main', inputProps });
for (const f of frames.split(',')) {
  const out = path.join(outDir, `f${String(f).padStart(5, '0')}.png`);
  await renderStill({ composition: comp, serveUrl, frame: Number(f), output: out, imageFormat: 'png', inputProps });
  console.log('wrote', out);
}
