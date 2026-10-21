#!/usr/bin/env python3
"""Video2 voice -> all time data the film reads (the ONLY step to redo when the real Fish Audio voice arrives).
  python3 src/video2/prep_voice.py <voice.mp3> [--tag placeholder|v1] [--skip-align]
Steps (same flow as out/video1/audio/ALIGN_REPORT_v3.md):
  1. scripts/align_words.py --lang zh --script out/video2/audio/script_fish.txt --auto-abbr  (turbo-q4, per character, waveform-refined)
  2. scripts/build_subtitles_from_words.py --lang zh (<= 14 chars per line, never across a sentence)
  3. compact data for the TSX: src/video2/data/words.json  [{id, start, end, w: [[text, start, end], ...]}]  (frames @30)
                               src/video2/data/subs.json   [{id, from, to, text, sentenceId, hl}]
                               src/video2/data/voice_env.json {env, raw} (10 ms RMS -> per frame, 0..1)
                               src/video2/data/meta.json   {total, voice, tag, durationSec}
The voice file is copied to public/projects/video2/audio/ (the composition plays it from there)."""
import json, os, re, shutil, subprocess, sys
import numpy as np
args = [a for a in sys.argv[1:] if not a.startswith('--')]
voice = args[0]
tag = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--tag=')), 'placeholder')
FPS = 30
AUD = 'out/video2/audio'; DATA = 'src/video2/data'; PUB = 'public/projects/video2/audio'
os.makedirs(AUD, exist_ok=True); os.makedirs(DATA, exist_ok=True); os.makedirs(PUB, exist_ok=True)
LINES = json.load(open('out/video2/script_lines.json'))
open(f'{AUD}/script_fish.txt', 'w').write('\n'.join(l['fish'] for l in LINES) + '\n')
pub = os.path.join(PUB, os.path.basename(voice))
if os.path.abspath(pub) != os.path.abspath(voice): shutil.copy(voice, pub)
align = f'{AUD}/voice_{tag}.align.json'
if '--skip-align' not in sys.argv or not os.path.exists(align):
    subprocess.run([sys.executable, 'scripts/align_words.py', voice, '--lang', 'zh', '--script', f'{AUD}/script_fish.txt', '--auto-abbr', '--out', align, '--raw', f'{AUD}/voice_{tag}.raw.json'], check=True)
subs_raw = f'{AUD}/subs_{tag}.json'
subprocess.run([sys.executable, 'scripts/build_subtitles_from_words.py', align, '--lang', 'zh', '--out', subs_raw], check=True)
A = json.load(open(align))
# the aligner splits at 。？ inside a script line -> regroup its words into the 12 script lines by character count
norm = lambda t: re.sub(r'[^0-9A-Za-z\u3400-\u9fff]', '', t)
allw = [w for s in A['sentences'] for w in s['words']]
words, i = [], 0
for li, l in enumerate(LINES):
    need = len(norm(l['fish'])); got, ws = 0, []
    while i < len(allw) and got < need:
        ws.append(allw[i]); got += len(norm(allw[i]['text'])); i += 1
    assert got == need, (li + 1, got, need, ''.join(w['text'] for w in ws))
    words.append({'id': li + 1, 'start': ws[0]['start'], 'end': ws[-1]['end'], 'w': [[w['text'], w['start'], w['end']] for w in ws]})
assert i == len(allw), (i, len(allw))
json.dump(words, open(f'{DATA}/words.json', 'w'), ensure_ascii=False, separators=(',', ':'))
# green key words per sentence (subtitle pill): first match wins inside each line
HL = {1: ['别人的', '一个都没做过', '看完'], 2: ['最牛的用法', '沉淀成 Skill', '沉淀成Skill'], 3: ['经常干', '流程复杂', '比较固定'],
      4: ['从头到尾', '干一遍'], 5: ['沉淀成一个 Skill', '沉淀成一个Skill', '踩的坑', '素材'], 6: ['随便说一句', '自己就会干'], 7: ['沉淀下来', 'Skill 库', 'Skill库'],
      8: ['养着它', '不等于完善', '更新进去'], 9: ['越来越强', '拖后腿', '定期精简'], 10: ['Skill 库', 'Skill库', '事半功倍', '剥离出来']}
subs = json.load(open(subs_raw))
for s in subs:
    k = next(w['id'] for w in words if w['start'] <= s['from'] <= w['end'])
    s['sentenceId'] = f's{k:02d}'
    s['hl'] = [h for h in HL.get(k, []) if h in s['text']][:2]
json.dump(subs, open(f'{DATA}/subs.json', 'w'), ensure_ascii=False, indent=1)
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', voice, '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'], capture_output=True).stdout
x = np.frombuffer(raw, np.float32)
dur = len(x) / 48000
n = int(np.ceil(dur * FPS))
hop = 1600
m = len(x) // hop
rms = np.sqrt((x[: m * hop].reshape(m, hop) ** 2).mean(1) + 1e-12)
db = 20 * np.log10(rms)
e = np.clip((db + 50) / 35, 0, 1)
env, cur = [], 0.0
for v in e:
    cur = v if v > cur else cur + (v - cur) * 0.2
    env.append(round(float(cur), 3))
json.dump({'fps': FPS, 'n': n, 'env': env, 'raw': [round(float(v), 3) for v in e]}, open(f'{DATA}/voice_env.json', 'w'), separators=(',', ':'))
last = words[-1]['end']
total = max(n, last + 40)  # closing title holds ~1.3 s after the last word (never cuts the audio)
json.dump({'tag': tag, 'voice': f'projects/video2/audio/{os.path.basename(voice)}', 'durationSec': round(dur, 3), 'total': int(total)}, open(f'{DATA}/meta.json', 'w'), indent=1)
print(json.dumps({'tag': tag, 'sec': round(dur, 2), 'total_frames': total, 'sentences': [(w['id'], w['start'], w['end']) for w in words], 'subs': len(subs)}, ensure_ascii=False))
