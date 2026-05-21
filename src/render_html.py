#!/usr/bin/env python3
"""按位置分组的克制速查 HTML, 含搜索框 + 字母锚点 + tier 角标."""
import json
from pathlib import Path
from collections import defaultdict

from pypinyin import lazy_pinyin

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)

POS_INFO = {
    1: ('对抗路', '#c0392b'),
    2: ('中路',   '#8e44ad'),
    3: ('发育路', '#2980b9'),
    4: ('游走',   '#16a085'),
    5: ('打野',   '#d35400'),
}
POS_ORDER = [1, 5, 2, 3, 4]

T_COLOR = {'T0': '#e74c3c', 'T1': '#e67e22', 'T2': '#3498db', 'T3': '#7f8c8d'}


def hero_main_position(hero_name, all_data):
    info = all_data['counters'].get(hero_name, {})
    tranks = info.get('tRanks', {})
    if not tranks:
        return 5
    best = sorted(tranks.items(), key=lambda x: (
        ['T0', 'T1', 'T2', 'T3'].index(x[1]) if x[1] in ['T0', 'T1', 'T2', 'T3'] else 99,
        int(x[0]),
    ))
    return int(best[0][0])


def slug(name):
    """生成英雄 anchor id (拼音)."""
    return ''.join(lazy_pinyin(name)).replace('(', '_').replace(')', '')


def main():
    with open(DATA / 'counters.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    update_time = data.get('updateTime', '')

    # 字母索引: {letter: [(name, main_pos)]}
    alpha_idx = defaultdict(list)
    for hero in data['counters']:
        if '(' in hero:
            continue
        py = ''.join(lazy_pinyin(hero))
        letter = py[0].upper() if py else '#'
        alpha_idx[letter].append((hero, hero_main_position(hero, data), py))
    for k in alpha_idx:
        alpha_idx[k].sort(key=lambda x: x[2])
    alpha_idx = dict(sorted(alpha_idx.items()))

    parts = []
    parts.append(f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>王者荣耀 对位克制速查 (顶端排位)</title>
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    font-size: 14px; line-height: 1.4; color: #222; background: #fafafa;
    padding: 0 0 80px;
  }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 12px 14px; }}
  h1 {{ margin: 0 0 4px; font-size: 20px; color: #c0392b; }}
  .meta {{ font-size: 12px; color: #666; margin-bottom: 8px; }}
  .note {{ font-size: 12px; color: #888; margin: 6px 0; line-height: 1.5; }}

  /* Sticky 顶部工具栏 */
  .toolbar {{
    position: sticky; top: 0; z-index: 100;
    background: rgba(255,255,255,.97); backdrop-filter: blur(8px);
    padding: 10px 14px; border-bottom: 1px solid #e0e0e0;
    box-shadow: 0 2px 6px rgba(0,0,0,.05);
  }}
  .toolbar-row {{ display: flex; gap: 8px; align-items: center; max-width: 720px; margin: 0 auto; }}
  #search {{
    flex: 1; padding: 6px 10px; font-size: 14px; border: 1.5px solid #c0392b;
    border-radius: 18px; outline: none;
  }}
  #search:focus {{ border-color: #e74c3c; }}
  .clear-btn {{
    background: #c0392b; color: #fff; border: none; padding: 6px 12px;
    border-radius: 18px; font-size: 13px; cursor: pointer;
  }}

  .alpha-bar {{
    display: flex; flex-wrap: wrap; gap: 3px; margin-top: 6px;
    max-width: 720px; margin: 6px auto 0;
  }}
  .alpha-bar a {{
    padding: 3px 7px; font-size: 12px; font-weight: bold;
    color: #c0392b; text-decoration: none; border: 1px solid #c0392b;
    border-radius: 3px;
  }}
  .alpha-bar a.pos {{ background: #c0392b; color: #fff; border-color: #c0392b; }}

  .legend {{ display: flex; flex-wrap: wrap; gap: 4px; margin: 8px 0; }}
  .legend span {{ padding: 2px 8px; border-radius: 10px; color: #fff; font-size: 12px; }}

  /* 索引区 */
  .index-block {{
    background: #faf5eb; border: 1px solid #dcc89a; border-radius: 6px;
    padding: 10px 12px; margin: 12px 0;
  }}
  .index-title {{ color: #c0392b; font-weight: bold; font-size: 14px; margin-bottom: 8px; }}
  .index-letter {{ display: flex; gap: 6px; padding: 3px 0; flex-wrap: wrap; align-items: center; }}
  .index-letter > b {{ color: #c0392b; font-size: 14px; min-width: 16px; }}
  .index-letter a {{
    display: inline-flex; align-items: center; gap: 3px;
    text-decoration: none; color: #222; font-size: 13px;
    padding: 2px 6px; border-radius: 3px;
  }}
  .index-letter a:hover {{ background: #fff; }}
  .index-letter .dot {{
    display: inline-block; width: 7px; height: 7px; border-radius: 1px;
  }}

  /* 位置 section */
  .pos-hdr {{
    color: #fff; padding: 8px 12px; font-weight: bold; font-size: 17px;
    border-radius: 4px 4px 0 0; margin-top: 18px;
    display: flex; justify-content: space-between; align-items: baseline;
  }}
  .pos-hdr small {{ font-size: 12px; opacity: .9; font-weight: normal; }}

  .row {{
    display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
    padding: 7px 4px; border-bottom: 1px dotted #e0e0e0; font-size: 13px;
    scroll-margin-top: 100px;
  }}
  .row.hidden {{ display: none; }}
  .name {{
    color: #fff; font-weight: bold; padding: 2px 8px; border-radius: 3px;
    font-size: 14px; flex-shrink: 0;
  }}
  .trank {{ font-size: 11px; font-weight: bold; flex-shrink: 0; }}
  .winrate {{ font-size: 11px; color: #888; flex-shrink: 0; }}
  .k-strong {{ color: #27ae60; font-weight: bold; flex-shrink: 0; }}
  .target {{ font-weight: 500; }}
  sup.t1 {{ font-size: 9px; color: #444; vertical-align: super; margin-left: 1px; }}
  sup.t2 {{ font-size: 9px; color: #999; vertical-align: super; margin-left: 1px; }}
  sup.t3 {{ font-size: 9px; color: #bbb; vertical-align: super; margin-left: 1px; }}

  /* 高亮匹配 */
  .row.match {{ background: #fff3cd; }}

  footer {{ margin-top: 24px; padding: 10px; border-top: 1px solid #ddd; font-size: 11px; color: #888; text-align: center; }}
  footer a {{ color: #c0392b; text-decoration: none; }}
</style>
</head>
<body>

<!-- Sticky 工具栏 (搜索 + 字母索引) -->
<div class="toolbar">
  <div class="toolbar-row">
    <input id="search" type="text" placeholder="🔍 输入英雄名快速定位 (李白/lubai/lb)" oninput="onSearch(this.value)">
    <button class="clear-btn" onclick="clearSearch()">清</button>
  </div>
  <div class="alpha-bar">
''')

    # 字母快速跳转
    for letter in alpha_idx:
        parts.append(f'    <a href="#L-{letter}">{letter}</a>\n')
    # 位置跳转
    for pos in POS_ORDER:
        name, color = POS_INFO[pos]
        parts.append(f'    <a class="pos" href="#P-{pos}" style="background:{color};border-color:{color}">{name}</a>\n')

    parts.append(f'''  </div>
</div>

<div class="container">
  <h1>王者荣耀 · 对位克制速查 (顶端排位)</h1>
  <div class="meta">国服 · 王者营地真实对局统计 · 更新 {update_time}</div>
  <div class="note">★ 表格说明: 行=自己英雄, 「克」=克制对象 (按对方位置上色, 同色=同位置对手)</div>
  <div class="note">★ 角标: <b>5.7</b> 精准数据(克制率%) · <span style="color:#999">5.7*</span> 反向构建 · <span style="color:#bbb">?</span> 同位置推断(置信度低)</div>
  <div class="legend">
''')
    for pos in POS_ORDER:
        name, color = POS_INFO[pos]
        parts.append(f'    <span style="background:{color}">{name}</span>\n')
    parts.append('''  </div>

  <!-- 英雄索引 -->
  <div class="index-block">
    <div class="index-title">★ 英雄索引 (点击跳转, 色块=主位置)</div>
''')

    for letter, items in alpha_idx.items():
        parts.append(f'    <div class="index-letter" id="L-{letter}"><b>{letter}</b>')
        for name, main_pos, _ in items:
            color = POS_INFO.get(main_pos, ('', '#888'))[1]
            parts.append(
                f'<a href="#H-{slug(name)}">'
                f'<span class="dot" style="background:{color}"></span>{name}</a>'
            )
        parts.append('</div>\n')

    parts.append('  </div>\n\n')

    # 位置 section
    for pos in POS_ORDER:
        pos_str = str(pos)
        if pos_str not in data['positions']:
            continue
        info = data['positions'][pos_str]
        name, color = POS_INFO[pos]
        heroes = info['heroes']
        parts.append(
            f'  <div class="pos-hdr" id="P-{pos}" style="background:{color}">'
            f'<span>{name}</span><small>{len(heroes)} 英雄 · 按胜率排名</small>'
            f'</div>\n'
        )
        for h in heroes:
            t_rank = h.get('tRank', '')
            wr = h.get('winRate', 0)
            cdata = data['counters'].get(h['name'], {})
            cs = cdata.get('counter', [])
            t_html = (f'<span class="trank" style="color:{T_COLOR.get(t_rank,"#888")}">{t_rank}</span>'
                      if t_rank else '')
            wr_html = f'<span class="winrate">{wr}%</span>' if wr else ''

            target_html = []
            for item in cs[:6]:
                if not isinstance(item, list):
                    continue
                tn = item[0]
                rate = item[1] if len(item) > 1 else 0
                tier = item[2] if len(item) > 2 else 1
                tpos = hero_main_position(tn, data)
                tcolor = POS_INFO.get(tpos, (None, '#888'))[1]
                if tier == 3:
                    sup_html = '<sup class="t3">?</sup>'
                elif tier == 2 and rate:
                    sup_html = f'<sup class="t2">{rate}*</sup>'
                elif rate:
                    sup_html = f'<sup class="t1">{rate}</sup>'
                else:
                    sup_html = ''
                target_html.append(
                    f'<span class="target" style="color:{tcolor}">{tn}{sup_html}</span>'
                )
            parts.append(
                f'  <div class="row" data-name="{h["name"]}" data-py="{slug(h["name"])}" id="H-{slug(h["name"])}">'
                f'<span class="name" style="background:{color}">{h["name"]}</span>'
                f'{t_html}{wr_html}'
                f'<span class="k-strong">克</span>'
                f'{" · ".join(target_html)}'
                f'</div>\n'
            )

    parts.append('''</div>

<footer>
  克 = 你强 (你打他容易) | 角标: 数字=克制率%, *=反向构建, ?=推断<br>
  <a href="https://github.com/yinrong/wzry-counter-cheatsheet">github.com/yinrong/wzry-counter-cheatsheet</a>
</footer>

<script>
function onSearch(q) {
  q = q.trim().toLowerCase();
  const rows = document.querySelectorAll('.row');
  if (!q) {
    rows.forEach(r => { r.classList.remove('hidden', 'match'); });
    return;
  }
  let firstMatch = null;
  rows.forEach(r => {
    const name = (r.dataset.name || '').toLowerCase();
    const py = (r.dataset.py || '').toLowerCase();
    const py_initial = py.split(/(?=[a-z])/).map(s=>s[0]).join('');
    const hit = name.includes(q) || py.includes(q) || py_initial.includes(q);
    r.classList.toggle('hidden', !hit);
    r.classList.toggle('match', hit);
    if (hit && !firstMatch) firstMatch = r;
  });
  if (firstMatch) firstMatch.scrollIntoView({behavior:'smooth', block:'center'});
}
function clearSearch() {
  document.getElementById('search').value = '';
  onSearch('');
}
</script>

</body>
</html>
''')

    out = OUT / 'cheatsheet_mobile.html'
    out.write_text(''.join(parts), encoding='utf-8')
    print(f'wrote: {out}')


if __name__ == '__main__':
    main()
