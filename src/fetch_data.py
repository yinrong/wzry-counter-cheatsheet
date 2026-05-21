#!/usr/bin/env python3
"""
从王者营地国服API拉取真实对战统计数据.

拉两份数据:
  1. 每英雄 3 个克制对象 (kzInfo) — getheroextrainfo
  2. 每位置的英雄列表 (按 T 级别排序) — getdetailranklistbyid

输出 data/counters.json:
  {
    "positions": {
      "1": {"name": "对抗路", "heroes": [{"name":..., "tRank":..., "heroId":...}, ...]},
      ...
    },
    "counters": {
      "英雄名": {
        "counter": [["对方", 克制率%], ...],
        "tRanks": {"1": "T0", ...}  # 该英雄在各位置的 T 级别
      }
    }
  }

位置编码:
  1=对抗路, 2=中路, 3=发育路, 4=游走, 5=打野
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
    """拉 5 个位置的英雄列表 (顶端段位)."""
    out = {}
    for pos in (1, 2, 3, 4, 5):
        resp = post(RANK_URL, {
            "rankId": 0, "position": pos, "segment": 4,
            "eId": None, "h5Get": 1
        }, token)
        if resp.get('returnCode') != 0:
            raise RuntimeError(f'position {pos} failed: {resp.get("returnMsg")}')
        lst = resp['data']['list']
        heroes = []
        for x in lst:
            heroes.append({
                'name': x['heroInfo']['heroName'],
                'heroId': x['heroId'],
                'tRank': x.get('tRank', ''),
                'winRate': round(x.get('winRate', 0) * 100, 1),
                'showRate': round(x.get('showRate', 0) * 100, 1),
                'banRate': round(x.get('banRate', 0) * 100, 1),
            })
        out[pos] = heroes
        print(f'  pos={pos} ({POSITION_NAMES[pos]}): {len(heroes)} heroes')
        time.sleep(0.1)
    return out


def fetch_counters(token: str, hero_list: list) -> dict:
    """每英雄拉 3 个克制对象."""
    out = {}
    for i, h in enumerate(hero_list):
        try:
            resp = post(COUNTER_URL, {"heroId": h['ename']}, token)
            if resp.get('returnCode') == 0:
                kz = resp['data'].get('kzInfo', {}).get('list', [])
                out[h['cname']] = [[x['szTitle'], round(x['kzParam'] * 100, 1)] for x in kz]
            else:
                out[h['cname']] = []
        except Exception as e:
            print(f'  ERR {h["cname"]}: {e}')
            out[h['cname']] = []

        if (i + 1) % 30 == 0:
            print(f'  counter progress: {i+1}/{len(hero_list)}')
        time.sleep(0.08)
    return out


def main():
    print('fetching token ...')
    token = get_token()
    print(f'token: {token}')

    print('fetching hero list ...')
    with urllib.request.urlopen(HERO_LIST_URL, timeout=10) as resp:
        heroes = json.loads(resp.read().decode('utf-8'))
    print(f'heroes: {len(heroes)}')

    print('\nfetching positions ...')
    positions = fetch_positions(token)

    print('\nfetching counters ...')
    counters = fetch_counters(token, heroes)
    success = sum(1 for v in counters.values() if v)
    print(f'  success: {success}/{len(heroes)}')

    # 构建每英雄的 tRank 映射 {hero_name: {pos: tRank}}
    hero_pos_rank = defaultdict(dict)
    for pos, lst in positions.items():
        for h in lst:
            hero_pos_rank[h['name']][pos] = h['tRank']

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
            'counter': counters.get(name, []),
            'tRanks': {str(p): r for p, r in hero_pos_rank.get(name, {}).items()},
        }

    out = DATA / 'counters.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'\nwrote: {out}')


if __name__ == '__main__':
    main()
