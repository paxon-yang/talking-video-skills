#!/usr/bin/env python3
"""pose_fit_css3d.py - 对每一帧拟合「平面素材的 CSS 3D 位姿」（用来拿 perspective 距离、后仰角、缩放这类可读的参数）。
模型：屏幕点 = 透视( Rz(c) Ry(b) Rx(a) · s·(u-w/2, v-h/2, 0) + (tx,ty,0) )，透视距离 P，消失点 = 画面中心（--center，默认取帧中心）。
等价 CSS：perspective:P（原点在画面中心）; transform: translate(tx,ty) rotateZ(c) rotateY(b) rotateX(a) scale(s)，transform-origin 居中，
且平面中心在平移前位于画面中心。做法：SIFT 匹配 → RANSAC（宽松）→ 稳健最小二乘（soft_l1）拟合 7 个参数（不固定 P 时 P 也是未知数）。
用法：
  python3 pose_fit_css3d.py plate.png ox,oy,w,h '<原片帧模式>' 0-80 out.txt [--frame-offset 1] [--P 3000] [--init tx,ty,s,a,b,c[,P]] [--fullh H] [--center 960,540]
输出每行：帧号 内点数 残差中位数px tx ty s ax by cz [P]（弧度）。
局限：面板大半出画时 rotateX 符号有歧义（A 的 f151–153 在 −0.27 / +0.28 间翻），此时改用 plane_track.py 的 8 自由度单应矩阵。
先用本脚本在稳定帧上不固定 P 拟合一次拿 P（A 得到约 3000），再用 --P 固定。
依赖：opencv-python-headless、scipy、numpy。
"""
import argparse, cv2, numpy as np
from scipy.optimize import least_squares

ap = argparse.ArgumentParser(); ap.add_argument('plate'); ap.add_argument('rect'); ap.add_argument('frames_pattern'); ap.add_argument('frames'); ap.add_argument('out')
ap.add_argument('--frame-offset', type=int, default=0); ap.add_argument('--P', type=float, default=0); ap.add_argument('--init', default=''); ap.add_argument('--fullh', type=int, default=0)
ap.add_argument('--center', default='')
a = ap.parse_args()
ox, oy, w, h = map(int, a.rect.split(','))
P0 = cv2.imread(a.plate, cv2.IMREAD_GRAYSCALE)[oy:oy + h, ox:ox + w]
if a.fullh: h = a.fullh  # 裁出的是更高平面的上半部分：保持平面中心不变
fr = []
for p in a.frames.split(','):
    if '-' in p:
        ab, st = (p.split(':') + ['1'])[:2]; x, y = ab.split('-'); fr += range(int(x), int(y) + 1, int(st))
    else:
        fr.append(int(p))
sift = cv2.SIFT_create(5000); kp1, d1 = sift.detectAndCompute(P0, None); bf = cv2.BFMatcher()
first = cv2.imread(a.frames_pattern % (fr[0] + a.frame_offset), cv2.IMREAD_GRAYSCALE)
CX, CY = map(float, a.center.split(',')) if a.center else (first.shape[1] / 2, first.shape[0] / 2)


def project(q, uv):
    tx, ty, s, ax, by, cz = q[:6]; Pp = q[6] if len(q) > 6 else a.P
    X = s * (uv[:, 0] - w / 2); Y = s * (uv[:, 1] - h / 2); Z = np.zeros_like(X)
    ca, sa = np.cos(ax), np.sin(ax); Y, Z = Y * ca - Z * sa, Y * sa + Z * ca
    cb, sb = np.cos(by), np.sin(by); X, Z = X * cb + Z * sb, -X * sb + Z * cb
    cc, sc = np.cos(cz), np.sin(cz); X, Y = X * cc - Y * sc, X * sc + Y * cc
    X = X + tx; Y = Y + ty
    k = Pp / (Pp - Z)
    return np.stack([CX + X * k, CY + Y * k], 1)


prev = np.array(list(map(float, a.init.split(',')))) if a.init else None
out = open(a.out, 'w')
for f in fr:
    I = cv2.imread(a.frames_pattern % (f + a.frame_offset), cv2.IMREAD_GRAYSCALE)
    kp2, d2 = sift.detectAndCompute(I, None)
    ms = bf.knnMatch(d1, d2, k=2) if d2 is not None and len(kp2) > 2 else []
    good = [m for m, n in (x for x in ms if len(x) == 2) if m.distance < 0.75 * n.distance]
    if len(good) < 10:
        out.write(f'{f} FAIL\n'); print(f, 'FAIL'); continue
    src = np.float32([kp1[m.queryIdx].pt for m in good]); dst = np.float32([kp2[m.trainIdx].pt for m in good])
    Hm, inl = cv2.findHomography(src, dst, cv2.RANSAC, 8.0)
    if inl is None or inl.sum() < 10:
        out.write(f'{f} FAIL\n'); print(f, 'FAIL'); continue
    inl = inl.ravel().astype(bool); s_, d_ = src[inl].astype(float), dst[inl].astype(float)
    if prev is None:
        c = d_.mean(0); sp = np.std(d_, 0).mean() / max(1e-3, np.std(s_, 0).mean())
        q0 = np.array([c[0] - CX, c[1] - CY, sp, 0, 0, 0] + ([1200.0] if a.P == 0 else []))
    else:
        q0 = prev.copy()
    lo = [-5000, -5000, 0.05, -1.3, -1.0, -0.5] + ([300] if a.P == 0 else [])
    hi = [5000, 5000, 20, 1.3, 1.0, 0.5] + ([8000] if a.P == 0 else [])
    q0 = np.clip(q0, np.array(lo) + 1e-6, np.array(hi) - 1e-6)
    res = lambda q: (project(q, s_) - d_).ravel()
    r = least_squares(res, q0, loss='soft_l1', f_scale=2.0, bounds=(lo, hi), x_scale='jac')
    q = r.x; e = np.abs(res(q)).reshape(-1, 2); med = float(np.median(np.hypot(e[:, 0], e[:, 1])))
    prev = q
    out.write(f'{f} {int(inl.sum())} {med:.2f} ' + ' '.join(f'{v:.6g}' for v in q) + '\n'); out.flush()
    print(f, int(inl.sum()), round(med, 2), np.round(q, 4).tolist(), flush=True)
