#!/usr/bin/env python3
"""replicate_score.py - 逐镜头复刻打分（合并自 study_compare_A / study_compare_C / study_compare_D 三份脚本的功能并集）。

对一段原片（--ref）和我们的复刻（--ours）逐帧对齐，输出：
  整帧 SSIM、内容 SSIM（只统计有纹理的窗口，留白/暗场不虚高）、PSNR，按镜头表汇总（均值/最小值），
  分数曲线图、最差 N 帧并排图（原片 | 我们 | 3 倍差异）、并排视频（每半边 1280x720，hstack，2px 白色分隔线）。
可选：屏蔽区域（录屏 UI）、先把我们的帧过一遍 x264 再比（对压缩录屏公平）、ffmpeg 自带的 YUV SSIM、对我们的帧加微弱模糊。

用法（路径全走参数）：
  python3 replicate_score.py --ref ref.mp4 --ours 'out/render/element-%04d.png' --start 0 --frames 510 \
      --shots shots.json --out out/study/X --tag r1
  --ref    原片：视频文件 / 帧目录 / printf 模式（element-%04d.png，需配 --fps）
  --ours   我们的：视频文件 / PNG|JPG 目录（文件名末尾数字 = 帧号）/ printf 模式
  --start  原片起点秒（视频）；--frames 帧数 或 --dur 秒数（都不给 = 取镜头表最后一帧，再不行取到片尾）
  --ours-start  我们的第一帧对应的合成帧号（只渲了一段时用；默认 0）
  --fps    对齐帧率（默认取原片的 avg_frame_rate；A 是 29.97，C 是 24，D 代理是 30）
  --shots  镜头表：JSON 列表 [{"id","name","from","to"}] 或 [{"id","name","start","end","scored":false}]，
           或内联字符串 'S1:0-57,S2:58-81'；帧号 = 从 --start 起的合成帧号
  --mask   屏蔽区域 'x,y,w,h;x,y,w,h'，坐标按原片原始分辨率（录屏 UI、字幕条等）；屏蔽区不参与任何分数
  --recompress CRF  先把我们的帧用 x264 编一遍再比（压缩录屏用 24；打分与最差帧图用压缩后的，并排视频用原始的）
  --width  打分用的工作宽度（默认 960，area 缩小；0 = 原片原始分辨率）
  --win    uniform7（A/C 用，7x7 均值窗）或 gauss11（D 用，高斯 11x11 σ1.5，等价 skimage gaussian_weights）
  --content-var  内容窗口的方差阈值（默认 36 = 标准差 6 灰阶，A 的口径；C 用 9 并配 --content-dilate 6）
  --blur   对我们的帧加高斯模糊 σ（0 = 关；仅复刻比对时用，A 试过 0.4-1.0）
  --ffmpeg-ssim  另算 ffmpeg 的 YUV 整帧 SSIM（C 的口径，原片原始分辨率，不受 --mask 影响）
  --worst N / --worst-by content|ssim / --worst-gap G  最差 N 帧（默认 10 帧、按内容 SSIM 排、相邻至少隔 3 帧）
  --no-video / --no-worst / --quiet
输出（--out）：scores_<tag>.csv、report_<tag>.md/.json、curve_<tag>.png、worst<N>_<tag>.png、worst_<tag>/、side_by_side_<tag>.mp4
依赖：ffmpeg/ffprobe、numpy、scipy、Pillow；--ffmpeg-ssim 只需要 ffmpeg。
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, tempfile
import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter, binary_dilation
from PIL import Image, ImageDraw


# ---------------------------------------------------------------- 输入处理
def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,avg_frame_rate',
                          '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip().split(',')
    w, h, fr = int(out[0]), int(out[1]), out[2]
    num, den = (fr.split('/') + ['1'])[:2]
    return w, h, float(num) / float(den), fr


def seq_pattern(spec):
    """目录 -> (printf 模式, 起始号)；含 % 的模式原样返回，起始号探测。"""
    if os.path.isdir(spec):
        files = [f for f in glob.glob(os.path.join(spec, '*')) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        idx = {}
        for f in files:
            m = re.search(r'(\d+)(\.\w+)$', os.path.basename(f))
            if m:
                idx[int(m.group(1))] = (f, len(m.group(1)), m.group(2))
        if not idx:
            sys.exit(f'目录里没有带编号的图片: {spec}')
        k = min(idx)
        f, wd, ext = idx[k]
        base = os.path.basename(f)
        pre = base[:len(base) - len(ext) - wd]
        return os.path.join(spec, f'{pre}%0{wd}d{ext}'), k
    if '%' in spec:
        d, b = os.path.split(spec)
        pat = re.sub(r'%0?(\d*)d', lambda m: '(\\d{%s})' % (m.group(1) or '1,'), re.escape(b).replace('\\%', '%'))
        rx = re.compile('^' + pat + '$')
        nums = [int(re.search(r'\d+', x).group(0)) for x in os.listdir(d or '.') if rx.match(x)] if os.path.isdir(d or '.') else []
        return spec, (min(nums) if nums else 0)
    return None, None


class Src:
    """一路输入（原片或我们的），统一成 ffmpeg 输入参数 + 滤镜。"""
    def __init__(self, spec, fps, start_sec=0.0, offset=0):
        self.spec, self.fps = spec, fps
        pat, k0 = seq_pattern(spec)
        self.is_seq = pat is not None
        if self.is_seq:
            self.args = ['-framerate', str(fps), '-start_number', str(k0), '-i', pat]
        else:
            self.args = (['-ss', str(start_sec)] if start_sec else []) + ['-i', spec]
        self.offset = offset  # 我们的第一帧对应合成帧号 offset

    def chain(self, extra=''):
        f = [f'fps={self.fps}']
        if self.offset > 0:
            f.append(f'tpad=start={self.offset}:start_mode=clone')
        elif self.offset < 0:
            f.append(f'trim=start_frame={-self.offset},setpts=PTS-STARTPTS')
        return ','.join(f + ([extra] if extra else []))


def decode_rgb(src, w, h, n, blur=0.0):
    vf = src.chain(f'scale={w}:{h}:flags=area')
    cmd = ['ffmpeg', '-v', 'error', *src.args, '-vf', vf, '-frames:v', str(n), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    sz = w * h * 3
    while True:
        b = p.stdout.read(sz)
        if len(b) < sz:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.stdout.close(); p.wait()


def luma(a):
    a = a.astype(np.float64)
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


# ---------------------------------------------------------------- 指标
def ssim_map(a, b, win):
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    if win == 'gauss11':
        g = lambda x: gaussian_filter(x, 1.5, truncate=3.5); r = 5; cn = 1.0
    else:
        g = lambda x: uniform_filter(x, 7, mode='reflect'); r = 7 // 2; cn = 49.0 / 48.0
    ua, ub = g(a), g(b)
    vaa, vbb, vab = cn * (g(a * a) - ua * ua), cn * (g(b * b) - ub * ub), cn * (g(a * b) - ua * ub)
    m = ((2 * ua * ub + C1) * (2 * vab + C2)) / ((ua ** 2 + ub ** 2 + C1) * (vaa + vbb + C2))
    return m, vaa, vbb, r


def parse_mask(s, w, h, rw, rh, border):
    keep = np.ones((h, w), bool)
    sx, sy = w / rw, h / rh
    for r in filter(None, (s or '').split(';')):
        x, y, ww, hh = [float(v) for v in r.split(',')]
        keep[int(y * sy):int(np.ceil((y + hh) * sy)), int(x * sx):int(np.ceil((x + ww) * sx))] = False
    keep[:border] = False; keep[-border:] = False; keep[:, :border] = False; keep[:, -border:] = False
    return keep


def parse_shots(s, n):
    if not s:
        return [dict(id='ALL', name='all', lo=0, hi=n - 1, scored=True)]
    if os.path.isfile(s):
        raw = json.load(open(s))
        return [dict(id=x['id'], name=x.get('name', ''), lo=x.get('from', x.get('start')), hi=x.get('to', x.get('end')), scored=x.get('scored', True)) for x in raw]
    out = []
    for part in filter(None, s.split(',')):
        nm, rg = part.split(':'); lo, hi = rg.split('-')
        out.append(dict(id=nm, name='', lo=int(lo), hi=int(hi), scored=True))
    return out


def fmt(x):
    return '  -  ' if x is None or (isinstance(x, float) and np.isnan(x)) else f'{x:.4f}'


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ref', required=True); ap.add_argument('--ours', required=True)
    ap.add_argument('--start', type=float, default=0.0); ap.add_argument('--frames', type=int, default=0); ap.add_argument('--dur', type=float, default=0)
    ap.add_argument('--ours-start', type=int, default=0); ap.add_argument('--fps', type=float, default=0)
    ap.add_argument('--shots', default=''); ap.add_argument('--mask', default='')
    ap.add_argument('--recompress', type=int, default=0); ap.add_argument('--width', type=int, default=960)
    ap.add_argument('--win', default='uniform7', choices=['uniform7', 'gauss11'])
    ap.add_argument('--content-var', type=float, default=36.0); ap.add_argument('--content-dilate', type=int, default=0)
    ap.add_argument('--blur', type=float, default=0.0); ap.add_argument('--ffmpeg-ssim', action='store_true')
    ap.add_argument('--worst', type=int, default=10); ap.add_argument('--worst-by', default='content', choices=['content', 'ssim'])
    ap.add_argument('--worst-gap', type=int, default=3)
    ap.add_argument('--out', default='out/replicate'); ap.add_argument('--tag', default='latest')
    ap.add_argument('--no-video', action='store_true'); ap.add_argument('--no-worst', action='store_true'); ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    ref_is_seq = seq_pattern(a.ref)[0] is not None
    if ref_is_seq:
        if not a.fps:
            sys.exit('原片是帧序列，必须给 --fps')
        im = Image.open(glob.glob(os.path.join(a.ref, '*'))[0]) if os.path.isdir(a.ref) else Image.open(seq_pattern(a.ref)[0] % seq_pattern(a.ref)[1])
        rw, rh, fps = im.size[0], im.size[1], a.fps
        fps_str = str(fps)
    else:
        rw, rh, vfps, fps_str = probe(a.ref)
        fps = a.fps or vfps
        fps_str = str(a.fps) if a.fps else fps_str
    W = rw if a.width == 0 else a.width
    H = rh if a.width == 0 else int(round(rh * W / rw))
    shots_raw = parse_shots(a.shots, 0)
    n = a.frames or (int(round(a.dur * fps)) if a.dur else (max(s['hi'] for s in shots_raw) + 1 if a.shots else 0)) or 100000
    shots = parse_shots(a.shots, n if n < 100000 else 1)

    ref = Src(a.ref, fps_str, a.start)
    tmpdir = tempfile.mkdtemp(prefix='replscore_')
    ours_raw = Src(a.ours, fps_str, 0, a.ours_start)
    ours = ours_raw
    try:
        if a.recompress:
            rc = os.path.join(tmpdir, 'rc.mp4')
            subprocess.check_call(['ffmpeg', '-v', 'error', '-y', *ours_raw.args, '-vf', 'fps=' + fps_str + ',scale=trunc(iw/2)*2:trunc(ih/2)*2',
                                   '-c:v', 'libx264', '-crf', str(a.recompress), '-preset', 'medium', '-pix_fmt', 'yuv420p', rc])
            ours = Src(rc, fps_str, 0, a.ours_start)

        keep = parse_mask(a.mask, W, H, rw, rh, 5 if a.win == 'gauss11' else 3)
        rows = []
        for f, (rf, of) in enumerate(zip(decode_rgb(ref, W, H, n), decode_rgb(ours, W, H, n))):
            ra, oa = luma(rf), luma(of)
            if a.blur > 0:
                oa = gaussian_filter(oa, a.blur)
            m, v1, v2, _ = ssim_map(ra, oa, a.win)
            tex = (v1 > a.content_var) | (v2 > a.content_var)
            if a.content_dilate:
                tex = binary_dilation(tex, iterations=a.content_dilate)
            cm = tex & keep
            mse = float(((ra - oa)[keep] ** 2).mean())
            rows.append(dict(f=f, ssim=float(m[keep].mean()), content=float(m[cm].mean()) if cm.sum() > 200 else float('nan'),
                             psnr=99.0 if mse < 1e-9 else float(10 * np.log10(255 ** 2 / mse))))
        if not rows:
            sys.exit('没有对上任何帧：检查 --start / --ours / --ours-start')
        N = len(rows)

        # ffmpeg 自带 YUV SSIM（C 的口径）
        if a.ffmpeg_ssim:
            sf = os.path.join(tmpdir, 'ssim.txt')
            fl = (f"[0:v]{ref.chain()},trim=end_frame={N},format=yuv420p[r];"
                  f"[1:v]{ours.chain(f'scale={rw}:{rh}:flags=bicubic')},trim=end_frame={N},format=yuv420p[o];[r][o]ssim=stats_file={sf}")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', *ref.args, *ours.args, '-filter_complex', fl, '-f', 'null', '-'], check=True)
            for l in open(sf):
                mm = re.match(r'n:(\d+) .* All:([\d.]+)', l)
                if mm and int(mm.group(1)) - 1 < N:
                    rows[int(mm.group(1)) - 1]['ffssim'] = float(mm.group(2))

        # 输出：csv
        with open(os.path.join(a.out, f'scores_{a.tag}.csv'), 'w') as fh:
            fh.write('frame,ssim,content_ssim,psnr' + (',ffmpeg_ssim' if a.ffmpeg_ssim else '') + '\n')
            for r in rows:
                fh.write(f"{r['f']},{r['ssim']:.4f},{r['content']:.4f},{r['psnr']:.2f}" + (f",{r.get('ffssim', float('nan')):.4f}" if a.ffmpeg_ssim else '') + '\n')

        # 按镜头汇总
        hdr = ['shot', 'name', 'frames', 'SSIM', 'SSIM min', 'content SSIM', 'PSNR'] + (['ffmpeg SSIM'] if a.ffmpeg_ssim else [])
        L = [f'# replicate_score [{a.tag}]', '',
             f'ref={a.ref} start={a.start}s fps={fps_str}; ours={a.ours} ours-start={a.ours_start}; frames={N}; work={W}x{H} {a.win}; '
             f'content var>{a.content_var:g} dilate={a.content_dilate}; mask={a.mask or "none"}; recompress crf={a.recompress or "off"}; blur={a.blur}', '',
             '| ' + ' | '.join(hdr) + ' |', '|' + '---|' * len(hdr)]
        summ = []
        scored_rows = []
        for s in shots:
            ids = [r for r in rows[s['lo']:s['hi'] + 1]]
            if not s['scored']:
                L.append(f"| {s['id']} | {s['name']} | {s['lo']}-{s['hi']} | not replicated |" + ' - |' * (len(hdr) - 4)); continue
            if not ids:
                continue
            scored_rows += ids
            c = [r['content'] for r in ids if not np.isnan(r['content'])]
            d = dict(id=s['id'], name=s['name'], lo=s['lo'], hi=ids[-1]['f'], ssim=float(np.mean([r['ssim'] for r in ids])), ssim_min=float(min(r['ssim'] for r in ids)),
                     content=float(np.mean(c)) if c else float('nan'), psnr=float(np.mean([r['psnr'] for r in ids])))
            ff = [r['ffssim'] for r in ids if 'ffssim' in r]
            if ff: d['ffssim'] = float(np.mean(ff))
            summ.append(d)
            L.append(f"| {d['id']} | {d['name']} | {d['lo']}-{d['hi']} | {d['ssim']:.4f} | {d['ssim_min']:.4f} | {fmt(d['content'])} | {d['psnr']:.1f} |" + (f" {d['ffssim']:.4f} |" if ff else (' - |' if a.ffmpeg_ssim else '')))
        if scored_rows:
            c = [r['content'] for r in scored_rows if not np.isnan(r['content'])]
            ff = [r['ffssim'] for r in scored_rows if 'ffssim' in r]
            tot = dict(id='ALL', ssim=float(np.mean([r['ssim'] for r in scored_rows])), ssim_min=float(min(r['ssim'] for r in scored_rows)),
                       content=float(np.mean(c)) if c else float('nan'), psnr=float(np.mean([r['psnr'] for r in scored_rows])), n=len(scored_rows))
            summ.append(tot)
            L.append(f"| ALL | scored n={tot['n']} | | {tot['ssim']:.4f} | {tot['ssim_min']:.4f} | {fmt(tot['content'])} | {tot['psnr']:.1f} |" + (f" {np.mean(ff):.4f} |" if ff else (' - |' if a.ffmpeg_ssim else '')))
        txt = '\n'.join(L) + '\n'
        open(os.path.join(a.out, f'report_{a.tag}.md'), 'w').write(txt)
        json.dump(summ, open(os.path.join(a.out, f'report_{a.tag}.json'), 'w'), indent=1)
        print(txt)
        if not a.quiet:
            for r in rows:
                print(f"  f{r['f']:04d} ssim {r['ssim']:.4f} content {fmt(r['content'])} psnr {r['psnr']:5.1f}")

        # 曲线图：红 = 整帧 SSIM，蓝 = 内容 SSIM
        cw, ch = 1500, 360
        im = Image.new('RGB', (cw, ch), 'white'); d = ImageDraw.Draw(im)
        X = lambda i: 40 + i / max(1, N - 1) * (cw - 60)
        lo_y = 0.0 if min(min(r['ssim'] for r in rows), np.nanmin([r['content'] for r in rows] + [1])) < 0.4 else 0.4
        Y = lambda s: ch - 20 - (max(lo_y, s) - lo_y) / (1 - lo_y) * (ch - 40)
        for s in shots:
            d.line([(X(s['lo']), 10), (X(s['lo']), ch - 20)], fill=(210, 210, 210)); d.text((X(s['lo']) + 2, 12), s['id'], fill=(120, 120, 120))
        for y in (0.5, 0.7, 0.8, 0.85, 0.9, 1.0):
            if y > lo_y:
                d.line([(40, Y(y)), (cw - 10, Y(y))], fill=(225, 225, 255)); d.text((4, Y(y) - 5), f'{y:.2f}', fill=(80, 80, 200))
        pts = [(X(r['f']), Y(r['ssim'])) for r in rows]
        if len(pts) > 1: d.line(pts, fill=(200, 30, 30), width=2)
        pts = [(X(r['f']), Y(r['content'])) for r in rows if not np.isnan(r['content'])]
        if len(pts) > 1: d.line(pts, fill=(30, 90, 220), width=2)
        d.text((cw - 260, ch - 16), 'red = SSIM, blue = content SSIM', fill=(60, 60, 60))
        im.save(os.path.join(a.out, f'curve_{a.tag}.png'))

        # 最差 N 帧
        scored_f = {r['f'] for r in scored_rows}
        if not a.no_worst and a.worst > 0:
            key = (lambda r: r['content'] if not np.isnan(r['content']) else r['ssim']) if a.worst_by == 'content' else (lambda r: r['ssim'])
            pick = []
            for r in sorted([r for r in rows if r['f'] in scored_f], key=key):
                if all(abs(r['f'] - j) >= a.worst_gap for j in pick):
                    pick.append(r['f'])
                if len(pick) >= a.worst:
                    break
            want = set(pick)
            got = {}
            for name, src in (('ref', ref), ('ours', ours)):
                for f, fr in enumerate(decode_rgb(src, W, H, N)):
                    if f in want:
                        got[(name, f)] = fr.copy()
            wd = os.path.join(a.out, f'worst_{a.tag}')
            shutil.rmtree(wd, ignore_errors=True); os.makedirs(wd)
            tw = 384; th = int(round(tw * H / W)); cols = 5
            rowsn = (len(pick) + cols - 1) // cols
            mont = Image.new('RGB', (cols * tw, rowsn * 3 * th), (20, 20, 20))
            for k, f in enumerate(sorted(pick)):
                R, O = got[('ref', f)], got[('ours', f)]
                diff = np.clip(np.abs(R.astype(int) - O.astype(int)) * 3, 0, 255).astype(np.uint8)
                cx, cy = (k % cols) * tw, (k // cols) * 3 * th
                for i, tile in enumerate([R, O, diff]):
                    mont.paste(Image.fromarray(tile).resize((tw, th)), (cx, cy + i * th))
                ImageDraw.Draw(mont).text((cx + 4, cy + 2), f"f{f} ssim {rows[f]['ssim']:.3f} c {fmt(rows[f]['content'])}", fill=(255, 255, 0))
                pair = Image.new('RGB', (W * 2 + 2, H), (255, 255, 255)); pair.paste(Image.fromarray(R), (0, 0)); pair.paste(Image.fromarray(O), (W + 2, 0))
                pair.save(os.path.join(a.out, f'worst_{a.tag}', f"f{f:04d}_ssim{rows[f]['ssim']:.3f}.png"))
            mont.save(os.path.join(a.out, f'worst{len(pick)}_{a.tag}.png'))
            print('worst frames:', [(f, round(rows[f]['ssim'], 3), fmt(rows[f]['content'])) for f in sorted(pick)])

        # 并排视频：左原片 | 2px 白线 | 右我们的（原始未压缩），每半边 1280x720
        if not a.no_video:
            out = os.path.join(a.out, f'side_by_side_{a.tag}.mp4')
            fl = (f"[0:v]{ref.chain('scale=1280:720:flags=bicubic')},trim=end_frame={N},setpts=PTS-STARTPTS[l];"
                  f"[1:v]{ours_raw.chain('scale=1280:720:flags=bicubic')},trim=end_frame={N},setpts=PTS-STARTPTS[r];"
                  f"color=c=white:s=2x720:r={fps_str}[sep];[l][sep][r]hstack=inputs=3:shortest=1,format=yuv420p[v]")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', *ref.args, *ours_raw.args, '-filter_complex', fl, '-map', '[v]', '-frames:v', str(N),
                            '-r', fps_str, '-c:v', 'libx264', '-crf', '18', out], check=True)
            print('side-by-side ->', out)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == '__main__':
    main()
