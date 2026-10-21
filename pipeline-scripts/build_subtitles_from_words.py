#!/usr/bin/env python3
"""Subtitle blocks FROM words.json (forced-alignment output of scripts/align_words.py). No estimation: block.from = first word start, block.to = last word end - 1 (inclusive).

  python3 scripts/build_subtitles_from_words.py words.json [--out subs.json] [--timeline t.json --inplace] [--offset 0]
        [--max-words 7] [--max-chars 38] [--min-words 3] [--pause 14] [--hold 0] [--id-prefix sub]

Segmentation rules (in order):
  1. never cross a sentence boundary of words.json (blocks keep `sentenceId`);
  2. hard break after . ? ! and after a pause >= --pause frames between two words (default 14 = 0.47 s);
  3. soft break after , ; : -- -- and inside a long segment (more than --max-words words or --max-chars characters) the segment is cut into the fewest
     balanced chunks, preferring a cut before a function word (and, of, on, in, to, with, for, that, ...) or after a comma;
  4. a short chunk (< --min-words words) is merged into its neighbour in the same sentence when the merge still fits the limits and no hard break lies between;
  5. blocks never overlap: to = min(last word end - 1, next block from - 1). --hold N keeps a block on screen up to N frames after its last word if the gap to the next block allows
     (default 0 = stick to the word; the sync gate measures the end against the word end, tolerance 6 frames).
Limits = the lint rule for English subtitles (src/targets.ts subtitleEn: <= 7 words and <= 38 characters per line).
Chinese (--lang zh, or automatic when words.json meta.lang == "zh"; 2026-10-19): words are single characters / Latin acronyms / numbers (align_words.py --lang zh), punctuation in word['punct'].
  Limits = lint (<= 14 characters, punctuation and spaces not counted; Latin acronyms and numbers count their characters). Rules, in order:
  1. never cross a sentence of words.json; hard break after 。？！ and after a pause >= --pause frames (default 14);
  2. soft break after ，、；：— (a clause per subtitle); a clause is merged with its neighbour only when one of them is shorter than --min-chars (4) or shorter than --min-dur (18 frames = 0.6 s) and the merge fits;
  3. a clause longer than 14 characters is cut into the fewest chunks by dynamic programming over cut costs: never inside a word (jieba if importable, else the built-in lexicon ZH_LEX), never inside a
     Latin acronym / number, never between 第 + number or number + measure word (步 年 个 ...), strongly avoid a line starting with a particle (的 了 吗 ...) or ending on a function word (的 和 在 把 ...), prefer a cut
     before a conjunction / preposition (但 如果 因为 所以 并 用 把 ...) and at a real pause; even line lengths;
  4. blocks never overlap; from = first character start, to = last character end - 1 (inclusive); a block shorter than --min-dur is extended up to that length when the next block allows
     (the end then lags the voice; marked `(ext)` in the stderr listing); trailing ，。、；： are dropped from the text, inner ones become a space, ？！ are kept.
Output: a JSON array of {id, from, to, text, sentenceId} = timeline.subtitles. With --timeline --inplace the array replaces timeline['subtitles'].
--offset N shifts every block by N frames (use when the timeline starts N frames after the audio, e.g. a cut that begins before the first word).
"""
import argparse, json, math, re, sys

FUNC = {'and', 'or', 'but', 'of', 'on', 'in', 'to', 'with', 'for', 'that', 'which', 'who', 'at', 'by', 'from', 'as', 'than', 'so', 'because', 'when', 'if', 'your', 'our', 'the', 'a', 'an'}
HARD_END = ('.', '?', '!', '…')
SOFT_END = (',', ';', ':', '—', '–')


def clen(ws):
    return len(' '.join(w['text'] for w in ws))


def fits(ws, mw, mc):
    return len(ws) <= mw and clen(ws) <= mc


def split_balanced(ws, mw, mc):
    """cut a too-long run of words into the fewest chunks that fit, choosing cut points by a cost (imbalance + bad-boundary penalties); dynamic programming."""
    n = len(ws)
    if fits(ws, mw, mc):
        return [ws]
    INF = 1e9

    def cut_cost(i):  # cost of cutting between ws[i-1] and ws[i]
        c = 0.0
        prev, nxt = ws[i - 1]['text'], ws[i]['text'].lower().strip(".,;:?!\"'")
        if prev.endswith(SOFT_END):
            c -= 3.0
        if nxt in FUNC:
            c -= 1.5
        if ws[i - 1]['text'].lower().strip(".,;:?!\"'") in FUNC and nxt not in FUNC:
            c += 4.0  # do not strand an article / preposition at the end of a line
        gap = ws[i]['start'] - ws[i - 1]['end']
        c -= min(gap, 12) / 6.0  # a real pause is a good place
        return c

    best = [[INF, -1] for _ in range(n + 1)]
    best[0] = [0.0, -1]
    for j in range(1, n + 1):
        for i in range(j):
            seg = ws[i:j]
            if not fits(seg, mw, mc) or best[i][0] >= INF:
                continue
            c = best[i][0] + 6.0  # each extra line costs
            c += (0 if i == 0 else cut_cost(i))
            # prefer even line lengths
            c += abs(clen(seg) - mc * 0.6) / 12.0
            if c < best[j][0]:
                best[j] = [c, i]
    if best[n][0] >= INF:  # single words too long etc.: fall back to word-count chunks
        k = math.ceil(n / mw)
        sz = math.ceil(n / k)
        return [ws[i:i + sz] for i in range(0, n, sz)]
    out, j = [], n
    while j > 0:
        i = best[j][1]
        out.append(ws[i:j])
        j = i
    return out[::-1]


def segments(sentence_words, pause, soft=True):
    """split one sentence into (words, strong_end) segments at sentence end / pause / comma"""
    segs, cur = [], []
    for k, w in enumerate(sentence_words):
        cur.append(w)
        last = k == len(sentence_words) - 1
        gap = (sentence_words[k + 1]['start'] - w['end']) if not last else 10 ** 6
        hard = last or w['text'].endswith(HARD_END) or gap >= pause
        soft_b = w['text'].endswith(SOFT_END)
        if hard or soft_b:
            segs.append((cur, hard))
            cur = []
    if cur:
        segs.append((cur, True))
    return segs


def build(words_json, mw=7, mc=38, min_words=3, pause=14, hold=0, prefix='sub', offset=0):
    blocks = []
    for sent in words_json['sentences']:
        ws = sent['words']
        if not ws:
            continue
        segs = segments(ws, pause)
        # merge short soft segments forward/backward when still fitting
        merged = []
        for words, hard in segs:
            if merged and not merged[-1][1] and fits(merged[-1][0] + words, mw, mc):
                merged[-1] = (merged[-1][0] + words, hard)
            else:
                merged.append((words, hard))
        # short chunks after a hard break: attach to the previous chunk if that fits and the break was only a pause (not a sentence end)
        chunks = []
        for words, hard in merged:
            for c in split_balanced(words, mw, mc):
                chunks.append(c)
        # merge short chunks with a neighbour when allowed
        i = 0
        while i < len(chunks):
            c = chunks[i]
            if len(c) < min_words:
                if i + 1 < len(chunks) and fits(c + chunks[i + 1], mw, mc) and not c[-1]['text'].endswith(HARD_END):
                    chunks[i:i + 2] = [c + chunks[i + 1]]
                    continue
                if i > 0 and fits(chunks[i - 1] + c, mw, mc) and not chunks[i - 1][-1]['text'].endswith(HARD_END):
                    chunks[i - 1:i + 1] = [chunks[i - 1] + c]
                    continue
            i += 1
        for c in chunks:
            blocks.append(dict(from_=c[0]['start'], end=c[-1]['end'], text=' '.join(w['text'] for w in c), sentenceId=sent.get('id')))
    blocks.sort(key=lambda b: b['from_'])
    out = []
    for k, b in enumerate(blocks):
        nxt = blocks[k + 1]['from_'] if k + 1 < len(blocks) else 10 ** 9
        to = b['end'] - 1
        if hold:
            to = min(to + hold, nxt - 1)
        to = min(to, nxt - 1)
        to = max(to, b['from_'])
        out.append(dict(id=f"{prefix}_{k:02d}", **{'from': b['from_'] + offset, 'to': to + offset}, text=b['text'], sentenceId=b['sentenceId']))
    return out


# ------------------------------------------------------------------------------------------------------------------------------------------ Chinese
ZH_LEX = set("""大模型 语言模型 人工智能 检索 增强 生成 检索增强 检索增强生成 知识库 机器人 客服 合同 制度 查询 问答 企业 资料 资料库 数据 数字 销售额 公司 去年 今年 明年 幻觉 一本正经 胡说八道 胡说
聪明 有时候 时候 比如 可能 业内 问题 解决 做法 第一步 第二步 第三步 相关 内容 一起 根据 回答 出处 适合 合适 每个月 更新 重新 训练 模型 便宜 通常 成本 最后 提醒 调用 一定 权限 控制 权限控制
用户 文档 切片 向量 向量库 搜索 数据库 提示词 上下文 准确 稳定 核对 方便 干净 合理 太长 太短 结论 魔法 答案 先说 为什么 什么 怎么 如何 如果 因为 所以 但是 而且 或者 已经 不是 就是 也就是 还能
我们 你们 他们 自己 可以 需要 应该 比较 非常 特别 以及 并且 然后 首先 其次 总之 一般 一些 这些 那些 这个 那个 这样 那样 只是 只要 只有 目前 现在 以前 之前 之后 同时 通过 使用 提供 支持 管理
系统 平台 工具 产品 服务 应用 技术 方法 方式 过程 结果 效果 效率 能力 质量 安全 风险 隐私 保护 部署 开发 测试 上线 运行 监控 优化 评估 指标 场景 案例 实践 经验 团队 项目 流程""".split())
ZH_MAXLEX = max(len(w) for w in ZH_LEX)
ZH_NOSTART = set('的了着过吗呢吧啊呀么们地得性化度率者')  # attach to the previous character (a cut right before them splits a word / phrase)
ZH_NOEND = set('的了在和与及或把被对向从用让给比跟同为将就都也还又很最更再')  # a line should not end on these
ZH_GOODSTART = set('但如因所而并和与用把被对在从就还也都再先然比让')  # a cut before these is natural
ZH_NOEND_WORDS = set('一定 必须 应该 可以 需要 能够 不能 不要 已经 正在 将要 就是 也是 还是 比较 非常'.split())
ZH_MODAL = set('要会能可应须该得')
ZH_MEASURE = set('步年个月日号条种次倍项点天周季位名件')
JIEBA = None
try:
    import jieba as _jb
    _jb.setLogLevel(60)
    JIEBA = _jb
except Exception:
    pass
ZH_SOFT = '，、；：—,;:'
ZH_HARD = '。！？!?…'
ZH_PUNCT_RE = re.compile(r"[\s，。？！、：；,.?!:;“”\"'（）()]")
ZH_CJK1 = re.compile(r'[㐀-鿿]')


def zh_base(w):
    p = w.get('punct') or ''
    return w['text'][:len(w['text']) - len(p)] if p else w['text']


def zh_weight(ws):
    return len(ZH_PUNCT_RE.sub('', ''.join(zh_base(w) for w in ws)))


def zh_inside_word(ws):
    """-> (inside, left_pos): inside[i] = True when a cut between ws[i-1] and ws[i] would split a multi-character word; left_pos[i] = part of speech of the word ending at that cut
    (jieba.posseg if jieba is importable, else ZH_LEX longest match and no POS). Latin / number tokens are single tokens already."""
    n = len(ws)
    inside = [False] * (n + 1)
    left_pos = [''] * (n + 1)
    bases = [ZH_PUNCT_RE.sub('', zh_base(w)) or '\0' for w in ws]
    if JIEBA:
        import jieba.posseg as _ps
        ends = {}  # char offset -> token boundary index
        off = 0
        for i, t in enumerate(bases):
            off += len(t)
            ends[off] = i + 1
        pos = 0
        for wd, flag in _ps.cut(''.join(bases), HMM=True):
            a, b = pos, pos + len(wd)
            for o, i in ends.items():
                if a < o < b:
                    inside[i] = True
            if b in ends:
                left_pos[ends[b]] = flag
            pos = b
    else:
        txt = ''.join(t if (len(t) == 1 and ZH_CJK1.match(t)) else '\0' for t in bases)  # \0 = non-CJK token, never merged
        i = 0
        while i < n:
            L = 1
            for l in range(min(ZH_MAXLEX, n - i), 1, -1):
                if txt[i:i + l] in ZH_LEX:
                    L = l
                    break
            for k in range(1, L):
                inside[i + k] = True
            i += L
    return inside, left_pos


def zh_cut_cost(ws, i, inside, left_pos=None):
    """cost of cutting between ws[i-1] and ws[i]"""
    a, b = zh_base(ws[i - 1]), zh_base(ws[i])
    c = 0.0
    if inside[i]:
        c += 20
    lp = (left_pos or {}) and left_pos[i]
    if lp and (lp[0] in 'nrt' or lp == 'eng'):
        c -= 1  # the line ends on a noun / pronoun / time word: a phrase boundary
    elif lp and lp[0] in 'adpc':
        c += 2  # the line ends on an adverb / adjective / preposition / conjunction that modifies what follows
    if a == '第' or (re.fullmatch(r'[\d.%]+', a) and b in ZH_MEASURE):
        c += 30
    if b in ZH_NOSTART:
        c += 8
    if a in ZH_NOEND:
        c += 6
    if ''.join(zh_base(w) for w in ws[max(0, i - 2):i]) in ZH_NOEND_WORDS or a in ZH_MODAL:
        c += 6  # a line ending on a modal / adverb (一定 / 必须 / 要 / 会 ...) leaves the verb on the next line
    if b[:1] in ZH_GOODSTART:
        c -= 1.5
    pu = ws[i - 1].get('punct') or ''
    if pu and pu[-1] in ZH_SOFT:
        c -= 3
    c -= min(ws[i]['start'] - ws[i - 1]['end'], 12) / 6.0
    return c


def zh_split(ws, mc, min_dur=18):
    n = len(ws)
    if zh_weight(ws) <= mc:
        return [ws]
    inside, left_pos = zh_inside_word(ws)
    INF = 1e9
    best = [[INF, -1] for _ in range(n + 1)]
    best[0] = [0.0, -1]
    for j in range(1, n + 1):
        for i in range(j):
            if best[i][0] >= INF or zh_weight(ws[i:j]) > mc:
                continue
            c = best[i][0] + 6.0 + (0 if i == 0 else zh_cut_cost(ws, i, inside, left_pos)) + abs(zh_weight(ws[i:j]) - mc * 0.6) / 8.0 + (10 if ws[j - 1]['end'] - ws[i]['start'] < min_dur else 0)
            if c < best[j][0]:
                best[j] = [c, i]
    if best[n][0] >= INF:
        k = math.ceil(n / mc)
        sz = math.ceil(n / k)
        return [ws[i:i + sz] for i in range(0, n, sz)]
    out, j = [], n
    while j > 0:
        i = best[j][1]
        out.append(ws[i:j])
        j = i
    return out[::-1]


def zh_text(ws):
    """characters joined without spaces (a space between two adjacent Latin / number tokens and where a clause mark was); trailing ，。、；： dropped, ？！ kept"""
    out = ''
    for k, w in enumerate(ws):
        base = zh_base(w)
        p = w.get('punct') or ''
        if out and re.match(r'[A-Za-z0-9]', out[-1]) and re.match(r'[A-Za-z0-9]', base[:1]):
            out += ' '
        out += base
        keep = ''.join(ch for ch in p if ch in '？！?!…')
        if k + 1 < len(ws):
            out += keep or (' ' if re.search(r'[，、；：,;:—。]', p) else '')
        else:
            out += keep
    return out.strip()


ZH_BREAK_RANK = {'cut': 0, 'pause': 1, 'punct': 2}


def zh_merge_short(chunks, mc, min_chars, min_dur):
    """a chunk shorter than min_chars characters or min_dur frames is merged with a neighbour when the merge fits: never across a 'hard' break (sentence end);
    of the two sides the one with the weaker break wins (inside a clause < pause < punctuation), then the shorter result"""
    dur = lambda c: c[-1]['end'] - c[0]['start']
    i = 0
    while i < len(chunks):
        c, kind = chunks[i]
        if zh_weight(c) < min_chars or dur(c) < min_dur:
            opts = []
            if i > 0 and chunks[i - 1][1] != 'hard' and zh_weight(chunks[i - 1][0] + c) <= mc:
                opts.append((ZH_BREAK_RANK[chunks[i - 1][1]], zh_weight(chunks[i - 1][0] + c), 'prev'))
            if i + 1 < len(chunks) and kind != 'hard' and zh_weight(c + chunks[i + 1][0]) <= mc:
                opts.append((ZH_BREAK_RANK[kind], zh_weight(c + chunks[i + 1][0]), 'next'))
            if opts:
                side = min(opts)[2]
                if side == 'prev':
                    chunks[i - 1:i + 1] = [(chunks[i - 1][0] + c, kind)]
                    i -= 1
                else:
                    chunks[i:i + 2] = [(c + chunks[i + 1][0], chunks[i + 1][1])]
                continue
        i += 1
    return chunks


def build_zh(words_json, mc=14, min_chars=4, pause=14, min_dur=18, hold=0, prefix='sub', offset=0):
    blocks = []
    dur = lambda c: c[-1]['end'] - c[0]['start']
    for sent in words_json['sentences']:
        ws = sent['words']
        if not ws:
            continue
        # break after each segment: 'hard' (。？！ / end of sentence: never merged across), 'punct' (，、；：), 'pause' (>= pause frames, no punctuation), 'cut' (inside a clause)
        segs, cur = [], []
        for k, w in enumerate(ws):
            cur.append(w)
            last = k == len(ws) - 1
            p = w.get('punct') or ''
            gap = (ws[k + 1]['start'] - w['end']) if not last else 10 ** 6
            kind = 'hard' if (last or any(ch in ZH_HARD for ch in p)) else 'punct' if (p and p[-1] in ZH_SOFT) else 'pause' if gap >= pause else None
            if kind:
                segs.append((cur, kind))
                cur = []
        if cur:
            segs.append((cur, 'hard'))
        chunks = []
        for words, kind in segs:
            parts = zh_split(words, mc, min_dur)
            for q in parts:
                chunks.append((q, kind if q is parts[-1] else 'cut'))
        chunks = zh_merge_short(chunks, mc, min_chars, min_dur)
        for c, _ in chunks:
            blocks.append(dict(from_=c[0]['start'], end=c[-1]['end'], text=zh_text(c), sentenceId=sent.get('id')))
    blocks.sort(key=lambda b: b['from_'])
    out = []
    for k, b in enumerate(blocks):
        nxt = blocks[k + 1]['from_'] if k + 1 < len(blocks) else 10 ** 9
        to = b['end'] - 1
        if hold:
            to = min(to + hold, nxt - 1)
        ext = False
        if to - b['from_'] + 1 < min_dur:  # minimum on-screen time ~0.6 s
            want = min(b['from_'] + min_dur - 1, nxt - 1)
            if want > to:
                to = want
                ext = True
        to = min(to, nxt - 1)
        to = max(to, b['from_'])
        d = dict(id=f"{prefix}_{k:02d}", **{'from': b['from_'] + offset, 'to': to + offset}, text=b['text'], sentenceId=b['sentenceId'])
        if ext:
            d['_ext'] = True
        out.append(d)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('words')
    ap.add_argument('--out')
    ap.add_argument('--timeline')
    ap.add_argument('--inplace', action='store_true')
    ap.add_argument('--lang', default='auto', choices=['auto', 'en', 'zh'], help='auto = zh when words.json meta.lang is zh')
    ap.add_argument('--min-chars', type=int, default=4, help='zh: clauses shorter than this are merged with a neighbour')
    ap.add_argument('--min-dur', type=int, default=18, help='zh: minimum on-screen frames (18 = 0.6 s)')
    ap.add_argument('--max-words', type=int, default=7)
    ap.add_argument('--max-chars', type=int, default=None, help='en 38 (default) / zh 14')
    ap.add_argument('--min-words', type=int, default=3)
    ap.add_argument('--pause', type=int, default=14)
    ap.add_argument('--hold', type=int, default=0)
    ap.add_argument('--offset', type=int, default=0)
    ap.add_argument('--id-prefix', default='sub')
    A = ap.parse_args()
    wj = json.load(open(A.words))
    zh = A.lang == 'zh' or (A.lang == 'auto' and wj.get('meta', {}).get('lang') == 'zh')
    if zh:
        mc = A.max_chars or 14
        subs = build_zh(wj, mc, A.min_chars, A.pause, A.min_dur, A.hold, A.id_prefix, A.offset)
        bad = [s for s in subs if len(ZH_PUNCT_RE.sub('', s['text'])) > mc]
        if bad:
            sys.exit('limit violated: ' + ', '.join(s['id'] for s in bad))
        ext = {s['id'] for s in subs if s.get('_ext')}
        for s in subs:
            s.pop('_ext', None)
        print(f"segmenter: {'jieba' if JIEBA else 'built-in lexicon (jieba not installed)'}", file=sys.stderr)
    else:
        A.max_chars = A.max_chars or 38
        subs = build(wj, A.max_words, A.max_chars, A.min_words, A.pause, A.hold, A.id_prefix, A.offset)
        bad = [s for s in subs if len(s['text'].split()) > A.max_words or len(s['text']) > A.max_chars]
        if bad:
            sys.exit('limit violated: ' + ', '.join(s['id'] for s in bad))
        ext = set()
    if A.timeline and A.inplace:
        tl = json.load(open(A.timeline))
        tl['subtitles'] = subs
        json.dump(tl, open(A.timeline, 'w'), indent=1, ensure_ascii=False)
        print(f'{A.timeline}: {len(subs)} subtitles written')
    if A.out:
        json.dump(subs, open(A.out, 'w'), indent=1, ensure_ascii=False)
    if not A.out and not (A.timeline and A.inplace):
        print(json.dumps(subs, indent=1, ensure_ascii=False))
    for s in subs:
        if zh:
            print(f"  {s['id']} {s['from']:>4}..{s['to']:<4} ({s['to'] - s['from'] + 1}f {len(ZH_PUNCT_RE.sub('', s['text']))}c){' (ext)' if s['id'] in ext else ''} {s['text']}", file=sys.stderr)
        else:
            print(f"  {s['id']} {s['from']:>4}..{s['to']:<4} ({len(s['text'].split())}w {len(s['text'])}c) {s['text']}", file=sys.stderr)


if __name__ == '__main__':
    main()
