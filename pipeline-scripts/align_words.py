#!/usr/bin/env python3
"""Word-level timestamps from the real audio -> words.json (same shape as WordsJSON in src/types.ts; frames @30fps, plus float seconds t0/t1 per word).

  python3 scripts/align_words.py AUDIO [--script script.txt|timeline.json|words.json] [--out words.json] [--model small|medium|<hf repo>] [--engine mlx|faster]
                                 [--fps 30] [--host-video projects/x/host.mp4] [--host-audio projects/x/host.wav] [--lang en] [--raw raw.json]

Engine: mlx-whisper (Apple Silicon, default) in the venv ~/.cache/combo-whisper-venv (this script re-execs itself there; override with COMBO_WHISPER_PY).
        faster-whisper (--engine faster) is a CPU fallback: `pip install faster-whisper` into that venv; not needed while mlx works.
Refinement (default on, --no-refine to disable): word starts after a pause / ends before a pause snap to the waveform speech edge (whisper is loose there).
Models: small  = mlx-community/whisper-small.en-mlx  (~0.5 GB fp16, default, fine on an 8 GB Mac)
        medium = mlx-community/whisper-medium.en-mlx (~1.5 GB fp16)  -- never use large on 8 GB.
        Downloaded by huggingface_hub to ~/.cache/huggingface/hub/models--mlx-community--whisper-*.
--lang zh (2026-10-19): Chinese mode. Multilingual model (default `turbo-q4` = mlx-community/whisper-large-v3-turbo-q4, 464 MB; `--model multi-small` = whisper-small-mlx is faster; see MODELS), per-character output: each Chinese character is one word, a Latin
  acronym / number ("RAG", "API", "90%") is one word; punctuation of the script stays attached to the preceding character (text "胡说，" + field punct "，") so the subtitle builder can break on it.
  --script (plain text, one paragraph per line) is strongly recommended: its characters are aligned to the recognised characters with a Needleman-Wunsch sequence alignment
  (digits are compared by their spoken reading: 90% = 百分之九十), the script spelling always wins, the time comes from the recognition; script characters the recogniser missed are interpolated
  between the neighbouring anchors (confidence 0.3, listed in meta.interpolated) and meta.align reports exact / substituted / interpolated counts. Waveform refinement as for English;
  pause splitting is ON by default for zh (zh_split_pauses: per character, punctuation-guided; --no-split-pauses turns it off). whisper stretches / skips are repaired by re-transcribing
  the affected slice (zh_fill_gaps / zh_fix_stretched, logged in meta.gapFills). With the hub cache present the run is offline (HF_HUB_OFFLINE=1).
Abbreviations (zh, 2026-10-20; needs --script): TTS reads RAG / LLM / API letter by letter. --pron [pron.json] ({"RAG": "R A G"}; picked up automatically from the script's / audio's folder if it exists, --no-pron ignores it)
  and/or --auto-abbr (script spelled "R A G" / "R-A-G" / "R·A·G": single capitals separated by space - middle dot) align the SPOKEN form (one slot per letter, matched against the recognised acronym spread over its letters)
  but emit ONE word whose text is the abbreviation (start = first letter start, end = last letter end); per-letter times go to meta.letters (energy-refined split inside the word). Without these flags / file the output is byte-identical to before.
Without --script: text = what was recognised; sentences split at . ? ! (and at pauses > 1.2 s).
With --script (plain text, or a timeline/words json whose sentences[].words[].text is used): text = the script, time = recognition;
  words are matched with difflib; misrecognised words keep the script spelling and the matched time; unmatched script words are interpolated
  between neighbours (confidence 0.3) and listed in meta.interpolated (also printed).
"""
import argparse, difflib, json, os, re, subprocess, sys

VENV_PY = os.environ.get('COMBO_WHISPER_PY', os.path.expanduser('~/.cache/combo-whisper-venv/bin/python'))
MODELS = {'small': 'mlx-community/whisper-small.en-mlx', 'medium': 'mlx-community/whisper-medium.en-mlx',
          # multilingual (needed for --lang zh); sizes on disk: see out/zh-sync/SYNC_REPORT_ZH.md
          'multi-small': 'mlx-community/whisper-small-mlx', 'multi-medium': 'mlx-community/whisper-medium-mlx',
          'turbo': 'mlx-community/whisper-large-v3-turbo', 'turbo-q4': 'mlx-community/whisper-large-v3-turbo-q4'}
ZH_DEFAULT_MODEL = 'turbo-q4'  # 2026-10-19 out/zh-sync: no skipped stretches, best exact match; ~12 s per minute of audio, ~2.4 GB peak
ZH_PROMPT = '以下是普通话的句子。'  # initial_prompt: keeps whisper in simplified Chinese with punctuation
norm = lambda w: re.sub(r"[^a-z0-9]", '', w.lower().replace('’', "'"))
CJK_RE = r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]'
normz = lambda w: re.sub(r"[^a-z0-9\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", '', w.lower())

def resolve_model(model, lang):
    """default model per language; the .en models cannot do Chinese, so small/medium map to their multilingual twins for --lang != en"""
    if not model: return 'small' if lang == 'en' else ZH_DEFAULT_MODEL
    if lang != 'en' and model in ('small', 'medium'): return 'multi-' + model
    return model

def recognise(audio, model, engine, lang):
    """-> list of (text, t0, t1, prob) over the whole file"""
    out = []
    if engine == 'mlx':
        import mlx_whisper
        r = mlx_whisper.transcribe(audio, path_or_hf_repo=MODELS.get(model, model), word_timestamps=True, language=lang, condition_on_previous_text=False, verbose=None,
                                **({'initial_prompt': ZH_PROMPT} if lang == 'zh' else {}))
        for seg in r['segments']:
            for w in seg.get('words', []): out.append((w['word'].strip(), float(w['start']), float(w['end']), float(w.get('probability', 0.5))))
    else:
        from faster_whisper import WhisperModel
        m = WhisperModel({'small': 'small.en', 'medium': 'medium.en'}.get(model, model), device='cpu', compute_type='int8')
        segs, _ = m.transcribe(audio, word_timestamps=True, language=lang, condition_on_previous_text=False)
        for seg in segs:
            for w in seg.words: out.append((w.word.strip(), float(w.start), float(w.end), float(w.probability)))
    if lang == 'zh':
        out = zh_clean_pieces(out)
        if engine == 'mlx':
            for _ in range(3):  # a re-transcribed slice can itself skip its first part: repeat while it still finds something
                k = len(out); out = zh_fill_gaps(out, audio, model)
                if len(out) == k: break
            out = zh_fix_stretched(out, audio, model)
        return out
    return [w for w in out if norm(w[0])]

def zh_clean_pieces(out):
    """zh: a punctuation-only piece is appended to the previous piece (keeps the recogniser's punctuation); split ASCII pieces are re-joined
    (whisper emits 'L','L','M' / 'AP','I' / '20','24年' as separate pieces; joined they match the script's LLM / API / 2024)"""
    m = []
    for w in out:
        t = w[0].strip()
        if not normz(t) and m: m[-1] = (m[-1][0] + t, *m[-1][1:]); continue
        if m and re.fullmatch(r'[A-Za-z0-9.%]+', m[-1][0]) and re.match(r'[A-Za-z0-9%]', t) and w[1] - m[-1][2] < .3:
            m[-1] = (m[-1][0] + t, m[-1][1], w[2], min(m[-1][3], w[3])); continue
        m.append((t, *w[1:]))
    return [w for w in m if normz(w[0])]

ZH_GAP_FILLS = []

def zh_fix_stretched(rec, audio, model, per_unit=.7, ctx=2):
    """whisper can also swallow a stretch of speech into one over-long piece (seen: '为' 14.54-16.30 s covering 'RAG，也就是检索增强生成'). A piece longer than per_unit s per character whose span is
    mostly speech is re-transcribed together with ctx neighbours on each side; the window's pieces are replaced when the new pass finds more characters. Logged in meta.gapFills (kind stretched)."""
    import numpy as np, mlx_whisper
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', audio, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).copy(); hop = 160; n = len(x) // hop
    if n < 10: return rec
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9); thr = max(np.percentile(db, 10) + 12, np.percentile(db, 90) - 35); sp = db > thr
    out = list(rec); i = 0
    while i < len(out):
        w = out[i]; u = max(1, sum(len(k) if k.isascii() else 1 for k in zh_units_from_text(w[0]))); d = w[2] - w[1]  # a Latin acronym is spoken letter by letter
        if d / u > per_unit and sp[int(w[1] / .01):int(w[2] / .01)].mean() > .6:
            a0, b0 = max(0, i - ctx), min(len(out), i + ctx + 1); lo = max(0.0, out[a0][1] - .1); hi = min(n * .01, out[b0 - 1][2] + .1)
            r = mlx_whisper.transcribe(x[int(lo * 16000):int(hi * 16000)], path_or_hf_repo=MODELS.get(model, model), word_timestamps=True, language='zh', condition_on_previous_text=False, verbose=None, initial_prompt=ZH_PROMPT)
            got = zh_clean_pieces([(q['word'].strip(), float(q['start']) + lo, float(q['end']) + lo, float(q.get('probability', 0.5))) for sg in r['segments'] for q in sg.get('words', [])])
            old_u = sum(len(zh_units_from_text(q[0])) for q in out[a0:b0]); new_u = sum(len(zh_units_from_text(q[0])) for q in got)
            ZH_GAP_FILLS.append(dict(kind='stretched', piece=w[0], span=[round(w[1], 2), round(w[2], 2)], window=[round(lo, 2), round(hi, 2)], old_units=old_u, new_units=new_u, used=new_u > old_u, text=''.join(q[0] for q in got)[:60]))
            if new_u > old_u: out[a0:b0] = got; i = a0 + len(got); continue
        i += 1
    return out

def zh_fill_gaps(rec, audio, model, min_gap=1.0, min_speech=.5):
    """whisper sometimes skips a whole stretch of speech (seen on a 62 s Chinese test: 13.7-29.8 s missing, the 30 s window seek jumped over it). For every gap between recognised pieces
    (and before the first / after the last) longer than min_gap that contains >= min_speech s of waveform speech, transcribe just that slice again and insert what it finds. Logged in meta.gapFills."""
    import numpy as np, mlx_whisper
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', audio, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).copy(); hop = 160; n = len(x) // hop
    if n < 10: return rec
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9); thr = max(np.percentile(db, 10) + 12, np.percentile(db, 90) - 35); sp = db > thr
    dur = n * .01; edges = [0.0] + [v for w in rec for v in (w[1], w[2])] + [dur]
    gaps = [(edges[k], edges[k + 1]) for k in range(0, len(edges), 2) if edges[k + 1] - edges[k] >= min_gap]
    add = []
    for a, b in gaps:
        if sp[int(a / .01):int(b / .01)].sum() * .01 < min_speech: continue
        lo = max(0.0, a - .2); hi = min(dur, b + .2)
        r = mlx_whisper.transcribe(x[int(lo * 16000):int(hi * 16000)], path_or_hf_repo=MODELS.get(model, model), word_timestamps=True, language='zh', condition_on_previous_text=False, verbose=None, initial_prompt=ZH_PROMPT)
        got = [(w['word'].strip(), float(w['start']) + lo, float(w['end']) + lo, float(w.get('probability', 0.5))) for sg in r['segments'] for w in sg.get('words', [])]
        got = [w for w in zh_clean_pieces(got) if w[1] >= a - .1 and w[2] <= b + .1]
        ZH_GAP_FILLS.append(dict(gap=[round(a, 2), round(b, 2)], pieces=len(got), text=''.join(w[0] for w in got)[:60]))
        add += got
    return sorted(rec + add, key=lambda w: w[1]) if add else rec

def refine(rec, audio, gap=.15):
    """whisper's DTW word times are loose at pauses (first word of a sentence can be off by 0.3-0.7 s). Snap word starts that follow a pause and word ends that precede one
    to the real speech edge in the waveform (10 ms RMS, threshold = max(floor + 12 dB, p90 - 35 dB)). Words inside continuous speech keep whisper's time."""
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', audio, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32); hop = 160; n = len(x) // hop
    if n < 10 or not rec: return rec, 0
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9); thr = max(np.percentile(db, 10) + 12, np.percentile(db, 90) - 35); sp = db > thr
    out = []; moved = 0
    for i, (w, a, b, p) in enumerate(rec):
        pe = rec[i - 1][2] if i else 0.0; nx = rec[i + 1][1] if i + 1 < len(rec) else n * .01
        if a - pe >= gap or i == 0:  # pause before: find the speech onset near a
            lo = int(max(pe, a - .5) / .01); hi = min(n - 3, int((a + .35) / .01))
            for k in range(lo, hi):
                if sp[k:k + 3].all(): moved += abs(k * .01 - a) > .02; a = k * .01; break
        if nx - b >= gap or i + 1 == len(rec):  # pause after: find where speech falls below threshold
            lo = int(max(a, b - .4) / .01); hi = min(n - 1, int(min(nx, b + .4) / .01))
            idx = [k for k in range(lo, hi) if sp[k]]
            if idx: moved += abs((idx[-1] + 1) * .01 - b) > .02; b = (idx[-1] + 1) * .01
        out.append((w, a, max(b, a + .03), p))
    return out, moved

def split_hidden_pauses(rec, audio, min_sil=.05, max_shift=.6):
    """--split-pauses (opt-in, 2026-10-19 showcase S2): whisper often lets a word run into a short pause and starts the NEXT word inside that pause
    (e.g. "management, | and": whisper 'and' starts 0.5 s before the speaker resumes), so the first pass above never sees a gap.
    For every pair of neighbouring words whose whisper gap is < 0.15 s, look for a real silence (>= min_sil, same threshold as refine) between the middle of
    the previous word and 50 ms before the end of the current one; if found, the previous word ends where the silence starts and the current word starts where it ends."""
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', audio, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32); hop = 160; n = len(x) // hop
    if n < 10 or len(rec) < 2: return rec, 0
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9); thr = max(np.percentile(db, 10) + 12, np.percentile(db, 90) - 35); sp = db > thr
    out = [list(w) for w in rec]; moved = 0
    for i in range(1, len(out)):
        pw, a, b = out[i - 1], out[i][1], out[i][2]
        if a - pw[2] >= .15: continue
        lo = int(max((pw[1] + pw[2]) / 2, a - max_shift) / .01); hi = int(min(n, max(a, b - .05) / .01))
        best = None; k = lo
        while k < hi:
            if not sp[k]:
                j = k
                while j < hi and not sp[j]: j += 1
                if (j - k) * .01 >= min_sil and (best is None or j - k > best[1] - best[0]): best = (k, j)
                k = j
            else: k += 1
        if best:
            s0, s1 = best[0] * .01, best[1] * .01
            if abs(s1 - a) > .02 or abs(s0 - pw[2]) > .02: moved += 1
            pw[2] = max(pw[1] + .03, s0); out[i][1] = s1; out[i][2] = max(out[i][2], s1 + .03)
    return [tuple(w) for w in out], moved

def load_script(path):
    """-> list of (sentence_id, [words])"""
    if path.endswith('.json'):
        j = json.load(open(path))
        return [(s['id'], [w['text'] for w in s['words']]) for s in j['sentences']]
    txt = open(path).read().strip()
    sents = [s for s in re.split(r'(?<=[.!?])\s+|\n+', txt) if s.strip()]
    return [(f's{i + 1:02d}', s.split()) for i, s in enumerate(sents)]

def split_sentences(rec, gap=1.2):
    sents, cur = [], []
    for i, w in enumerate(rec):
        cur.append(w)
        end = re.search(r'[.!?]["\')\]]*$', w[0]) is not None or (i + 1 < len(rec) and rec[i + 1][1] - w[2] > gap)
        if end: sents.append(cur); cur = []
    if cur: sents.append(cur)
    return [(f's{i + 1:02d}', [(w[0], w[1], w[2], w[3], False) for w in s]) for i, s in enumerate(sents)]

def align_script(script, rec):
    S = [(sid, w) for sid, ws in script for w in ws]; Sn = [norm(w) for _, w in S]; Rn = [norm(w[0]) for w in rec]
    t = [None] * len(S)  # (t0, t1, prob, interpolated)
    sm = difflib.SequenceMatcher(None, Sn, Rn, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1): t[i1 + k] = (rec[j1 + k][1], rec[j1 + k][2], rec[j1 + k][3], False)
        elif tag == 'replace' and (i2 - i1) == (j2 - j1):
            for k in range(i2 - i1): t[i1 + k] = (rec[j1 + k][1], rec[j1 + k][2], min(rec[j1 + k][3], .6), False)
    # interpolate runs of unmatched script words (proportional to character count) between neighbours
    i = 0; log = []
    while i < len(S):
        if t[i] is not None: i += 1; continue
        j = i
        while j < len(S) and t[j] is None: j += 1
        a = t[i - 1][1] if i > 0 else (rec[0][1] if rec else 0.0); b = t[j][0] if j < len(S) else (rec[-1][2] if rec else a + .3 * (j - i))
        b = max(b, a + .05 * (j - i)); tot = sum(max(1, len(S[k][1])) for k in range(i, j)); c = a
        for k in range(i, j):
            d = (b - a) * max(1, len(S[k][1])) / tot; t[k] = (c, c + d, .3, True); c += d; log.append(f'{S[k][0]}:{S[k][1]}')
        i = j
    out = []; k = 0
    for sid, ws in script:
        out.append((sid, [(w, *t[k + n][:3], t[k + n][3]) for n, w in enumerate(ws)])); k += len(ws)
    return out, log

# ---------------------------------------------------------------------------------------------------------------------------------- Chinese (--lang zh)
ZD = '零一二三四五六七八九'
ZFOLD = {'两': '二', '兩': '二', '〇': '零'}

def zh_int(n):
    """integer -> spoken reading, 0..99999999 (3 -> 三, 90 -> 九十, 105 -> 一百零五, 12 -> 十二)"""
    if n < 10: return ZD[n]
    if n < 20: return '十' + (ZD[n - 10] if n > 10 else '')
    if n < 100: return ZD[n // 10] + '十' + (ZD[n % 10] if n % 10 else '')
    if n < 10000:
        out = ''; units = [(1000, '千'), (100, '百')]; rest = n; zero = False
        for u, name in units:
            d, rest = divmod(rest, u)
            if d: out += ('零' if zero else '') + ZD[d] + name; zero = False
            elif out: zero = True
        if rest:
            if rest < 10: out += '零' + ZD[rest]
            elif rest < 20 and not out.endswith('零'): out += '一十' + (ZD[rest - 10] if rest > 10 else '')
            else: out += ('零' if zero else '') + zh_int(rest)
        return out
    if n < 10 ** 8:
        a, b = divmod(n, 10000); return zh_int(a) + '万' + (('零' if b < 1000 else '') + zh_int(b) if b else '')
    return ''.join(ZD[int(c)] for c in str(n))

def zh_number_reading(tok, nxt=''):
    """spoken reading of a number token like 90 / 90% / 3.5 / 2024 (a 4-digit number before 年 is read digit by digit); returns the reading string"""
    pct = tok.endswith('%'); t = tok.rstrip('%')
    if '.' in t:
        a, b = t.split('.', 1); r = zh_int(int(a)) + '点' + ''.join(ZD[int(c)] for c in b)
    elif len(t) == 4 and nxt.startswith('年') or (len(t) > 1 and t[0] == '0'): r = ''.join(ZD[int(c)] for c in t)
    else: r = zh_int(int(t))
    return ('百分之' if pct else '') + r

def fold_unit(c):
    return ZFOLD.get(c, c)

def zh_units_from_text(text):
    """text of one recognised piece -> list of keys (CJK char each; Latin/number runs: digits -> reading chars, other ascii -> one key)"""
    keys = []
    for m in re.finditer(r"\d+(?:\.\d+)?%?|[A-Za-z0-9]+(?:[-'.][A-Za-z0-9]+)*|" + CJK_RE, text):
        t = m.group(0)
        if re.fullmatch(r"\d+(?:\.\d+)?%?", t): keys += [fold_unit(c) for c in zh_number_reading(t, text[m.end():m.end() + 1])]
        elif re.match(CJK_RE, t): keys.append(fold_unit(t))
        else: keys.append(re.sub(r'[^a-z0-9]', '', t.lower()))
    return keys

def zh_rec_units(rec, expand=None):
    """recognised pieces -> per-unit (key, t0, t1, prob); a piece with several units shares its span evenly.
    expand (pron mode only): {'rag': ['r','a','g']} -> a recognised acronym is spread over its letters, like the spoken form in the script"""
    out = []
    for w, a, b, p in rec:
        ks = zh_units_from_text(w)
        if expand: ks = [x for k in ks for x in expand.get(k, [k])]
        for i, k in enumerate(ks):
            d = (b - a) / len(ks); out.append((k, a + i * d, a + (i + 1) * d, p))
    return out

# ---------------------------------------------------------------------------------------------------------------------------------- abbreviations (pron.json / --auto-abbr)
ABBR_SEP = r'[ \t \-·・]'
def load_pron(path):
    """pron.json {"RAG": "R A G", ...} -> dict abbreviation -> spoken form (keys starting with _ are comments)"""
    j = json.load(open(path))
    return {k: v for k, v in j.items() if isinstance(v, str) and v.strip() and not k.startswith('_')}

def find_pron(*dirs):
    for d in dirs:
        f = os.path.join(d, 'pron.json')
        if d and os.path.exists(f): return f
    return None

def abbr_keys(units):
    """spoken units -> (keys, labels): one key per spoken unit (a Latin letter run / number reading / CJK char), labels = what is shown for each key"""
    keys, labels = [], []
    for u in units:
        ks = zh_units_from_text(u); keys += ks
        labels += [u] if len(ks) == 1 else (list(u) if len(ks) == len(u) else [u] * len(ks))
    return keys, labels

def build_abbr(pron, auto):
    """-> None or dict(rx=regex source for all abbreviations, entries=[(display, rx_display, rx_spoken, units)], auto=bool). Priority: pron.json entries (longest first), then the auto rule."""
    ents = []; alts = []
    for ab, sp in sorted((pron or {}).items(), key=lambda kv: -len(kv[0])):
        units = [u for u in re.split(r'[\s\-·・]+', sp.strip()) if u]
        r1 = r'(?<![A-Za-z0-9])' + re.escape(ab) + r'(?![A-Za-z0-9]|-[A-Za-z0-9])'
        r2 = r'(?<![A-Za-z0-9])' + (ABBR_SEP + '+').join(re.escape(u) for u in units) + r'(?![A-Za-z0-9])'
        ents.append((ab, re.compile(r1), re.compile(r2), units)); alts += [r1, r2]
    if auto: alts.append(r'(?<![A-Za-z0-9])[A-Z](?:' + ABBR_SEP + r'[A-Z])+(?![A-Za-z0-9])')
    if not alts: return None
    return dict(rx='(?P<abbr>' + '|'.join(alts) + ')', entries=ents, auto=auto)

def abbr_resolve(t, AB):
    """matched text -> (display, units)"""
    for ab, r1, r2, units in AB['entries']:
        if r1.fullmatch(t) or r2.fullmatch(t): return ab, units
    letters = re.findall('[A-Z]', t)
    return ''.join(letters), letters

def abbr_expand_map(sents):
    """{'rag': ['r','a','g']} for letter-by-letter abbreviations in the script (used to spread recognised acronyms over their letters)"""
    return {''.join(t['keys']): t['keys'] for _, toks in sents for t in toks if t.get('kind') == 'abbr' and len(t['keys']) > 1 and all(len(k) == 1 for k in t['keys'])}

def refine_letters(sents, audio):
    """letter times inside each abbreviation word: start from an even split, then move each interior boundary to the quietest 10 ms frame within +-40 % of a letter length
    (TTS leaves a small dip between letters; a boundary only moves for a dip >= 6 dB deep). The first letter starts at the word start, the last ends at the word end. Mutates sents; returns the list for meta.letters."""
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', audio, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32); hop = 160; n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9) if n >= 10 else None
    log = []
    for si, (sid, ws) in enumerate(sents):
        for k, w in enumerate(ws):
            if len(w) < 7 or not w[6]: continue
            labels = [l[0] for l in w[6]]; m = len(labels); a, b = w[1], w[2]; L = (b - a) / m
            cuts = [a + L * i for i in range(1, m)]
            if db is not None:
                for i in range(len(cuts)):
                    lo = max(int((cuts[i] - .4 * L) / .01), int(a / .01) + 1); hi = min(n - 1, int((cuts[i] + .4 * L) / .01))
                    if hi > lo:
                        seg = db[lo:hi + 1]; best = lo + int(np.argmin(seg + .02 * np.abs(np.arange(lo, hi + 1) * .01 - cuts[i]) * 100))  # quietest frame, ties -> closest to the even split
                        if db[best] < db[min(n - 1, int(cuts[i] / .01))] - 6: cuts[i] = best * .01  # only follow a real dip (>= 6 dB below the even-split point); continuous speech keeps the even split
                for i in range(len(cuts)):  # monotonic, each letter >= 40 % of an even share (and >= 30 ms)
                    mn = max(.03, .4 * L)
                    cuts[i] = min(max(cuts[i], (cuts[i - 1] if i else a) + mn), b - mn * (m - 1 - i))
            edges = [a] + cuts + [b]
            lt = [(labels[i], round(edges[i], 3), round(edges[i + 1], 3)) for i in range(m)]
            ws[k] = (*w[:6], lt)
            log.append(dict(sentence=sid, index=k, text=w[0], spoken=' '.join(labels), letters=[dict(c=c, t0=t0, t1=t1) for c, t0, t1 in lt]))
    return log

def zh_tokens(text, AB=None):
    """script text -> sentences: list of (sid, [token]); token = dict(text, keys, punct, kind). One paragraph per line; sentence ends at 。！？!? (closing quotes included) or end of line."""
    sents = []; cur = []; pre = ''
    pat = re.compile((AB['rx'] + '|' if AB else '') + r"\d+(?:\.\d+)?%?|[A-Za-z0-9]+(?:[-'.][A-Za-z0-9]+)*|" + CJK_RE + r"|[^\sA-Za-z0-9]|\s")
    isab = lambda m: bool(AB) and m.lastgroup == 'abbr'
    for line in text.splitlines():
        ms = list(pat.finditer(line))
        i = 0
        while i < len(ms):
            t = ms[i].group(0)
            if t.isspace(): i += 1; continue
            if isab(ms[i]) or re.fullmatch(r"\d+(?:\.\d+)?%?", t) or re.match(r"[A-Za-z0-9]", t) or re.match(CJK_RE, t):
                nxt = line[ms[i].end():ms[i].end() + 1]
                if isab(ms[i]): disp, units = abbr_resolve(t, AB); keys, labels = abbr_keys(units); kind = 'abbr'; t = disp
                elif re.fullmatch(r"\d+(?:\.\d+)?%?", t): keys = [fold_unit(c) for c in zh_number_reading(t, nxt)]; kind = 'num'
                elif re.match(CJK_RE, t): keys = [fold_unit(t)]; kind = 'cjk'
                else: keys = [re.sub(r'[^a-z0-9]', '', t.lower())]; kind = 'latin'
                tok = dict(text=pre + t, keys=keys, punct='', kind=kind); pre = ''
                if kind == 'abbr': tok['labels'] = labels
                j = i + 1; pu = ''
                while j < len(ms) and not (isab(ms[j]) or re.match(r"[A-Za-z0-9]", ms[j].group(0)) or re.match(CJK_RE, ms[j].group(0))):
                    if not ms[j].group(0).isspace(): pu += ms[j].group(0)
                    j += 1
                tok['text'] += pu; tok['punct'] = pu; cur.append(tok); i = j
                # a closing/opening bracket or quote after a sentence mark belongs to the sentence just ended; an opening one before the next token is picked up by `pre` below
                if re.search(r"[。！？!?]", pu) and not re.search(r"[“‘（(《「『【]$", pu): sents.append(cur); cur = []
                elif re.search(r"[“‘（(《「『【]$", pu): tok['text'] = tok['text'][:-1]; tok['punct'] = tok['punct'][:-1]; pre = pu[-1]
            else:
                pre += t; i += 1   # leading punctuation / opening quote before the first token of a sentence
        if cur: sents.append(cur); cur = []
    return [(f's{i + 1:02d}', s) for i, s in enumerate(sents)]

def nw_align(S, R, match=2.0, sub=-1.0, gap=-1.5):
    """global Needleman-Wunsch over script keys S and recognised keys R -> list of (i, j) with i/j None for gaps"""
    n, m = len(S), len(R)
    import numpy as np
    H = np.zeros((n + 1, m + 1), np.float32); T = np.zeros((n + 1, m + 1), np.int8)  # 0 diag, 1 up (script unit unmatched), 2 left (recognised extra)
    H[:, 0] = np.arange(n + 1) * gap; H[0, :] = np.arange(m + 1) * gap; T[1:, 0] = 1; T[0, 1:] = 2
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d = H[i - 1, j - 1] + (match if S[i - 1] == R[j - 1] else sub); u = H[i - 1, j] + gap; l = H[i, j - 1] + gap
            if d >= u and d >= l: H[i, j] = d; T[i, j] = 0
            elif u >= l: H[i, j] = u; T[i, j] = 1
            else: H[i, j] = l; T[i, j] = 2
    i, j = n, m; pairs = []
    while i > 0 or j > 0:
        t = T[i, j]
        if i > 0 and j > 0 and t == 0: pairs.append((i - 1, j - 1)); i -= 1; j -= 1
        elif i > 0 and (t == 1 or j == 0): pairs.append((i - 1, None)); i -= 1
        else: pairs.append((None, j - 1)); j -= 1
    return pairs[::-1]

def align_script_zh(sents, rec):
    """sents: zh_tokens() output; rec: recognised pieces -> (sentences in the align_script() shape, interpolation log, stats)"""
    U = zh_rec_units(rec, abbr_expand_map(sents)); R = [u[0] for u in U]
    flat = [(sid, ti, k) for sid, toks in sents for ti, t in enumerate(toks) for k in t['keys']]
    S = [k for _, _, k in flat]
    pairs = nw_align(S, R)
    ut = [None] * len(S)  # (t0, t1, prob, interpolated, exact)
    for i, j in pairs:
        if i is not None and j is not None:
            ex = S[i] == R[j]; ut[i] = (U[j][1], U[j][2], U[j][3] if ex else min(U[j][3], .6), False, ex)
    log = []; i = 0
    while i < len(S):
        if ut[i] is not None: i += 1; continue
        j = i
        while j < len(S) and ut[j] is None: j += 1
        a = ut[i - 1][1] if i > 0 else (U[0][1] if U else 0.0); b = ut[j][0] if j < len(S) else (U[-1][2] if U else a + .2 * (j - i))
        b = max(b, a + .04 * (j - i))
        for k in range(i, j): d = (b - a) / (j - i); ut[k] = (a + (k - i) * d, a + (k - i + 1) * d, .3, True, False)
        i = j
    # units -> tokens
    out = []; p = 0; stats = dict(units=len(S), exact=0, substituted=0, interpolated=0, recognised_units=len(R))
    for sid, toks in sents:
        ws = []
        for t in toks:
            us = ut[p:p + len(t['keys'])]; p += len(t['keys'])
            stats['exact'] += sum(u[4] for u in us); stats['interpolated'] += sum(u[3] for u in us); stats['substituted'] += sum((not u[3]) and (not u[4]) for u in us)
            t0 = us[0][0]; t1 = us[-1][1]; pr = min(u[2] for u in us); interp = all(u[3] for u in us)
            if any(u[3] for u in us): log.append(f"{sid}:{t['text']}")
            ws.append((t['text'], t0, t1, pr, interp, t['punct'], [(l, u[0], u[1]) for l, u in zip(t['labels'], us)]) if t['kind'] == 'abbr' else (t['text'], t0, t1, pr, interp, t['punct']))
        out.append((sid, ws))
    # monotonic clean-up: no overlaps (a start never before the previous end), at least 30 ms long
    prev = 0.0
    for sid, ws in out:
        for n, w in enumerate(ws):
            a = max(w[1], prev); b = max(w[2], a + .03); ws[n] = (w[0], a, b, w[3], w[4], w[5], *w[6:]); prev = b
    stats['match_rate_exact'] = round(stats['exact'] / max(1, stats['units']), 4); stats['match_rate_incl_substituted'] = round((stats['exact'] + stats['substituted']) / max(1, stats['units']), 4)
    return out, log, stats

def zh_monotonic(sents):
    """no overlaps (a start never before the previous end; whisper's Chinese pieces are sometimes out of order after gap filling), each word >= 30 ms"""
    prev = 0.0
    for sid, ws in sents:
        for n, w in enumerate(ws):
            a = max(w[1], prev); b = max(w[2], a + .03); ws[n] = (w[0], a, b, *w[3:]); prev = b
    return sents

def zh_split_pauses(sents, audio, min_sil=.06, free_sil=.15):
    """--split-pauses for Chinese (the English split_hidden_pauses works on whisper pieces and, with one piece per character, misplaces the silence: it moved the character
    BEFORE a comma behind the comma pause). Here it runs after alignment, on characters, guided by punctuation: for a character carrying punctuation (，。、：…) the longest
    silence >= min_sil between its start + 40 ms and the end of the next character is the pause: the character ends where it starts, the next one starts where it ends.
    Without punctuation only a clear pause (>= free_sil) between the two midpoints is used. Same waveform threshold as refine."""
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', audio, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32); hop = 160; n = len(x) // hop
    flat = [(si, k) for si, (_, ws) in enumerate(sents) for k in range(len(ws))]
    if n < 10 or len(flat) < 2: return sents, 0
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9); thr = max(np.percentile(db, 10) + 12, np.percentile(db, 90) - 35); sp = db > thr
    W = [list(sents[si][1][k]) for si, k in flat]; moved = 0
    for i in range(len(W) - 1):
        w, nx = W[i], W[i + 1]; punct = len(w) > 5 and bool(w[5])
        lo, hi = (w[1] + .04, max(nx[2], nx[1] + .05)) if punct else ((w[1] + w[2]) / 2, (nx[1] + nx[2]) / 2)
        lo_k, hi_k = int(max(0, lo) / .01), int(min(n * .01, hi) / .01); best = None; k = lo_k
        while k < hi_k:
            if not sp[k]:
                j = k
                while j < hi_k and not sp[j]: j += 1
                if best is None or j - k > best[1] - best[0]: best = (k, j)
                k = j
            else: k += 1
        if not best: continue
        k, j = best  # the window can cut the silence (whisper put the next character inside the pause): follow it to its real edges, at most 1 s
        while j < n and not sp[j] and j - best[1] < 100: j += 1
        while k > 0 and not sp[k - 1] and best[0] - k < 100: k -= 1
        if (j - k) * .01 < (min_sil if punct else free_sil): continue
        s0, s1 = k * .01, j * .01
        if abs(s0 - w[2]) > .02 or abs(s1 - nx[1]) > .02: moved += 1
        w[2] = max(w[1] + .03, s0); nx[1] = s1; nx[2] = max(nx[2], s1 + .03)
    # a character whose start still lies in silence (whisper splits a multi-character piece evenly, so '第三' starting inside a pause gives '第' a silent head) starts at the
    # first 30 ms of speech inside it; one whose end lies in silence ends after its last speech frame
    for i, w in enumerate(W):
        k0, k1 = int(w[1] / .01), min(n, int(w[2] / .01))
        lim = min(n - 2, max(k1, min(k0 + 40, int(W[i + 1][2] / .01) - 3))) if i + 1 < len(W) else min(n - 2, k1)  # a character lying entirely in the pause may move up to 0.4 s, never past the next one's end
        if k0 < lim and not sp[k0:k0 + 3].all():
            for j in range(k0, lim):
                if sp[j:j + 3].all():
                    if j * .01 - w[1] > .02: moved += 1
                    w[1] = j * .01; w[2] = max(w[2], w[1] + .03); break
        k0, k1 = int(w[1] / .01), min(n, int(w[2] / .01))
        if k0 < k1 and not sp[k1 - 1]:
            idx = [j for j in range(k0, k1) if sp[j]]
            if idx: w[2] = max(w[1] + .03, (idx[-1] + 1) * .01)
    out = [(sid, []) for sid, _ in sents]
    for (si, k), w in zip(flat, W): out[si][1].append(tuple(w))
    return zh_monotonic(out), moved

def zh_rec_words(rec, gap=1.2):
    """no --script: recognised pieces -> sentences of (text, t0, t1, prob, False, punct), one word per CJK char / Latin run / number; sentence ends at 。！？ or a pause > gap"""
    pat = re.compile(r"\d+(?:\.\d+)?%?|[A-Za-z0-9]+(?:[-'.][A-Za-z0-9]+)*|" + CJK_RE)
    sents, cur = [], []
    for i, (w, a, b, p) in enumerate(rec):
        ms = list(pat.finditer(w)); n = len(ms)
        for k, m in enumerate(ms):
            end = ms[k + 1].start() if k + 1 < n else len(w); pu = re.sub(r'\s', '', w[m.end():end]) if k + 1 == n else ''
            d = (b - a) / n; cur.append((m.group(0) + pu, a + k * d, a + (k + 1) * d, p, False, pu))
        if cur and (re.search(r"[。！？!?]", cur[-1][5]) or (i + 1 < len(rec) and rec[i + 1][1] - b > gap)): sents.append(cur); cur = []
    if cur: sents.append(cur)
    return [(f's{i + 1:02d}', s_) for i, s_ in enumerate(sents)]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('audio'); ap.add_argument('--script'); ap.add_argument('--out', default='words.json'); ap.add_argument('--model', default=None, help='default: small (en) / turbo-q4 (zh)')
    ap.add_argument('--engine', default='mlx', choices=['mlx', 'faster']); ap.add_argument('--fps', type=int, default=30); ap.add_argument('--lang', default='en')
    ap.add_argument('--host-video', default=''); ap.add_argument('--host-audio'); ap.add_argument('--raw', help='also dump the raw recognised words here'); ap.add_argument('--no-refine', action='store_true', help='keep whisper times as is (no waveform snapping at pauses)')
    ap.add_argument('--split-pauses', action='store_true', help='also split words at real silences whisper ran over (see split_hidden_pauses); opt-in')
    ap.add_argument('--pron', nargs='?', const='auto', default=None, help='zh: pronunciation map pron.json {"RAG": "R A G"}: abbreviations are aligned by their spoken form (letter by letter) and come out as ONE word with the abbreviation as text; '
                    'without a path pron.json next to --script / the audio is used. If omitted, such a pron.json is still picked up automatically if it exists (--no-pron to ignore it)')
    ap.add_argument('--no-pron', action='store_true'); ap.add_argument('--auto-abbr', action='store_true', help='zh: also recognise spoken-letter abbreviations in the script by rule: single capitals separated by space / - / middle dot ("R A G", "R-A-G", "R·A·G") -> RAG')
    ap.add_argument('--no-split-pauses', action='store_true', help='zh only: turn off the pause splitting that is ON by default for --lang zh (zh_split_pauses)')
    A = ap.parse_args()
    if A.engine == 'mlx':  # model already in the hub cache -> do not ask the hub again (a flaky connection otherwise kills a run that needs no download)
        import glob
        repo = MODELS.get(resolve_model(A.model, A.lang), resolve_model(A.model, A.lang))
        if glob.glob(os.path.expanduser(f"~/.cache/huggingface/hub/models--{repo.replace('/', '--')}/snapshots/*/weights.*")): os.environ.setdefault('HF_HUB_OFFLINE', '1')
    try:
        if A.engine == 'mlx': import mlx_whisper  # noqa
        else: import faster_whisper  # noqa
    except ImportError:
        if os.path.exists(VENV_PY) and os.path.realpath(sys.executable) != os.path.realpath(VENV_PY): os.execv(VENV_PY, [VENV_PY] + sys.argv)
        sys.exit(f'{A.engine} whisper not installed. Run: python3.12 -m venv ~/.cache/combo-whisper-venv && ~/.cache/combo-whisper-venv/bin/pip install mlx-whisper')
    A.model = resolve_model(A.model, A.lang); zh = A.lang == 'zh'
    if zh and not A.no_split_pauses: A.split_pauses = True  # zh default: measured 5-10 frames early subtitle starts without it (out/zh-sync/SYNC_REPORT_ZH.md)
    rec = recognise(A.audio, A.model, A.engine, A.lang)
    moved = 0
    if not A.no_refine: rec, moved = refine(rec, A.audio)
    split = 0
    if A.split_pauses and not zh: rec, split = split_hidden_pauses(rec, A.audio)
    if A.raw: json.dump([dict(text=w[0], t0=w[1], t1=w[2], p=w[3]) for w in rec], open(A.raw, 'w'), ensure_ascii=False)
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', A.audio], capture_output=True, text=True).stdout.strip() or 0)
    stats = None; letters_log = []
    if zh:
        if A.script:
            src = A.script
            if src.endswith('.json'): j0 = json.load(open(src)); txt = '\n'.join(''.join(w['text'] for w in s_['words']) for s_ in j0['sentences'])
            else: txt = open(src).read()
            AB = None; pf = None
            if not A.no_pron:
                if A.pron not in (None, 'auto'):
                    pf = A.pron
                    if not os.path.exists(pf): sys.exit(f'--pron file not found: {pf}')
                else:
                    pf = find_pron(os.path.dirname(os.path.abspath(src)), os.path.dirname(os.path.abspath(A.audio)))
                    if A.pron == 'auto' and not pf: sys.exit('--pron: no pron.json next to the script / audio')
            if pf or A.auto_abbr: AB = build_abbr(load_pron(pf) if pf else {}, A.auto_abbr)
            sents, log, stats = align_script_zh(zh_tokens(txt, AB), rec)
        else: sents, log = zh_rec_words(rec), []
        sents = zh_monotonic(sents)
        if A.split_pauses: sents, split = zh_split_pauses(sents, A.audio)
        if any(len(w) > 6 for _, ws in sents for w in ws): letters_log = refine_letters(sents, A.audio)
    elif A.script: sents, log = align_script(load_script(A.script), rec)
    else: sents, log = split_sentences(rec), []
    F = A.fps; fr = lambda x: int(round(x * F)); res = []
    for sid, ws in sents:
        words = []
        for w in ws:
            s = fr(w[1]); d = {'text': w[0], 'start': s, 'end': max(s + 1, fr(w[2])), 'confidence': round(w[3], 2), 't0': round(w[1], 3), 't1': round(w[2], 3)}
            if zh and len(w) > 5 and w[5]: d['punct'] = w[5]
            words.append(d)
        if words: res.append({'id': sid, 'start': words[0]['start'], 'end': words[-1]['end'], 'words': words})
    j = {'fps': F, 'hostVideo': A.host_video, 'durationInFrames': fr(dur), 'sentences': res,
         'meta': {'engine': A.engine, 'model': MODELS.get(A.model, A.model) if A.engine == 'mlx' else A.model, 'script': bool(A.script), 'words': sum(len(s['words']) for s in res), 'refinedEdges': moved, 'splitPauses': split, 'interpolated': log}}
    if zh: j['meta']['lang'] = 'zh'; j['meta']['gapFills'] = ZH_GAP_FILLS
    if stats: j['meta']['align'] = stats
    if letters_log: j['meta']['abbr'] = dict(pron=pf, autoAbbr=bool(A.auto_abbr), count=len(letters_log)); j['meta']['letters'] = letters_log
    if A.host_audio: j['hostAudio'] = A.host_audio
    json.dump(j, open(A.out, 'w'), ensure_ascii=False, indent=1)
    print(f"{A.out}: {j['meta']['words']} words, {len(res)} sentences, {len(log)} interpolated; model {j['meta']['model']}" + (f"; exact {stats['match_rate_exact']:.1%}, incl. substituted {stats['match_rate_incl_substituted']:.1%}" if stats else ''))
    if log: print('interpolated:', ', '.join(log[:40]), '...' if len(log) > 40 else '')

if __name__ == '__main__': main()
