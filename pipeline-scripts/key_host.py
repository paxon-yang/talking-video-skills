#!/usr/bin/env python3
"""Green-screen host -> alpha host layer for Video1 "host + motion in one space".

HeyGen's green is a flat synthetic colour (measured (12,203,65) on every background pixel of leo_sample_v1.mp4, no light falloff), so a
colour-difference key with exact UNMIXING beats a generic chroma key: for P = a*F + (1-a)*K with K known,
    d(P) = G - max(R, B)            (screen dominance; K gives dK = 138)
    a    = 1 - clamp((d(P) - lo) / (dK*hi - lo))   then a tiny choke + 0.6 px blur on the alpha edge band only
    F    = (P - (1-a) K) / a        (removes the green that is MIXED into hair / motion-blurred fingers / glasses rims)
    despill: G <= max(R,B) + spill  (residual green cast on skin facing the screen)
Chroma is upsampled with full_chroma_int before keying (4:2:0 blocks otherwise give stair-stepped edges).

usage:
  python3 src/video1/integration/key_host.py --src public/projects/video1/heygen/leo_sample_v1.mp4 --out public/projects/video1/host_alpha/leo_v1
  options: --start S --dur S --lo 18 --hi 0.92 --spill 4 --crf 24 --prores (also write a ProRes 4444 for comparison) --ffkey (also write
           ffmpeg chromakey+despill for comparison) --frames 65,120 (dump keyed RGBA PNGs of these source frames for inspection)
outputs (paths under --out):
  host.webm         VP9 yuva420p, source fps (25), straight alpha, unmixed colour   -> <OffthreadVideo transparent>
  m_NNNNNN.png      alpha at 960x540 (8-bit) per source frame                         -> silhouette.json (scripts/matte_silhouette.py),
                                                                                        CSS masks (silhouette reveal, shadows on the host)
  mp_NNNNNN.png     the same without the desk (person only)                          -> silhouette reveal / fills (the desk is not him)
  energy.json      per-frame motion energy of the alpha (hands region / whole body)   -> gesture-timed triggers
  manifest.json     {src, fps, width, height, mode:'greenkey', ranges:[{start,end,cutout}]} (same shape as matte_pipeline.py)
  rgba_NNNNNN.png   only with --frames
"""
import argparse, json, os, subprocess, sys, time
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, grey_erosion

ap = argparse.ArgumentParser()
ap.add_argument('--src', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--start', type=float, default=0)
ap.add_argument('--dur', type=float, default=None)
ap.add_argument('--key', default='auto', help='R,G,B of the screen or auto (median of the top rows)')
ap.add_argument('--lo', type=float, default=18.0, help='dominance below this = fully opaque')
ap.add_argument('--hi', type=float, default=0.92, help='fraction of the key dominance that is fully transparent')
ap.add_argument('--choke', type=int, default=1, help='alpha erosion px (0 = off)')
ap.add_argument('--soft', type=float, default=0.6, help='alpha blur sigma px on the edge band')
ap.add_argument('--spill', type=float, default=4.0)
ap.add_argument('--desk-top', dest='desk_top', type=float, default=0.866, help='source desk top (fraction of H) for the person-only mattes mp_*.png; 0 = none')
ap.add_argument('--precomp', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'remotion_vp9_curve.json'), help='measured decode curve JSON; its inverse is applied to the colour before encoding ("" = off)')
ap.add_argument('--extend', type=float, default=2.5, help='edge colour extension sigma px (0 = pure unmix)')
ap.add_argument('--crf', default='24')
ap.add_argument('--matte', default='960x540')
ap.add_argument('--prores', action='store_true')
ap.add_argument('--ffkey', action='store_true')
ap.add_argument('--frames', default='')
ap.add_argument('--sharpen', type=float, default=0.0, help='luma-only unsharp amount on the solid interior (0 = off; v3: 0.65)')
ap.add_argument('--sharpen-r', dest='sharpen_r', type=float, default=1.2, help='unsharp gaussian sigma px')
ap.add_argument('--sharpen-clip', dest='sharpen_clip', type=float, default=9.0, help='max |detail| added (levels) - no halos on glasses / dark edges')
ap.add_argument('--sharpen-core', dest='sharpen_core', type=float, default=1.5, help='detail below this (levels) is not boosted - no noise on skin')
a = ap.parse_args()

os.makedirs(a.out, exist_ok=True)
pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=width,height,r_frame_rate:format=duration', '-of', 'json', a.src], capture_output=True, text=True).stdout)
W, H = int(pr['streams'][0]['width']), int(pr['streams'][0]['height'])
n_, d_ = (int(x) for x in pr['streams'][0]['r_frame_rate'].split('/'))
fps = n_ / d_
dur = a.dur if a.dur is not None else float(pr['format']['duration']) - a.start
f0 = int(round(a.start * fps))
mw, mh = (int(v) for v in a.matte.split('x'))
dump = {int(x) for x in a.frames.split(',') if x}

dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{a.start}', '-t', f'{dur}', '-i', a.src,
                        '-vf', 'scale=flags=bicubic+accurate_rnd+full_chroma_int+full_chroma_inp,format=rgb24', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                       stdout=subprocess.PIPE)
webm = os.path.join(a.out, 'host.webm')
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', f'{fps}', '-i', '-',
                        # explicit BT.709 (limited range) conversion + tags: untagged rgb->yuv defaults to BT.601 in ffmpeg while Chrome decodes HD as
                        # BT.709 -> the host rendered ~+12 R / -6 B warmer in Remotion than in ffmpeg (measured on the desk, integration test 1)
                        '-vf', 'scale=out_color_matrix=bt709:out_range=tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
                        '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-b:v', '0', '-crf', a.crf, '-row-mt', '1', '-deadline', 'good', '-cpu-used', '4',
                        '-auto-alt-ref', '0', webm], stdin=subprocess.PIPE)
pro = None
if a.prores:
    pro = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', f'{fps}', '-i', '-',
                            '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', os.path.join(a.out, 'host_prores4444.mov')], stdin=subprocess.PIPE)

CURVE = None
if a.precomp:
    _c = json.load(open(a.precomp)); CURVE = (np.array(_c['in'], np.float32), np.maximum.accumulate(np.array(_c['out'], np.float32)))
K = None
energy = []
prev_small = None
t0 = time.time()
k = 0
fsz = W * H * 3
while True:
    buf = dec.stdout.read(fsz)
    if len(buf) < fsz:
        break
    P = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32)
    if K is None:
        K = np.array([float(v) for v in a.key.split(',')], np.float32) if a.key != 'auto' else np.median(P[:40].reshape(-1, 3), axis=0)
        dK = K[1] - max(K[0], K[2])
        print('key', K, 'dominance', dK)
    d = P[..., 1] - np.maximum(P[..., 0], P[..., 2])
    al = 1.0 - np.clip((d - a.lo) / (dK * a.hi - a.lo), 0, 1)
    if a.choke:
        al = np.minimum(al, grey_erosion(al, size=(2 * a.choke + 1, 2 * a.choke + 1)) * 0.5 + al * 0.5)
    if a.soft > 0:
        band = (al > 0.002) & (al < 0.998)
        bl = gaussian_filter(al, a.soft)
        al = np.where(gaussian_filter(band.astype(np.float32), 1.5) > 0.01, bl, al)
    al = np.clip(al, 0, 1)
    # unmix: F = (P - (1-a)K)/a  (only where a is meaningful)
    safe = np.maximum(al, 0.06)[..., None]
    F = (P - (1 - al)[..., None] * K[None, None, :]) / safe
    F = np.where((al > 0.995)[..., None], P, F)
    # residual spill
    mx = np.maximum(F[..., 0], F[..., 2])
    F[..., 1] = np.minimum(F[..., 1], mx + a.spill)
    F = np.clip(F, 0, 255)
    # edge colour extension: HeyGen's own green composite is not a linear mix at the silhouette, so unmixing over-subtracts green there
    # (a 1 px magenta line on arms/shoulders in the first test). In the semi-transparent band take the colour of the nearest solid pixels
    # (normalised convolution), blending back to the unmixed colour as alpha -> 1.
    if a.extend > 0:
        solid = (al > 0.97).astype(np.float32)
        num = np.stack([gaussian_filter(P[..., c] * solid, a.extend) for c in range(3)], -1)
        den = gaussian_filter(solid, a.extend)[..., None]
        ext = num / np.maximum(den, 1e-4)
        w = np.clip((0.97 - al) / 0.5, 0, 1)[..., None] * (den > 0.02)
        F = F * (1 - w) + ext * w
    if a.sharpen > 0:
        # luma-only unsharp mask, interior only (alpha eroded 3 px: the silhouette edge and the semi-transparent hair band are untouched),
        # cored (tiny detail = noise / skin texture not boosted) and soft-clipped (no bright halo on glasses rims)
        Y = 0.2126 * F[..., 0] + 0.7152 * F[..., 1] + 0.0722 * F[..., 2]
        det = Y - gaussian_filter(Y, a.sharpen_r)
        mag = np.abs(det)
        det = np.sign(det) * np.clip(mag - a.sharpen_core, 0, None)
        det = a.sharpen_clip * np.tanh(det / a.sharpen_clip)
        wint = grey_erosion((al > 0.99).astype(np.float32), size=(7, 7))
        F = np.clip(F + (a.sharpen * wint * det)[..., None], 0, 255)
    if CURVE is not None:  # Remotion's decode crushes the shadow toe (28 -> 19); pre-lift with the inverse of the measured curve
        F = np.interp(F, CURVE[1], CURVE[0])
    rgba = np.concatenate([F, (al * 255)[..., None]], axis=2).round().astype(np.uint8)
    enc.stdin.write(rgba.tobytes())
    if pro:
        pro.stdin.write(rgba.tobytes())
    src_f = f0 + k
    m = Image.fromarray((al * 255).round().astype(np.uint8)).resize((mw, mh), Image.BILINEAR)
    m.save(os.path.join(a.out, f'm_{src_f:06d}.png'))
    # person-only matte (desk rows removed with a 6 px ramp at the desk top): silhouette effects (reveal, rim fill) must not include the desk
    if a.desk_top > 0:
        yd = int(a.desk_top * mh) - 1
        ramp = np.ones(mh, np.float32); ramp[yd - 3:yd + 3] = np.linspace(1, 0, 6); ramp[yd + 3:] = 0
        Image.fromarray((np.asarray(m, np.float32) * ramp[:, None]).round().astype(np.uint8)).save(os.path.join(a.out, f'mp_{src_f:06d}.png'))
    small = np.asarray(m, np.float32) / 255
    if prev_small is not None:
        diff = np.abs(small - prev_small)
        # hands region in SOURCE fractions: below the chin (y > 0.47 H) and above the desk top (y < 0.865 H); whole body = everything
        hy0, hy1 = int(0.47 * mh), int(0.865 * mh)
        energy.append({'f': src_f, 'hands': round(float(diff[hy0:hy1].mean()) * 1000, 3), 'body': round(float(diff.mean()) * 1000, 3)})
    else:
        energy.append({'f': src_f, 'hands': 0.0, 'body': 0.0})
    prev_small = small
    if src_f in dump:
        Image.fromarray(rgba).save(os.path.join(a.out, f'rgba_{src_f:06d}.png'))
    k += 1
dec.wait()
enc.stdin.close(); enc.wait()
if pro:
    pro.stdin.close(); pro.wait()
el = time.time() - t0
print(f'frames {k}  {el:.1f} s  ({el / max(1, k) * 1000:.0f} ms/frame)')
if a.ffkey:
    hexk = '0x%02X%02X%02X' % tuple(int(v) for v in K)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a.start}', '-t', f'{dur}', '-i', a.src, '-vf',
                    f'scale=flags=bicubic+full_chroma_int,format=yuva444p,chromakey={hexk}:0.10:0.06,despill=type=green:mix=0.6:expand=0.2,format=yuva420p',
                    '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-b:v', '0', '-crf', a.crf, '-auto-alt-ref', '0', os.path.join(a.out, 'host_ffchromakey.webm')], check=True)
json.dump({'src': os.path.relpath(a.src, 'public') if a.src.startswith('public') else a.src, 'fps': fps, 'width': W, 'height': H, 'mode': 'greenkey',
           'ranges': [{'start': f0, 'end': f0 + k, 'cutout': os.path.relpath(webm, 'public')}]}, open(os.path.join(a.out, 'manifest.json'), 'w'), indent=1)
json.dump({'fps': fps, 'unit': 'mean |d alpha| x1000 between consecutive frames (960x540 matte)', 'frames': energy}, open(os.path.join(a.out, 'energy.json'), 'w'))
for p in [webm] + ([os.path.join(a.out, 'host_prores4444.mov')] if a.prores else []) + ([os.path.join(a.out, 'host_ffchromakey.webm')] if a.ffkey else []):
    print(os.path.basename(p), f'{os.path.getsize(p) / 1e6:.2f} MB')
