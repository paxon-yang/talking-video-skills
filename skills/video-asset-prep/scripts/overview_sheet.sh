#!/bin/bash
# 通览拼图：按固定采样率抽帧拼成多张大图，用 Read 看图做编目。本机 ffmpeg 没有 drawtext，图上没有时间码，时间靠下面的公式算。
# usage: overview_sheet.sh <视频> <输出目录> [fps=1] [cols=8] [rows=4] [格宽=240] [起点秒=0] [时长秒=全片]
#   输出 <目录>/sheet_001.jpg …，并写 <目录>/index.txt（每张图第一格的时间）。
#   第 n 张图、第 r 行、第 c 列（都从 1 数）的时间：
#       t = 起点 + ((n-1)*cols*rows + (r-1)*cols + (c-1)) / fps
#   注意：这个时间有 ±1 个采样间隔的误差（fps 滤镜取整 + 拼图时的帧对齐，B 片实测 1fps 拼图最多偏 1.5s）。
#   拼图只用来「找大概在哪」，任何要写进技法卡的时间都要用 dense_sheet.sh / extract_frames.sh 按 -ss 重新定位。
#   长录屏（>10 分钟）先用 fps=0.5（每格 2 秒）编目，再对感兴趣的段用 fps=1–2 细看。
set -euo pipefail
v=${1:?视频}; out=${2:?输出目录}; fps=${3:-1}; cols=${4:-8}; rows=${5:-4}; w=${6:-240}; ss=${7:-0}; dur=${8:-}
mkdir -p "$out"
tflag=(); [ -n "$dur" ] && tflag=(-t "$dur")
ffmpeg -v error -y -ss "$ss" ${tflag[@]+"${tflag[@]}"} -i "$v" -vf "fps=$fps,scale=$w:-2,tile=${cols}x${rows}:padding=2:color=red" -q:v 3 "$out/sheet_%03d.jpg"
n=$(ls "$out"/sheet_*.jpg | wc -l | tr -d ' ')
total=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$v")
python3 - "$out" "$n" "$fps" "$cols" "$rows" "$ss" "${dur:-0}" "$total" <<'PY'
import sys
out, n, fps, cols, rows, ss = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6])
dur, total = float(sys.argv[7]), float(sys.argv[8])
end = ss + dur if dur > 0 else total
per = cols * rows
with open(f"{out}/index.txt", "w") as f:
    f.write(f"# t = {ss} + ((n-1)*{per} + (r-1)*{cols} + (c-1)) / {fps}   (n=图号, r=行, c=列, 从 1 数；误差 ±{1/fps:.2f}s)\n")
    for k in range(1, n + 1):
        t0 = ss + (k - 1) * per / fps
        f.write(f"sheet_{k:03d}.jpg  {t0:.2f}s - {min(t0 + (per - 1) / fps, end):.2f}s\n")
print(f"{n} 张拼图 -> {out}，时间对照 {out}/index.txt")
PY
