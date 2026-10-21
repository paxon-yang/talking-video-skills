#!/usr/bin/env python3
"""Video2 sound-effects track (no BGM).
  python3 src/video2/make_sfx.py [ver]          (ver = output suffix, default = voice tag from src/video2/data/meta.json; v2 film: `v2`)
Two buses, both ducked under the voice (sidechain, up to -8 dB, attack 15 ms / release 300 ms):
  * sfx bus    — the picture's key frames (events.ts sfxEvents().events, no identical sound twice in a row), at voice -20 LU
  * typing bus — event type `typing`: every typing block registered in typing.ts (start frame, text, frames per character) becomes one key
                 sound PER CHARACTER at exactly start + k*fpc (fpc >= 2, blocks never overlap -> keys >= 2 frames apart):
                 letters / Han -> one of 4 soft key samples (never the same twice in a row) with seeded pitch 0.92-1.08 and level +-2.5 dB,
                 space / Chinese punctuation -> low space-bar thunk, '\\n' -> enter key, end of block -> a quiet 'ding'; bus at voice -20 LU
The mix is normalised to -16 LUFS and limited to a sample peak <= -3.2 dBFS.
Outputs out/video2/audio/: sfx_events_<ver>.json, typing_events_<ver>.json, sfx_<ver>.wav, typing_<ver>.wav, mix_<ver>.wav, sfx_check_<ver>.json"""
import json, os, re, subprocess, sys
import numpy as np
OUT = 'out/video2/audio'
META = json.load(open('src/video2/data/meta.json'))
TAG = META['tag']
VER = sys.argv[1] if len(sys.argv) > 1 else TAG
subprocess.run(f'node src/video2/dump_events.mjs > {OUT}/_ev.json', shell=True, check=True)
D = json.load(open(f'{OUT}/_ev.json')); os.remove(f'{OUT}/_ev.json')
SR, FPS, NFR = 48000, 30, D['total']
DUR = NFR / FPS
MAN = json.load(open('public/sfx/manifest.json'))
E = [list(e) for e in D['events'] if 0 <= e[0] < NFR]
for i in range(1, len(E)):
    assert E[i][1] != E[i - 1][1], ('repeat', E[i - 1], E[i])
for e in E: assert e[1] in MAN, e

# ── typing events (one per character)
KEYS = ['key_soft_a', 'key_soft_b', 'key_soft_c', 'key_soft_d']
LOW = set(' ，、：；。,')
rng = np.random.default_rng(2026)
T = []  # dict(frame, sound, gain, pitch, block, unit)
blocks_check = []
prev_key = None
for b in D.get('typing', []):
    n_keys = 0
    for k, u in enumerate(b['units']):
        f = b['start'] + k * b['fpc']
        if u == '\n': snd, g, p = 'key_enter', -1.0, 1.0
        elif u in LOW: snd, g, p = 'key_space', -2.0, float(rng.uniform(0.95, 1.03))
        else:
            choices = [x for x in KEYS if x != prev_key]
            snd = choices[int(rng.integers(len(choices)))]; prev_key = snd
            g, p = float(rng.uniform(-2.5, 2.5)), float(rng.uniform(0.92, 1.08))
        T.append({'frame': f, 'sound': snd, 'gain_db': round(g, 2), 'pitch': round(p, 3), 'block': b['id'], 'unit': u, 'type': 'typing'})
        n_keys += 1
    T.append({'frame': b['end'] + 3, 'sound': 'ding', 'gain_db': -14.0, 'pitch': 1.0, 'block': b['id'], 'unit': '(行尾叮)', 'type': 'typing_end'})
    blocks_check.append({'block': b['id'], 'start': b['start'], 'fpc': b['fpc'], 'chars': len(b['units']), 'key_events': n_keys, 'ok': n_keys == len(b['units']), 'text': b['text']})
keyf = sorted(t['frame'] for t in T if t['type'] == 'typing')
min_gap = min((b - a for a, b in zip(keyf, keyf[1:])), default=99)

def load(path, ch=2):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', str(ch), '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, ch).copy()
N = int(round(DUR * SR))
cache = {}
def sample(s):
    if s not in cache: cache[s] = load(os.path.join('public', MAN[s]['file']))
    return cache[s]
def place(bus, f, x):
    i0 = int(round(f / FPS * SR)); i1 = min(N, i0 + len(x))
    if i0 < N: bus[i0:i1] += x[: i1 - i0]
bus = np.zeros((N, 2), np.float32)
for f, s, gdb, _ in E:
    place(bus, f, sample(s) * MAN[s]['defaultVolume'] * 10 ** (gdb / 20))
tbus = np.zeros((N, 2), np.float32)
for t in T:
    x = sample(t['sound']) * MAN[t['sound']]['defaultVolume'] * 10 ** (t['gain_db'] / 20)
    if abs(t['pitch'] - 1) > 1e-3:  # varispeed pitch (resample)
        L = len(x); m = int(L / t['pitch']); src = np.arange(m) * t['pitch']
        x = np.stack([np.interp(src, np.arange(L), x[:, c]) for c in range(2)], 1).astype(np.float32)
    place(tbus, t['frame'], x)

voice = load('public/' + META['voice'], 1)[:, 0]
voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]
hop = 480
m = N // hop
rms = np.sqrt((voice[: m * hop].reshape(m, hop) ** 2).mean(1) + 1e-12)
vdb = 20 * np.log10(rms + 1e-9)
target = -8.0 * np.clip((vdb + 45) / 20, 0, 1)
gcur = np.zeros(m); cur = 0.0
for i in range(m):
    a = 0.49 if target[i] < cur else 0.033
    cur += (target[i] - cur) * a; gcur[i] = cur
gain = np.repeat(10 ** (gcur / 20), hop)
gain = np.pad(gain, (0, N - len(gain)), constant_values=gain[-1])
bus *= gain[:, None]; tbus *= gain[:, None]

def tmpwav(path, x):
    x = np.asarray(x, np.float32)
    ch = 1 if x.ndim == 1 else x.shape[1]
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', str(ch), '-i', '-', '-c:a', 'pcm_f32le', path], input=x.tobytes(), check=True)
def loud(path):
    r = subprocess.run(['ffmpeg', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1]); P = float(re.findall(r'Peak:\s+(-?[\d.inf]+) dBFS', r)[-1])
    return I, P
voice2 = np.stack([voice, voice], 1)
tmpwav(f'{OUT}/_voice.wav', voice2); tmpwav(f'{OUT}/_bus.wav', bus); tmpwav(f'{OUT}/_tbus.wav', tbus)
Iv, _ = loud(f'{OUT}/_voice.wav'); Ib, _ = loud(f'{OUT}/_bus.wav'); It, _ = loud(f'{OUT}/_tbus.wav')
REL, TREL = -20.0, -20.0
bus *= 10 ** ((Iv + REL - Ib) / 20)
tbus *= 10 ** ((Iv + TREL - It) / 20)
mix = voice2 + bus + tbus
tmpwav(f'{OUT}/_mix.wav', mix)
Im, _ = loud(f'{OUT}/_mix.wav')
k = 10 ** ((-16.0 - Im) / 20)
pk = float(np.abs(mix).max()) * k
if pk > 10 ** (-3.2 / 20): k *= 10 ** (-3.2 / 20) / pk
mix *= k; bus *= k; tbus *= k; voice2 *= k
tmpwav(f'{OUT}/mix_{VER}.wav', mix); tmpwav(f'{OUT}/sfx_{VER}.wav', bus); tmpwav(f'{OUT}/typing_{VER}.wav', tbus); tmpwav(f'{OUT}/_voice.wav', voice2)
I2, P2 = loud(f'{OUT}/mix_{VER}.wav'); Ib2, Pb2 = loud(f'{OUT}/sfx_{VER}.wav'); It2, Pt2 = loud(f'{OUT}/typing_{VER}.wav'); Iv2, _ = loud(f'{OUT}/_voice.wav')
win = SR * 2 // 5
snr = []
for i in range(0, N - win, win):
    v = float(np.sqrt((voice2[i:i + win] ** 2).mean() + 1e-12)); b = float(np.sqrt(((bus + tbus)[i:i + win] ** 2).mean() + 1e-12))
    if 20 * np.log10(v) > -40 and b > 1e-6: snr.append(20 * np.log10(v / b))
chk = {'events': len(E), 'distinct_sounds': len({e[1] for e in E}), 'typing_blocks': len(blocks_check), 'typing_key_events': len(keyf), 'typing_min_gap_frames': min_gap,
       'typing_counts_all_match': all(b['ok'] for b in blocks_check),
       'voice_I_LUFS': Iv2, 'sfx_I_LUFS': Ib2, 'typing_I_LUFS': It2, 'sfx_minus_voice_LU': round(Ib2 - Iv2, 2), 'typing_minus_voice_LU': round(It2 - Iv2, 2),
       'mix_I_LUFS': I2, 'mix_true_peak_dBTP': P2, 'mix_sample_peak_dBFS': round(float(20 * np.log10(np.abs(mix).max())), 2), 'clipping_samples': int((np.abs(mix) >= 1.0).sum()),
       'voice_over_all_sfx_dB_in_speech': {'min': round(min(snr), 1), 'p10': round(float(np.percentile(snr, 10)), 1), 'median': round(float(np.median(snr)), 1), 'windows': len(snr)},
       'ducking': 'voice sidechain on both buses, up to -8 dB, attack 15 ms / release 300 ms', 'blocks': blocks_check}
json.dump([{'frame': e[0], 'time_s': round(e[0] / FPS, 3), 'sound': e[1], 'gain_db': e[2], 'event': e[3], 'type': 'sfx'} for e in E], open(f'{OUT}/sfx_events_{VER}.json', 'w'), ensure_ascii=False, indent=1)
json.dump(T, open(f'{OUT}/typing_events_{VER}.json', 'w'), ensure_ascii=False, indent=1)
json.dump(chk, open(f'{OUT}/sfx_check_{VER}.json', 'w'), ensure_ascii=False, indent=1)
for f in ['_voice.wav', '_bus.wav', '_tbus.wav', '_mix.wav']:
    if os.path.exists(f'{OUT}/{f}'): os.remove(f'{OUT}/{f}')
print(json.dumps({k: v for k, v in chk.items() if k != 'blocks'}, ensure_ascii=False, indent=1))
for b in blocks_check: print(b['block'], b['start'], b['fpc'], b['chars'], b['key_events'], 'OK' if b['ok'] else 'MISMATCH', repr(b['text']))
