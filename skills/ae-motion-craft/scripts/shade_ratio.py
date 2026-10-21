#!/usr/bin/env python3
"""shade_ratio.py - 屏幕空间暗角/光照衰减的测量：把原片帧按单应矩阵拉正，与干净的 plate 做逐格亮度比值，输出网格表。
（A 复刻用它发现：面板的渐暗是固定在屏幕上的暗角，不是面板自己的渐变；底部中央约 0.62、底角约 0.2。）
用法：
  python3 shade_ratio.py plate.png ox,oy,w,h track.txt '<原片帧模式>' 230,300 [--frame-offset 1] [--grid 12x9]
    track.txt 是 plane_track.py 的输出；帧列表用逗号分隔。
每帧输出 grid 行 × 列 的比值表（只统计 plate 亮度 >240 的白底处，格内像素 >800 才算数）；比值随帧基本不变 = 屏幕空间暗角。
依赖：opencv-python-headless、numpy。
"""
import argparse, cv2, numpy as np

ap = argparse.ArgumentParser(); ap.add_argument('plate'); ap.add_argument('rect'); ap.add_argument('track'); ap.add_argument('frames_pattern'); ap.add_argument('frames')
ap.add_argument('--frame-offset', type=int, default=0); ap.add_argument('--grid', default='12x9')
a = ap.parse_args()
ox, oy, w, h = map(int, a.rect.split(','))
P = cv2.imread(a.plate, 0)[oy:oy + h, ox:ox + w].astype(np.float32)
Hs = {}
for l in open(a.track):
    t = l.split()
    if len(t) >= 12 and t[1] != 'FAIL': Hs[int(t[0])] = np.array(list(map(float, t[3:12]))).reshape(3, 3)
GX, GY = map(int, a.grid.split('x'))
for f in map(int, a.frames.split(',')):
    I = cv2.imread(a.frames_pattern % (f + a.frame_offset), 0).astype(np.float32)
    Hh, Ww = I.shape
    S = cv2.warpPerspective(P, Hs[f], (Ww, Hh), borderValue=-1)
    m = S > 240; cw, ch = Ww // GX, Hh // GY
    print(f)
    for j in range(GY):
        row = []
        for i in range(GX):
            ys, xs = slice(j * ch, (j + 1) * ch), slice(i * cw, (i + 1) * cw); mm = m[ys, xs]
            row.append('  -- ' if mm.sum() < 800 else f'{np.median(I[ys, xs][mm] / S[ys, xs][mm]):5.2f}')
        print(f'  y{j * ch + ch // 2:4d} ' + ' '.join(row))
