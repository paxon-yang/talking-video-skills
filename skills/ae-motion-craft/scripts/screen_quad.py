#!/usr/bin/env python3
"""粗测「亮屏」四角（实拍显示器、手机屏等），给 ScreenComposite 当初值或核对四角跟踪 JSON。来自 D/W3 quad.py，改成参数化。

  python3 screen_quad.py <视频> --ss 811 --dur 2 --fps 10 --thr 215 [--crop 408:720:436:0] [--ymin 0 --ymax 9999] [--min-px 3000]

做法：灰度 > thr 的像素中，x+y 最小/最大 = 左上/右下，x−y 最大/最小 = 右上/左下。坐标是裁剪后（未缩放）的像素。
局限（D 实测）：屏幕某个角是暗内容时阈值会提前停（那一角可偏 20+ px）；只适合屏幕明显比周围亮的帧。
精确的逐帧四角要用 Mocha/AE 跟踪，或在本机装 opencv 后 findHomography（本机目前没有 opencv）。
输出可直接改写成 ScreenComposite 的 quad 关键帧：[{"frame":f,"quad":[[x,y]×4 按 TL,TR,BR,BL]}]（--json）。
"""
import argparse, json, subprocess
import numpy as np

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--ss", type=float, required=True); ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--fps", type=float, default=10); ap.add_argument("--thr", type=int, default=215)
    ap.add_argument("--crop", default=None); ap.add_argument("--ymin", type=int, default=0); ap.add_argument("--ymax", type=int, default=10**6)
    ap.add_argument("--min-px", type=int, default=3000); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    vf = f"fps={a.fps}" + (f",crop={a.crop}" if a.crop else "") + ",format=gray"
    hdr = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a.ss), "-i", a.video, "-vf", vf, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "ppm", "-"], capture_output=True, check=True).stdout.split(maxsplit=4)
    W, H = int(hdr[1]), int(hdr[2])
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a.ss), "-t", str(a.dur), "-i", a.video, "-vf", vf, "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw[: len(raw) // (W * H) * W * H], np.uint8).reshape(-1, H, W)
    keys = []
    for i, f in enumerate(fr):
        m = f > a.thr; m[: a.ymin] = False; m[min(H, a.ymax):] = False
        ys, xs = np.nonzero(m); t = a.ss + i / a.fps
        if len(xs) < a.min_px:
            if not a.json: print(f"{t:.2f} n={len(xs)} -")
            continue
        p, q = xs + ys, xs - ys
        tl = (int(xs[p.argmin()]), int(ys[p.argmin()])); br = (int(xs[p.argmax()]), int(ys[p.argmax()]))
        tr = (int(xs[q.argmax()]), int(ys[q.argmax()])); bl = (int(xs[q.argmin()]), int(ys[q.argmin()]))
        keys.append({"t": round(t, 3), "quad": [tl, tr, br, bl]})
        if not a.json: print(f"{t:.2f} n={len(xs)} TL{tl} TR{tr} BR{br} BL{bl}")
    if a.json: print(json.dumps(keys))

if __name__ == "__main__":
    main()
