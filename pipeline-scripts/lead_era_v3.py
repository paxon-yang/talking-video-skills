#!/usr/bin/env python3
"""Mouth-vs-voice timing as the viewer sees it, for host leads 0..4 composition frames.
Displayed source frame at composition frame f = floor((f + lead) * 25 / 30) (same mapping as lib.ts srcF). Vision inner-lip opening of that
frame, averaged over the 22 sentence onsets and over all character onsets (voice_v2 word alignment), lags -10..+10 composition frames.
'open' = first lag where the onset-average crosses half way from its pre-onset baseline (min of lags -10..-2) to its peak (max of -6..+6)."""
import json, numpy as np
L = np.array(json.load(open('out/video1/final/lips_vision_v3.json'))['lips'])[:, 0]
W = json.load(open('src/video1/final/data/words_v3.json'))
sent = [l['start'] for l in W]
chars = [w[1] for l in W for w in l['w']]
def era(events, lead):
    rows = []
    for c in events:
        r = []
        for d in range(-10, 11):
            f = c + d
            s = min(2022, max(0, int((f + lead) * 25 / 30 + 1e-6)))
            r.append(L[s])
        rows.append(r)
    return np.mean(rows, 0)
out = {}
for lead in range(0, 5):
    a = era(sent, lead)
    lags = list(range(-10, 11))
    pk_i = max(range(4, 17), key=lambda i: a[i])
    base = min(a[:9])
    half = base + 0.5 * (a[pk_i] - base)
    op = next((lags[i] for i in range(0, pk_i + 1) if a[i] >= half), None)
    out[lead] = {'peak_lag': lags[pk_i], 'half_rise_lag': op, 'curve_x1000': [round(float(v) * 1000, 1) for v in a]}
    print(lead, 'peak', lags[pk_i], 'half-rise', op)
json.dump(out, open('out/video1/final/lead_era_v3.json', 'w'), indent=1)
