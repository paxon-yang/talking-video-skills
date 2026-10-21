#!/usr/bin/env python3
"""判断一段运动是什么缓动，并给出参数。输入是一串等间隔采样值（位移、宽度、缩放、亮度…，来自 measure.py）。

  python3 fit_decay.py "882,724,640,584,548,520" [--final 420] [--step-fps 15] [--to-fps 30]

输出：
  - 每步剩余比 r_n = (终值 - x_{n+1}) / (终值 - x_n)：几乎恒定 → 指数衰减 ease-out，k = 几何平均（每采样步）
  - k 换算到 --to-fps（默认 30）每帧：k30 = k ** (step_fps / 30)，对照两套预设 calm 0.84 / snappy 0.68
  - 每步增量：几乎恒定 → 线性；先增后减 → ease-in-out（用 fit_bezier.js 拟合）；只增 → ease-in
  - 连续相等的值（成对重复）→ 隔帧（on twos，12fps 手 K 味）；某一步占总量 >60% → 近似硬切/跳变
不给 --final 时用最后一个值当终值（序列要采到「已经停住」）。
"""
import argparse, math

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("values"); ap.add_argument("--final", type=float, default=None)
    ap.add_argument("--step-fps", type=float, default=30, help="采样率（两个值之间隔 1/step_fps 秒）")
    ap.add_argument("--to-fps", type=float, default=30)
    a = ap.parse_args()
    x = [float(v) for v in a.values.replace(" ", "").split(",") if v]
    fin = a.final if a.final is not None else x[-1]
    total = fin - x[0]
    if abs(total) < 1e-9: print("起点等于终值，没有运动"); return
    d = [x[i + 1] - x[i] for i in range(len(x) - 1)]
    print(f"{len(x)} 个样本，步长 {1/a.step_fps:.4f}s，总变化 {total:+.3f}")
    print("进度:", " ".join(f"{(v - x[0]) / total:.3f}" for v in x))
    # 隔帧 / 跳变
    holds = sum(1 for v in d if abs(v) < 1e-6 * max(1, abs(total)))
    if holds: print(f"有 {holds} 步完全没动：若成对出现 = 隔帧（on twos），量曲线时按 2 帧一个样本")
    big = max(d, key=abs)
    if abs(big) / abs(total) > 0.6: print(f"单步占总量 {abs(big)/abs(total):.0%}：接近硬切/跳变（或采样太稀）")
    # 指数衰减检验
    rem = [(fin - v) / (fin - x[0]) for v in x]
    ratios = [rem[i + 1] / rem[i] for i in range(len(rem) - 1) if rem[i] > 0.02 and rem[i + 1] > 0]
    if len(ratios) >= 2:
        g = math.exp(sum(math.log(r) for r in ratios) / len(ratios))
        cv = (sum((r - g) ** 2 for r in ratios) / len(ratios)) ** 0.5 / g
        k_to = g ** (a.step_fps / a.to_fps)
        print("剩余比:", " ".join(f"{r:.3f}" for r in ratios))
        print(f"几何平均 k = {g:.3f} /步  → {k_to:.3f} /帧@{a.to_fps:g}fps   离散度 {cv:.1%}")
        if cv < 0.12:
            near = "calm(0.84)" if abs(k_to - 0.84) < abs(k_to - 0.68) else "snappy(0.68)"
            print(f"判断：指数衰减 ease-out（剩余比稳定），接近 {near}；88% 到位约 {math.log(0.12)/math.log(k_to):.1f} 帧@{a.to_fps:g}")
        else:
            print("判断：剩余比不稳定 → 不是单纯指数衰减（看增量形状，或用 fit_bezier.js）")
    # 增量形状
    if len(d) >= 3:
        mean = sum(d) / len(d)
        cvd = (sum((v - mean) ** 2 for v in d) / len(d)) ** 0.5 / (abs(mean) or 1)
        peak = max(range(len(d)), key=lambda i: abs(d[i]))
        shape = "近似线性（增量恒定）" if cvd < 0.15 else ("先快后慢（ease-out）" if peak <= 1 else ("越来越快（ease-in，可能接硬停）" if peak >= len(d) - 2 else "两头慢中间快（ease-in-out）"))
        print("每步增量:", " ".join(f"{v:+.2f}" for v in d), "→", shape)

if __name__ == "__main__":
    main()
