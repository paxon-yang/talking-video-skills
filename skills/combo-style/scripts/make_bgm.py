#!/usr/bin/env python3
"""OPTIONAL - NOT USED BY DEFAULT (the user adds music in Jianying; do not set assets.bgm). Kept for reference only.
SYNTHETIC PLACEHOLDER ambient bed (~160s), A minor i-VI-III-VII @84bpm -> public/projects/bee-level8/bgm.wav.
No melody, speech band (1-4k) dipped. Replace with a real track any time (timeline assets.bgm.src)."""
import os, re, subprocess, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000; DUR = 160.0; BPM = 84
OUT = os.path.join(os.path.dirname(__file__), '..', 'public', 'projects', 'bee-level8', 'bgm.wav')
TARGET_LUFS = -28.0
rng = np.random.default_rng(11)
N = int(SR * DUR)
bar = 4 * 60 / BPM
mid = lambda m: 440 * 2 ** ((m - 69) / 12)
lp = lambda x, f, o=2: signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x, axis=0)
hp = lambda x, f, o=2: signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x, axis=0)

chords = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (55, [55, 59, 62])]  # Am F C G (root, triad)
seg = 2 * bar  # two bars per chord
def saw(f, n, ph0):
    return 2 * ((np.arange(n) * f / SR + ph0) % 1.0) - 1

pad = np.zeros((N, 2)); sub = np.zeros(N)
nseg = int(DUR / seg) + 2
xf = int(1.6 * SR)
for k in range(nseg):
    root, tri = chords[k % 4]
    n = int(seg * SR) + 2 * xf
    t0 = int(k * seg * SR) - xf
    notes = [m - 12 for m in tri] + [tri[0] - 24, tri[0] + 0, tri[2]]
    L = np.zeros(n); R = np.zeros(n)
    for j, m in enumerate(notes):
        for d, cents in enumerate((-9, 0, 8)):
            f = mid(m) * 2 ** (cents / 1200)
            s = saw(f, n, rng.random()) * (0.5 if d == 1 else 0.3)
            pan = ((j * 3 + d) % 5) / 4  # spread
            L += s * (1 - pan * 0.6); R += s * (0.4 + pan * 0.6)
    # slow filter movement: crossfade two lowpasses with LFO, per segment phase
    st = np.stack([L, R], 1)
    a = lp(st, 380, 3); b = lp(st, 900, 3)
    lfo = (0.5 + 0.5 * np.sin(2 * np.pi * np.arange(n) / SR / (bar * 3) + k * 1.3))[:, None]
    seg_s = a * (1 - lfo) + b * lfo
    env = np.ones(n); env[:xf] = np.sin(np.linspace(0, np.pi / 2, xf)) ** 2; env[-xf:] = np.cos(np.linspace(0, np.pi / 2, xf)) ** 2
    seg_s *= env[:, None]
    a0, b0 = max(t0, 0), min(t0 + n, N)
    if b0 > a0: pad[a0:b0] += seg_s[a0 - t0:b0 - t0] * 0.12

# very soft sub pulse: root sine one octave below, once per bar on beat 1 (+ soft beat 3)
for k in range(int(DUR / bar)):
    root = chords[(k // 2) % 4][0]
    f = mid(root - 24)
    for beat, amp in ((0, 1.0), (2, 0.55)):
        s = int((k * bar + beat * 60 / BPM) * SR); n = int(1.2 * SR)
        if s + n > N: continue
        t = np.arange(n) / SR
        e = np.minimum(1, t / 0.03) * np.exp(-t / 0.45)
        sub[s:s + n] += np.sin(2 * np.pi * f * t) * e * amp * 0.28

# airy textures: bandpassed noise swells ~every 14s, high band, wide stereo
tex = np.zeros((N, 2))
for k in range(int(DUR / 14)):
    s = int((6 + k * 14 + rng.uniform(-2, 2)) * SR); n = int(6 * SR)
    if s + n > N: break
    nz = rng.standard_normal((n, 2))
    nz = signal.sosfilt(signal.butter(2, [5000, 11000], 'bandpass', fs=SR, output='sos'), nz, axis=0)
    e = np.sin(np.linspace(0, np.pi, n)) ** 3
    sweep = np.linspace(rng.uniform(.8, 1.2), rng.uniform(.8, 1.2), n)
    tex[s:s + n] += nz * e[:, None] * 0.05
    # soft glassy tone
    f = mid(chords[(k * 2) % 4][1][2] + 24)
    tt = np.arange(n) / SR
    tone = np.sin(2 * np.pi * f * tt) * e * 0.012
    tex[s:s + n, 0] += tone * 0.8; tex[s:s + n, 1] += tone

mix = pad + sub[:, None] + tex

# reverb tail (stereo, decorrelated IR)
irn = int(2.6 * SR)
def ir(seed):
    r = np.random.default_rng(seed); x = r.standard_normal(irn) * np.exp(-np.arange(irn) / SR / 0.55)
    x = lp(x, 5000); x[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR)); return x / np.sqrt((x ** 2).sum())
wet = np.stack([signal.fftconvolve(mix[:, 0], ir(1))[:N], signal.fftconvolve(mix[:, 1], ir(2))[:N]], 1)
mix = mix * 0.6 + wet * 0.7

# EQ: gentle dip in speech band (peaking -7 dB @ 2.2k wide), cut sub rumble, trim top
def peaking(x, f0, q, gain_db):
    A = 10 ** (gain_db / 40); w0 = 2 * np.pi * f0 / SR; al = np.sin(w0) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w0), 1 - al * A]; a = [1 + al / A, -2 * np.cos(w0), 1 - al / A]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)
mix = peaking(mix, 2200, 0.5, -9)
mix = hp(mix, 35)
mix = lp(mix, 12000)

# light width: mid/side, boost side a little
m = (mix[:, 0] + mix[:, 1]) / 2; s = (mix[:, 0] - mix[:, 1]) / 2
mix = np.stack([m + 1.3 * s, m - 1.3 * s], 1)

# seamless loop-ish: 0.5s fades at both ends
fn = int(0.5 * SR); mix[:fn] *= np.linspace(0, 1, fn)[:, None]; mix[-fn:] *= np.linspace(1, 0, fn)[:, None]

def lufs(x):
    tmp = OUT + '.tmp.wav'
    wavfile.write(tmp, SR, x.astype(np.float32))
    r = subprocess.run(['/opt/homebrew/bin/ffmpeg', '-nostats', '-i', tmp, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True)
    os.remove(tmp)
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)[-1])

os.makedirs(os.path.dirname(OUT), exist_ok=True)
for _ in range(2):
    mix = mix * 10 ** ((TARGET_LUFS - lufs(mix)) / 20)
pk = np.abs(mix).max()
print(f'LUFS {lufs(mix):.1f}  peak {20*np.log10(pk):.1f} dBFS  dur {len(mix)/SR:.1f}s')
assert pk < 0.9
wavfile.write(OUT, SR, (mix * 32767).astype(np.int16))
sp = np.abs(np.fft.rfft(mix.mean(1))) ** 2; fr = np.fft.rfftfreq(N, 1 / SR)
tot = sp.sum()
for lo, hi in ((0, 200), (200, 1000), (1000, 4000), (4000, 12000)):
    print(f'{lo}-{hi} Hz: {10*np.log10(sp[(fr>=lo)&(fr<hi)].sum()/tot+1e-12):.1f} dB of total')
