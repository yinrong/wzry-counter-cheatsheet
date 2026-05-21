#!/usr/bin/env python3
"""
从王者营地国服API拉取真实对战统计数据 + 三层数据补全.

数据源:
  - https://kohcamp.qq.com/hero/getheroextrainfo  (kzInfo + bkzInfo)
  - https://kohcamp.qq.com/gametoolbox/hero/getdetailranklistbyid  (按位置英雄列表)
  - https://api.t1qq.com/api/tool/wzrr/wztoken  (token)

三层数据 (置信度从高到低):
  tier=1 精准: 接口直给的 kzInfo (该英雄克制谁)
  tier=2 反向: 其他英雄的 bkzInfo 反推 (B 的 bkzInfo 里有 A → A 克制 B)
  tier=3 推断: 同位置高频克制对象补全

输出 data/counters.json:
  positions: {pos_id: {name, heroes:[{name,heroId,tRank,winRate,...}]}}
  counters: {hero_name: {counter:[[target,rate,tier],...], tRanks:{pos:tRank}}}
"""
import json
import time
import urllib.request
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'

HERO_LIST_URL = "https://pvp.qq.com/web201605/js/herolist.json"
COUNTER_URL = "https://kohcamp.qq.com/hero/getheroextrainfo"
RANK_URL = "https://kohcamp.qq.com/gametoolbox/hero/getdetailranklistbyid"
TOKEN_URL = "https://api.t1qq.com/api/tool/wzrr/wztoken"

POSITION_NAMES = {1: '对抗路', 2: '中路', 3: '发育路', 4: '游走', 5: '打野'}
TARGET_PER_HERO = 6  # 每英雄目标克制对象数

HEADERS_BASE = {
    "Content-Type": "application/json",
    "cchannelid": "2002",
    "cclientversioncode": "2037905606",
    "cclientversionname": "8.101.1017",
    "ccurrentgameid": "20001",
    "cgameid": "20001",
    "csystem": "android",
    "csystemversioncode": "32",
    "gameareaid": "1",
    "gameid": "20001",
    "gameopenid": "54533036A3D6E4241440CBCD66694578",
    "gameroleid": "2157931910",
    "gameserverid": "1312",
    "noencrypt": "1",
    "openid": "472AD0DD361C8EC026E52F445041F843",
    "userid": "2118558336",
    "kohDimGender": "1",
}


def get_token() -> str:
    req = urllib.request.Request(TOKEN_URL, headers={"User-Agent": "wzry-cheatsheet/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8')).get('token', '')


def post(url: str, body: dict, token: str) -> dict:
    headers = {**HEADERS_BASE, "token": token}
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode('utf-8'))


def fetch_positions(token: str) -> dict:
    out = {}
    for pos in (1, 2, 3, 4, 5):
        resp = post(RANK_URL, {
            "rankId": 0, "position": pos, "segment": 4,
            "eId": None, "h5Get": 1
        }, token)
        if resp.get('returnCode') != 0:
            raise RuntimeError(f'position {pos} failed: {resp.get("returnMsg")}')
        lst = resp['data']['list']
        out[pos] = [{
            'name': x['heroInfo']['heroName'],
            'heroId': x['heroId'],
            'tRank': x.get('tRank', ''),
            'winRate': round(x.get('winRate', 0) * 100, 1),
            'showRate': round(x.get('showRate', 0) * 100, 1),
            'banRate': round(x.get('banRate', 0) * 100, 1),
        } for x in lst]
        print(f'  pos={pos} ({POSITION_NAMES[pos]}): {len(out[pos])} heroes')
        time.sleep(0.1)
    return out


def fetch_raw_counters(token: str, hero_list: list) -> dict:
    """返回 raw API 数据, 含 kzInfo 和 bkzInfo."""
    out = {}
    for i, h in enumerate(hero_list):
        try:
            resp = post(COUNTER_URL, {"heroId": h['ename']}, token)
            if resp.get('returnCode') == 0:
                out[h['cname']] = resp['data']
            else:
                out[h['cname']] = {}
        except Exception as e:
            print(f'  ERR {h["cname"]}: {e}')
            out[h['cname']] = {}
        if (i + 1) % 30 == 0:
            print(f'  counter progress: {i+1}/{len(hero_list)}')
        time.sleep(0.08)
    return out


def hero_main_position(hero_name: str, hero_pos_rank: dict) -> int:
    """英雄主位置 (T 级最优)."""
    ranks = hero_pos_rank.get(hero_name, {})
    if not ranks:
        return None
    best = sorted(ranks.items(), key=lambda x: (
        ['T0', 'T1', 'T2', 'T3'].index(x[1]) if x[1] in ['T0', 'T1', 'T2', 'T3'] else 99,
        x[0],
    ))
    return best[0][0]


def expand_three_tiers(raw: dict, hero_pos_rank: dict, target_count: int = TARGET_PER_HERO):
    """三层数据扩展.
    返回 {hero: [(target, rate, tier), ...]}, 已按 tier→rate 排序.
    """
    # tier=1: 精准 (kzInfo)
    counters = defaultdict(dict)  # {hero: {target: (rate, tier)}}
    for hero, info in raw.items():
        for x in info.get('kzInfo', {}).get('list', []):
            target = x['szTitle']
            rate = round(x['kzParam'] * 100, 1)
            counters[hero][target] = (rate, 1)

    # tier=2: 反向 (B 的 bkzInfo 里有 A → A 克制 B)
    for hero, info in raw.items():
        for x in info.get('bkzInfo', {}).get('list', []):
            attacker = x['szTitle']
            victim = hero
            rate = round(x['bkzParam'] * 100, 1)
            if victim not in counters[attacker]:  # 不覆盖 tier=1
                counters[attacker][victim] = (rate, 2)

    # tier=3: 同位置推断 (用同主位置英雄的克制对象高频补全)
    pos_to_heroes = defaultdict(list)
    for hero in counters:
        p = hero_main_position(hero, hero_pos_rank)
        if p:
            pos_to_heroes[p].append(hero)

    for hero in list(counters.keys()):
        if len(counters[hero]) >= target_count:
            continue
        p = hero_main_position(hero, hero_pos_rank)
        if not p:
            continue
        # 同位置同伴
        peers = [h for h in pos_to_heroes[p] if h != hero]
        # 统计他们克制对象的频率 (只用 tier=1, tier=2 数据)
        freq = defaultdict(int)
        for peer in peers:
            for tgt in counters[peer]:
                if tgt != hero and tgt not in counters[hero]:
                    freq[tgt] += 1
        # 按频率排序
        for tgt, _ in sorted(freq.items(), key=lambda x: -x[1]):
            if len(counters[hero]) >= target_count:
                break
            counters[hero][tgt] = (0, 3)  # rate=0 表示推断 (无真实克制率)

    # 排序: tier 升序 (精准在前) + rate 降序
    out = {}
    for hero, items in counters.items():
        sorted_items = sorted(
            [(t, r, tier) for t, (r, tier) in items.items()],
            key=lambda x: (x[2], -x[1])
        )
        out[hero] = [[t, r, tier] for t, r, tier in sorted_items]
    return out


def main():
    print('fetching token ...')
    token = get_token()
    print(f'token: {token}')

    print('\nfetching hero list ...')
    with urllib.request.urlopen(HERO_LIST_URL, timeout=10) as resp:
        heroes = json.loads(resp.read().decode('utf-8'))
    print(f'heroes: {len(heroes)}')

    print('\nfetching positions ...')
    positions = fetch_positions(token)

    print('\nfetching raw counters (kz + bkz) ...')
    raw = fetch_raw_counters(token, heroes)
    success = sum(1 for v in raw.values() if v)
    print(f'  raw success: {success}/{len(heroes)}')

    # 每英雄的 tRank by 位置
    hero_pos_rank = defaultdict(dict)
    for pos, lst in positions.items():
        for h in lst:
            hero_pos_rank[h['name']][pos] = h['tRank']

    print('\nexpanding three tiers ...')
    expanded = expand_three_tiers(raw, hero_pos_rank, TARGET_PER_HERO)

    # 统计
    tier_counts = defaultdict(int)
    for items in expanded.values():
        for _, _, tier in items:
            tier_counts[tier] += 1
    sizes = [len(v) for v in expanded.values()]
    print(f'  total relations: {sum(tier_counts.values())} '
          f'(tier1={tier_counts[1]}, tier2={tier_counts[2]}, tier3={tier_counts[3]})')
    print(f'  per-hero: min={min(sizes)} max={max(sizes)} avg={sum(sizes)/len(sizes):.1f}')

    # 输出
    result = {
        'updateTime': time.strftime('%Y-%m-%d'),
        'positions': {},
        'counters': {},
    }
    for pos, lst in positions.items():
        result['positions'][str(pos)] = {
            'name': POSITION_NAMES[pos],
            'heroes': lst,
        }
    for h in heroes:
        name = h['cname']
        result['counters'][name] = {
            'counter': expanded.get(name, []),
            'tRanks': {str(p): r for p, r in hero_pos_rank.get(name, {}).items()},
        }

    out = DATA / 'counters.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'\nwrote: {out}')


if __name__ == '__main__':
    main()
