#!/usr/bin/env python3
"""
渲染手机版克制速查 PNG — 紧凑单行排版.
每英雄占一行: [色块名] 克:A·B·C  怕:X·Y·Z
"""
import json
import os
from pathlib import Path
from collections import defaultdict

from PIL import Image, ImageDraw, ImageFont
from pypinyin import lazy_pinyin

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)

TYPE_MAP = {1: '战士', 2: '法师', 3: '坦克', 4: '刺客', 5: '射手', 6: '辅助'}
TYPE_COLOR = {
    '战士': (192, 57, 43),
    '法师': (142, 68, 173),
    '坦克': (22, 160, 133),
    '刺客': (211, 84, 0),
    '射手': (41, 128, 185),
    '辅助': (127, 140, 141),
    '多形态': (52, 73, 94),
}

BG = (255, 255, 255)
FG = (34, 34, 34)
SUB = (110, 110, 110)
GRP_COLOR = (192, 57, 43)
LINE_COLOR = (235, 235, 235)
GREEN = (39, 174, 96)
RED = (192, 57, 43)
WARN_BG = (255, 248, 225)

W = 1080  # 更宽以适配单行内容
PAD_X = 20
PAD_Y = 20

FONT_REG = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
FONT_BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'

MAX_DISPLAY = 5  # 每边最多显示 5 个英雄名

SUPERSCRIPT_DIGIT = {0: '⁰', 1: '¹', 2: '²', 3: '³', 4: '⁴',
                     5: '⁵', 6: '⁶', 7: '⁷', 8: '⁸', 9: '⁹'}


def font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REG
    if os.path.exists(path):
        return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def load_data():
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

    # 合并元流之子多形态的克制数据
    merged_counter = {}
    merged_by = {}
    for k, v in counters.items():
        if '元流之子' in k:
            for item in v.get('counter', []):
                name_w = item if isinstance(item, list) else [item, 2]
                n, w = name_w[0], name_w[1]
                merged_counter[n] = max(merged_counter.get(n, 0), w)
            for item in v.get('countered_by', []):
                name_w = item if isinstance(item, list) else [item, 2]
                n, w = name_w[0], name_w[1]
                merged_by[n] = max(merged_by.get(n, 0), w)
    if merged_counter:
        counters['元流之子'] = {
            'counter': [[n, w] for n, w in sorted(merged_counter.items(), key=lambda x: -x[1])],
            'countered_by': [[n, w] for n, w in sorted(merged_by.items(), key=lambda x: -x[1])],
        }

    return uniq, dict(sorted(groups.items())), counters


def render():
    uniq, groups, counters = load_data()

    f_title = font(True, 36)
    f_sub = font(False, 20)
    f_grp = font(True, 28)
    f_name = font(True, 22)
    f_data = font(False, 20)
    f_label = font(True, 20)
    f_foot = font(False, 18)

    ROW_H = 44      # 每英雄行高
    GRP_H = 36      # 分组标题行高
    HEADER_H = 146  # 头部 (标题+副标题+图例+系数说明)

    # 计算总高度
    total_h = HEADER_H
    for letter, items in groups.items():
        total_h += GRP_H
        total_h += len(items) * ROW_H
    total_h += 60  # footer
    total_h += 20  # 底部间距

    img = Image.new('RGB', (W, total_h), BG)
    d = ImageDraw.Draw(img)
    y = PAD_Y

    # 标题
    d.text((PAD_X, y), '王者荣耀 · 全英雄克制速查', font=f_title, fill=GRP_COLOR)
    y += 42

    # 副标题 + 数据来源
    sub_text = f'共 {len(uniq)} 英雄 · 数据来自王者营地国服 (真实对局统计)'
    d.text((PAD_X, y), sub_text, font=f_sub, fill=SUB)
    y += 26

    # 图例 (一行): 定位色块
    leg_x = PAD_X
    f_leg = font(True, 18)
    for tn, color in TYPE_COLOR.items():
        bbox = d.textbbox((0, 0), tn, font=f_leg)
        tw = bbox[2] - bbox[0]
        chip_w = tw + 12
        d.rectangle([leg_x, y, leg_x + chip_w, y + 22], fill=color)
        d.text((leg_x + 6, y + 1), tn, font=f_leg, fill=(255, 255, 255))
        leg_x += chip_w + 4
    y += 26

    # 评分说明 (一行)
    f_note = font(False, 17)
    note = '角标 = 克制率% (对该英雄的胜率优势, 越高克制越明显)  更新: 2026-05'
    d.text((PAD_X, y), note, font=f_note, fill=SUB)
    y += 24

    # 各分组
    for letter, items in groups.items():
        # 分组标题
        d.text((PAD_X, y + 4), letter, font=f_grp, fill=GRP_COLOR)
        bbox = d.textbbox((0, 0), letter, font=f_grp)
        lw = bbox[2] - bbox[0]
        d.line([PAD_X + lw + 10, y + GRP_H // 2, W - PAD_X, y + GRP_H // 2], fill=GRP_COLOR, width=1)
        y += GRP_H

        for hero in items:
            name = hero['cname']
            type_cn = hero['type_cn']
            color = TYPE_COLOR.get(type_cn, (80, 80, 80))

            data = counters.get(name, {'counter': [['—', 0]], 'countered_by': [['—', 0]]})
            counter_list = data['counter'][:MAX_DISPLAY]
            by_list = data['countered_by'][:MAX_DISPLAY]

            # 兼容旧格式 (纯字符串列表)
            def normalize(lst):
                return [[x, 2] if isinstance(x, str) else x for x in lst]
            counter_list = normalize(counter_list)
            by_list = normalize(by_list)

            # 名字色块
            bbox = d.textbbox((0, 0), name, font=f_name)
            nw = bbox[2] - bbox[0]
            chip_w = nw + 14
            chip_h = 28
            cy = y + (ROW_H - chip_h) // 2
            d.rectangle([PAD_X, cy, PAD_X + chip_w, cy + chip_h], fill=color)
            d.text((PAD_X + 7, cy + 2), name, font=f_name, fill=(255, 255, 255))

            # 克/怕 数据 (同一行, 用角标)
            data_x = PAD_X + chip_w + 10
            data_y = y + (ROW_H - 24) // 2

            def draw_list_with_sup(draw, items, x, y_pos, label, label_color):
                draw.text((x, y_pos), label, font=f_label, fill=label_color)
                cx = x + 26
                f_sup = font(False, 12)
                for i, (n, w) in enumerate(items):
                    if i > 0:
                        draw.text((cx, y_pos), ' ', font=f_data, fill=SUB)
                        cx += 6
                    draw.text((cx, y_pos), n, font=f_data, fill=FG)
                    nw2 = draw.textbbox((0, 0), n, font=f_data)[2]
                    cx += nw2
                    if w:
                        # 画评分角标 (普通数字, 小字号, 偏上)
                        sup_text = str(round(w, 1))
                        draw.text((cx + 1, y_pos - 6), sup_text, font=f_sup, fill=SUB)
                        cx += draw.textbbox((0, 0), sup_text, font=f_sup)[2] + 3
                    cx += 2
                return cx

            draw_list_with_sup(d, counter_list, data_x, data_y, '克', GREEN)

            mid_x = W // 2 + 40
            draw_list_with_sup(d, by_list, mid_x, data_y, '怕', RED)

            # 分隔线
            d.line([PAD_X, y + ROW_H - 1, W - PAD_X, y + ROW_H - 1], fill=LINE_COLOR, width=1)
            y += ROW_H

    # footer
    y += 10
    d.text((PAD_X, y), '克 = 你强 (你打他容易)  |  怕 = 你弱 (他打你容易)', font=f_foot, fill=SUB)
    y += 22
    d.text((PAD_X, y), 'github.com/yinrong/wzry-counter-cheatsheet', font=f_foot, fill=SUB)
    y += 30

    img = img.crop((0, 0, W, y))
    out = OUT / 'cheatsheet_mobile.png'
    img.save(out, optimize=True)
    print(f'wrote: {out}  size: {img.size}  bytes: {os.path.getsize(out)}')


if __name__ == '__main__':
    render()
