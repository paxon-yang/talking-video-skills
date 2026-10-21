#!/usr/bin/env python3
"""[Skill copy of <工程目录>/scripts/make_sfx_cues.py; run it from the project root: python3 scripts/make_sfx_cues.py <timeline.json>]
DEFAULT = NO BGM (user adds music in Jianying). assets.bgm is NOT set and any existing one is removed; pass --with-bgm to restore the old placeholder-bed behaviour.
Derive sfx cues from full.timeline.json -> its `sfx` array. Backs up original to full.timeline.pre_sfx.json (once).
Also covers the creative motion-graphics layer (scene props .mg, overlays kind 'mg' with props.sfx).
Pipeline order: make_bee_full -> apply_transitions_bee -> apply_creative_bee -> make_sfx_cues (no bgm asset by default).
Usage: python3 scripts/make_sfx_cues.py [timeline.json] [--rebase] [--with-bgm]   (--rebase, or a timeline without `sfx` = fresh pipeline output: refresh the pristine backup first)"""
import json, os, re, shutil, sys
ROOT = os.path.join(os.path.dirname(__file__), '..')
_args = [a for a in sys.argv[1:] if not a.startswith('--')]
TL = _args[0] if _args else os.path.join(ROOT, 'public/projects/bee-level8/full.timeline.json')  # EDIT: pass your own timeline path
REVIEW = os.path.join(os.path.dirname(os.path.abspath(TL)), 'sfx_cues.md')  # human-readable cue list next to the timeline
WITH_BGM = '--with-bgm' in sys.argv
FPS = 30
bak = TL.replace('.timeline.json', '.timeline.pre_sfx.json')
_cur = json.load(open(TL))
if '--rebase' in sys.argv or not os.path.exists(bak) or 'sfx' not in _cur:  # new content in TL (e.g. creative layer) -> the backup must carry it, minus the old cues
    _cur.pop('sfx', None)
    json.dump(_cur, open(bak, 'w'), ensure_ascii=False, indent=2)
tl = json.load(open(bak))  # always derive from the pristine copy

VOL = {'whoosh_short': 0.30, 'whoosh_long': 0.34, 'pop': 0.32, 'tick': 0.22, 'ding': 0.34, 'impact_low': 0.40,
       'riser': 0.26, 'shimmer': 0.26, 'swipe': 0.28, 'whoosh_down': 0.28, 'flash': 0.2}
PRIO = {'impact_low': 9, 'riser': 9, 'ding': 9, 'whoosh_long': 8, 'shimmer': 8, 'swipe': 6, 'pop': 6, 'whoosh_short': 5, 'tick': 3}
cues = []  # (frame, type, reason, extra)
def add(f, ty, why, **kw): cues.append(dict(at=max(0, int(f)), type=ty, volume=VOL[ty], reason=why, **kw))

words = {}
for s in tl['sentences']:
    for w in s['words']: words.setdefault(s['id'], []).append(w)
def at_word(aw, default):
    if not aw: return default
    key = lambda x: re.sub(r"[^\w']", '', x.lower())
    for w in words.get(aw['sentenceId'], []):
        if key(w['text']) == key(aw['word']): return w['start']
    return default

scenes = sorted(tl['scenes'], key=lambda s: s['from'])
special = {'chapter_card', 'big_number', 'compare', 'summary_card', 'keyword_card', 'step_list'}
# 1) cut whooshes: every second plain cut, >=1.2s apart
cand = [s for i, s in enumerate(scenes) if i and s['kind'] not in special and not (s['kind'] == 'broll' and scenes[i-1]['kind'] == 'broll' and False)]
last = -999; n = 0
for s in cand:
    n += 1
    if n % 2: continue
    f = s['from'] - 2
    if f - last < 36: continue
    add(f, 'whoosh_short', f'cut -> {s["kind"]} {s["id"]}'); last = f
for s in scenes:
    k, f, p = s['kind'], s['from'], s['props']
    if k == 'chapter_card':
        add(f - 4, 'whoosh_long', f'chapter transition {s["id"]}')
        add(f + (p.get('enterDelay') or 0), 'impact_low', f'chapter card "{p.get("title")}"')
        if p.get('mg'): add(f + (p.get('enterDelay') or 0) + 7, 'tick', f'chapter icon draws on ({p["mg"]["icon"]})')
    elif k == 'big_number':
        it = p['items']
        for j, item in enumerate(it):
            rev = at_word(item.get('atWord'), f + 8)
            add(rev - 40, 'riser', f'riser (2s clip @1.5x = 40f) into big number {item["value"]}', rate=1.5)
            add(rev, 'impact_low', f'big number reveal {item["value"]}')
            if p.get('mg') == 'ladder': add(rev + 10, 'tick', 'level ladder fills'); add(rev + 34, 'pop', 'lowest rung lights red')
    elif k == 'keyword_card':
        add(f, 'pop', 'keyword card enter')
    elif k == 'compare':
        add(f, 'swipe', f'compare enters {s["id"]}')
        cols = [p.get(c) for c in ('left', 'middle', 'right') if p.get(c)]
        for c in cols:
            if c.get('atWord'): add(at_word(c['atWord'], f), 'pop', f'column "{c["label"]}"')
            if c.get('atWord') and c.get('icon'): add(at_word(c['atWord'], f) + 8, 'tick', f'column icon draws ({c["icon"]})')
        if p.get('listAtWord'): add(at_word(p['listAtWord'], f + 30), 'tick', 'compare list cascade')
    elif k == 'summary_card':
        if p.get('variant') == 'quote':
            q = p['quote']; qf = at_word(q.get('atWord'), f)
            add(f, 'swipe', 'quote card enter')
            add(qf + 24, 'shimmer', f'gold highlight "{(q.get("highlight") or [""])[0]}"')
            if q.get('underlineAtWord'): add(at_word(q['underlineAtWord'], qf) + 2, 'tick', 'gold underline draws')
        else:
            add(f, 'swipe', 'summary card enter')
            for it in p['items']: add(at_word(it.get('atWord'), f + 12), 'tick', f'summary item {it["no"]}')
            if p.get('mg'): add(at_word(p['items'][-1].get('atWord'), f + 12) + 12, 'ding', 'summary: last check lands')
    elif k == 'step_list':
        for st in p['steps']: add(at_word(st.get('atWord'), f), 'tick', f'step {st["no"]}')
for o in tl['overlays']:
    if o['kind'] == 'head_flank': add(o['from'], 'tick', f'head_flank "{o["text"]}"')
    elif o['kind'] == 'mg':
        for c in (o.get('props') or {}).get('sfx', []): add(o['from'] + c['t'], c['type'], f'mg {o["graphic"]}: {c["why"]}')
    elif o['kind'] in ('pill', 'keyword', 'callout', 'spotlight'): add(o['from'], 'pop', f'{o["kind"]} "{o.get("text") or o.get("label") or ""}"')
if tl.get('subtitles'): add(tl['subtitles'][-1]['from'], 'ding', 'final line')

# 2) thin: same type >=0.5s apart (keep higher priority first), global cap 0.8 cues/s, 1 tick/pop not within 6 frames of another
dur = tl['meta']['durationInFrames'] / FPS
cues.sort(key=lambda c: (-PRIO[c['type']], c['at']))
kept = []
for c in cues:
    if any(k['type'] == c['type'] and abs(k['at'] - c['at']) < 15 for k in kept): continue
    if c['type'] in ('tick', 'pop', 'swipe') and any(k['type'] in ('tick', 'pop', 'swipe') and abs(k['at'] - c['at']) < 6 for k in kept): continue
    if len(kept) >= int(0.8 * dur): continue
    kept.append(c)
kept.sort(key=lambda c: c['at'])
for c in kept: c['at'] = min(c['at'], tl['meta']['durationInFrames'] - 2)
tl['sfx'] = [{k: v for k, v in c.items()} for c in kept]
if WITH_BGM:  # optional / not default
    if os.path.exists(os.path.join(ROOT, 'public/projects/bee-level8/bgm.wav')): tl['assets'].setdefault('bgm', {'src': 'projects/bee-level8/bgm.wav', 'volume': 0.4})
else:
    tl['assets'].pop('bgm', None)  # default: voice + SFX only; music is added later in Jianying
json.dump(tl, open(TL, 'w'), ensure_ascii=False, indent=2)

os.makedirs(os.path.dirname(REVIEW), exist_ok=True)
with open(REVIEW, 'w') as fh:
    fh.write(f'# SFX cues ({len(kept)} cues, {len(kept)/dur:.2f}/s over {dur:.1f}s)\n\n| time | frame | type | vol | reason |\n|---|---|---|---|---|\n')
    for c in kept:
        m, s = divmod(c['at'] / FPS, 60)
        fh.write(f'| {int(m):02d}:{s:04.1f} | {c["at"]} | {c["type"]} | {c["volume"]:.2f} | {c["reason"]} |\n')
print(f'{len(kept)} cues, {len(kept)/dur:.2f}/s ->', TL)
