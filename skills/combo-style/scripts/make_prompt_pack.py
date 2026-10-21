#!/usr/bin/env python3
"""make_prompt_pack.py - shotlist (JSON/YAML) + style_bible.md -> prompt_pack.md + prompt_pack.html

Usage:
  python3 scripts/make_prompt_pack.py <shotlist.json> <style_bible.md> [--out DIR] [--slug SLUG]
Default --out = the shotlist's folder. Needs only the Python 3 standard library
(YAML shotlists need PyYAML; JSON does not).

Shotlist schema (see references/gemini-asset-prompts.md section 3):
  {"slug": "...", "title": "...", "assets": [ {
     "id": "b02", "type": "video"|"image", "slug": "haul-trucks-aerial",
     "purpose": "script line / beat this serves", "gloss_zh": "short Chinese gloss",
     "seconds": 6,            # video: seconds to GENERATE (4/6/8). image: omit
     "use_seconds": 3.5,      # video: seconds the timeline needs (ingest trims to this)
     "subject","setting","action","camera","lighting","mood": "...",
     "text_safe_area": "none|left|right|upper_third|lower_third|center",
     "depth_for_type_behind": false, "loop": false,
     "image_kind": "still|plate|cutout",   # image only
     "ref": "s05",            # optional: tell the user to use this still as first frame / reference
     "avoid": "extra negatives", "notes": "free text", "trim": "center|head" } ] }

style_bible.md sections (all optional except STYLE):
  ## STYLE         fixed paragraph prepended to every prompt
  ## VIDEO_SPEC    technical line for video ({seconds} is substituted)
  ## IMAGE_SPEC    technical line for image
  ## NEGATIVE      the "avoid" list
"""
import argparse, html, json, os, re, sys

DEF_VIDEO_SPEC = ("Duration: exactly {seconds} seconds. Aspect ratio 16:9 landscape, 1080p, 24 fps natural cinematic motion. "
                  "Silent footage: no dialogue, no music, no voice-over. "
                  "No text, no captions, no logos, no watermarks, no subtitles.")
DEF_IMAGE_SPEC = ("Single still image, aspect ratio 16:9 landscape, 2K resolution (2048x1152 or larger). "
                  "No text, no captions, no logos, no watermarks.")
DEF_NEGATIVE = ("text, letters, numbers, captions, subtitles, logos, brand names, watermarks, real people or celebrities, "
                "distorted hands, extra fingers, warped faces, flicker, jump cuts, camera shake, oversaturated colours")

AREA_TXT = {
    "left": "the left third of the frame", "right": "the right third of the frame",
    "upper_third": "the upper third of the frame", "lower_third": "the lower third of the frame",
    "center": "the central area of the frame",
}


def load_shotlist(path):
    with open(path, encoding="utf-8") as f:
        if path.lower().endswith((".yaml", ".yml")):
            import yaml  # optional dependency
            return yaml.safe_load(f)
        return json.load(f)


def parse_bible(path):
    txt = open(path, encoding="utf-8").read()
    txt = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
    secs, cur, buf = {}, None, []
    for line in txt.splitlines():
        m = re.match(r"^##\s+([A-Z_]+)\s*$", line)
        if m:
            if cur: secs[cur] = "\n".join(buf).strip()
            cur, buf = m.group(1), []
        elif cur:
            buf.append(line)
    if cur: secs[cur] = "\n".join(buf).strip()
    if "STYLE" not in secs:  # no headings: whole file is the style paragraph
        secs["STYLE"] = txt.strip()
    secs["STYLE"] = " ".join(secs["STYLE"].split())
    for k in ("VIDEO_SPEC", "IMAGE_SPEC", "NEGATIVE"):
        if k in secs: secs[k] = " ".join(secs[k].split())
    return secs


def filename(a):
    ext = ".mp4" if a["type"] == "video" else ".png"
    return f'{a["id"]}_{a.get("slug", "asset")}{ext}'


def build_prompt(a, bible):
    style = bible["STYLE"]
    neg = bible.get("NEGATIVE", DEF_NEGATIVE)
    if a.get("avoid"): neg += ", " + a["avoid"]
    lines = [style, ""]
    isvid = a["type"] == "video"
    if isvid:
        lines.append(f'SHOT (video, exactly {a["seconds"]} seconds, 16:9):')
    else:
        kind = a.get("image_kind", "still")
        lines.append({"still": "IMAGE (still frame, 16:9):", "plate": "IMAGE (background plate, 16:9):",
                      "cutout": "IMAGE (isolated element, 16:9):"}[kind])
    for key, lab in (("subject", "Subject"), ("setting", "Setting"), ("action", "Action"),
                     ("camera", "Camera"), ("lighting", "Lighting"), ("mood", "Mood")):
        if a.get(key) and not (key in ("action", "camera") and not isvid):
            lines.append(f"{lab}: {a[key]}")
    comp = []
    ts = a.get("text_safe_area", "none")
    if ts and ts != "none":
        comp.append(f"Keep {AREA_TXT.get(ts, ts)} as clean negative space (low detail, no important subject there) because on-screen text will be placed over it.")
    if a.get("depth_for_type_behind"):
        comp.append("Strong foreground subject, sharply separated from the background (clear depth layers, clean edge contrast, "
                    "no clutter touching the subject outline) so text can be placed behind the subject.")
    if a.get("loop") and isvid:
        comp.append("Seamless loop: the last frame matches the first frame; slow, steady, repeatable motion.")
    kind = a.get("image_kind", "still")
    if not isvid and kind == "plate":
        comp.append("Out-of-focus room plate: very heavy lens blur, no sharp detail, soft bokeh shapes only, no people, nothing readable.")
    if not isvid and kind == "cutout":
        comp.append("Single isolated object centred on a plain flat solid neutral grey (#808080) background, even lighting, no ground, no cast shadow, "
                    "whole object visible with generous margin, clean sharp edges for later background removal.")
    if a.get("ref"):
        comp.append(f'Use the approved still {a["ref"]} as the reference / first frame so the location and look stay consistent.')
    if comp: lines.append("Composition: " + " ".join(comp))
    if isvid:
        spec = bible.get("VIDEO_SPEC", DEF_VIDEO_SPEC).replace("{seconds}", str(a["seconds"]))
    else:
        spec = bible.get("IMAGE_SPEC", DEF_IMAGE_SPEC)
    lines.append("Technical: " + spec)
    lines.append("Negative / avoid: " + neg)
    return "\n".join(lines)


def chips(a):
    c = []
    if a["type"] == "video":
        c += ["VIDEO", f'generate {a["seconds"]}s', "16:9 1080p", "24/30fps"]
        if a.get("use_seconds"): c.append(f'use {a["use_seconds"]}s')
    else:
        c += ["IMAGE", "16:9 2K", a.get("image_kind", "still")]
    ts = a.get("text_safe_area", "none")
    if ts and ts != "none": c.append("text-safe: " + ts)
    if a.get("depth_for_type_behind"): c.append("depth: type-behind")
    if a.get("loop"): c.append("loop")
    if a.get("ref"): c.append("ref " + a["ref"])
    return c


def make_md(sl, bible, assets):
    o = [f'# Prompt pack - {sl.get("title", sl.get("slug", ""))}', "",
         f'{len(assets)} assets ({sum(a["type"]=="video" for a in assets)} video, {sum(a["type"]=="image" for a in assets)} image). '
         'Paste each prompt into Gemini (video: Veo; image: Nano Banana / Imagen). Save files into `projects/<slug>/gen/` with the exact filename shown.', "",
         "## Style bible (already prepended to every prompt below)", "", "```", bible["STYLE"], "```", "",
         "## Overview", "", "| id | type | gen sec | use sec | save as | purpose |", "|---|---|---|---|---|---|"]
    for a in assets:
        o.append(f'| {a["id"]} | {a["type"]} | {a.get("seconds","-")} | {a.get("use_seconds","-")} | `{filename(a)}` | {a.get("purpose","")} |')
    o.append("")
    for a in assets:
        o += [f'## {a["id"]} - {a["type"].upper()}' + (f' - {a["seconds"]}s' if a["type"] == "video" else ""), "",
              f'- Save as: `{filename(a)}`', f'- Spec: {" | ".join(chips(a))}',
              f'- Purpose: {a.get("purpose","")}']
        if a.get("gloss_zh"): o.append(f'- 说明: {a["gloss_zh"]}')
        if a.get("notes"): o.append(f'- Notes: {a["notes"]}')
        o += ["", "```", build_prompt(a, bible), "```", ""]
    return "\n".join(o)


HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ - prompt pack</title><style>
:root{--bg:#0d1420;--card:#16202f;--line:#26364d;--fg:#e7eef9;--mut:#8ea2bf;--acc:#4f8cff;--ok:#2fbf71}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,"PingFang SC",Helvetica,Arial,sans-serif}
header{position:sticky;top:0;z-index:5;background:#0d1420ee;backdrop-filter:blur(6px);border-bottom:1px solid var(--line);padding:12px 20px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
header h1{font-size:18px;margin:0}.prog{color:var(--mut)}.bar{flex:1;min-width:120px;height:8px;background:var(--line);border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:var(--ok);width:0}
button{cursor:pointer;border:0;border-radius:8px;font:inherit;font-weight:600}.hbtn{background:var(--line);color:var(--fg);padding:7px 12px}
.filters button{background:transparent;color:var(--mut);padding:6px 10px;border:1px solid var(--line)}.filters button.on{color:var(--fg);border-color:var(--acc)}
main{max-width:1000px;margin:0 auto;padding:18px 16px 80px;display:grid;gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}.card.done{opacity:.55;border-color:var(--ok)}
.top{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.id{font-size:22px;font-weight:800}.dur{background:var(--acc);color:#fff;padding:3px 10px;border-radius:999px;font-weight:700}
.dur.img{background:#8a5cf6}.chk{margin-left:auto;display:flex;gap:6px;align-items:center;color:var(--mut)}.chk input{width:20px;height:20px}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}.chip{border:1px solid var(--line);color:var(--mut);padding:2px 8px;border-radius:6px;font-size:12px}
.file{font-family:Menlo,monospace;background:#0a101a;padding:3px 8px;border-radius:6px;font-size:13px;user-select:all}
.purpose{color:var(--mut);margin:6px 0}.gloss{color:#ffd479;margin:2px 0 8px}
pre{white-space:pre-wrap;background:#0a101a;border:1px solid var(--line);border-radius:10px;padding:12px;font:12.5px/1.5 Menlo,monospace;max-height:210px;overflow:auto;margin:8px 0}
.copy{background:var(--acc);color:#fff;font-size:20px;padding:14px 0;width:100%}.copy.ok{background:var(--ok)}
.row2{display:flex;gap:8px;margin-top:8px}.row2 button{flex:1;background:var(--line);color:var(--fg);padding:8px}
textarea{width:100%;margin-top:8px;background:#0a101a;color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:8px;font:inherit;min-height:44px}
.note{color:var(--mut);font-size:13px}
</style></head><body>
<header><h1>__TITLE__</h1><span class="prog" id="prog"></span><div class="bar"><i id="barfill"></i></div>
<span class="filters"><button data-f="all" class="on">All</button><button data-f="video">Video</button><button data-f="image">Image</button><button data-f="todo">To do</button></span>
<button class="hbtn" id="copystyle">Copy style bible</button></header>
<main id="main"></main>
<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
var D=JSON.parse(document.getElementById('data').textContent);var KEY='promptpack:'+D.slug;
var S={};try{S=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}}
function copy(t,btn,label){function ok(){var o=btn.textContent;btn.textContent=label||'Copied';btn.classList.add('ok');setTimeout(function(){btn.textContent=o;btn.classList.remove('ok')},1200)}
 function fb(){var x=document.createElement('textarea');x.value=t;document.body.appendChild(x);x.select();try{document.execCommand('copy');ok()}catch(e){alert('Copy failed - select the text manually')}document.body.removeChild(x)}
 if(navigator.clipboard&&window.isSecureContext!==false){navigator.clipboard.writeText(t).then(ok,fb)}else fb()}
function el(tag,cls,txt){var e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e}
var main=document.getElementById('main'),cards=[];
D.assets.forEach(function(a){
 var st=S[a.id]||(S[a.id]={done:false,note:''});var c=el('div','card');c.dataset.type=a.type;
 var top=el('div','top');top.appendChild(el('span','id',a.id));
 top.appendChild(el('span','dur'+(a.type==='image'?' img':''),a.type==='video'?a.seconds+' s':'IMAGE'));
 var lab=el('label','chk');var cb=document.createElement('input');cb.type='checkbox';cb.checked=!!st.done;lab.appendChild(cb);lab.appendChild(document.createTextNode('generated & saved'));top.appendChild(lab);c.appendChild(top);
 var ch=el('div','chips');a.chips.forEach(function(x){ch.appendChild(el('span','chip',x))});c.appendChild(ch);
 var f=el('div');f.appendChild(document.createTextNode('Save as  '));f.appendChild(el('span','file',a.filename));c.appendChild(f);
 c.appendChild(el('div','purpose',a.purpose||''));if(a.gloss_zh)c.appendChild(el('div','gloss',a.gloss_zh));
 if(a.notes)c.appendChild(el('div','note','Note: '+a.notes));
 c.appendChild(el('pre',null,a.prompt));
 var b=el('button','copy','COPY PROMPT');b.onclick=function(){copy(a.prompt,b,'COPIED')};c.appendChild(b);
 var r2=el('div','row2');var b2=el('button',null,'Copy filename');b2.onclick=function(){copy(a.filename,b2,'Copied')};r2.appendChild(b2);
 var b3=el('button',null,'Copy REGENERATE prompt');r2.appendChild(b3);c.appendChild(r2);
 var ta=el('textarea');ta.placeholder='Regenerate notes: what is wrong / what to change (e.g. "trucks too small, remove the text on the sign")';ta.value=st.note||'';c.appendChild(ta);
 b3.onclick=function(){var n=(ta.value||'').trim()||'[describe what to change]';copy('Regenerate the previous '+(a.type==='video'?'video':'image')+' with the SAME style, composition and settings, but change ONLY this: '+n+'\n\nFull original prompt for reference:\n'+a.prompt,b3,'Copied')};
 cb.onchange=function(){st.done=cb.checked;c.classList.toggle('done',cb.checked);save();upd()};
 ta.oninput=function(){st.note=ta.value;save()};
 c.classList.toggle('done',!!st.done);main.appendChild(c);cards.push([a,c,st]);});
function upd(){var n=0;cards.forEach(function(x){if(x[2].done)n++});document.getElementById('prog').textContent=n+' / '+cards.length+' done';document.getElementById('barfill').style.width=(100*n/cards.length)+'%';filt()}
var cur='all';function filt(){cards.forEach(function(x){var a=x[0],s=x[2],show=cur==='all'||cur===a.type||(cur==='todo'&&!s.done);x[1].style.display=show?'':'none'})}
Array.prototype.forEach.call(document.querySelectorAll('.filters button'),function(b){b.onclick=function(){cur=b.dataset.f;Array.prototype.forEach.call(document.querySelectorAll('.filters button'),function(y){y.classList.toggle('on',y===b)});filt()}});
var cs=document.getElementById('copystyle');cs.onclick=function(){copy(D.style,cs,'Copied')};
upd();})();
</script></body></html>
"""


def make_html(sl, bible, assets):
    data = {"slug": sl.get("slug", "pack"), "style": bible["STYLE"], "assets": []}
    for a in assets:
        data["assets"].append({"id": a["id"], "type": a["type"], "seconds": a.get("seconds"), "filename": filename(a),
                               "purpose": a.get("purpose", ""), "gloss_zh": a.get("gloss_zh", ""), "notes": a.get("notes", ""),
                               "chips": chips(a), "prompt": build_prompt(a, bible)})
    js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(sl.get("title", sl.get("slug", "")))
    return HTML.replace("__TITLE__", title).replace("__DATA__", js)


def validate(assets):
    ids = set()
    for a in assets:
        if a["id"] in ids: sys.exit(f'duplicate id {a["id"]}')
        ids.add(a["id"])
        if a["type"] not in ("video", "image"): sys.exit(f'{a["id"]}: type must be video|image')
        if a["type"] == "video" and not a.get("seconds"): sys.exit(f'{a["id"]}: video needs seconds')
        if a["type"] == "video" and a.get("use_seconds") and a["use_seconds"] > a["seconds"]:
            sys.exit(f'{a["id"]}: use_seconds > seconds')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shotlist"); ap.add_argument("style_bible")
    ap.add_argument("--out"); ap.add_argument("--slug")
    ns = ap.parse_args()
    sl = load_shotlist(ns.shotlist)
    if ns.slug: sl["slug"] = ns.slug
    bible = parse_bible(ns.style_bible)
    assets = sl["assets"]; validate(assets)
    out = ns.out or os.path.dirname(os.path.abspath(ns.shotlist))
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "prompt_pack.md"), "w", encoding="utf-8").write(make_md(sl, bible, assets))
    open(os.path.join(out, "prompt_pack.html"), "w", encoding="utf-8").write(make_html(sl, bible, assets))
    nv = sum(a["type"] == "video" for a in assets)
    print(f"wrote {out}/prompt_pack.md and .html: {len(assets)} assets ({nv} video, {len(assets)-nv} image)")


if __name__ == "__main__":
    main()
