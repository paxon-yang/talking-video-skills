#!/bin/bash
# 逐帧导出 PNG（放大看单帧、做并排对照的原片一侧）。文件名带时间（毫秒），不靠 drawtext。
# usage: extract_frames.sh <视频> <输出目录> <起点秒> <时长秒> <fps> [宽=原尺寸]
#   单帧：时长给 1/fps，例如 extract_frames.sh src.mp4 out 12.913 0.034 30
set -euo pipefail
v=${1:?视频}; out=${2:?输出目录}; ss=${3:?起点秒}; dur=${4:?时长秒}; fps=${5:?fps}; w=${6:-}
mkdir -p "$out"
vf="fps=$fps"; [ -n "$w" ] && vf="$vf,scale=$w:-2"
tmp=$(mktemp -d)
ffmpeg -v error -y -ss "$ss" -t "$dur" -i "$v" -vf "$vf" "$tmp/f_%04d.png"
python3 - "$tmp" "$out" "$ss" "$fps" <<'PY'
import os, sys, shutil
tmp, out, ss, fps = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
fs = sorted(os.listdir(tmp))
for k, f in enumerate(fs):
    t = ss + k / fps
    shutil.move(os.path.join(tmp, f), os.path.join(out, f"t{int(round(t * 1000)):08d}ms.png"))
print(f"{len(fs)} 帧 -> {out}（文件名 = 毫秒时间）")
PY
rmdir "$tmp"
