#!/usr/bin/env python3
"""Gate G5.5: subtitles must start/end on the first/last spoken word (timeline.subtitles vs a word-timed recognition of the real audio).
  python3 scripts/check_sub_sync.py --timeline public/projects/x/full.timeline.json (--words words.json | --audio voice.wav) [--fps 30]
        [--start-tol 3] [--end-tol 6] [--audio-offset 0] [--report out/sound/SYNC_REPORT.md] [--json out/x.json] [--top 8] [--model small]

 --words   words.json from scripts/align_words.py (run WITHOUT --script, so it is an independent recognition, not the planner's own estimate)
 --audio   run align_words.py on this audio first (temp file); use the audio track of the rendered preview for the real gate
 --audio-offset  frames: subtitle frame f hears audio at f - offset (timeline audio starts offset frames late)
 --voice-only WAV  PREFERRED gate input: the pure voice track (e.g. host_full.wav / host.wav - no SFX, no BGM) instead of the rendered mix. SFX fill the short pauses and make the recogniser stretch words
                 over the pause (S2 showed this: +7.5 f mean bias on the mix, +1.4 f on the clean voice). Recognition runs WITHOUT the script (independent of the subtitle generator) and, because a clean
                 track has real silences, with --split-pauses by default (--no-split-pauses = plain whisper, shows the recogniser's own pause bias). The report header states the source.
Drift (frames) = subtitle frame - word frame; + = subtitle LATE, - = EARLY. Start uses the first word of the subtitle, end uses the last word's end (to is inclusive, so expected = round(t1*fps) - 1).
Matching: subtitle tokens are matched to recognised words with difflib over the whole text (order-preserving); a first/last word the recogniser missed is taken from the neighbouring word.
FAIL (exit 1) if any |start drift| > --start-tol (default 3 frames @30fps = 0.1 s) or |end drift| > --end-tol (default 6), or > 10 % of subtitles cannot be matched (--allow-frac F tolerates a fraction F of out-of-tolerance subtitles).
Chinese (2026-10-19): automatic when the subtitles contain CJK characters (or --lang zh). The independent recognition runs align_words.py --lang zh (multilingual model, default turbo-q4);
  subtitle text and recognised words are both turned into units (one per character; numbers by their spoken reading, 90% = 百分之九十; a Latin acronym = one unit) and matched with difflib;
  the first / last unit of each subtitle gives the word start / end (a unit inside a multi-unit word takes its share of the word span). Same tolerances, same report.
Noise floor: the verifying recogniser itself is off by ~1.5-2 frames mean abs / ~5 frames P95 at pauses (measured on 示例项目: small vs medium), so a perfect file can still show a few >3 frame entries; judge by mean/P95 and the worst list.
Also prints the constant offset (median start drift) and the drift left after removing it: a big median = one global shift (audio offset); a big residual = per-block timing error (estimated words).
"""
import argparse, difflib, json, os, re, statistics, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
norm = lambda w: re.sub(r"[^a-z0-9]", '', w.lower().replace('’', "'"))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--timeline', required=True); ap.add_argument('--words'); ap.add_argument('--audio'); ap.add_argument('--fps', type=float, default=30)
    ap.add_argument('--start-tol', type=float, default=3); ap.add_argument('--end-tol', type=float, default=6); ap.add_argument('--audio-offset', type=float, default=0)
    ap.add_argument('--report'); ap.add_argument('--json'); ap.add_argument('--top', type=int, default=8); ap.add_argument('--model', default=None, help='default small (en) / turbo-q4 (zh)')
    ap.add_argument('--lang', default='auto', choices=['auto', 'en', 'zh'], help='auto = zh when the subtitles contain CJK characters')
    ap.add_argument('--allow-frac', type=float, default=0.0, help='tolerate this fraction of out-of-tolerance subtitles (recogniser noise); default 0 = strict')
    ap.add_argument('--title', default='Subtitle sync (G5.5)')
    ap.add_argument('--voice-only', help='pure voice wav (no SFX / BGM): recognise this instead of a rendered mix; implies --split-pauses unless --no-split-pauses')
    ap.add_argument('--no-split-pauses', action='store_true', help='with --voice-only: do not split words at real silences (plain whisper)')
    A = ap.parse_args(); fps = A.fps
    source = 'words.json given'
    tl = json.load(open(A.timeline))
    zh = A.lang == 'zh' or (A.lang == 'auto' and any(re.search(r'[\u3400-\u9fff]', s.get('text', '')) for s in tl.get('subtitles', [])))
    if not zh and A.model is None: A.model = 'small'
    if not A.words:
        if A.voice_only: A.audio = A.voice_only
        if not A.audio: sys.exit('need --words, --audio or --voice-only')
        A.words = os.path.join(tempfile.mkdtemp(prefix='sync_'), 'words.json')
        cmd = [sys.executable, os.path.join(HERE, 'align_words.py'), A.audio, '--out', A.words] + (['--model', A.model] if A.model else []) + (['--lang', 'zh'] if zh else [])
        if A.voice_only and not A.no_split_pauses: cmd.append('--split-pauses')
        if zh and not (A.voice_only and not A.no_split_pauses): cmd.append('--no-split-pauses')  # zh splits by default; keep the plain-whisper column plain
        subprocess.run(cmd, check=True)
        source = ('voice-only track %s, no script%s' % (A.voice_only, '' if A.no_split_pauses else ', split-pauses') if A.voice_only else 'audio %s (rendered mix?), no script' % A.audio)
    wj = json.load(open(A.words))
    subs = [s for s in tl['subtitles'] if not s.get('hidden')]
    W = [w for s in wj['sentences'] for w in s['words']]
    t0 = lambda w: w['t0'] * fps if 't0' in w else w['start'] * (fps / wj.get('fps', fps)); t1 = lambda w: w['t1'] * fps if 't1' in w else w['end'] * (fps / wj.get('fps', fps))
    S = []; own = []  # flattened subtitle tokens
    if zh:  # per-unit: split every word into its units (time shared evenly), so W/Wn are units from here on
        sys.path.insert(0, HERE); from align_words import zh_units_from_text
        U = []
        for w in W:
            ks = zh_units_from_text(w['text']); a, b = t0(w), t1(w)
            for k, key in enumerate(ks): U.append(dict(text=key, _t0=a + (b - a) * k / len(ks), _t1=a + (b - a) * (k + 1) / len(ks)))
        W = U; t0 = lambda w: w['_t0']; t1 = lambda w: w['_t1']; Wn = [w['text'] for w in W]
        for i, s in enumerate(subs):
            for key in zh_units_from_text(s['text']): S.append(key); own.append(i)
    else:
        Wn = [norm(w['text']) for w in W]
        for i, s in enumerate(subs):
            for tok in s['text'].split():
                if norm(tok): S.append(norm(tok)); own.append(i)
    m = [None] * len(S)
    for a, b, n in difflib.SequenceMatcher(None, S, Wn, autojunk=False).get_matching_blocks():
        for k in range(n): m[a + k] = b + k
    rows = []; unmatched = []
    for i, s in enumerate(subs):
        idx = [k for k in range(len(S)) if own[k] == i]
        hit = [(k, m[k]) for k in idx if m[k] is not None]
        if not hit: unmatched.append(s); continue
        k0, j0 = hit[0]; k1, j1 = hit[-1]
        jf = max(0, j0 - (k0 - idx[0])); jl = min(len(W) - 1, j1 + (idx[-1] - k1))  # first/last word missed by ASR -> neighbouring word
        fa = t0(W[jf]) + A.audio_offset; fb = t1(W[jl]) + A.audio_offset - 1
        rows.append(dict(id=s['id'], text=s['text'], sub_from=s['from'], sub_to=s['to'], word_from=round(fa, 1), word_to=round(fb, 1), d_start=round(s['from'] - fa, 1), d_end=round(s['to'] - fb, 1),
                         edge_guess=(jf != j0 - (k0 - idx[0])) or (jl != j1 + (idx[-1] - k1)) or k0 != idx[0] or k1 != idx[-1]))
    if not rows: sys.exit('no subtitle could be matched to the recognised words')
    st = [r['d_start'] for r in rows]; en = [r['d_end'] for r in rows]
    p95 = lambda v: sorted(abs(x) for x in v)[min(len(v) - 1, int(round(.95 * (len(v) - 1))))]
    stat = lambda v: dict(mean=round(statistics.mean(v), 2), mean_abs=round(statistics.mean(abs(x) for x in v), 2), max_abs=round(max(abs(x) for x in v), 1), p95_abs=round(p95(v), 1), median=round(statistics.median(v), 1))
    S_, E_ = stat(st), stat(en); med = S_['median']; res_start = [x - med for x in st]
    bad = [r for r in rows if abs(r['d_start']) > A.start_tol or abs(r['d_end']) > A.end_tol]
    umr = len(unmatched) / len(subs); ok = len(bad) <= A.allow_frac * len(rows) and umr <= .10
    L = [f'# {A.title}', '', f'timeline `{A.timeline}`  /  source: {source}  /  words `{A.words}` ({wj.get("meta", {}).get("model", "?")}, {len(W)} {"characters" if zh else "words"})  /  fps {fps:g}  /  audio-offset {A.audio_offset:g} f',
         f'subtitles {len(subs)}, matched {len(rows)}, unmatched {len(unmatched)}.  Drift = subtitle - word, frames; + = subtitle late, - = early.', '',
         f'**{"PASS" if ok else "FAIL"}**  (start tol +-{A.start_tol:g} f = {A.start_tol / fps * 1000:.0f} ms, end tol +-{A.end_tol:g} f)', '',
         '| | mean (signed) | mean abs | max abs | P95 abs | median |', '|---|---|---|---|---|---|',
         f"| start | {S_['mean']} f ({S_['mean'] / fps * 1000:.0f} ms) | {S_['mean_abs']} f | {S_['max_abs']} f ({S_['max_abs'] / fps * 1000:.0f} ms) | {S_['p95_abs']} f | {S_['median']} f |",
         f"| end | {E_['mean']} f | {E_['mean_abs']} f | {E_['max_abs']} f | {E_['p95_abs']} f | {E_['median']} f |", '',
         f'constant offset (median start drift) = {med:g} f; start drift after removing it: mean abs {statistics.mean(abs(x) for x in res_start):.2f} f, max abs {max(abs(x) for x in res_start):.1f} f, P95 {p95(res_start):.1f} f.',
         f'start drift outside +-{A.start_tol:g}: {sum(abs(x) > A.start_tol for x in st)}/{len(st)}; subtitles early (<= -1 f): {sum(x <= -1 for x in st)}; late (>= +3 f): {sum(x >= 3 for x in st)}.']
    worst = sorted(rows, key=lambda r: -max(abs(r['d_start']), abs(r['d_end']) * A.start_tol / A.end_tol))[:A.top]
    L += ['', f'## worst {len(worst)}', '', '| id | sub from..to | word from..to | d start | d end | text |', '|---|---|---|---|---|---|'] + [f"| {r['id']} | {r['sub_from']}..{r['sub_to']} | {r['word_from']}..{r['word_to']} | {r['d_start']:+} | {r['d_end']:+} | {r['text']}{' (edge word guessed)' if r['edge_guess'] else ''} |" for r in worst]
    if bad: L += ['', f'## FAIL list ({len(bad)})', '', '| id | sub from..to | word from..to | d start | d end | text |', '|---|---|---|---|---|---|'] + [f"| {r['id']} | {r['sub_from']}..{r['sub_to']} | {r['word_from']}..{r['word_to']} | {r['d_start']:+} | {r['d_end']:+} | {r['text']} |" for r in bad]
    if unmatched: L += ['', 'unmatched: ' + ', '.join(s['id'] for s in unmatched)]
    txt = '\n'.join(L) + '\n'; print(txt)
    if A.report: os.makedirs(os.path.dirname(os.path.abspath(A.report)), exist_ok=True); open(A.report, 'w').write(txt)
    if A.json: json.dump(dict(ok=ok, start=S_, end=E_, rows=rows, unmatched=[s['id'] for s in unmatched]), open(A.json, 'w'), indent=1)
    sys.exit(0 if ok else 1)

if __name__ == '__main__': main()
