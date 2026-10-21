#!/bin/bash
# 把参考视频（尤其是手机/屏幕录制、可变帧率、超长）转成可逐帧分析的本地代理：恒定帧率、固定宽度、关键帧密。
# usage: make_proxy.sh <源视频> <输出 proxy.mp4> [宽=1280] [fps=30]
#   - 输出恒定 fps（-ss 定位和「帧号 = 秒 × fps」才可靠）；-g 30 让每秒都有关键帧，-ss 快速而准确
#   - 保留音轨（屏幕录制若本来无声，输出也无声；音频分析另用 extract_audio，见 README）
#   - 19 分钟录屏在本机（M2 8GB）约 2.5 分钟
set -euo pipefail
src=${1:?源视频}; out=${2:?输出路径}; w=${3:-1280}; fps=${4:-30}
ffmpeg -v error -y -i "$src" -vf "fps=$fps,scale=$w:-2" -c:v libx264 -preset veryfast -crf 18 -g "$fps" -pix_fmt yuv420p -c:a aac -b:a 128k "$out"
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate,duration -of default=nw=1 "$out"
