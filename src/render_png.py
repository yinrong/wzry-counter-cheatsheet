#!/usr/bin/env python3
"""
按位置分组的克制 cheat sheet PNG, 含快速索引.

布局:
  Header (标题 + 数据来源 + tier 说明 + 位置图例)
  ★ 快速索引区: 130 英雄按拼音 A-Z, 每英雄带主位置色块
  对抗路 section
  打野 section
  中路 section
  发育路 section
  游走 section
  Footer

每行: [英雄(自身位置色)] T级 胜率% 克 [对手1] [对手2] ...
克制对象按对方主位置上色, 角标按 tier 区分:
  tier=1 (精准): 数字角标, 黑色
  tier=2 (反向): 数字角标, 灰色 (旁加 *)
  tier=3 (推断): ? 角标, 浅灰
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

POS_COLOR = {
    1: ('对抗路', (192, 57, 43)),
    5: ('打野',   (211, 84, 0)),
    2: ('中路',   (142, 68, 173)),
    3: ('发育路', (41, 128, 185)),
    4: ('游走',   (22, 160, 133)),
}
POS_ORDER = [1, 5, 2, 3, 4]

TRANK_COLOR = {
    'T0': (231, 76, 60),
    'T1': (230, 126, 34),
    'T2': (52, 152, 219),
    'T3': (127, 140, 141),
}

BG = (255, 255, 255)
FG = (34, 34, 34)
SUB = (110, 110, 110)
LIGHT = (180, 180, 180)
TITLE_COLOR = (192, 57, 43)
LINE_COLOR = (235, 235, 235)
GREEN = (39, 174, 96)
INDEX_BG = (250, 245, 235)

# Tier 显示样式
TIER_COLOR = {
    1: (60, 60, 60),       # 精准: 深色
    2: (140, 140, 140),    # 反向: 中灰
    3: (190, 190, 190),    # 推断: 浅灰
}

W = 1080
PAD_X = 20
PAD_Y = 20

FONT_REG = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
FONT_BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'


def font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REG
    if os.path.exists(path):
        return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def load_data():
    with open(DATA / 'counters.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def hero_main_position(hero_name: str, all_data: dict) -> int:
    info = all_data['counters'].get(hero_name, {})
    tranks = info.get('tRanks', {})
    if not tranks:
        return 5
    best = sorted(tranks.items(), key=lambda x: (
        ['T0', 'T1', 'T2', 'T3'].index(x[1]) if x[1] in ['T0', 'T1', 'T2', 'T3'] else 99,
        int(x[0]),
    ))
    return int(best[0][0])


def build_alphabet_index(all_data: dict):
    """按拼音 A-Z 分组, 返回 {letter: [(name, main_pos), ...]}."""
    groups = defaultdict(list)
    for hero in all_data['counters']:
        # 跳过多形态 (元流之子(...))
        if '(' in hero:
            continue
        py = ''.join(lazy_pinyin(hero))
        letter = py[0].upper() if py else '#'
        main_pos = hero_main_position(hero, all_data)
        groups[letter].append((hero, main_pos, py))
    for k in groups:
        groups[k].sort(key=lambda x: x[2])
    return dict(sorted(groups.items()))


def render():
    data = load_data()
    positions = data['positions']
    counters = data['counters']
    update_time = data.get('updateTime', '')

    # 字体
    f_title = font(True, 38)
    f_sub = font(False, 19)
    f_pos_hdr = font(True, 26)
    f_pos_count = font(False, 17)
    f_idx_letter = font(True, 22)
    f_idx_name = font(False, 17)
    f_name = font(True, 22)
    f_trank = font(True, 16)
    f_data = font(False, 20)
    f_label = font(True, 20)
    f_sup = font(True, 13)
    f_foot = font(False, 17)

    ROW_H = 44
    POS_HDR_H = 48

    # 索引区 (按拼音首字母分组)
    alpha_idx = build_alphabet_index(data)

    # ===== 估算总高度 =====
    total_h = PAD_Y
    total_h += 44  # 标题
    total_h += 26  # 副标题
    total_h += 28  # 角标 tier 说明
    total_h += 36  # 位置图例

    # 索引区高度
    IDX_LINE_H = 30
    idx_lines = 0
    for letter, items in alpha_idx.items():
        # 估算每个字母占多少行 (每行约 1080-PAD_X*2 - 30 = 1010px, 每英雄约 110px)
        per_row = max(1, (W - PAD_X * 2 - 30) // 105)
        idx_lines += max(1, (len(items) + per_row - 1) // per_row)
    INDEX_H = 50 + idx_lines * IDX_LINE_H + 20  # 标题 + 行 + 边距
    total_h += INDEX_H

    # 各位置 section
    for pos in POS_ORDER:
        pos_str = str(pos)
        if pos_str not in positions:
            continue
        total_h += POS_HDR_H + 8
        total_h += len(positions[pos_str]['heroes']) * ROW_H
        total_h += 16

    total_h += 80

    canvas_h = max(int(total_h * 1.1), 8000)
    img = Image.new('RGB', (W, canvas_h), BG)
    d = ImageDraw.Draw(img)

    y = PAD_Y

    # ===== Header =====
    d.text((PAD_X, y), '王者荣耀 · 对位克制速查 (顶端排位)', font=f_title, fill=TITLE_COLOR)
    y += 44
    sub = f'国服真实对局统计 · 更新 {update_time}   ★ 表格说明: 行=自己英雄, 克=克制对象 (按对方位置上色, 同色=同位置对手)'
    d.text((PAD_X, y), sub, font=f_sub, fill=SUB)
    y += 26

    # 角标 tier 说明
    note = '角标 = 克制率%   黑色=精准官方  灰色=反向构建  「?」=同位置推断 (置信度低)'
    d.text((PAD_X, y), note, font=f_sub, fill=SUB)
    y += 28

    # 位置图例
    leg_x = PAD_X
    for pos in POS_ORDER:
        name, color = POS_COLOR[pos]
        bbox = d.textbbox((0, 0), name, font=f_pos_count)
        tw = bbox[2] - bbox[0]
        cw = tw + 14
        d.rectangle([leg_x, y, leg_x + cw, y + 24], fill=color)
        d.text((leg_x + 7, y + 2), name, font=f_pos_count, fill=(255, 255, 255))
        leg_x += cw + 6
    y += 36

    # ===== 快速索引区 =====
    idx_top = y
    d.rectangle([PAD_X, y, W - PAD_X, y + INDEX_H], fill=INDEX_BG, outline=(220, 200, 170), width=1)
    d.text((PAD_X + 12, y + 8), '★ 英雄索引 (拼音 A-Z, 色块=主位置)',
           font=font(True, 20), fill=TITLE_COLOR)
    cy = y + 40

    per_row = max(1, (W - PAD_X * 2 - 30) // 105)  # 一行容纳几个英雄
    for letter, items in alpha_idx.items():
        d.text((PAD_X + 12, cy + 4), letter, font=f_idx_letter, fill=TITLE_COLOR)
        ix = PAD_X + 40
        col = 0
        for name, main_pos, _ in items:
            color = POS_COLOR.get(main_pos, (130, 130, 130))[1]
            # 小色块
            d.rectangle([ix, cy + 8, ix + 8, cy + 16], fill=color)
            # 英雄名
            d.text((ix + 12, cy + 4), name, font=f_idx_name, fill=FG)
            tw = d.textbbox((0, 0), name, font=f_idx_name)[2]
            ix += 12 + tw + 18
            col += 1
            if col >= per_row:
                col = 0
                cy += IDX_LINE_H
                ix = PAD_X + 40
                d.text((PAD_X + 12, cy + 4), letter, font=f_idx_letter, fill=LIGHT)
        cy += IDX_LINE_H
    y = idx_top + INDEX_H + 12

    # ===== 各位置 section =====
    for pos in POS_ORDER:
        pos_str = str(pos)
        if pos_str not in positions:
            continue
        info = positions[pos_str]
        pos_name, pos_color = POS_COLOR[pos]
        heroes = info['heroes']

        # section header
        d.rectangle([PAD_X, y, W - PAD_X, y + POS_HDR_H], fill=pos_color)
        d.text((PAD_X + 14, y + 9), pos_name, font=f_pos_hdr, fill=(255, 255, 255))
        cnt_text = f'共 {len(heroes)} 英雄 · 按胜率排名'
        d.text((PAD_X + 200, y + 16), cnt_text, font=f_pos_count, fill=(255, 255, 255))
        y += POS_HDR_H + 4

        for hero in heroes:
            name = hero['name']
            t_rank = hero.get('tRank', '')
            cdata = counters.get(name, {})
            cs = cdata.get('counter', [])

            # 英雄名色块
            bbox = d.textbbox((0, 0), name, font=f_name)
            nw = bbox[2] - bbox[0]
            chip_w = nw + 16
            chip_h = 30
            cy = y + (ROW_H - chip_h) // 2
            d.rectangle([PAD_X, cy, PAD_X + chip_w, cy + chip_h], fill=pos_color)
            d.text((PAD_X + 8, cy + 3), name, font=f_name, fill=(255, 255, 255))

            tx = PAD_X + chip_w + 6
            if t_rank:
                t_color = TRANK_COLOR.get(t_rank, (130, 130, 130))
                d.text((tx, cy + 7), t_rank, font=f_trank, fill=t_color)
                tx += 30

            wr = hero.get('winRate', 0)
            if wr:
                d.text((tx, cy + 8), f'{wr}%', font=f_pos_count, fill=SUB)
                tx += 56

            # 克
            data_x = tx + 4
            data_y = y + (ROW_H - 24) // 2
            d.text((data_x, data_y), '克', font=f_label, fill=GREEN)
            cx = data_x + 26

            for i, item in enumerate(cs[:6]):
                if not isinstance(item, list):
                    continue
                target_name = item[0]
                rate = item[1] if len(item) > 1 else 0
                tier = item[2] if len(item) > 2 else 1

                target_pos = hero_main_position(target_name, data)
                target_color = POS_COLOR.get(target_pos, (100, 100, 100))[1]

                if i > 0:
                    cx += 6

                # 名字
                d.text((cx, data_y), target_name, font=f_data, fill=target_color)
                tw = d.textbbox((0, 0), target_name, font=f_data)[2]
                cx += tw

                # 角标
                sup_color = TIER_COLOR.get(tier, (140, 140, 140))
                if tier == 3:
                    sup_text = '?'
                elif tier == 2 and rate:
                    sup_text = f'{rate}*'
                elif rate:
                    sup_text = str(rate)
                else:
                    sup_text = ''
                if sup_text:
                    d.text((cx + 1, data_y - 6), sup_text, font=f_sup, fill=sup_color)
                    cx += d.textbbox((0, 0), sup_text, font=f_sup)[2] + 3

            d.line([PAD_X, y + ROW_H - 1, W - PAD_X, y + ROW_H - 1], fill=LINE_COLOR, width=1)
            y += ROW_H

        y += 16

    # footer
    y += 8
    d.text((PAD_X, y), '克 = 你强 (你打他容易) | 角标含义: 数字=克制率%, 数字+*=反向构建, ?=同位置推断',
           font=f_foot, fill=SUB)
    y += 22
    d.text((PAD_X, y), 'github.com/yinrong/wzry-counter-cheatsheet', font=f_foot, fill=SUB)
    y += 30

    crop_h = min(y, img.height)
    img = img.crop((0, 0, W, crop_h))
    out = OUT / 'cheatsheet_mobile.png'
    img.save(out, optimize=True)
    print(f'wrote: {out}  size: {img.size}  bytes: {os.path.getsize(out)}')


if __name__ == '__main__':
    render()
