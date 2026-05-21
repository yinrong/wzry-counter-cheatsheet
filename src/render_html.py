#!/usr/bin/env python3
"""按位置分组的克制速查 HTML (手机版)."""
import json
from pathlib import Path

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


def main():
    with open(DATA / 'counters.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    update_time = data.get('updateTime', '')

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
    padding: 12px 14px 60px; max-width: 600px; margin: 0 auto;
  }}
  h1 {{ margin: 0 0 4px; font-size: 20px; color: #c0392b; }}
  .meta {{ font-size: 12px; color: #666; }}
  .note {{ font-size: 12px; color: #888; margin: 8px 0; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 4px; margin: 6px 0 14px; }}
  .legend span {{ padding: 2px 8px; border-radius: 10px; color: #fff; font-size: 12px; }}
  .pos-hdr {{
    color: #fff; padding: 8px 12px; font-weight: bold; font-size: 17px;
    border-radius: 4px 4px 0 0; margin-top: 18px;
    display: flex; justify-content: space-between; align-items: baseline;
  }}
  .pos-hdr small {{ font-size: 12px; opacity: .85; font-weight: normal; }}
  .row {{
    display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
    padding: 7px 4px; border-bottom: 1px dotted #e0e0e0; font-size: 13px;
  }}
  .name {{
    color: #fff; font-weight: bold; padding: 2px 8px; border-radius: 3px;
    font-size: 14px; flex-shrink: 0;
  }}
  .trank {{ font-size: 11px; font-weight: bold; flex-shrink: 0; }}
  .winrate {{ font-size: 11px; color: #888; flex-shrink: 0; }}
  .k-strong {{ color: #27ae60; font-weight: bold; flex-shrink: 0; }}
  .target {{ font-weight: 500; }}
  sup {{ font-size: 9px; color: #888; vertical-align: super; margin-left: 1px; }}
</style>
</head>
<body>
<h1>王者荣耀 · 对位克制速查 (顶端排位)</h1>
<div class="meta">国服 · 王者营地真实对局统计 · 更新 {update_time}</div>
<div class="note">角标 = 克制率% (对该英雄的胜率优势) · 颜色 = 对方位置 (同色 = 同位置对手, 用户最常用对位)</div>
<div class="legend">
''')
    for pos in POS_ORDER:
        name, color = POS_INFO[pos]
        parts.append(f'  <span style="background:{color}">{name}</span>\n')
    parts.append('</div>\n')

    for pos in POS_ORDER:
        pos_str = str(pos)
        if pos_str not in data['positions']:
            continue
        info = data['positions'][pos_str]
        name, color = POS_INFO[pos]
        heroes = info['heroes']
        parts.append(
            f'<div class="pos-hdr" style="background:{color}">'
            f'<span>{name}</span><small>{len(heroes)} 英雄 · 按胜率排名</small>'
            f'</div>\n'
        )
        for h in heroes:
            t_rank = h.get('tRank', '')
            wr = h.get('winRate', 0)
            cdata = data['counters'].get(h['name'], {})
            cs = cdata.get('counter', [])
            t_html = (
                f'<span class="trank" style="color:{T_COLOR.get(t_rank,"#888")}">{t_rank}</span>'
                if t_rank else ''
            )
            wr_html = f'<span class="winrate">{wr}%</span>' if wr else ''

            target_html = []
            for item in cs[:6]:
                if isinstance(item, list):
                    tn, rate = item[0], item[1]
                else:
                    tn, rate = item, 0
                tpos = hero_main_position(tn, data)
                tcolor = POS_INFO.get(tpos, (None, '#888'))[1]
                rate_html = f'<sup>{rate}</sup>' if rate else ''
                target_html.append(
                    f'<span class="target" style="color:{tcolor}">{tn}{rate_html}</span>'
                )
            parts.append(
                f'<div class="row">'
                f'<span class="name" style="background:{color}">{h["name"]}</span>'
                f'{t_html}{wr_html}'
                f'<span class="k-strong">克</span>'
                f'{" · ".join(target_html)}'
                f'</div>\n'
            )

    parts.append(f'''<footer style="margin-top:24px; padding-top:10px; border-top:1px solid #ddd; font-size:11px; color:#888; text-align:center;">
  克 = 你强 (你打他容易) &nbsp;|&nbsp; 角标 = 克制率%<br>
  <a href="https://github.com/yinrong/wzry-counter-cheatsheet" style="color:#c0392b">github.com/yinrong/wzry-counter-cheatsheet</a>
</footer>
</body>
</html>
''')

    out = OUT / 'cheatsheet_mobile.html'
    out.write_text(''.join(parts), encoding='utf-8')
    print(f'wrote: {out}')


if __name__ == '__main__':
    main()
