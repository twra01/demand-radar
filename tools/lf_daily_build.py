#!/usr/bin/env python3
"""국내선 일자별 탑승률 엑셀 → data/loadfactor_daily.json (공항별·일자별 합계만 저장, 원본 행·항공사별 행은 저장하지 않음).
  python tools/lf_daily_build.py "탑승률_일자별.xlsx"
엑셀 열: 년, 월, 일, 요일, 국내/국제, 노선_국가, Bound, Leg(출발-도착), 출발공항(국내), 국적사/외항사, FSC/LCC, 항공사코드, 운항편수, 공급석, 수송석, L/F ...
- 전 항공사·양방향을 합산. 출발=도착인 구간(PUS-PUS 등 무착륙 관광비행)과 국제선(노선_국가≠Republic of Korea)은 제외.
- all: 국내선 전체 일자별 공급석(se)·수송석(px)
- ap[공항]: 그 공항 도착편(as/ap)·출발편(ds/dp) 일자별 공급석·수송석 (CJU 제주, PUS 부산, TAE 대구, KWJ 광주, CJJ 청주, GMP 김포, ICN 인천)
- 시작일 start, 길이 n. 마지막 날이 평소보다 데이터가 적으면(부분 집계) 잘라 냄."""
import sys, json, pathlib
import pandas as pd
ROOT = pathlib.Path(__file__).resolve().parent.parent
AP = ['CJU', 'PUS', 'TAE', 'KWJ', 'CJJ', 'GMP', 'ICN']
src = sys.argv[1]
df = pd.read_excel(src)
df = df[df['노선_국가'] == 'Republic of Korea'].copy()
df['date'] = pd.to_datetime(dict(year=df['년'], month=df['월'].astype(int), day=df['일']))
df['o'] = df['Leg'].str.split('-').str[0]; df['d'] = df['Leg'].str.split('-').str[1]
df = df[df['o'] != df['d']]
start = df['date'].min().normalize(); end = df['date'].max().normalize()
cnt = df.groupby('date').size()
if cnt.iloc[-1] < cnt.iloc[-8:-1].mean() * 0.8: end = end - pd.Timedelta(days=1)   # 부분 집계 마지막 날 제외
idx = pd.date_range(start, end, freq='D'); n = len(idx)
df = df[df['date'] <= end]
def arr(sub, col):
    return [int(v) for v in sub.groupby('date')[col].sum().reindex(idx, fill_value=0).tolist()]
out = {'start': start.strftime('%Y-%m-%d'), 'n': n, 'asof': end.strftime('%Y-%m-%d'),
       'all': {'se': arr(df, '공급석'), 'px': arr(df, '수송석')}, 'ap': {}}
for a in AP:
    arrv = df[df['d'] == a]; dep = df[df['o'] == a]
    out['ap'][a] = {'as': arr(arrv, '공급석'), 'ap': arr(arrv, '수송석'), 'ds': arr(dep, '공급석'), 'dp': arr(dep, '수송석')}
p = ROOT / 'data/loadfactor_daily.json'
p.write_text(json.dumps(out, separators=(',', ':')), encoding='utf-8')
tot = sum(out['all']['px']) / sum(out['all']['se'])
print('daily', out['start'], '~', out['asof'], 'days', n, 'national LF', round(tot * 100, 1), 'size KB', p.stat().st_size // 1024)
