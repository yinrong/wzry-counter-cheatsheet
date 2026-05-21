#!/usr/bin/env python3
"""
渲染按位置分组的克制 cheat sheet PNG.

布局:
  顶部: 标题 + 数据来源
  5 个位置 section (对抗路/打野/中路/发育路/游走)
  每 section 内:
    位置头部 (色块 + 位置名 + 该位置英雄数)
    每英雄一行: [英雄色块] [T级] 克 对象1·对象2·对象3 (角标=克制率%)
  克制对象按对方位置颜色编码 (同位置同色, 用户最常用对位)

颜色编码: 5 位置各一色
"""
import json
import os
from pathlib import Path
from collections import defaultdict

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)

# 5 位置颜色 (饱和度高, 区分明显)
POS_COLOR = {
    1: ('对抗路', (192, 57, 43)),    # 红
    5: ('打野',   (211, 84, 0)),     # 橙
    2: ('中路',   (142, 68, 173)),   # 紫
    3: ('发育路', (41, 128, 185)),   # 蓝
    4: ('游走',   (22, 160, 133)),   # 青绿
}
POS_ORDER = [1, 5, 2, 3, 4]  # 显示顺序: 对抗→打野→中→发育→游走

# T 级颜色
TRANK_COLOR = {
    'T0': (231, 76, 60),
    'T1': (230, 126, 34),
    'T2': (52, 152, 219),
    'T3': (127, 140, 141),
}

BG = (255, 255, 255)
FG = (34, 34, 34)
SUB = (110, 110, 110)
TITLE_COLOR = (192, 57, 43)
LINE_COLOR = (235, 235, 235)
GREEN = (39, 174, 96)

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
    """找英雄的主位置: T 级最高的, 同 T 级取胜率最高."""
    info = all_data['counters'].get(hero_name, {})
    tranks = info.get('tRanks', {})
    if not tranks:
        return None
    best = sorted(tranks.items(), key=lambda x: (
        ['T0', 'T1', 'T2', 'T3'].index(x[1]) if x[1] in ['T0', 'T1', 'T2', 'T3'] else 99,
        int(x[0]),
    ))
    return int(best[0][0])


def get_target_position(target_name: str, all_data: dict) -> int:
    """目标英雄主位置."""
    p = hero_main_position(target_name, all_data)
    return p if p else 5  # 默认打野色


def render():
    data = load_data()
    positions = data['positions']
    counters = data['counters']
    update_time = data.get('updateTime', '')

    # 字体
    f_title = font(True, 38)
    f_sub = font(False, 20)
    f_pos_hdr = font(True, 28)
    f_pos_count = font(False, 18)
    f_name = font(True, 22)
    f_trank = font(True, 16)
    f_label = font(True, 20)
    f_data = font(False, 20)
    f_sup = font(True, 13)
    f_foot = font(False, 18)

    ROW_H = 44
    POS_HDR_H = 50
    HEADER_H = 110

    # 估算总高度
    total_h = HEADER_H
    for pos_str, info in positions.items():
        total_h += POS_HDR_H
        total_h += len(info['heroes']) * ROW_H
        total_h += 16  # section 间距
    total_h += 80  # footer

    canvas_h = max(int(total_h * 1.2), 8000)
    img = Image.new('RGB', (W, canvas_h), BG)
    d = ImageDraw.Draw(img)

    y = PAD_Y

    # 标题
    d.text((PAD_X, y), '王者荣耀 · 对位克制速查 (顶端排位)', font=f_title, fill=TITLE_COLOR)
    y += 44

    # 副标题
    sub = f'数据来自王者营地国服顶端段位真实对局统计 · 更新 {update_time}'
    d.text((PAD_X, y), sub, font=f_sub, fill=SUB)
    y += 26

    # 说明 + 位置图例 (一行)
    note = '角标 = 克制率%   颜色 = 对方位置 (相同颜色 = 同位置对手)'
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

    # 各位置 section
    for pos in POS_ORDER:
        pos_str = str(pos)
        if pos_str not in positions:
            continue
        info = positions[pos_str]
        pos_name, pos_color = POS_COLOR[pos]
        heroes = info['heroes']

        # 位置头部 (大色条)
        d.rectangle([PAD_X, y, W - PAD_X, y + POS_HDR_H], fill=pos_color)
        d.text((PAD_X + 14, y + 10), pos_name, font=f_pos_hdr, fill=(255, 255, 255))
        cnt_text = f'共 {len(heroes)} 英雄 · 按胜率排名'
        d.text((PAD_X + 200, y + 18), cnt_text, font=f_pos_count, fill=(255, 255, 255, 200))
        y += POS_HDR_H + 4

        # 每英雄一行
        for hero in heroes:
            name = hero['name']
            t_rank = hero.get('tRank', '')
            cdata = counters.get(name, {})
            cs = cdata.get('counter', [])

            # 英雄名色块 (用主位置色)
            bbox = d.textbbox((0, 0), name, font=f_name)
            nw = bbox[2] - bbox[0]
            chip_w = nw + 16
            chip_h = 30
            cy = y + (ROW_H - chip_h) // 2
            d.rectangle([PAD_X, cy, PAD_X + chip_w, cy + chip_h], fill=pos_color)
            d.text((PAD_X + 8, cy + 3), name, font=f_name, fill=(255, 255, 255))

            # T 级标签
            tx = PAD_X + chip_w + 6
            if t_rank:
                t_color = TRANK_COLOR.get(t_rank, (130, 130, 130))
                d.text((tx, cy + 7), t_rank, font=f_trank, fill=t_color)
                tx += 30

            # 胜率
            wr = hero.get('winRate', 0)
            if wr:
                d.text((tx, cy + 8), f'{wr}%', font=f_pos_count, fill=SUB)
                tx += 56

            # "克"标签
            data_x = tx + 4
            data_y = y + (ROW_H - 24) // 2
            d.text((data_x, data_y), '克', font=f_label, fill=GREEN)
            cx = data_x + 26

            # 克制对象 (按对方位置上色)
            for i, item in enumerate(cs[:6]):  # 最多 6 个
                target_name, rate = item if isinstance(item, list) else (item, 0)
                target_pos = get_target_position(target_name, data)
                target_color = POS_COLOR.get(target_pos, (100, 100, 100))[1]

                if i > 0:
                    cx += 6  # 间距

                # 目标英雄名 (用对方位置色)
                d.text((cx, data_y), target_name, font=f_data, fill=target_color)
                tw = d.textbbox((0, 0), target_name, font=f_data)[2]
                cx += tw

                # 角标 (克制率)
                if rate:
                    sup = str(rate)
                    d.text((cx + 1, data_y - 6), sup, font=f_sup, fill=SUB)
                    cx += d.textbbox((0, 0), sup, font=f_sup)[2] + 3

            # 行分隔线
            d.line([PAD_X, y + ROW_H - 1, W - PAD_X, y + ROW_H - 1], fill=LINE_COLOR, width=1)
            y += ROW_H

        y += 16  # section 间距

    # footer
    y += 8
    d.text((PAD_X, y), '克 = 你强 (你打他容易)  |  克制率% = 对该英雄的胜率优势', font=f_foot, fill=SUB)
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
