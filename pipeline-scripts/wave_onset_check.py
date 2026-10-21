#!/usr/bin/env python3
"""Independent check of subtitle starts/ends against the waveform (no whisper involved).
  python3 wave_onset_check.py --timeline t.json --audio voice.wav [--fps 30] [--min-sil 4] [--run 3] [--win 15] [--json out.json]

Per 30 fps frame RMS (dB); threshold = max(p10 + 15 dB, p90 - 30 dB) (deliberately a different window and threshold than align_words.refine, 10 ms / +12 / -35).
Onset = first frame k in [from - win, from + win] with >= --min-sil silent frames before it and --run consecutive frames above threshold from k on (= "after silence, 3 frames over").
Offset = last loud frame before >= --min-sil silent frames, searched in [to - win, to + win].
Subtitles that start / end inside continuous speech (no silence nearby) are listed as n/a - there is no waveform edge to compare with.
Drift = subtitle frame - waveform frame (+ = subtitle late). End uses to (inclusive) vs the last loud frame.
"""
import argparse, json, subprocess, statistics
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument('--timeline', required=True); ap.add_argument('--audio', required=True); ap.add_argument('--fps', type=float, default=30)
ap.add_argument('--min-sil', type=int, default=4); ap.add_argument('--run', type=int, default=3); ap.add_argument('--win', type=int, default=15); ap.add_argument('--json'); ap.add_argument('--offset', type=float, default=0)
A = ap.parse_args()
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', A.audio, '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'], capture_output=True).stdout
x = np.frombuffer(raw, np.float32); hop = int(48000 / A.fps); n = len(x) // hop
db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
thr = max(np.percentile(db, 10) + 15, np.percentile(db, 90) - 30); loud = db > thr
subs = [s for s in json.load(open(A.timeline))['subtitles'] if not s.get('hidden')]
rows = []
for s in subs:
    f0 = int(s['from'] - A.offset); f1 = int(s['to'] - A.offset); on = off = None
    for k in range(max(A.min_sil, f0 - A.win), min(n - A.run, f0 + A.win + 1)):
        if loud[k:k + A.run].all() and not loud[k - A.min_sil:k].any(): on = k; break
    cands = [k for k in range(max(0, f1 - A.win), min(n - A.min_sil, f1 + A.win + 1)) if loud[k] and not loud[k + 1:k + 1 + A.min_sil].any()]
    if cands: off = min(cands, key=lambda k: abs(k - f1))
    rows.append(dict(id=s['id'], text=s['text'], sub_from=s['from'], sub_to=s['to'], wave_on=on, wave_off=off,
                     d_start=None if on is None else s['from'] - A.offset - on, d_end=None if off is None else s['to'] - A.offset - off))

def stat(v):
    if not v: return 'n/a'
    a = sorted(abs(t) for t in v); p95 = a[min(len(a) - 1, int(round(.95 * (len(a) - 1))))]
    return f'n={len(v)} mean {statistics.mean(v):+.2f} f, mean abs {statistics.mean(a):.2f} f, max abs {max(a):.0f} f, P95 abs {p95:.0f} f, outside +-3: {sum(t > 3 for t in a)}'

st = [r['d_start'] for r in rows if r['d_start'] is not None]; en = [r['d_end'] for r in rows if r['d_end'] is not None]
print(f'waveform check  {A.audio}  thr {thr:.1f} dB  subtitles {len(rows)}')
print('start:', stat(st)); print('end  :', stat(en))
print('no silence before start (n/a):', ', '.join(r['id'] for r in rows if r['d_start'] is None) or '-')
for r in rows: print(f"  {r['id']} {r['sub_from']:>5}..{r['sub_to']:<5} wave {str(r['wave_on']):>5}..{str(r['wave_off']):<5} d {'' if r['d_start'] is None else format(r['d_start'], '+.0f'):>4} / {'' if r['d_end'] is None else format(r['d_end'], '+.0f'):>4}  {r['text']}")
if A.json: json.dump(dict(start=st, end=en, rows=rows, thr=float(thr)), open(A.json, 'w'), ensure_ascii=False, indent=1)
