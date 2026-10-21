/**
 * Video2 — typing registry (v2). Every on-screen "typing / input / writing" is a block (start frame, text, frames per character); the
 * shots draw `typedAt(block, f)` + a Caret, and make_sfx.py turns every character into one key sound (space / comma -> low thunk,
 * '\n' -> enter, end of block -> soft ding). Frames per character >= 2, and blocks are chained on ONE lane (a block starts no earlier than
 * 2 frames after the previous one ends), so key sounds are never closer than 2 frames and the per-block counts can be checked 1:1.
 * All desired starts come from the voice timeline (timeline.ts), nothing is hard-coded.
 */
import { at, atEnd, shot } from './timeline';

export type TypeBlock = { id: string; start: number; text: string; fpc: number; end: number; units: string[] };
/** typing units: one Han / punctuation / space / '\n' / Latin letter each (a key per unit) */
export const unitsOf = (text: string) => Array.from(text);
const MIN_FPC = 2, GAP = 2;
type Want = { id: string; want: number; text: string; fpc?: number; until?: number };

export const TYPE_TEXT = {
  m1: '帮我把这周的数据，做成周报', m2: '好，我们从头到尾一步步来：', m3: '第3步换成折线图', m4: '改好了，周报已生成',
  m5: '把刚才这整个过程，沉淀成一个 Skill',
  tab0: '收集数据\n做图表\n导出', tab1: '日期先统一\n别用饼图\n先写数字', tab2: '周报模板\n数据表\n配色',
  say: '做一下这周的周报', last: '最后一步', rule: '新格式先转换', model: '模型能力',
};
const wants = (): Want[] => {
  const s4 = shot(4);
  const r0 = at(4, '从头到尾');
  const rEnd = atEnd(4, '干一遍') - 10;
  const row2 = Math.round(r0 + 4 + ((rEnd - (r0 + 4)) * 2) / 4);
  return [
    { id: 'm1', want: s4.from + 8, text: TYPE_TEXT.m1 },
    { id: 'm2', want: at(4, '别想太多') + 2, text: TYPE_TEXT.m2 },
    { id: 'm3', want: row2 + 6, text: TYPE_TEXT.m3 },
    { id: 'm4', want: atEnd(4, '干一遍') - 6, text: TYPE_TEXT.m4 },
    { id: 'm5', want: at(5, '直接跟它说') + 4, text: TYPE_TEXT.m5, until: at(5, '沉淀成一个') - 2 },
    { id: 'tab0', want: at(5, 'Skill') + 14, text: TYPE_TEXT.tab0 },
    { id: 'tab1', want: at(5, '踩的坑'), text: TYPE_TEXT.tab1 },
    { id: 'tab2', want: at(5, '素材'), text: TYPE_TEXT.tab2 },
    { id: 'say', want: at(6, '随便说一句'), text: TYPE_TEXT.say, until: atEnd(6, '一句') - 4 },
    { id: 'last', want: at(8, '最后一步'), text: TYPE_TEXT.last, fpc: 3 },
    { id: 'rule', want: at(8, '更新进去') + 6, text: TYPE_TEXT.rule },
    { id: 'model', want: at(9, '越来越强') - 4, text: TYPE_TEXT.model, fpc: 3 },
  ];
};
let CACHE: TypeBlock[] | null = null;
export const typeBlocks = (): TypeBlock[] => {
  if (CACHE) return CACHE;
  const out: TypeBlock[] = [];
  let laneFree = -99;
  for (const w of wants()) {
    const units = unitsOf(w.text);
    const start = Math.max(w.want, laneFree);
    const fpc = Math.max(MIN_FPC, w.fpc ?? (w.until ? Math.min(4, Math.floor((w.until - start) / units.length)) : MIN_FPC));
    const end = start + (units.length - 1) * fpc;
    out.push({ id: w.id, start, text: w.text, fpc, end, units });
    laneFree = end + GAP;
  }
  CACHE = out;
  return out;
};
export const block = (id: string) => { const b = typeBlocks().find((x) => x.id === id); if (!b) throw new Error(`typing block ${id}`); return b; };
/** state of a block at frame f: text typed so far (unit k appears at start + k*fpc), last key frame, done */
export const typedAt = (b: TypeBlock, f: number) => {
  const n = f < b.start ? 0 : Math.min(b.units.length, Math.floor((f - b.start) / b.fpc) + 1);
  return { text: b.units.slice(0, n).join(''), n, lastKey: n > 0 ? b.start + (n - 1) * b.fpc : b.start, done: n >= b.units.length, active: f >= b.start };
};
/** frame at which unit k of the block appears */
export const keyFrame = (b: TypeBlock, k: number) => b.start + k * b.fpc;
/** frame the line `li` (0-based, '\n'-separated) of a block starts / ends */
export const lineSpan = (b: TypeBlock, li: number) => {
  let k = 0, line = 0, a = -1, e = -1;
  for (const u of b.units) { if (line === li && a < 0 && u !== '\n') a = k; if (u === '\n') { if (line === li) { e = k - 1; break; } line++; } k++; }
  if (e < 0) e = b.units.length - 1;
  return [keyFrame(b, Math.max(0, a)), keyFrame(b, e)];
};
