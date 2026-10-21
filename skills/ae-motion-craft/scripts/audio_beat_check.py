#!/usr/bin/env python3
"""音频节拍分析 + 「动效卡操作还是卡拍」检验（B 片卡 14 的做法写成脚本）。

  python3 audio_beat_check.py <音频或视频> --events "2.5,5.125,7.72,..." [--tol 0.1] [--bpm-range 60:180] [--onset-db 6]

步骤：
  1. ffmpeg 解成 22.05k 单声道 → 40ms 窗 / 10ms 步的 RMS(dB) 包络
  2. onset = 电平比前 30ms 最大值高出 --onset-db 且 > -50 dB
  3. 节拍：onset 强度序列的自相关在 --bpm-range 内的峰 → 拍长（自动估可能差 2:3 / 1:2 倍：B 片卡 14 定为 0.729s，
     本脚本全频自动估出 0.489s；拿不准就把两种拍长都用 --period 跑一遍，结论一致才算数）；相位取 onset 强度落在拍点上最多的那个
  4. 卡拍检验：把每个视觉事件（--events，秒，来自逐帧定位）对到最近拍点，平均绝对偏移 vs 随机预期（拍长/4）。
       比值 < 0.6 → 倾向卡拍；0.6–1.3 → 与随机无异（不卡拍）。
  5. 卡 onset 检验：事件 ±tol 内有 onset 的比例 vs 随机时刻命中率（onset 越密，随机命中越高，要扣掉）。
结论只当「中等置信」：能量峰估相位，节拍弱的音乐床（A 片节拍强度 0.04）误差大；C 片就出现过「10/12 个事件落在 onset 上，
但 onset 密度 2/s、随机命中率约 40%」的情况——这时只能说「可能贴旁白/重音」，不能说卡拍。
另打印：每秒电平（找「掉电平→重击」式的大转场强调）、静音段（>0.4s 低于 -40dB）。
依赖：ffmpeg、numpy。
"""
import argparse, subprocess
import numpy as np

SR = 22050

def load(path, hp=0):
    af = ["-af", f"highpass=f={hp}"] if hp else []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), *af, "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio"); ap.add_argument("--events", default="")
    ap.add_argument("--tol", type=float, default=0.1); ap.add_argument("--bpm-range", default="60:180")
    ap.add_argument("--onset-db", type=float, default=6.0); ap.add_argument("--quiet", action="store_true", help="不打印每秒电平")
    ap.add_argument("--highpass", type=float, default=0, help="先高通（如 3000）：点击/键击类音效藏在音乐床下时用，B 片就是这样找到操作音的")
    ap.add_argument("--period", type=float, default=0, help="已知拍长（秒）就直接用，不自动估（自动估常差 2:3 或 1:2 倍）")
    a = ap.parse_args()
    x = load(a.audio, a.highpass)
    dur = len(x) / SR
    win, hop = int(0.04 * SR), int(0.01 * SR)
    n = max(1, (len(x) - win) // hop)
    rms = np.array([np.sqrt(np.mean(x[i * hop: i * hop + win] ** 2) + 1e-12) for i in range(n)])
    db = 20 * np.log10(rms + 1e-9)
    t = np.arange(n) * hop / SR + win / SR / 2
    print(f"时长 {dur:.2f}s，整体 RMS {20*np.log10(np.sqrt(np.mean(x**2))+1e-9):.1f} dBFS")
    if not a.quiet:
        print("每秒平均电平 dB：", " ".join(f"{int(s)}:{db[(t>=s)&(t<s+1)].mean():.0f}" for s in range(int(dur))))
    # 静音段
    low = db < -40; sil = []; s0 = None
    for i, v in enumerate(low):
        if v and s0 is None: s0 = t[i]
        if not v and s0 is not None:
            if t[i] - s0 > 0.4: sil.append((s0, t[i]))
            s0 = None
    if sil: print("静音段(>0.4s,<-40dB):", ", ".join(f"{p:.2f}-{q:.2f}" for p, q in sil))
    # onset
    strength = np.zeros(n)
    on = []
    for i in range(3, n):
        rise = db[i] - db[i - 3:i].max()
        if rise > 0: strength[i] = rise
        if rise > a.onset_db and db[i] > -50 and (not on or t[i] - on[-1] > 0.05): on.append(t[i])
    on = np.array(on)
    print(f"onset {len(on)} 个，平均 {len(on)/dur:.2f} 个/秒")
    # tempo
    lo, hi = (float(v) for v in a.bpm_range.split(":"))
    s = strength - strength.mean()
    ac = np.correlate(s, s, mode="full")[n - 1:]
    lags = np.arange(len(ac)) * hop / SR
    sel = (lags >= 60 / hi) & (lags <= 60 / lo)
    if not sel.any(): print("音频太短，估不了节拍"); return
    li = np.nonzero(sel)[0][np.argmax(ac[sel])]
    period = lags[li]
    if a.period: period = a.period; li = int(round(period * SR / hop))
    phases = np.linspace(0, period, 50, endpoint=False)
    score = [strength[np.clip(((np.arange(ph, dur, period)) * SR / hop).astype(int), 0, n - 1)].sum() for ph in phases]
    phase = phases[int(np.argmax(score))]
    strength_rel = ac[li] / (ac[0] + 1e-9)
    print(f"节拍：拍长 {period:.3f}s ≈ {60/period:.1f} BPM，相位 {phase:.3f}s，自相关强度 {strength_rel:.2f}（<0.1 = 节拍很弱，结论要降级）")
    ev = np.array([float(v) for v in a.events.replace(" ", "").split(",") if v])
    if not len(ev): print("没给 --events，只做了节拍估计"); return
    off = ((ev - phase + period / 2) % period) - period / 2
    m = np.mean(np.abs(off)); exp = period / 4
    print("事件→最近拍点偏移(s)：", " ".join(f"{e:.2f}:{o:+.2f}" for e, o in zip(ev, off)))
    verdict = "倾向卡拍" if m / exp < 0.6 else ("与随机无异 → 不卡拍" if m / exp < 1.3 else "偏离拍点比随机还大（可能拍长估错，换 --period 再跑）")
    print(f"平均绝对偏移 {m:.3f}s，随机预期 {exp:.3f}s，比值 {m/exp:.2f} → {verdict}")
    if len(on):
        hit = np.mean([np.min(np.abs(on - e)) <= a.tol for e in ev])
        rnd = np.random.default_rng(0).uniform(0, dur, 4000)
        chance = np.mean([np.min(np.abs(on - r)) <= a.tol for r in rnd])
        print(f"事件 ±{a.tol}s 内有 onset：{hit:.0%}；随机时刻命中率 {chance:.0%} → {'高于随机，可能贴音效/旁白重音' if hit > chance + 0.25 else '和随机差不多'}")

if __name__ == "__main__":
    main()
