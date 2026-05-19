#!/usr/bin/env python3
"""
渲染手机版克制速查 PNG.
- 输入: data/heroes.json (官方英雄列表), data/counters.json (克制关系)
- 输出: output/cheatsheet_mobile.png (竖版, 适配手机屏幕)

设计:
- 宽度 750 px (iPhone 标准 @2x logical 375 -> 物理 750)
- 单列垂直布局, 拼音首字母分组
- 每行: 英雄名 (色块) + 定位 + "克"列表 + "怕"列表
- 字号针对手机阅读放大
"""
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypinyin import lazy_pinyin

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)

# ---------- 字体 ----------
FONT_REG = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
FONT_BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
# 兜底字体
FONT_FALLBACKS = [
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/System/Library/Fonts/PingFang.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    '/usr/share/fonts/truetype/arphic/uming.ttc',
]


def pick_font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    candidates = [FONT_BOLD, FONT_REG] if bold else [FONT_REG]
    candidates += FONT_FALLBACKS
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------- 配色 ----------
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

BG = (250, 250, 250)
FG = (34, 34, 34)
SUB = (110, 110, 110)
GRP = (192, 57, 43)
LINE = (220, 220, 220)
GREEN = (39, 174, 96)
RED = (192, 57, 43)
WARN_BG = (255, 248, 225)
WARN_BD = (243, 156, 18)


# ---------- 尺寸 ----------
W = 750
PAD_X = 24
PAD_Y = 28

H_TITLE = 46        # 大标题字号
H_SUB = 24          # 副标题
H_GROUP = 40        # 分组标题字号
H_NAME = 30         # 英雄名字号
H_TAG = 22          # 定位标签字号
H_LINE = 26         # "克"/"怕" 行字号
H_FOOT = 20         # 页脚字号

LINE_GAP = 10       # 行间距
HERO_GAP = 18       # 每个英雄块之间间距
GROUP_GAP = 26      # 分组之间间距


def load_data():
    with open(DATA / 'heroes.json', 'r', encoding='utf-8') as f:
        heroes = json.load(f)
    with open(DATA / 'counters.json', 'r', encoding='utf-8') as f:
        counters = json.load(f)

    # 合并多形态 (元流之子)
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

    # 按字母分组
    from collections import defaultdict
    groups = defaultdict(list)
    for h in uniq:
        groups[h['initial']].append(h)

    return uniq, dict(sorted(groups.items())), counters


def measure_height(uniq, groups, counters):
    """先量高度, 一次性创建画布."""
    f_title = pick_font(True, H_TITLE)
    f_sub = pick_font(False, H_SUB)
    f_grp = pick_font(True, H_GROUP)
    f_name = pick_font(True, H_NAME)
    f_tag = pick_font(False, H_TAG)
    f_line = pick_font(False, H_LINE)
    f_foot = pick_font(False, H_FOOT)

    h = PAD_Y
    h += H_TITLE + 8           # 大标题
    h += H_SUB + 8             # 副标题
    h += H_SUB + 12            # 警告条 (单行)
    h += 24                    # 警告条 padding + 间距

    for letter, items in groups.items():
        h += H_GROUP + 12      # 分组标题 + 下划线
        for hero in items:
            data = counters.get(hero['cname'])
            need_lines = 1 + 1 + 1  # name行 + 克 + 怕
            # 长列表可能要折行, 简单按字符估算
            block_h = H_NAME + LINE_GAP + (H_LINE + LINE_GAP) * 2
            if data:
                # 大致估算"克"和"怕"行是否会折行
                for arr in (data.get('counter', []), data.get('countered_by', [])):
                    text = ' · '.join(arr)
                    if len(text) > 22:  # 阈值, 后面会精确换行
                        block_h += H_LINE + LINE_GAP
            h += block_h
            h += HERO_GAP
        h += GROUP_GAP

    h += 60  # footer
    return h, (f_title, f_sub, f_grp, f_name, f_tag, f_line, f_foot)


def draw_text_wrapped(draw, text, font, x, y, max_w, color):
    """按 max_w 自动换行, 返回最后 y."""
    words = list(text)  # 按字符
    line = ''
    for ch in words:
        test = line + ch
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_w and line:
            draw.text((x, y), line, font=font, fill=color)
            y += font.size + 2
            line = ch
        else:
            line = test
    if line:
        draw.text((x, y), line, font=font, fill=color)
        y += font.size + 2
    return y


def render():
    uniq, groups, counters = load_data()

    # 量高度
    total_h, fonts = measure_height(uniq, groups, counters)
    f_title, f_sub, f_grp, f_name, f_tag, f_line, f_foot = fonts

    # 高度估算可能偏小, 给足缓冲再 crop. measure 误差主要来自换行.
    canvas_h = max(int(total_h * 1.5), 25000)
    img = Image.new('RGB', (W, canvas_h), BG)
    d = ImageDraw.Draw(img)

    y = PAD_Y

    # 标题
    d.text((PAD_X, y), '王者荣耀 · 全英雄克制速查', font=f_title, fill=GRP)
    y += H_TITLE + 6

    # 副标题
    sub = f'共 {len(uniq)} 英雄 · 拼音 A-Z 分组 · 生成 2026-05-20'
    d.text((PAD_X, y), sub, font=f_sub, fill=SUB)
    y += H_SUB + 14

    # 警告条 (高度根据 wrap 后的实际文本计算)
    warn_inner_w = W - PAD_X * 2 - 24
    msg = '英雄列表来自 pvp.qq.com 官方 (实时); 克制关系基于通用克制框架 + 历史版本认知, 仅供方向参考, 非王者营地实时数据.'
    # 先在透明画布预演高度
    tmp_img = Image.new('RGB', (W, 1000))
    tmp_d = ImageDraw.Draw(tmp_img)
    end_y = draw_text_wrapped(tmp_d, msg, pick_font(False, H_SUB - 2), 0, 0, warn_inner_w, (0, 0, 0))
    msg_h = end_y
    warn_h = H_SUB + 8 + msg_h + 16  # 标题"数据说明:" + 间距 + 正文 + 底部 padding
    d.rectangle([PAD_X, y, W - PAD_X, y + warn_h], fill=WARN_BG, outline=WARN_BD, width=2)
    wt_x, wt_y = PAD_X + 12, y + 10
    d.text((wt_x, wt_y), '数据说明:', font=pick_font(True, H_SUB), fill=(120, 80, 0))
    wt_y += H_SUB + 6
    draw_text_wrapped(d, msg, pick_font(False, H_SUB - 2), wt_x, wt_y, warn_inner_w, (90, 70, 30))
    y += warn_h + 16

    # 图例 (定位色块)
    leg_x = PAD_X
    f_leg = pick_font(True, H_TAG)
    for tn, color in TYPE_COLOR.items():
        text = tn
        bbox = d.textbbox((0, 0), text, font=f_leg)
        tw = bbox[2] - bbox[0]
        chip_w = tw + 16
        d.rectangle([leg_x, y, leg_x + chip_w, y + H_TAG + 10], fill=color)
        d.text((leg_x + 8, y + 4), text, font=f_leg, fill=(255, 255, 255))
        leg_x += chip_w + 6
    y += H_TAG + 22

    # 各分组
    for letter, items in groups.items():
        # 分组标题
        d.text((PAD_X, y), letter, font=f_grp, fill=GRP)
        # 标题右侧装饰横线
        bbox = d.textbbox((0, 0), letter, font=f_grp)
        lw = bbox[2] - bbox[0]
        d.line([PAD_X + lw + 12, y + H_GROUP // 2, W - PAD_X, y + H_GROUP // 2], fill=GRP, width=2)
        y += H_GROUP + 8

        for hero in items:
            name = hero['cname']
            type_cn = hero['type_cn']
            color = TYPE_COLOR.get(type_cn, (80, 80, 80))
            data = counters.get(name, {'counter': ['—'], 'countered_by': ['—']})

            # 英雄名色块
            bbox = d.textbbox((0, 0), name, font=f_name)
            nw = bbox[2] - bbox[0]
            chip_h = H_NAME + 14
            d.rectangle([PAD_X, y, PAD_X + nw + 24, y + chip_h], fill=color)
            d.text((PAD_X + 12, y + 6), name, font=f_name, fill=(255, 255, 255))

            # 定位标签 (色块右侧)
            tag_x = PAD_X + nw + 36
            d.text((tag_x, y + 14), type_cn, font=f_tag, fill=color)

            y += chip_h + LINE_GAP + 2

            # 克
            label_w = 56
            d.text((PAD_X, y), '克', font=pick_font(True, H_LINE), fill=GREEN)
            text = ' · '.join(data.get('counter', []))
            ny = draw_text_wrapped(d, text, f_line, PAD_X + label_w, y, W - PAD_X * 2 - label_w, FG)
            y = max(y + H_LINE, ny) + LINE_GAP

            # 怕
            d.text((PAD_X, y), '怕', font=pick_font(True, H_LINE), fill=RED)
            text = ' · '.join(data.get('countered_by', []))
            ny = draw_text_wrapped(d, text, f_line, PAD_X + label_w, y, W - PAD_X * 2 - label_w, FG)
            y = max(y + H_LINE, ny) + LINE_GAP + 2

            # 分隔线
            d.line([PAD_X, y, W - PAD_X, y], fill=LINE, width=1)
            y += HERO_GAP

        y += GROUP_GAP - HERO_GAP

    # 页脚
    y += 8
    foot1 = '克 = 你强 (你打他容易)   |   怕 = 你弱 (他打你容易)'
    foot2 = 'github.com/yinrong/wzry-counter-cheatsheet'
    d.text((PAD_X, y), foot1, font=f_foot, fill=SUB)
    y += H_FOOT + 6
    d.text((PAD_X, y), foot2, font=f_foot, fill=SUB)
    y += H_FOOT + PAD_Y

    # 裁掉多余空白 (确保不超出画布)
    crop_h = min(y, img.height)
    img = img.crop((0, 0, W, crop_h))
    out = OUT / 'cheatsheet_mobile.png'
    img.save(out, optimize=True)
    print(f'wrote: {out}  size: {img.size}  bytes: {os.path.getsize(out)}')


if __name__ == '__main__':
    render()
