#!/usr/bin/env python3
"""
从王者营地国服API拉取真实对战统计克制数据.

数据源:
  https://kohcamp.qq.com/hero/getheroextrainfo
  国服王者营地 · 基于真实对局统计

输出:
  data/counters.json - 每英雄 3 克制 + 3 被克制, 带克制率(%)

角标含义:
  数字 = 克制率 (对该英雄的胜率优势百分比, 越高克制越明显)
"""
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'

HERO_LIST_URL = "https://pvp.qq.com/web201605/js/herolist.json"
API_URL = "https://kohcamp.qq.com/hero/getheroextrainfo"
TOKEN_URL = "https://api.t1qq.com/api/tool/wzrr/wztoken"

HEADERS = {
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
}


def get_token() -> str:
    req = urllib.request.Request(TOKEN_URL, headers={"User-Agent": "wzry-cheatsheet/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return data.get('token', '')


def fetch_hero_counter(hero_id: int, token: str) -> dict:
    headers = {**HEADERS, "token": token}
    body = json.dumps({"heroId": hero_id}).encode('utf-8')
    req = urllib.request.Request(API_URL, data=body, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))


def main():
    print('fetching token ...')
    token = get_token()
    print(f'token: {token}')

    print('fetching hero list ...')
    with urllib.request.urlopen(HERO_LIST_URL, timeout=10) as resp:
        heroes = json.loads(resp.read().decode('utf-8'))
    print(f'heroes: {len(heroes)}')

    results = {}
    errors = []
    for i, h in enumerate(heroes):
        hero_id = h['ename']
        hero_name = h['cname']
        try:
            resp = fetch_hero_counter(hero_id, token)
            if resp.get('returnCode') == 0:
                info = resp['data']
                kz_list = info.get('kzInfo', {}).get('list', [])
                bkz_list = info.get('bkzInfo', {}).get('list', [])
                results[hero_name] = {
                    'counter': [[x['szTitle'], round(x['kzParam'] * 100, 1)] for x in kz_list],
                    'countered_by': [[x['szTitle'], round(x['bkzParam'] * 100, 1)] for x in bkz_list],
                    'update_time': info.get('kzInfo', {}).get('updateTime', ''),
                }
            else:
                errors.append((hero_name, resp.get('returnMsg', '')))
        except Exception as e:
            errors.append((hero_name, str(e)))

        if (i + 1) % 20 == 0:
            print(f'  progress: {i+1}/{len(heroes)}')
        time.sleep(0.1)

    print(f'\nsuccess: {len(results)}, errors: {len(errors)}')
    if errors:
        print(f'errors: {errors[:5]}')

    out = DATA / 'counters.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'wrote: {out}')


if __name__ == '__main__':
    main()
