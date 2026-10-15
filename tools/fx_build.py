"""환율(원화 기준 월평균) → data/fx.json. 출처: Frankfurter(유럽중앙은행 참고환율). 참고용.
사용: python tools/fx_build.py  →  python tools/radar.py build
ECB 고시 통화만 가능(대만·베트남 등은 아래 보조 출처로 보충)."""
import json, sys, datetime as dt, urllib.request, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
CUR = {  # 코드: (이름, 표기 단위, 국가들)
    'JPY': ('엔', 100, ['일본']), 'USD': ('달러', 1, ['미국']), 'CNY': ('위안', 1, ['중국']),
    'HKD': ('홍콩달러', 1, ['홍콩']), 'THB': ('바트', 1, ['태국']), 'SGD': ('싱가포르달러', 1, ['싱가포르']),
    'IDR': ('루피아', 10000, ['인도네시아']), 'AUD': ('호주달러', 1, ['호주']), 'CAD': ('캐나다달러', 1, ['캐나다']),
    'EUR': ('유로', 1, ['프랑스', '스페인', '이탈리아', '유럽']),
    'INR': ('루피', 100, ['인도']), 'MYR': ('링깃', 1, ['말레이시아']), 'NZD': ('뉴질랜드달러', 1, ['뉴질랜드']),
}
start = '2024-01-01'; end = dt.date.today().isoformat()
url = f"https://api.frankfurter.dev/v1/{start}..{end}?base=KRW&symbols={','.join(CUR)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 demand-radar", "Accept": "application/json"})
d = json.load(urllib.request.urlopen(req, timeout=60))
acc = {c: {} for c in CUR}
for day, rs in d['rates'].items():
    ym = day[:7]
    for c, (_, unit, _) in CUR.items():
        if c in rs and rs[c]: acc[c].setdefault(ym, []).append(unit / rs[c])
out = {'asof': max(d['rates']), 'src': '유럽중앙은행(ECB) 참고환율, 월평균', 'cur': {}}
last = max(d['rates'])[:7]
for c, (name, unit, ctry) in CUR.items():
    out['cur'][c] = {'name': name, 'unit': unit, 'c': ctry, 'm': {k: round(sum(v) / len(v), 2) for k, v in sorted(acc[c].items())}}

# 보조 출처: ECB가 고시하지 않는 통화(오픈 시장환율 API, 2024-03부터). 월 3회(5·15·25일) 표본 평균
EXTRA = {  # 코드: (이름, 표기 단위, 국가들)
    'TWD': ('대만달러', 1, ['대만']), 'VND': ('동', 10000, ['베트남']), 'MOP': ('파타카', 1, ['마카오']),
    'AED': ('디르함', 1, ['UAE']), 'NPR': ('루피', 100, ['네팔']), 'LAK': ('킵', 10000, ['라오스']),
    'MNT': ('투그릭', 100, ['몽골']), 'MMK': ('짯', 100, ['미얀마']), 'UZS': ('숨', 1000, ['우즈베키스탄']),
    'EGP': ('파운드', 1, ['이집트']), 'KZT': ('텡게', 100, ['카자흐스탄']), 'KHR': ('리엘', 1000, ['캄보디아']),
    'KGS': ('솜', 1, ['키르기스스탄']),
}
def extra():
    acc = {c: {} for c in EXTRA}; today = dt.date.today(); y, m = 2024, 3
    while (y, m) <= (today.year, today.month):
        for day in (5, 15, 25):
            ds = dt.date(y, m, day)
            if ds > today: continue
            u = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{ds.isoformat()}/v1/currencies/krw.json"
            try: k = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 demand-radar"}), timeout=30))['krw']
            except Exception: continue
            for c, (_, unit, _) in EXTRA.items():
                v = k.get(c.lower())
                if v: acc[c].setdefault(f"{y}-{m:02d}", []).append(unit / v)
        m += 1
        if m > 12: y, m = y + 1, 1
    return acc
ex = extra()
for c, (name, unit, ctry) in EXTRA.items():
    if ex[c]: out['cur'][c] = {'name': name, 'unit': unit, 'c': ctry, 's': '시장환율', 'm': {k: round(sum(v) / len(v), 2) for k, v in sorted(ex[c].items())}}
out['partial'] = last   # 마지막 달은 월 일부만 반영(잠정)
(ROOT / 'data/fx.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print('fx', out['asof'], 'months', len(out['cur']['JPY']['m']), 'JPY last', out['cur']['JPY']['m'][last])
