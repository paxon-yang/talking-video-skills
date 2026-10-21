#!/usr/bin/env python3
"""template_track.py - 多尺度模板跟踪：从 plate 图里裁一块模板，在原片每帧里找（位置 + 缩放），用来跟踪卡片、图标这类平移 + 缩放的元素。
用法：
  python3 template_track.py plate.png x,y,w,h '<原片帧模式>' 0-80 smin smax [blur] [cx0,cx1] [--frame-offset 1]
    x,y,w,h   模板在 plate 里的矩形；smin/smax 缩放搜索范围（步长 0.01）；blur 给模板加高斯模糊（原片里虚化的卡片用）
    cx0,cx1   限定匹配中心的 x 范围（排除相似的邻卡）
输出每行：帧号 缩放 左上x 左上y 得分 centre cx cy
依赖：opencv-python-headless、numpy。
"""
import sys, cv2, numpy as np

args = [x for x in sys.argv[1:] if not x.startswith('--')]
off = int(sys.argv[sys.argv.index('--frame-offset') + 1]) if '--frame-offset' in sys.argv else 0
if '--frame-offset' in sys.argv:
    args.remove(sys.argv[sys.argv.index('--frame-offset') + 1])
plate, crop, pattern, frames, smin, smax = args[:6]
smin, smax = float(smin), float(smax)
blur = float(args[6]) if len(args) > 6 else 0
roi = list(map(int, args[7].split(','))) if len(args) > 7 else None
x, y, w, h = map(int, crop.split(','))
P = cv2.imread(plate, cv2.IMREAD_GRAYSCALE)[y:y + h, x:x + w].astype(np.float32)
fr = []
for p in frames.split(','):
    if '-' in p:
        ab, st = (p.split(':') + ['1'])[:2]; a, b = ab.split('-'); fr += range(int(a), int(b) + 1, int(st))
    else:
        fr.append(int(p))
for f in fr:
    I = cv2.imread(pattern % (f + off), cv2.IMREAD_GRAYSCALE)
    if I is None:
        print(f, 'MISSING'); continue
    I = I.astype(np.float32); best = None
    for s in np.arange(smin, smax + 1e-6, 0.01):
        T = cv2.resize(P, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        if blur > 0: T = cv2.GaussianBlur(T, (0, 0), blur)
        if T.shape[0] >= I.shape[0] or T.shape[1] >= I.shape[1]: continue
        r = cv2.matchTemplate(I, T, cv2.TM_CCOEFF_NORMED)
        if roi:
            cx = np.arange(r.shape[1]) + T.shape[1] / 2
            r[:, (cx < roi[0]) | (cx > roi[1])] = -1
        _, mv, _, ml = cv2.minMaxLoc(r)
        if best is None or mv > best[0]: best = (mv, s, ml)
    mv, s, ml = best
    print(f, round(s, 3), ml[0], ml[1], round(mv, 3), 'centre', round(ml[0] + w * s / 2, 1), round(ml[1] + h * s / 2, 1), flush=True)
