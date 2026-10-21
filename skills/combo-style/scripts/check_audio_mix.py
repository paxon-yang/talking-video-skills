#!/usr/bin/env python3
"""Usage (from project root): python3 check_audio_mix.py [timeline.json]; edit SLUG below. BGM is optional: with no assets.bgm the mix is voice+SFX (the default deliverable).
Offline mock of the Remotion audio mix -> review/audio_mix_check.wav + LUFS stats + spectrogram."""
import json, os, re, subprocess, sys
import numpy as np
from scipy.io import wavfile
from scipy import signal
R = os.path.join(os.path.dirname(__file__), '..'); P = R + '/public/'; SR = 48000; FF = '/opt/homebrew/bin/ffmpeg'
SLUG = 'bee-level8'  # EDIT
tl = json.load(open(sys.argv[1] if len(sys.argv) > 1 else P + f'projects/{SLUG}/full.timeline.json'))
def rd(path):
    sr, x = wavfile.read(path); x = x.astype(np.float32) / (32768 if x.dtype == np.int16 else 1)
    if x.ndim == 1: x = np.stack([x, x], 1)
    if sr != SR: x = signal.resample_poly(x, SR, sr, axis=0)
    return x
N = int(tl['meta']['durationInFrames'] / 30 * SR)
host = rd(P + tl['assets']['hostAudio'])[:N]; host = np.pad(host, ((0, N - len(host)), (0, 0)))
bgm = np.zeros((N, 2), np.float32); bgv = 0
if 'bgm' in tl['assets']:  # optional; absent by default
    bg = rd(P + tl['assets']['bgm']['src']); bgv = tl['assets']['bgm'].get('volume', 0.5); k = min(N, len(bg)); bgm[:k] = bg[:k]
env = np.interp(np.arange(N) / SR, [0, 1, N / SR - 2.5, N / SR], [0, 1, 1, 0])
bgm *= env[:, None] * bgv
sfx = np.zeros((N, 2), np.float32)
for c in tl.get('sfx', []):
    x = rd(P + f'sfx/{c["type"]}.wav')
    r = c.get('rate', 1)
    if r != 1: x = signal.resample(x, int(len(x) / r), axis=0)
    s = int(c['at'] / 30 * SR); e = min(N, s + len(x)); sfx[s:e] += x[:e - s] * c['volume']
def lufs(x, tag):
    tmp = R + '/projects/bee-level8/review/_tmp.wav'; wavfile.write(tmp, SR, x.astype(np.float32))
    r = subprocess.run([FF, '-nostats', '-i', tmp, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    os.remove(tmp); tail = r[r.rfind('Summary:'):]
    I = float(re.search(r'I:\s+(-?[\d.]+) LUFS', tail).group(1)); tp = float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', tail).group(1))
    print(f'{tag:14s} integrated {I:6.1f} LUFS   true-ish peak {tp:6.1f} dBFS'); return I
Iv = lufs(host, 'voice only'); (lufs(bgm, 'bgm@vol') if bgv else None); lufs(sfx, 'sfx only'); mix = host + bgm + sfx; Im = lufs(mix, 'mix')
print(f'mix - voice = {Im - Iv:+.2f} LU  (target <= +1.5)')
# SFX-vs-voice: max over cues of (sfx short-term RMS - voice RMS) in the 400ms after cue
worst = []
for c in tl['sfx']:
    s = int(c['at'] / 30 * SR); w = slice(s, s + int(.4 * SR))
    v = np.sqrt((host[w] ** 2).mean()) + 1e-9; q = np.sqrt((sfx[w] ** 2).mean()) + 1e-9
    worst.append((20 * np.log10(q / v), c['type'], c['at']))
worst.sort(reverse=True); print('loudest sfx relative to voice (dB RMS, 0.4s):', [(round(a, 1), b, c) for a, b, c in worst[:5]])
out = R + '/projects/bee-level8/review/audio_mix_check.wav'
wavfile.write(out, SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16)); print('clip count', int((np.abs(mix) >= 1).sum()))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, ax = plt.subplots(3, 1, figsize=(16, 9), sharex=True); t = np.arange(N)[::480] / SR
for a, x, n in zip(ax[:2], (host, mix), ('voice only', 'mix (voice+bgm+sfx)')):
    a.plot(t, x[::480, 0], lw=.4); a.set_ylabel(n); a.set_ylim(-1, 1)
f, tt, S = signal.spectrogram(mix.mean(1), SR, nperseg=2048); ax[2].pcolormesh(tt, f, 10 * np.log10(S + 1e-12), vmin=-110, vmax=-30, shading='auto'); ax[2].set_ylim(0, 12000)
for c in tl['sfx']: ax[0].axvline(c['at'] / 30, color='r', lw=.3)
plt.tight_layout(); plt.savefig(R + '/projects/bee-level8/review/audio_mix_check.png', dpi=80)
