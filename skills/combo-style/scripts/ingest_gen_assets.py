#!/usr/bin/env python3
"""ingest_gen_assets.py - validate, normalise and QA the clips/images the user generated with Gemini.

Run from the Remotion project root (or pass --root):
  python3 scripts/ingest_gen_assets.py <slug>
      [--shotlist projects/<slug>/gen_plan/shotlist.json]
      [--gen-dir projects/<slug>/gen] [--out public/projects/<slug>/gen30]
      [--qa-dir projects/<slug>/gen_plan/qa] [--trim center|head]
      [--mci b04,b18] [--no-ocr] [--check-only] [--crf 18]

What it does
  1. Scans gen-dir; a file belongs to shotlist id X when its name starts with "X_" (or is X.ext).
     Reports missing files, extra files, duplicates (newest wins).
  2. ffprobe each video: res / fps / duration / audio; warns when not 16:9, < 1080p, too short, has audio.
  3. Converts videos to 1920x1080 30fps CFR H.264 yuv420p, audio stripped, trimmed to use_seconds
     (center or head; per-asset "trim" overrides; loop assets use head). --mci = minterpolate (aerials ONLY,
     never people/hands). Images are copied as PNG (flagged if < 1920x1080).
  4. Writes <out>/<name>.mp4|png, <qa-dir>/contact_sheet_NN.png (3 frames per clip) and <qa-dir>/qa_report.md.
  5. OCR (tools/ocr, macOS Vision) on 3 frames per clip: any CJK -> ERROR, any other text-like detection -> WARN
     "unexpected text" (assets with "allow_text": true are only noted).
Exit code 1 if any ERROR.
"""
import argparse, glob, json, os, re, shutil, subprocess, sys

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
OCR = os.environ.get("OCR_BIN") or "<素材目录>"
VID_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
# strict tier = ideographs/kana/hangul (as in english.md); full-width punctuation alone (OCR reads "!" as U+FF01) is only text-like
CJK = re.compile("[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path):
    r = run([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    if r.returncode != 0:
        return None
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    if not v:
        return None
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    dur = float(j["format"].get("duration") or v.get("duration") or 0)
    return {"w": int(v["width"]), "h": int(v["height"]), "fps": fps, "dur": dur, "codec": v.get("codec_name"),
            "audio": any(s["codec_type"] == "audio" for s in j["streams"])}


def load_shotlist(p):
    with open(p, encoding="utf-8") as f:
        if p.lower().endswith((".yaml", ".yml")):
            import yaml
            return yaml.safe_load(f)
        return json.load(f)


def match_files(gen_dir, assets):
    files = [f for f in glob.glob(os.path.join(gen_dir, "*")) if os.path.isfile(f) and not os.path.basename(f).startswith(".")]
    by_id, extra = {}, []
    ids = {a["id"].lower(): a["id"] for a in assets}
    for f in sorted(files, key=os.path.getmtime):
        stem = os.path.splitext(os.path.basename(f))[0]
        key = stem.split("_")[0].lower()
        ext = os.path.splitext(f)[1].lower()
        if key in ids and ext in (VID_EXT | IMG_EXT):
            by_id.setdefault(ids[key], []).append(f)
        else:
            extra.append(os.path.basename(f))
    return by_id, extra


def convert_video(src, dst, start, length, mci, crf):
    vf = []
    if mci:
        vf.append("minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
    vf += ["scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos", "crop=1920:1080", "fps=30", "setsar=1"]
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", src, "-t", f"{length:.3f}", "-an",
           "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
           "-r", "30", "-movflags", "+faststart", dst]
    r = run(cmd)
    return r.returncode == 0, " ".join(r.stderr.split())[-300:]


def grab_frames(path, is_video, dur, outprefix, n=3):
    outs = []
    if not is_video:
        o = f"{outprefix}_1.png"
        r = run([FFMPEG, "-y", "-loglevel", "error", "-i", path, "-frames:v", "1", o])
        return [o] if r.returncode == 0 else []
    for i, frac in enumerate((0.1, 0.5, 0.9), 1):
        o = f"{outprefix}_{i}.png"
        r = run([FFMPEG, "-y", "-loglevel", "error", "-ss", f"{max(0, dur*frac - 0.02):.3f}", "-i", path, "-frames:v", "1", o])
        if r.returncode == 0 and os.path.exists(o):
            outs.append(o)
    return outs


def ocr_frames(frames):
    """returns {path: [(text, conf), ...]} ; {} if OCR unavailable."""
    if not frames or not os.path.exists(OCR):
        return None
    lst = frames[0] + ".ocrlist.txt"
    open(lst, "w").write("\n".join(frames))
    r = run([OCR, "--list", lst])
    os.remove(lst)
    if r.returncode != 0:
        return None
    try:
        j = json.loads(r.stdout)
    except Exception:
        return None
    return {p: [(b["text"], b["confidence"]) for b in v["blocks"]] for p, v in j.items()}


def contact_sheet(rows, qa_dir, per_page=10):
    from PIL import Image, ImageDraw, ImageFont
    tw, th, lab = 384, 216, 210
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 17)
    except Exception:
        font = ImageFont.load_default()
    pages = []
    for pi in range(0, len(rows), per_page):
        chunk = rows[pi:pi + per_page]
        im = Image.new("RGB", (lab + 3 * tw + 8, len(chunk) * (th + 6)), (13, 20, 32))
        d = ImageDraw.Draw(im)
        for ri, (label, color, frames) in enumerate(chunk):
            y = ri * (th + 6)
            d.rectangle([0, y, lab - 4, y + th], fill=(22, 32, 47))
            for li, line in enumerate(label.split("\n")):
                d.text((8, y + 8 + li * 22), line, fill=color if li == 0 else (200, 210, 225), font=font)
            for fi, fp in enumerate(frames[:3]):
                try:
                    t = Image.open(fp).convert("RGB").resize((tw, th))
                    im.paste(t, (lab + fi * tw + 2, y))
                except Exception:
                    pass
        p = os.path.join(qa_dir, f"contact_sheet_{pi // per_page + 1:02d}.png")
        im.save(p)
        pages.append(p)
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--root", default=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
    ap.add_argument("--shotlist"); ap.add_argument("--gen-dir"); ap.add_argument("--out"); ap.add_argument("--qa-dir")
    ap.add_argument("--trim", choices=["center", "head"], default="center")
    ap.add_argument("--mci", default="", help="comma list of asset ids to frame-interpolate (aerials/timelapse only)")
    ap.add_argument("--no-ocr", action="store_true"); ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--crf", type=int, default=18)
    ns = ap.parse_args()
    R = ns.root
    shot = ns.shotlist or os.path.join(R, "projects", ns.slug, "gen_plan", "shotlist.json")
    gen = ns.gen_dir or os.path.join(R, "projects", ns.slug, "gen")
    out = ns.out or os.path.join(R, "public", "projects", ns.slug, "gen30")
    qa = ns.qa_dir or os.path.join(R, "projects", ns.slug, "gen_plan", "qa")
    mci_ids = {x.strip().lower() for x in ns.mci.split(",") if x.strip()}
    sl = load_shotlist(shot)
    assets = sl["assets"]
    os.makedirs(qa, exist_ok=True)
    os.makedirs(os.path.join(qa, "frames"), exist_ok=True)
    if not ns.check_only:
        os.makedirs(out, exist_ok=True)
    by_id, extra = match_files(gen, assets)
    missing = [a["id"] for a in assets if a["id"] not in by_id]

    results, sheet_rows, all_frames, frame_owner = [], [], [], {}
    for a in assets:
        aid = a["id"]
        if aid not in by_id:
            continue
        cand = by_id[aid]
        src = cand[-1]
        notes, level = [], "OK"

        def flag(lv, msg):
            nonlocal level
            notes.append(f"{lv}: {msg}")
            rank = {"OK": 0, "INFO": 0, "WARN": 1, "ERROR": 2}
            if rank[lv] > rank[level]:
                level = lv
        if len(cand) > 1:
            flag("WARN", f"{len(cand)} files for {aid}; using newest {os.path.basename(src)}")
        isvid_expected = a["type"] == "video"
        ext = os.path.splitext(src)[1].lower()
        if isvid_expected != (ext in VID_EXT):
            flag("ERROR", f"shotlist says {a['type']} but file is {ext}")
        info = probe(src)
        if not info:
            results.append({"id": aid, "src": os.path.basename(src), "level": "ERROR", "notes": ["ERROR: unreadable (ffprobe failed)"], "out": None})
            continue
        row = {"id": aid, "src": os.path.basename(src), "info": info, "out": None}
        if abs(info["w"] / info["h"] - 16 / 9) > 0.02:
            flag("WARN", f"aspect {info['w']}x{info['h']} is not 16:9 - will be center-cropped")
        outpath = None
        if isvid_expected and ext in VID_EXT:
            if info["h"] < 1080:
                flag("WARN", f"resolution {info['w']}x{info['h']} below 1080p - will be upscaled (soft)")
            if info["audio"]:
                flag("INFO", "has audio track - stripped")
            if abs(info["fps"] - 30) > 0.5:
                flag("INFO", f"{info['fps']:.2f} fps -> converted to 30 fps CFR")
            seconds = float(a.get("seconds") or 0)
            use = float(a.get("use_seconds") or seconds or info["dur"])
            if info["dur"] + 0.05 < use:
                flag("ERROR", f"too short: {info['dur']:.2f}s < needed {use:.2f}s - regenerate or lower use_seconds")
                use = info["dur"]
            elif seconds and info["dur"] + 0.3 < seconds:
                flag("WARN", f"generated {info['dur']:.2f}s, shotlist asked {seconds}s")
            mode = "head" if a.get("loop") else a.get("trim", ns.trim)
            start = 0.0 if mode == "head" else max(0.0, (info["dur"] - use) / 2)
            name = os.path.splitext(os.path.basename(src))[0] + ".mp4"
            outpath = os.path.join(out, name)
            row.update(use=use, start=start, mode=mode, mci=aid.lower() in mci_ids)
            if not ns.check_only:
                ok, err = convert_video(src, outpath, start, use, aid.lower() in mci_ids, ns.crf)
                if not ok:
                    flag("ERROR", "ffmpeg failed: " + err)
                    outpath = None
            else:
                outpath = None
        elif not isvid_expected and ext in IMG_EXT:
            if info["w"] < 1920 or info["h"] < 1080:
                flag("WARN", f"image {info['w']}x{info['h']} below 1920x1080")
            name = os.path.splitext(os.path.basename(src))[0] + ".png"
            outpath = os.path.join(out, name)
            if not ns.check_only:
                r = run([FFMPEG, "-y", "-loglevel", "error", "-i", src, outpath])
                if r.returncode != 0:
                    flag("ERROR", "image convert failed")
                    outpath = None
        row["out"] = outpath
        probe_src = outpath if outpath and os.path.exists(outpath) else src
        pdur = (row.get("use") if outpath else info["dur"]) or info["dur"]
        frames = grab_frames(probe_src, isvid_expected and ext in VID_EXT, pdur, os.path.join(qa, "frames", aid))
        row["frames"] = frames
        for fp in frames:
            all_frames.append(fp); frame_owner[fp] = aid
        row["level"], row["notes"] = level, notes
        results.append(row)

    # OCR
    ocr_status = "skipped (--no-ocr)"
    if not ns.no_ocr:
        res = ocr_frames(all_frames)
        if res is None:
            ocr_status = "UNAVAILABLE (tools/ocr missing or failed) - check text by eye"
        else:
            ocr_status = f"ran on {len(all_frames)} frames"
            asset_by_id = {a["id"]: a for a in assets}
            for row in results:
                hits, cjk = [], []
                for fp in row.get("frames", []):
                    for text, conf in res.get(fp, []):
                        t = text.strip()
                        if CJK.search(t):
                            cjk.append(t)
                        elif len(re.findall(r"[A-Za-z0-9]", t)) >= 2 or len(t) >= 3:
                            hits.append(f"{t} ({conf:.2f})")
                allow = asset_by_id[row["id"]].get("allow_text")
                if cjk:
                    row["notes"].append("ERROR: CJK text detected: " + " | ".join(sorted(set(cjk))[:4]))
                    row["level"] = "ERROR"
                if hits:
                    msg = "unexpected text: " + " | ".join(sorted(set(hits))[:5])
                    if allow:
                        row["notes"].append("INFO: " + msg + " (allow_text)")
                    else:
                        row["notes"].append("WARN: " + msg + " - regenerate or confirm it is harmless")
                        if row["level"] == "OK":
                            row["level"] = "WARN"
                row["ocr"] = "CJK" if cjk else ("text" if hits else "clean")

    # sheets
    colors = {"OK": (80, 220, 140), "WARN": (255, 200, 80), "ERROR": (255, 100, 100)}
    for row in results:
        i = row.get("info") or {}
        dur = f"{row['use']:.1f}s" if row.get("use") else (f"{i.get('dur', 0):.1f}s" if i else "")
        sheet_rows.append((f"{row['id']}  {row['level']}\n{i.get('w','?')}x{i.get('h','?')} {i.get('fps',0):.0f}fps\n{dur} ocr:{row.get('ocr','-')}",
                           colors[row["level"]], row.get("frames", [])))
    pages = contact_sheet(sheet_rows, qa) if sheet_rows else []

    # report
    n_err = sum(r["level"] == "ERROR" for r in results) + 0
    n_warn = sum(r["level"] == "WARN" for r in results)
    L = [f"# Gen asset QA - {ns.slug}", "",
         f"- shotlist: {len(assets)} assets; found {len(results)}; missing {len(missing)}; extra files {len(extra)}",
         f"- OK {sum(r['level']=='OK' for r in results)} / WARN {n_warn} / ERROR {n_err}", f"- OCR: {ocr_status}",
         f"- output: `{out}`" + (" (check-only: nothing converted)" if ns.check_only else ""),
         f"- contact sheets: " + (", ".join(f"`{p}`" for p in pages) or "none"), ""]
    if missing:
        L += ["## Missing (not generated / wrong filename)", ""] + [f"- {m}" for m in missing] + [""]
    if extra:
        L += ["## Extra files (no matching shotlist id)", ""] + [f"- {e}" for e in extra] + [""]
    L += ["## Per asset", "", "| id | status | src | res | fps | dur | audio | out | notes |", "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        i = r.get("info") or {}
        L.append(f"| {r['id']} | {r['level']} | {r['src']} | {i.get('w','?')}x{i.get('h','?')} | {i.get('fps',0):.2f} | {i.get('dur',0):.2f} | "
                 f"{'yes' if i.get('audio') else 'no'} | {os.path.basename(r['out']) if r.get('out') else '-'} | {'; '.join(r['notes']) or '-'} |")
    L += ["", "Next: look at the contact sheets (text artefacts, wrong subject, faces/hands), then regenerate flagged items "
          "with the 'regenerate prompt' template in references/gemini-asset-prompts.md."]
    rp = os.path.join(qa, "qa_report.md")
    open(rp, "w", encoding="utf-8").write("\n".join(L))
    print(f"found {len(results)}/{len(assets)}  missing {len(missing)}  extra {len(extra)}  OK/WARN/ERROR "
          f"{sum(r['level']=='OK' for r in results)}/{n_warn}/{n_err}")
    print("report:", rp)
    for p in pages: print("sheet:", p)
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
