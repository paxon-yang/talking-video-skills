#!/usr/bin/env python3
"""plane_track.py - 平面跟踪：对每一帧求「素材平面（我们用真实 DOM 渲出的 plate 图）→ 原片画面」的单应矩阵 H。
流程：SIFT 匹配 + RANSAC 给初值（失败则沿用上一帧）→ ECC（MOTION_HOMOGRAPHY，半分辨率）精修；
ECC 结果偏离 RANSAC 初值太多（面板中心区 >25px）或相关系数 <0.9 时退回初值（输出里 cc 取负号标记）。
H 的方向：plate 局部像素 (u,v) → 原片屏幕像素 (x,y)，3x3 行主序。再用 hom_to_css.py 转成 CSS matrix3d。

用法：
  python3 plane_track.py plate.png ox,oy,w,h '<原片帧模式>' 0-80 out.txt [--frame-offset 1] [--mask x0,y0,x1,y1 ...] [--prev h00,...,h22] [--nosift]
    plate.png     素材平面所在的截图；ox,oy,w,h = 平面在该图里的矩形（局部坐标原点 = 左上角）
    <原片帧模式>  如 analysis/replicate/A/frames/f%04d.jpg（printf 模式，帧号 = 序号 + --frame-offset；A 的帧从 f0001 起，所以 offset=1）
    帧范围        '0-80'、'0-80:2'、'5,9,12-20' 可混用
    --mask        局部坐标里要忽略的矩形（会动的内容，如滑入的文字）；可重复
输出每行：帧号 内点数 cc h00 h01 h02 h10 h11 h12 h20 h21 h22（FAIL 行 = 没跟上）
依赖：opencv-python-headless、numpy（本机 pip --user 已装）。
教训（A 复刻）：文字要对齐，误差必须小于 1px；6 参数的旋转/缩放模型在面板大半出画时 rotateX 正负号会来回翻，
所以关键帧段直接用 8 自由度单应矩阵；平滑窗口会让快速镜头滞后，别平滑；原片里面板背景与内容有视差时单平面对不上，需拆成两层分别跟踪。
"""
import argparse, cv2, numpy as np


def parse_frames(s):
    out = []
    for p in s.split(','):
        if '-' in p:
            ab, st = (p.split(':') + ['1'])[:2]; x, y = ab.split('-'); out += range(int(x), int(y) + 1, int(st))
        else:
            out.append(int(p))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plate'); ap.add_argument('rect'); ap.add_argument('frames_pattern'); ap.add_argument('frames'); ap.add_argument('out')
    ap.add_argument('--frame-offset', type=int, default=0); ap.add_argument('--mask', action='append', default=[]); ap.add_argument('--prev', default=None)
    ap.add_argument('--nosift', action='store_true')
    a = ap.parse_args()
    ox, oy, w, h = map(int, a.rect.split(','))
    P = cv2.imread(a.plate, cv2.IMREAD_GRAYSCALE)[oy:oy + h, ox:ox + w]
    M = np.full(P.shape, 255, np.uint8)
    for m in a.mask:
        x0, y0, x1, y1 = map(int, m.split(',')); M[y0:y1, x0:x1] = 0
    sift = cv2.SIFT_create(4000); kp1, d1 = sift.detectAndCompute(P, M); bf = cv2.BFMatcher()
    S = np.diag([0.5, 0.5, 1.0]); Si = np.linalg.inv(S)
    prev = np.array(list(map(float, a.prev.split(',')))).reshape(3, 3) if a.prev else None
    Ph = cv2.resize(P, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA).astype(np.float32)
    out = open(a.out, 'w')
    for f in parse_frames(a.frames):
        I = cv2.imread(a.frames_pattern % (f + a.frame_offset), cv2.IMREAD_GRAYSCALE)
        if I is None:
            out.write(f'{f} FAIL\n'); continue
        Hs, ninl = None, 0
        if not a.nosift:
            kp2, d2 = sift.detectAndCompute(I, None)
            if d2 is not None and len(kp2) > 10:
                ms = bf.knnMatch(d1, d2, k=2)
                good = [m for m, n in (x for x in ms if len(x) == 2) if m.distance < 0.75 * n.distance]
                if len(good) >= 12:
                    src = np.float32([kp1[m.queryIdx].pt for m in good]); dst = np.float32([kp2[m.trainIdx].pt for m in good])
                    Hs, inl = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
                    ninl = int(inl.sum()) if inl is not None else 0
                    if ninl < 15: Hs = None
        H0 = Hs if Hs is not None else prev
        if H0 is None:
            out.write(f'{f} FAIL\n'); continue
        Ih = cv2.resize(I, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA).astype(np.float32)
        W0 = (S @ H0 @ Si).astype(np.float32); W0 /= W0[2, 2]
        cc = -1.0
        try:
            cc, W = cv2.findTransformECC(Ph, Ih, W0, cv2.MOTION_HOMOGRAPHY, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-5), None, 3)
            H = Si @ W.astype(np.float64) @ S; H /= H[2, 2]
            pts = np.array([[w * .2, w * .8, w * .5, w * .2, w * .8], [h * .1, h * .1, h * .4, h * .6, h * .6], [1, 1, 1, 1, 1]], float)
            A = H @ pts; A = A[:2] / A[2]; B = H0 @ pts; B = B[:2] / B[2]
            if np.abs(A - B).max() > 25 or cc < 0.9: H = H0; cc = -abs(cc)
        except cv2.error:
            H = H0
        prev = H
        out.write(f'{f} {ninl} {cc:.4f} ' + ' '.join(f'{v:.7g}' for v in H.flatten()) + '\n'); out.flush()
        c = H @ np.array([[0, w, w, 0], [0, 0, h, h], [1, 1, 1, 1]], float); c = c[:2] / c[2]
        print(f, ninl, round(cc, 3), 'corners', np.round(c.T).astype(int).tolist(), flush=True)


if __name__ == '__main__':
    main()
