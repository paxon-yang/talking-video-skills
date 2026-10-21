#!/usr/bin/env python3
"""usage: contact_strip.py outDir rawDir  -> one contact sheet per group prefix (files <group>_<frame>.png), 3 columns of 640x360 with frame labels"""
import sys, os, re, collections
from PIL import Image, ImageDraw
out, raw = sys.argv[1], sys.argv[2]
g = collections.OrderedDict()
for fn in sorted(os.listdir(raw), key=lambda x: (re.sub(r'_\d+\.png$', '', x), int(re.search(r'_(\d+)\.png$', x).group(1)) if re.search(r'_(\d+)\.png$', x) else 0)):
    m = re.match(r'(.+)_(\d+)\.png$', fn)
    if m: g.setdefault(m.group(1), []).append((int(m.group(2)), fn))
os.makedirs(out, exist_ok=True)
for name, items in g.items():
    cols = 3; rows = (len(items) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * 640, rows * 360), (0, 0, 0))
    for i, (fr, fn) in enumerate(items):
        im = Image.open(os.path.join(raw, fn)).convert('RGB').resize((640, 360), Image.LANCZOS)
        ImageDraw.Draw(im).text((8, 6), f'{name} f{fr}', fill=(255, 255, 0))
        sheet.paste(im, ((i % cols) * 640, (i // cols) * 360))
    sheet.save(os.path.join(out, f'{name}.jpg'), quality=88)
print(len(g), 'sheets')
