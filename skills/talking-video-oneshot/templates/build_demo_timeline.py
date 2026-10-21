#!/usr/bin/env python3
"""Build templates/timeline.example.json (90s, template A, N=2) from a hand-written beat spec.

This is NOT a planner. It reuses the mechanical builder in the Remotion project
(<工程目录>/scripts/make_sample_timelines.py: sentence/word frames by uniform chars-per-second fill,
subtitle splitting <=14 chars, scene from/dur on sentence starts, overlays at word.start+2, chapters/HUD) and only supplies the beats.
Placeholder assets only (public/placeholder/). Real project: replace sentence/word frames with the digital-human tool's
word timestamps (see references/digital-human.md section 6) and the placeholder paths with real files.

Usage: python3 build_demo_timeline.py [out.json]
"""
import json, os, sys

sys.path.insert(0, os.path.expanduser('<工程目录>/scripts'))
import make_sample_timelines as m  # noqa: E402

m.TOTAL = 2700  # 90 s @ 30 fps
S, PUSH, PAN, PULL, PUNCH, PIP, FLANK, CALL, SPOT = m.S, m.PUSH, m.PAN, m.PULL, m.PUNCH, m.PIP, m.FLANK, m.CALL, m.SPOT

HUD = ['转成文字', '整理纪要']
SPEC = {
    'title': '示例：新手怎么用 AI 整理会议纪要（90 秒，模板 A 教程型，N=2；素材与数字均为示例数据）',
    'template': 'A_tool_review',
    'files': {
        'logo': 'placeholder/logo.png',
        'screen_prompt': 'placeholder/screen_upload.mp4', 'screen_ask': 'placeholder/screen_transcribe.mp4',
        'screen_script': 'placeholder/screen_summary.mp4', 'screen_render': 'placeholder/screen_share.mp4',
        'clip_before': 'placeholder/clip_orig.mp4', 'clip_after': 'placeholder/clip_ai.mp4',
        'broll_desk': 'placeholder/broll_2.jpg', 'broll_city': 'placeholder/broll_4.jpg',
        'thumb_1': 'placeholder/broll_1.jpg', 'thumb_2': 'placeholder/broll_3.jpg',
    },
    'beats': [
        # 钩子 0-12s
        {'kind': 'host_tag', 'sents': [S('开会十分钟，整理纪要四十分钟？', '四十分钟'), S('其实交给AI，五分钟就够了。', '五分钟')],
         'overlays': [FLANK(0, '四十分钟', 'left', 'red'), FLANK(1, '五分钟', 'right', 'lime')], 'rhythm': 'tight'},
        {'kind': 'broll', 'sents': [S('以前开完会，要回听录音、逐条打字，'), S('还得熬一下午。')], 'props': {'src': 'broll_desk', 'kind': 'image', 'dim': 0.45}},
        {'kind': 'host_tag', 'sents': [S('今天教你用AI，两步搞定这件事。', '两步'), S('不用学复杂软件，会打字就行。')], 'overlays': [FLANK(0, '两步', 'right', 'lime')]},
        # 定义 / 对比 12-30s
        {'kind': 'brand_card', 'sents': [S('Claude是个AI助手，'), S('会议录音转出的文字，它也能直接整理。')], 'pip': PIP,
         'props': {'logo': 'logo', 'name': 'Claude', 'variant': 'white_card'}},
        {'kind': 'compare', 'sents': [S('以前要回听、打字、反复核对待办，', '以前'), S('现在先转成文字，再让它整理就行。', '现在', '转成文字')],
         'props': {'variant': 'pills_vs', 'left': {'label': '手动整理', 'items': ['回听', '打字', '核对', '排版'], 'atWord': ('@', 0, '以前')},
                   'right': {'label': '交给AI', 'items': ['转文字', '提结论', '列待办', '发群里'], 'atWord': ('@', 1, '现在')}, 'listAtWord': ('@', 1, '转成文字')}},
        {'kind': 'step_list', 'sents': [S('整个流程就两步：转文字，再整理。', '转文字', '再整理')], 'pip': PIP,
         'props': {'activeIndex': 1, 'steps': [{'no': '01', 'title': '转成文字', 'thumb': 'thumb_1', 'atWord': ('@', 0, '转文字')}, {'no': '02', 'title': '整理纪要', 'thumb': 'thumb_2', 'atWord': ('@', 0, '再整理')}]}},
        {'kind': 'host_full', 'sents': [S('我们一步一步来，'), S('先看最简单的第一步。')]},
        # 演示单元 1
        {'kind': 'chapter_card', 'sents': [S('第一步，先把会议录音转成文字。')], 'props': {'label': 'STEP 1', 'title': '转成文字', 'ghostText': 'TEXT'},
         'chapter': {'index': 1, 'title': '转成文字', 'label': 'STEP 1', 'hud': {'stack': HUD}}},
        {'kind': 'screen_demo', 'sents': [S('把录音文件上传，选好语言，', '录音'), S('比如：一场四十分钟的周会。')], 'pip': PIP,
         'props': {'src': 'screen_prompt', 'kind': 'video'}, 'camera': [PUSH(6, [0.5, 0.5])],
         'overlays': [CALL(0, '录音', {'x': 0.3, 'y': 0.35, 'w': 0.4, 'h': 0.3}, '先上传', 'down')]},
        {'kind': 'screen_demo', 'sents': [S('它会先转写，你等进度条走完就行。')], 'pip': PIP,
         'props': {'src': 'screen_ask', 'kind': 'video'}, 'camera': [PULL(4)]},
        {'kind': 'screen_demo', 'sents': [S('转完之后，文字稿会分好发言人。', '发言人'), S('这个过程大概一分钟。', '一分钟')], 'pip': PIP,
         'props': {'src': 'screen_script', 'kind': 'video'}, 'camera': [PUSH(4, [0.7, 0.3], 1.1)],
         'overlays': [SPOT(0, '发言人', {'x': 0.53, 'y': 0.18, 'w': 0.33, 'h': 0.16}, '分好发言人')]},
        {'kind': 'host_punch', 'sents': [S('这一步，你只需要把录音传上去，'), S('别的什么都不用管。')], 'camera': [PUNCH]},
        # 演示单元 2
        {'kind': 'chapter_card', 'sents': [S('第二步，让它把纪要整理出来。')], 'props': {'label': 'STEP 2', 'title': '整理纪要', 'ghostText': 'NOTES'},
         'chapter': {'index': 2, 'title': '整理纪要', 'label': 'STEP 2', 'hud': {'stack': HUD}, 'until': 16}},
        {'kind': 'screen_demo', 'sents': [S('输入要求，纪要就开始自己生成了。', '输入要求')], 'pip': PIP,
         'props': {'src': 'screen_render', 'kind': 'video'},
         'camera': [{'kind': 'push', 'atWord': (0, '输入要求'), 'dur': 28, 'scale': [1, 1.12], 'origin': [0.8, 0.15], 'ease': 'inOutCubic', 'hold': True}],
         'overlays': [CALL(0, '输入要求', {'x': 0.74, 'y': 0.1, 'w': 0.14, 'h': 0.08}, None, 'down')]},
        {'kind': 'compare', 'sents': [S('左边是原始文字，右边是整理好的纪要。', '左边', '右边')],
         'props': {'variant': 'result_pair', 'left': {'label': '原始文字', 'items': [], 'media': 'clip_before', 'atWord': ('@', 0, '左边')},
                   'right': {'label': '纪要', 'items': [], 'media': 'clip_after', 'atWord': ('@', 0, '右边')}}},
        {'kind': 'host_full', 'sents': [S('说实话，结论和待办都比我手写的清楚。'), S('我只花了五分钟，其余全是它在跑。')]},
        # 证据数字
        {'kind': 'big_number', 'sents': [S('我拿自己的五场会试了一遍，平均每场从四十分钟，降到五分钟。', '四十分钟', '五分钟')], 'pip': PIP,
         'props': {'variant': 'center', 'bg': 'broll_city', 'items': [
             {'label': '以前整理一场（示例数据）', 'value': '40', 'unit': '分钟', 'sub': 'BEFORE', 'atWord': ('@', 0, '四十分钟')},
             {'label': '现在整理一场（示例数据）', 'value': '5', 'unit': '分钟', 'sub': 'NOW', 'atWord': ('@', 0, '五分钟')}]}},
        {'kind': 'host_punch', 'sents': [S('所以关键不是工具多强，'), S('而是你的时间被省下了多少。')], 'camera': [PUNCH]},
        # 总结 / CTA
        {'kind': 'summary_card', 'sents': [S('最后复述一遍：先转文字，再整理，', '转文字', '再整理'), S('两步就够了。')],
         'props': {'variant': 'single', 'title': '两步搞定', 'items': [{'no': '1', 'text': '先转文字', 'atWord': ('@', 0, '转文字')}, {'no': '2', 'text': '再整理', 'atWord': ('@', 0, '再整理')}]}},
        {'kind': 'host_tag', 'sents': [S('你最想整理哪种会议？', '哪种会议'), S('评论区告诉我，我们下期见。')], 'overlays': [FLANK(0, '哪种会议', 'right', 'red')]},
    ],
}

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'timeline.example.json')
    tl, cps, C = m.build(SPEC)
    with open(out, 'w') as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    print(f'{out}: {len(tl["scenes"])} scenes, {len(tl["overlays"])} overlays, {len(tl["subtitles"])} subtitle lines, {C} chars, {cps:.2f} chars/s')
