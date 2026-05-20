#!/usr/bin/env python3
"""
从公开 API 拉取实时克制关系数据, 反向推导 + 同类补全到 >= 3+3.

数据源:
  https://qing762.is-a.dev/api/wangzhe
  (基于 pvp.qq.com 官方英雄详情页爬取, 实时更新)

策略:
  1. 官方每英雄给 2 个 suppressingHeroes + 2 个 suppressedHeroes
  2. 反向推导: 如果 A 克制 B, 则 B 被 A 克制 (即使 B 的 suppressedHeroes 里没列 A)
  3. 同类补全: 如果英雄仍不够 3 个, 用同定位英雄的高频克制对象补全

输出: data/counters.json (格式不变)
"""
import json
import urllib.request
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'

API_URL = 'https://qing762.is-a.dev/api/wangzhe'

TYPE_MAP = {1: '战士', 2: '法师', 3: '坦克', 4: '刺客', 5: '射手', 6: '辅助'}


def fetch():
    print(f'fetching {API_URL} ...')
    req = urllib.request.Request(API_URL, headers={'User-Agent': 'wzry-cheatsheet/1.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read().decode('utf-8'))
    return raw


def build_counter_graph(main, heroes_json):
    """构建完整克制关系图."""
    counters = defaultdict(set)       # A -> {B, C} means A counters them
    countered_by = defaultdict(set)   # A -> {X, Y} means they counter A

    for name, hero in main.items():
        for target in hero.get('suppressingHeroes', {}).keys():
            counters[name].add(target)
            countered_by[target].add(name)
        for threat in hero.get('suppressedHeroes', {}).keys():
            countered_by[name].add(threat)
            counters[threat].add(name)

    return counters, countered_by


def get_hero_types(heroes_json):
    """返回 {英雄名: 定位} 和 {定位: [英雄名列表]}."""
    hero_type = {}
    type_heroes = defaultdict(list)
    for h in heroes_json:
        name = h['cname'].split('(')[0]
        t = TYPE_MAP.get(h.get('hero_type', 0), '?')
        hero_type[name] = t
        type_heroes[t].append(name)
    return hero_type, type_heroes


def fill_by_type(counters, countered_by, hero_type, type_heroes, min_count=3):
    """对于不够 min_count 的英雄, 用同定位的高频克制对象补全."""
    all_heroes = set(counters.keys()) | set(countered_by.keys())

    # 对 counters 不足 3 的补全
    for name in list(all_heroes):
        if len(counters[name]) >= min_count:
            continue
        t = hero_type.get(name, '?')
        # 同定位英雄克制的目标, 按频率排序
        freq = defaultdict(int)
        for peer in type_heroes.get(t, []):
            if peer == name:
                continue
            for target in counters[peer]:
                if target != name and target not in counters[name]:
                    freq[target] += 1
        # 按频率填充
        for target, _ in sorted(freq.items(), key=lambda x: -x[1]):
            if len(counters[name]) >= min_count:
                break
            counters[name].add(target)
            countered_by[target].add(name)

    # 对 countered_by 不足 3 的补全
    for name in list(all_heroes):
        if len(countered_by[name]) >= min_count:
            continue
        t = hero_type.get(name, '?')
        freq = defaultdict(int)
        for peer in type_heroes.get(t, []):
            if peer == name:
                continue
            for threat in countered_by[peer]:
                if threat != name and threat not in countered_by[name]:
                    freq[threat] += 1
        for threat, _ in sorted(freq.items(), key=lambda x: -x[1]):
            if len(countered_by[name]) >= min_count:
                break
            countered_by[name].add(threat)
            counters[threat].add(name)


def main():
    raw = fetch()
    api_main = raw['main']
    print(f'got {len(api_main)} heroes from API')

    with open(DATA / 'heroes.json', 'r', encoding='utf-8') as f:
        heroes_json = json.load(f)

    hero_type, type_heroes = get_hero_types(heroes_json)
    counters, countered_by = build_counter_graph(api_main, heroes_json)

    # 补全
    fill_by_type(counters, countered_by, hero_type, type_heroes, min_count=3)

    # 统计
    both3 = sum(1 for name in api_main if len(counters.get(name, set())) >= 3 and len(countered_by.get(name, set())) >= 3)
    print(f'两边都>=3 的英雄: {both3}/{len(api_main)}')

    # 输出
    result = {}
    for name in api_main:
        result[name] = {
            'counter': sorted(counters.get(name, set())),
            'countered_by': sorted(countered_by.get(name, set())),
        }

    out = DATA / 'counters.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'wrote: {out}')


if __name__ == '__main__':
    main()
