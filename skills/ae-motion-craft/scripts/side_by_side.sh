#!/bin/bash
# 并排对照图：左原片、右我们（各缩到同尺寸后 hstack）。本机 ffmpeg 没有 drawtext，所以说明写进文件名，别想往图上写字。
# usage: side_by_side.sh <输出.png> <左: 图片或视频> <左时间秒|-> <右: 图片或视频> <右时间秒|-> [宽=960] [高=540]
#   图片就把时间写成 -；视频按 -ss 取那一帧。
#   我们这一侧通常用 remotion still 先出图（见 promo-and-hosted-pipeline.md），或直接从渲染的 mp4 按时间取。
#   比例不同（如竖屏）时会被拉伸：先按原片比例给宽高，例如竖屏 406x722 → 宽 406 高 722。
#   命名约定：compare_<积木>_<原片>_<秒>.png，例如 compare_scroll_A27.4.png
set -euo pipefail
out=${1:?输出}; L=${2:?左}; lt=${3:?左时间或-}; R=${4:?右}; rt=${5:?右时间或-}; w=${6:-960}; h=${7:-540}
inl=(-i "$L"); [ "$lt" != "-" ] && inl=(-ss "$lt" -i "$L")
inr=(-i "$R"); [ "$rt" != "-" ] && inr=(-ss "$rt" -i "$R")
ffmpeg -hide_banner -loglevel error -y "${inl[@]}" "${inr[@]}" -filter_complex "[0:v]scale=$w:$h[a];[1:v]scale=$w:$h[b];[a][b]hstack" -frames:v 1 "$out"
echo "$out"
