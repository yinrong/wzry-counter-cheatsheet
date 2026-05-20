#!/usr/bin/env python3
"""
渲染手机版克制速查 HTML.
- 输入: data/heroes.json, data/counters.json
- 输出: output/cheatsheet_mobile.html (单列竖版, viewport 适配手机)
"""
import json
from pathlib import Path
from collections import defaultdict

from pypinyin import lazy_pinyin

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)

TYPE_MAP = {1: '战士', 2: '法师', 3: '坦克', 4: '刺客', 5: '射手', 6: '辅助'}
TYPE_COLOR = {
    '战士': '#c0392b',
    '法师': '#8e44ad',
    '坦克': '#16a085',
    '刺客': '#d35400',
    '射手': '#2980b9',
    '辅助': '#7f8c8d',
    '多形态': '#34495e',
}


def main():
    with open(DATA / 'heroes.json', 'r', encoding='utf-8') as f:
        heroes = json.load(f)
    with open(DATA / 'counters.json', 'r', encoding='utf-8') as f:
        counters = json.load(f)

    seen = set()
    uniq = []
    for h in heroes:
        base = h['cname'].split('(')[0]
        if base in seen:
            continue
        seen.add(base)
        h['cname'] = base
        h['type_cn'] = '多形态' if base == '元流之子' else TYPE_MAP.get(h['hero_type'], '?')
        h['py'] = ''.join(lazy_pinyin(base))
        h['initial'] = h['py'][0].upper() if h['py'] else '#'
        uniq.append(h)
    uniq.sort(key=lambda x: (x['initial'], x['py']))

    groups = defaultdict(list)
    for h in uniq:
        groups[h['initial']].append(h)
    groups = dict(sorted(groups.items()))

    parts = []
    parts.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>王者荣耀 全英雄克制速查 (手机版)</title>
<style>
  :root { --primary: #c0392b; --green: #27ae60; --red: #c0392b; --line: #e0e0e0; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    font-size: 15px; line-height: 1.5;
    color: #222; background: #fafafa;
    padding: 14px 16px 80px;
    max-width: 480px; margin: 0 auto;
  }
  header h1 { margin: 0 0 4px; font-size: 22px; color: var(--primary); }
  header .meta { font-size: 12px; color: #666; }
  .warn {
    background: #fff8e1; border-left: 4px solid #f39c12;
    padding: 10px 12px; margin: 14px 0; font-size: 13px; color: #555;
    border-radius: 4px;
  }
  .warn b { color: #b87100; }
  .legend { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 16px; }
  .legend span { padding: 3px 10px; border-radius: 12px; color: #fff; font-size: 12px; }
  .toc { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
  .toc a {
    text-decoration: none; color: var(--primary); border: 1px solid var(--primary);
    padding: 4px 9px; border-radius: 4px; font-weight: bold; font-size: 13px;
  }
  .group-title {
    font-size: 20px; font-weight: bold; color: var(--primary);
    border-bottom: 2px solid var(--primary); margin: 18px 0 10px;
    padding-bottom: 4px; scroll-margin-top: 8px;
  }
  .row { padding: 8px 0; border-bottom: 1px dotted var(--line); }
  .row:last-child { border-bottom: none; }
  .name {
    display: inline-block; padding: 3px 10px; border-radius: 4px;
    color: #fff; font-weight: bold; font-size: 16px; margin-right: 6px;
  }
  .type { font-size: 12px; color: #666; }
  .kv { display: block; margin-top: 4px; font-size: 14px; }
  .k-strong { color: var(--green); font-weight: bold; margin-right: 8px; }
  .k-weak { color: var(--red); font-weight: bold; margin-right: 8px; }
  sup { font-size: 10px; color: #999; vertical-align: super; margin-left: 1px; }
  .note { font-size: 12px; color: #888; margin: 0 0 14px; }
  footer {
    margin-top: 28px; padding-top: 12px; border-top: 1px solid var(--line);
    font-size: 11px; color: #888; text-align: center;
  }
  footer a { color: var(--primary); text-decoration: none; }
</style>
</head>
<body>
<header>
  <h1>王者荣耀 · 全英雄克制速查</h1>
  <div class="meta">共 ''' + str(len(uniq)) + ''' 英雄 · 拼音 A-Z 分组 · 生成 2026-05-20</div>
</header>
<div class="warn">
  <b>数据说明:</b> 英雄列表来自 pvp.qq.com 官方接口 (实时);
  克制关系基于<b>通用克制框架 + 历史版本认知</b>整理, 仅供方向性参考,
  非王者营地实时巅峰赛/顶端排位数据.
</div>
<div class="legend">
''')
    for tn, color in TYPE_COLOR.items():
        parts.append(f'  <span style="background:{color}">{tn}</span>\n')
    parts.append('</div>\n')
    parts.append('<p class="note">角标: <sup>3</sup>=双向确认(最强) <sup>2</sup>=单向官方 <sup>1</sup>=同类推断</p>\n')
    parts.append('<div class="toc">\n')
    for letter in groups:
        parts.append(f'  <a href="#g-{letter}">{letter}</a>\n')
    parts.append('</div>\n')

    def fmt_list(items, max_show=5):
        """Format [[name, weight], ...] or [name, ...] with <sup> tags."""
        out = []
        for item in items[:max_show]:
            if isinstance(item, list):
                n, w = item[0], item[1]
                sup = f'<sup>{w}</sup>' if w else ''
            else:
                n, sup = item, ''
            out.append(f'{n}{sup}')
        return ' · '.join(out)

    for letter, items in groups.items():
        parts.append(f'<div class="group-title" id="g-{letter}">{letter}</div>\n')
        for h in items:
            data = counters.get(h['cname'], {'counter': [['—', 0]], 'countered_by': [['—', 0]]})
            color = TYPE_COLOR[h['type_cn']]
            counter_s = fmt_list(data['counter'])
            by_s = fmt_list(data['countered_by'])
            parts.append(
                f'<div class="row">'
                f'<span class="name" style="background:{color}">{h["cname"]}</span>'
                f'<span class="type">{h["type_cn"]}</span>'
                f'<span class="kv"><span class="k-strong">克</span>{counter_s}</span>'
                f'<span class="kv"><span class="k-weak">怕</span>{by_s}</span>'
                f'</div>\n'
            )

    parts.append('''<footer>
  克 = 你强 (你打他容易) &nbsp;|&nbsp; 怕 = 你弱 (他打你容易)<br>
  <a href="https://github.com/yinrong/wzry-counter-cheatsheet">github.com/yinrong/wzry-counter-cheatsheet</a>
</footer>
</body>
</html>
''')

    out = OUT / 'cheatsheet_mobile.html'
    out.write_text(''.join(parts), encoding='utf-8')
    print(f'wrote: {out}')


if __name__ == '__main__':
    main()
