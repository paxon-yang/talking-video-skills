#!/usr/bin/env python3
"""逐帧像素测量（ffmpeg 解码成裸帧 + numpy）。同一条命令既量原片也量我们的渲染，才有可比性。

  python3 measure.py <子命令> <视频> --ss 起点秒 --dur 时长秒 --fps 采样fps [--scale 480:270] [--crop w:h:x:y] [其它参数]

子命令（输出每行一帧：时间 + 数值；加 --csv 输出 CSV）：
  bbox    亮(或暗)像素的外接框 x0 x1 y0 y1 w h：量缩放、位移、显现宽度。
          --thr 150 阈值；--dark 取暗像素；--minfrac 0.0 某行/列至少多少比例像素过阈值才算（去噪，B 片用 0.15）
          --expr 'np.maximum(np.maximum(r,g),b)>100' 用 RGB 表达式代替灰度阈值（暗紫色文字用最大通道，灰度阈值会漏）
  shift   相邻帧的平移量（互相关/SAD 最小）与累计位移：量滚动、镜头平移速度。
          --axis y|x|xy；--max 14 最大搜索像素（按缩放后的像素）
  region  区域均值亮度与「墨量」（过阈值像素占比）：量淡入淡出、曝光、字形消散。--thr 128 --dark
  sharp   清晰度代理：水平相邻差均值 + 拉普拉斯方差：量模糊→清晰的进度（只比归一化后的时间，不给绝对模糊半径）。
  color   颜色掩膜计数与外接框：--expr '(b-r>110)&(r<130)'（r,g,b 为 0–255 的 int 数组）量红笔/紫圈等。

注意：
  - --scale 先缩放再测，数值是缩放后的像素；换回原分辨率要乘回去（写进技法卡时注明「px @宽度」）。
  - 时间 = ss + k/fps；ss 用 -ss 输入定位，对恒定帧率的代理是准确的（录屏先 make_proxy.sh）。
  - 依赖：python3 + numpy（本机 numpy 2.0），ffmpeg。不需要 opencv。
"""
import argparse, subprocess, sys
import numpy as np

def read_frames(a, rgb=False):
    vf = [f"fps={a.fps}"]
    if a.crop: vf.append(f"crop={a.crop}")
    if a.scale: vf.append(f"scale={a.scale}")
    vf.append("format=rgb24" if rgb else "format=gray")
    probe_vf = ",".join(vf)
    # 先问尺寸：取 1 帧
    w, h = frame_size(a.video, a.ss, probe_vf)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a.ss), "-t", str(a.dur), "-i", a.video, "-vf", probe_vf,
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    c = 3 if rgb else 1
    n = len(raw) // (w * h * c)
    arr = np.frombuffer(raw[: n * w * h * c], np.uint8)
    return arr.reshape(n, h, w, c) if rgb else arr.reshape(n, h, w)

def frame_size(video, ss, vf):
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(ss), "-i", video, "-vf", vf, "-frames:v", "1", "-f", "image2pipe",
                          "-vcodec", "ppm", "-"], capture_output=True, check=True).stdout
    # PPM/PGM 头：P5/P6 w h maxval
    parts = out.split(maxsplit=4)
    return int(parts[1]), int(parts[2])

def emit(a, rows, header):
    if a.csv:
        print("t," + ",".join(header))
        for t, vals in rows: print(f"{t:.3f}," + ",".join(str(v) for v in vals))
    else:
        for t, vals in rows: print(f"{t:.3f}  " + "  ".join(f"{k}={v}" for k, v in zip(header, vals)))

def mask_from_expr(fr, expr):
    r, g, b = (fr[..., i].astype(int) for i in range(3))
    return eval(expr, {"np": np, "r": r, "g": g, "b": b})

def bbox_of(m, minfrac):
    h, w = m.shape
    cols = m.sum(0) > max(0, minfrac * h); rows = m.sum(1) > max(0, minfrac * w)
    if not cols.any() or not rows.any(): return None
    xs = np.nonzero(cols)[0]; ys = np.nonzero(rows)[0]
    return int(xs[0]), int(xs[-1]), int(ys[0]), int(ys[-1]), int(xs[-1] - xs[0]), int(ys[-1] - ys[0]), int(m.sum())

def cmd_bbox(a):
    rows = []
    fr = read_frames(a, rgb=bool(a.expr))
    for k, f in enumerate(fr):
        m = mask_from_expr(f, a.expr) if a.expr else ((f < a.thr) if a.dark else (f > a.thr))
        bb = bbox_of(m, a.minfrac)
        rows.append((a.ss + k / a.fps, bb if bb else ("-",) * 7))
    emit(a, rows, ["x0", "x1", "y0", "y1", "w", "h", "n"])

def cmd_color(a):
    if not a.expr: sys.exit("color 需要 --expr")
    cmd_bbox(a)

def best_shift(p, q, M, axis):
    """p, q: 2D float. 返回使 q 平移 (dx,dy) 后最像 p 的位移 = 内容从 p 到 q 的移动量"""
    best = (1e30, 0, 0)
    h, w = p.shape
    my = M if axis in ("y", "xy") else 0
    mx = M if axis in ("x", "xy") else 0
    a = p[my: h - my, mx: w - mx]
    for dy in range(-my, my + 1):
        for dx in range(-mx, mx + 1):
            b = q[my + dy: h - my + dy, mx + dx: w - mx + dx]   # q(y+dy, x+dx) 对 p(y, x)
            d = float(np.mean(np.abs(a - b)))
            if d < best[0]: best = (d, dx, dy)
    return best

def cmd_shift(a):
    fr = read_frames(a).astype(np.float32)
    rows = []; cx = cy = 0
    for k in range(1, len(fr)):
        if a.axis == "y":   # 行剖面（整宽平均）比 2D 快且抗噪：滚动只看竖直
            p = fr[k - 1].mean(1, keepdims=True); q = fr[k].mean(1, keepdims=True)
        elif a.axis == "x":
            p = fr[k - 1].mean(0, keepdims=True); q = fr[k].mean(0, keepdims=True)
        else:
            p, q = fr[k - 1], fr[k]
        d, dx, dy = best_shift(p, q, a.max, a.axis)
        cx += dx; cy += dy
        rows.append((a.ss + k / a.fps, (dx, dy, cx, cy, round(float(d), 2))))
    emit(a, rows, ["dx", "dy", "cum_x", "cum_y", "sad"])
    print("# 正 dy = 内容向下移（向上滚动时内容上移，dy 为负）；速度 px/帧 = |dx|,|dy| × (原宽/缩放宽) × (原fps/采样fps)", file=sys.stderr)

def cmd_region(a):
    fr = read_frames(a)
    rows = []
    for k, f in enumerate(fr):
        ink = (f < a.thr) if a.dark else (f > a.thr)
        rows.append((a.ss + k / a.fps, (round(float(f.mean()), 2), round(float(ink.mean()) * 100, 2))))
    emit(a, rows, ["mean", "ink_pct"])

def cmd_sharp(a):
    fr = read_frames(a).astype(np.float32)
    rows = []
    for k, f in enumerate(fr):
        hd = np.mean(np.abs(np.diff(f, axis=1)))
        lap = f[1:-1, 1:-1] * 4 - f[:-2, 1:-1] - f[2:, 1:-1] - f[1:-1, :-2] - f[1:-1, 2:]
        rows.append((a.ss + k / a.fps, (round(float(hd), 3), round(float(lap.var()), 1))))
    emit(a, rows, ["hdiff", "lapvar"])

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["bbox", "shift", "region", "sharp", "color"])
    ap.add_argument("video")
    ap.add_argument("--ss", type=float, required=True); ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--fps", type=float, required=True)
    ap.add_argument("--scale", default="480:-2", help="缩放后再测，默认 480 宽；给 'iw:ih' 不缩放")
    ap.add_argument("--crop", default=None)
    ap.add_argument("--thr", type=int, default=150); ap.add_argument("--dark", action="store_true")
    ap.add_argument("--minfrac", type=float, default=0.0); ap.add_argument("--expr", default=None)
    ap.add_argument("--axis", default="y", choices=["x", "y", "xy"]); ap.add_argument("--max", type=int, default=14)
    ap.add_argument("--csv", action="store_true")
    a = ap.parse_args()
    {"bbox": cmd_bbox, "shift": cmd_shift, "region": cmd_region, "sharp": cmd_sharp, "color": cmd_color}[a.cmd](a)

if __name__ == "__main__":
    main()
