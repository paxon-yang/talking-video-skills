#!/bin/bash
# 窗口内密集抽帧拼成一张图（逐帧目视：动作分几步、哪帧硬切、有没有隔帧重复）。
# usage: dense_sheet.sh <视频> <输出.jpg> <起点秒> <时长秒> <fps> [cols=6] [格宽=320] [crop=w:h:x:y]
#   第 k 格（从 0 数，按行从左到右）的时间 = 起点 + k / fps。格与格之间是红色细缝。
#   常用：12fps 看大致节奏，24/30fps（=原片帧率）看单帧细节；时长一般 0.5–3s，格数 ≤ 60。
#   crop 先裁再缩放：放大局部细节（例如只看按钮 crop=400:200:760:600）。
set -euo pipefail
v=${1:?视频}; out=${2:?输出 jpg}; ss=${3:?起点秒}; dur=${4:?时长秒}; fps=${5:?fps}; cols=${6:-6}; w=${7:-320}; crop=${8:-}
vf="fps=$fps"; [ -n "$crop" ] && vf="$vf,crop=$crop"; vf="$vf,scale=$w:-2"
cnt=$(python3 -c "print(max(1,int(round($dur*$fps))))")
rows=$(python3 -c "import math;print(math.ceil($cnt/$cols))")
ffmpeg -v error -y -ss "$ss" -t "$dur" -i "$v" -vf "$vf,tile=${cols}x${rows}:padding=2:color=red" -frames:v 1 -q:v 3 "$out"
echo "$out: $cnt 格 (${cols}x${rows})，第 k 格 t = $ss + k/$fps"
