#!/usr/bin/env python3
"""Post-process bee-level8 full.timeline.json: add the motionPolish scene transitions (slide_push / zoom_through / flash_cut / wipe).
Plan (<= ~1 in 3 cuts is a special transition, counting the 4 chapter push_blur): every B-roll -> host cut alternates zoom_through / slide_push;
only two card -> B-roll cuts get flash_cut / wipe (picked away from other special cuts); everything else stays a clean cut (+ the exit choreography).
Idempotent: removes earlier slide_push/zoom_through/flash_cut/wipe first. Usage: python3 scripts/apply_transitions_bee.py [timeline.json]
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(ROOT, 'public/projects/bee-level8/full.timeline.json')
NEW = {'slide_push', 'zoom_through', 'flash_cut', 'wipe'}
DUR = {'slide_push': 12, 'zoom_through': 10, 'flash_cut': 4, 'wipe': 12}
CARD = {'chapter_card', 'big_number', 'compare', 'step_list', 'summary_card', 'pill_stack', 'news_collage', 'keyword_card', 'image_cards'}
# card -> B-roll cuts that get a special transition (incoming scene id -> type)
CARD_TO_BROLL = {'sc25': 'wipe', 'sc40': 'flash_cut'}

def apply(tl):
    sc = sorted(tl['scenes'], key=lambda s: s['from'])
    for s in sc:
        if s.get('transitionIn', {}).get('type') in NEW: del s['transitionIn']
    k = 0
    for prev, cur in zip(sc, sc[1:]):
        if cur.get('transitionIn'): continue  # keep chapter push_blur
        t = None
        if prev['kind'] == 'broll' and cur['kind'].startswith('host'):
            t = ['zoom_through', 'slide_push'][k % 2]; k += 1
        elif prev['kind'] in CARD and cur['kind'] == 'broll' and cur['id'] in CARD_TO_BROLL:
            t = CARD_TO_BROLL[cur['id']]
        if t:
            assert cur['dur'] >= DUR[t] + 4 and prev['dur'] >= DUR[t], (cur['id'], t)
            cur['transitionIn'] = {'type': t, 'dur': DUR[t]}
    return tl

if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    tl = apply(json.load(open(p)))
    with open(p, 'w') as f: json.dump(tl, f, ensure_ascii=False, indent=1)
    sp = [(s['id'], s['transitionIn']['type']) for s in tl['scenes'] if s.get('transitionIn')]
    print(f"{len(sp)} special transitions / {len(tl['scenes']) - 1} cuts: {sp}")
