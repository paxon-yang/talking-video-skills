#!/usr/bin/env python3
"""Render one frame range of Video2 with a watchdog (concurrency 1): kills stray headless Chrome / old remotion bundles first, restarts the
render when no new frame has been reported for 5 minutes (max 3 attempts), appends start / end timestamps to out/video2/NOTES.md,
and removes remotion-webpack-bundle-* temp folders on exit.
  python3 src/video2/watchdog_render.py <from> <to> <out.mp4> <label> [extra render_v2.mjs args, e.g. --scale=0.5 --crf=20]"""
import atexit, glob, os, shutil, subprocess, sys, time
fr, to, out, label = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
extra = sys.argv[5:]
NOTES = 'out/video2/NOTES.md'
def note(msg):
    line = f"- [{time.strftime('%Y-%m-%d %H:%M:%S')}] {label}: {msg}"
    print(line, flush=True); open(NOTES, 'a').write(line + '\n')
def clean(age=60):
    subprocess.run(['pkill', '-f', 'chrome-headless-shell'], capture_output=True)
    subprocess.run(['pkill', '-f', 'render_v2.mjs'], capture_output=True)
    for d in glob.glob(os.path.join(os.environ.get('TMPDIR', '/tmp'), 'remotion-webpack-bundle-*')):
        if time.time() - os.path.getmtime(d) > age: shutil.rmtree(d, ignore_errors=True)
atexit.register(lambda: clean(0))
for attempt in range(1, 4):
    clean()
    note(f'start attempt {attempt} frames {fr}-{to} {" ".join(extra)}')
    t0 = time.time()
    p = subprocess.Popen(['node', 'src/video2/render_v2.mjs', f'--from={fr}', f'--to={to}', f'--out={out}', '--concurrency=1'] + extra, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    os.set_blocking(p.stdout.fileno(), False)
    last = time.time(); buf = ''
    while p.poll() is None:
        try:
            chunk = p.stdout.read()
        except Exception:
            chunk = None
        if chunk:
            buf += chunk
            if 'frames ' in chunk or 'done' in chunk: last = time.time()
        if time.time() - last > 300:
            note('no new frame for 5 min -> kill and retry'); p.kill(); break
        time.sleep(2)
    buf += p.stdout.read() or ''
    if p.returncode == 0 and os.path.exists(out) and 'done' in buf:
        note(f'end ok {time.time() - t0:.0f} s'); sys.exit(0)
    tail = buf.strip().splitlines()[-1][:200] if buf.strip() else ''
    note(f'failed (rc {p.returncode}): {tail}')
note('gave up after 3 attempts'); sys.exit(1)
