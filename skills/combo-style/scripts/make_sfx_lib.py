#!/usr/bin/env python3
"""Synthesize the SFX library (48k stereo wav) into public/sfx/. Pure numpy/scipy, no samples."""
import json, os
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
OUT = os.path.join(os.path.dirname(__file__), '..', 'public', 'sfx')
rng = np.random.default_rng(7)
T = lambda d: np.arange(int(SR * d)) / SR

def env_exp(n, tau):  # exponential decay
    return np.exp(-np.arange(n) / SR / tau)

def fade(x, fi=0.004, fo=0.02):
    n = len(x); a = min(int(fi * SR), n // 3); b = min(int(fo * SR), n // 3)
    if a: x[:a] *= np.linspace(0, 1, a) ** 2
    if b: x[-b:] *= np.linspace(1, 0, b) ** 2
    return x

def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [max(lo, 20), min(hi, SR / 2 - 100)], 'bandpass', fs=SR, output='sos')
    return signal.sosfilt(sos, x)

def lp(x, f, order=2): return signal.sosfilt(signal.butter(order, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, order=2): return signal.sosfilt(signal.butter(order, f, 'high', fs=SR, output='sos'), x)

def swept_bandpass_noise(d, f0, f1, f2, q=1.2, seed=0):
    """noise through a time-varying resonant bandpass (state-variable filter), center f0->f1->f2"""
    n = int(SR * d); r = np.random.default_rng(seed); x = r.standard_normal(n)
    t = np.linspace(0, 1, n)
    fc = np.where(t < 0.5, f0 * (f1 / f0) ** (t / 0.5), f1 * (f2 / f1) ** ((t - 0.5) / 0.5))
    out = np.zeros(n); low = band = 0.0
    F = 2 * np.sin(np.pi * np.minimum(fc, SR / 6) / SR); Qd = 1 / q
    for i in range(n):
        low += F[i] * band
        high = x[i] - low - Qd * band
        band += F[i] * high
        out[i] = band
    return lp(out, 6500)

def reverb(x, tail=0.5, wet=0.25, seed=3, damp=6000):
    r = np.random.default_rng(seed); n = int(tail * SR)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / SR / (tail / 5))
    ir = lp(ir, damp); ir[0] = 0
    ir /= np.sqrt((ir ** 2).sum()) + 1e-9
    wetsig = signal.fftconvolve(x, ir)
    x = np.pad(x, (0, len(wetsig) - len(x)))
    return x * (1 - wet * 0.5) + wetsig * wet

def stereo(m, width=0.0, seed=1, delay_ms=0.0):
    """mono -> stereo with decorrelated ir / haas"""
    d = int(delay_ms / 1000 * SR)
    L = m.copy(); R = np.concatenate([np.zeros(d), m])[:len(m)] if d else m.copy()
    if width:
        r = np.random.default_rng(seed)
        ap = lp(r.standard_normal(len(m)), 400) * 0  # placeholder (keep phase-safe)
    return np.stack([L, R], 1)

def pan_sweep(m, a=-0.5, b=0.5):
    p = np.linspace(a, b, len(m)); ang = (p + 1) * np.pi / 4
    return np.stack([m * np.cos(ang), m * np.sin(ang)], 1) * 1.414

def decor(m, tail=0.25, wet=0.5, seed=5):
    """stereo reverb: independent IR per channel"""
    return np.stack([reverb(m, tail, wet, seed), reverb(m, tail, wet, seed + 11)], 1) if False else \
        _st(m, tail, wet, seed)

def _st(m, tail, wet, seed):
    a = reverb(m, tail, wet, seed); b = reverb(m, tail, wet, seed + 11)
    n = max(len(a), len(b)); a = np.pad(a, (0, n - len(a))); b = np.pad(b, (0, n - len(b)))
    return np.stack([a, b], 1)

PEAK = 10 ** (-14 / 20)  # -14 dBFS peak target (then loudness-matched by RMS cap below)

def finish(x, name):
    if x.ndim == 1: x = np.stack([x, x], 1)
    x = x - x.mean(0)
    # trim trailing near-silence
    e = np.abs(x).max(1); idx = np.where(e > e.max() * 0.002)[0]
    x = x[:idx[-1] + 1]
    x = x.copy()
    for c in range(2): x[:, c] = fade(x[:, c], 0.003, 0.03)
    x = x / (np.abs(x).max() + 1e-9) * PEAK
    return x

def brz(f, n):  # constant
    return np.full(n, f)

def phase_sine(f_inst):  # f_inst array Hz
    return np.sin(2 * np.pi * np.cumsum(f_inst) / SR)

lib = {}

# whoosh_short
w = swept_bandpass_noise(0.35, 500, 2600, 900, q=3.5, seed=1)
w *= np.sin(np.linspace(0, np.pi, len(w))) ** 1.8
lib['whoosh_short'] = (pan_sweep(w, -0.4, 0.4), 'whoosh_short', 0.35, '短转场（B-roll/host 切点，提前 2 帧）')
w = swept_bandpass_noise(0.7, 350, 2200, 700, q=3.0, seed=2)
w *= np.sin(np.linspace(0, np.pi, len(w))) ** 1.6
lib['whoosh_long'] = (_st(w, 0.3, 0.3, 4)[:int(0.7 * SR) + 4000], 'whoosh_long', 0.7, '章节转场/大镜头')
w = swept_bandpass_noise(0.5, 3000, 1200, 300, q=3.0, seed=3)
w *= np.sin(np.linspace(0, np.pi, len(w))) ** 1.0 * np.linspace(0.6, 1, len(w))
w *= np.concatenate([np.linspace(0, 1, int(.04 * SR)), np.ones(len(w) - int(.04 * SR))])
lib['whoosh_down'] = (pan_sweep(w, 0.4, -0.4), 'whoosh_down', 0.5, '下沉式转场/收束')

# pop
n = int(0.08 * SR); t = T(0.08)
f = 180 + 700 * np.exp(-t / 0.012)
p = phase_sine(f) * env_exp(n, 0.03)
click = hp(rng.standard_normal(n), 2500) * np.exp(-np.arange(n) / SR / 0.0015) * 0.25
lib['pop'] = (p + click, 'pop', 0.08, '卡片/标注/药丸出现')
# tick
n = int(0.03 * SR)
c = bp(rng.standard_normal(n), 2500, 7000) * env_exp(n, 0.004)
c += np.sin(2 * np.pi * 1900 * T(0.03)) * env_exp(n, 0.005) * 0.5
lib['tick'] = (c, 'tick', 0.03, '字幕/列表项干脆点击')
# ding
d = 1.2; t = T(d)
b = (np.sin(2 * np.pi * 1318.5 * t) * np.exp(-t / 0.35) + 0.45 * np.sin(2 * np.pi * 1318.5 * 2.76 * t) * np.exp(-t / 0.16)
     + 0.25 * np.sin(2 * np.pi * 1318.5 * 5.4 * t) * np.exp(-t / 0.05))
b *= np.minimum(1, t / 0.002)
lib['ding'] = (_st(b, 0.6, 0.25, 8)[:int(1.5 * SR)], 'ding', 1.2, '结尾/完成/正确提示')
# impact_low
d = 1.0; t = T(d); n = len(t)
f = 48 + 90 * np.exp(-t / 0.07)
body = phase_sine(f) * np.exp(-t / 0.28)
nz = lp(rng.standard_normal(n), 900) * np.exp(-t / 0.07) * 0.8
nz += hp(lp(rng.standard_normal(n), 6000), 1500) * np.exp(-t / 0.012) * 0.3
m = body + nz; m = lp(m, 4000)
lib['impact_low'] = (_st(m, 1.2, 0.5, 9)[:int(1.6 * SR)], 'impact_low', 1.0, '章节卡/大数字揭示的低频重击')
# riser
d = 2.0; t = T(d); n = len(t); u = t / d
nz = swept_bandpass_noise(d, 300, 5000, 6000, q=0.9, seed=5)
nz = bp(rng.standard_normal(n), 200, 7000) * 0 + nz
tone = phase_sine(120 * (4 ** u ** 1.5)) * 0.25 + phase_sine(240 * (4 ** u ** 1.5)) * 0.12
r = (nz / (np.abs(nz).max()) * 0.9 + tone) * (u ** 2.2)
r *= np.minimum(1, (d - t) / 0.03)
lib['riser'] = (pan_sweep(r, -0.3, 0.3), 'riser', 2.0, '铺垫关键时刻（结束点=揭示帧）')
# shimmer
d = 1.0; t = T(d); n = len(t)
sh = np.zeros(n)
for k, f0 in enumerate([2093, 2637, 3136, 3951, 4699, 5588]):
    st = int(0.05 * SR * k * 0.7)
    seg = np.sin(2 * np.pi * f0 * t[:n - st]) * np.exp(-t[:n - st] / 0.25) * np.minimum(1, t[:n - st] / 0.003)
    sh[st:] += seg * (1 / (1 + 0.15 * k))
sh += hp(rng.standard_normal(n), 6000) * np.exp(-t / 0.2) * 0.05
lib['shimmer'] = (_st(sh, 0.7, 0.4, 12)[:int(1.3 * SR)], 'shimmer', 1.0, '金句高亮/金色强调')
# swipe
w = swept_bandpass_noise(0.25, 1200, 3500, 5000, q=2.5, seed=9)
w *= np.sin(np.linspace(0, np.pi, len(w))) ** 1.3
lib['swipe'] = (pan_sweep(w, -0.6, 0.6), 'swipe', 0.25, '卡片滑入')
# flash
n = int(0.12 * SR); t = T(0.12)
fl = hp(rng.standard_normal(n), 4000) * np.exp(-t / 0.012) + np.sin(2 * np.pi * 3200 * t) * np.exp(-t / 0.02) * 0.4
lib['flash'] = (fl, 'flash', 0.12, 'flash_cut 亮闪瞬态')

# loudness match: RMS-balance sustained sounds slightly (percussive stay at peak norm)
os.makedirs(OUT, exist_ok=True)
manifest = {}
print(f"{'file':14s} {'dur':>5s} {'peak dB':>8s} {'rms dB':>8s} {'centroid Hz':>11s}")
for name, (x, _, nom, use) in lib.items():
    y = finish(x, name)
    wavfile.write(os.path.join(OUT, name + '.wav'), SR, (y * 32767).astype(np.int16))
    pk = 20 * np.log10(np.abs(y).max()); rms = 20 * np.log10(np.sqrt((y ** 2).mean()))
    m = y.mean(1); sp = np.abs(np.fft.rfft(m)); fr = np.fft.rfftfreq(len(m), 1 / SR)
    cen = (sp * fr).sum() / sp.sum()
    assert pk < -1 and rms > -60, name
    print(f'{name:14s} {len(y)/SR:5.2f} {pk:8.1f} {rms:8.1f} {cen:11.0f}')
    manifest[name] = {'file': f'sfx/{name}.wav', 'duration': round(len(y) / SR, 3), 'peakDb': round(pk, 1), 'rmsDb': round(rms, 1),
                      'centroidHz': round(float(cen)), 'use': use}
json.dump(manifest, open(os.path.join(OUT, 'manifest.json'), 'w'), ensure_ascii=False, indent=2)
