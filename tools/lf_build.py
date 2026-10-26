#!/usr/bin/env python3
"""탑승률 엑셀(연도별) → data/loadfactor.json (노선별·월별 합계만 저장, 원본 행은 저장하지 않음).
  python tools/lf_build.py "24년 탑승률.xlsx" "25년 탑승률.xlsx" "26년 탑승률.xlsx"
  python tools/lf_build.py --merge "10월 탑승률.xlsx"   # 새로 받은 달만 기존 json에 덮어써 합침(다 안 들어온 끝 날짜는 자동 제외, 월 일부면 잠정)
엑셀 열: 년, 월, 노선, Bound, 국적사/외항사, 항공사코드, 운항편수, 공급석, 수송석, L/F ...
노선은 양방향(Inbound+Outbound)·전 항공사를 합산한다. 'na'는 그 달 운항한 항공사 수, 'so'/'po'는 Outbound(한국 출발편) 공급석·수송석(Inbound = 전체 − Outbound)."""
import sys, re, json, pathlib
import pandas as pd
ROOT = pathlib.Path(__file__).resolve().parent.parent
KR = {'ICN':'인천','GMP':'김포','PUS':'부산','CJU':'제주','CJJ':'청주','TAE':'대구','KWJ':'광주','RSU':'여수','USN':'울산','HIN':'사천','KUV':'군산','KPO':'포항','WJU':'원주','YNY':'양양','MWX':'무안'}
def P(c, city): return (c, city)
F = {}
for code, city in {'AKJ':'아사히카와','AOJ':'아오모리','CTS':'삿포로','FUK':'후쿠오카','HIJ':'히로시마','HKD':'하코다테','HND':'도쿄(하네다)','IBR':'이바라키','IZO':'이즈모','KIJ':'니가타','KIX':'오사카','KKJ':'기타큐슈','KMI':'미야자키','KMJ':'구마모토','KOJ':'가고시마','MYJ':'마쓰야마','NGO':'나고야','NGS':'나가사키','NRT':'도쿄(나리타)','OIT':'오이타','OKA':'오키나와','OKJ':'오카야마','SDJ':'센다이','SHM':'난키시라하마','TAK':'다카마쓰','TOY':'도야마','UKB':'고베','YGJ':'요나고','HSG':'사가','KMQ':'고마쓰','FSZ':'시즈오카','OBO':'오비히로','SHI':'시모지시마','ISG':'이시가키','HNA':'하나마키','TKS':'도쿠시마','UBJ':'우베','MMJ':'마쓰모토','AXT':'아키타','GAJ':'야마가타','HAC':'하치조지마'}.items(): F[code] = P('일본', city)
for code, city in {'CAN':'광저우','CGO':'정저우','CGQ':'창춘','CKG':'충칭','CSX':'창사','DLC':'다롄','DYG':'장자제','FOC':'푸저우','HAK':'하이커우','HET':'후허하오터','HFE':'허페이','HGH':'항저우','HRB':'하얼빈','JMU':'자무쓰','KMG':'쿤밍','LHW':'란저우','LYI':'린이','NGB':'닝보','NKG':'난징','NTG':'난퉁','PEK':'베이징','PKX':'베이징(다싱)','PVG':'상하이(푸둥)','SHA':'상하이(훙차오)','SHE':'선양','SJW':'스자좡','SYX':'싼야','SYTX':'싼야','SZX':'선전','TAO':'칭다오','TFU':'청두','TNA':'지난','TSN':'톈진','TXN':'황산','TYN':'타이위안','WEH':'웨이하이','WNZ':'원저우','WUH':'우한','WUX':'우시','XIY':'시안','XMN':'샤먼','YIH':'이창','YNJ':'옌지','YNT':'옌타이','YNZ':'옌청','YTY':'양저우','DSN':'어얼두어쓰','DAT':'다퉁','KWL':'구이린','BAR':'충하이','BTH':'바오터우','HLD':'하이라얼','LXA':'라싸'}.items(): F[code] = P('중국', city)
F['BTH'] = P('인도네시아','바탐')  # BTH=바탐(인도네시아). 바오터우는 BAV
F['BAV'] = P('중국','바오터우')
F['HKG'] = P('홍콩','홍콩'); F['MFM'] = P('마카오','마카오')
for code, city in {'TPE':'타이베이','TSA':'타이베이(쑹산)','KHH':'가오슝','RMQ':'타이중','HUN':'화롄','TNN':'타이난'}.items(): F[code] = P('대만', city)
for code, city in {'BKK':'방콕','DMK':'방콕(돈므앙)','CNX':'치앙마이','HKT':'푸껫','CEI':'치앙라이','KBV':'크라비','USM':'코사무이'}.items(): F[code] = P('태국', city)
for code, city in {'HAN':'하노이','SGN':'호치민','DAD':'다낭','CXR':'나트랑','PQC':'푸꾸옥','HPH':'하이퐁','DLI':'달랏','VII':'빈','HUI':'후에','VCA':'껀터','VDO':'반돈'}.items(): F[code] = P('베트남', city)
F['SIN'] = P('싱가포르','싱가포르')
for code, city in {'CGK':'자카르타','DPS':'발리','BTH':'바탐','MDC':'마나도','SUB':'수라바야'}.items(): F[code] = P('인도네시아', city)
for code, city in {'MNL':'마닐라','CEB':'세부','TAG':'보홀','CRK':'클라크','KLO':'칼리보','MPH':'보라카이','PPS':'푸에르토프린세사','ILO':'일로일로'}.items(): F[code] = P('필리핀', city)
for code, city in {'SYD':'시드니','MEL':'멜버른','BNE':'브리즈번'}.items(): F[code] = P('호주', city)
for code, city in {'AKL':'오클랜드'}.items(): F[code] = P('뉴질랜드', city)
for code, city in {'LAX':'로스앤젤레스','SFO':'샌프란시스코','SEA':'시애틀','JFK':'뉴욕','EWR':'뉴욕(뉴어크)','ATL':'애틀랜타','BOS':'보스턴','DFW':'댈러스','IAD':'워싱턴','LAS':'라스베이거스','MSP':'미니애폴리스','ORD':'시카고','SLC':'솔트레이크시티','HNL':'호놀룰루','GUM':'괌','SPN':'사이판','DTW':'디트로이트','PDX':'포틀랜드','ANC':'앵커리지'}.items(): F[code] = P('미국', city)
for code, city in {'YVR':'밴쿠버','YYZ':'토론토'}.items(): F[code] = P('캐나다', city)
F.update({'BCN':P('스페인','바르셀로나'),'MAD':P('스페인','마드리드'),'FCO':P('이탈리아','로마'),'MXP':P('이탈리아','밀라노'),'CDG':P('프랑스','파리')})
for code, city in {'AMS':'암스테르담','ATH':'아테네','BUD':'부다페스트','FRA':'프랑크푸르트','LHR':'런던','LIS':'리스본','MUC':'뮌헨','OSL':'오슬로','PRG':'프라하','VIE':'빈','ZAG':'자그레브','ZRH':'취리히','IST':'이스탄불','CPH':'코펜하겐','HEL':'헬싱키','WAW':'바르샤바'}.items(): F[code] = P('유럽', city)
for code, city, c in [('BKI','코타키나발루','말레이시아'),('KUL','쿠알라룸푸르','말레이시아'),('PNH','프놈펜','캄보디아'),('KTI','프놈펜(테쵸)','캄보디아'),('SAI','씨엠립','캄보디아'),('VTE','비엔티안','라오스'),('RGN','양곤','미얀마'),('UBN','울란바토르','몽골'),('KTM','카트만두','네팔'),('DEL','델리','인도'),('DXB','두바이','UAE'),('CAI','카이로','이집트'),('TAS','타슈켄트','우즈베키스탄'),('ALA','알마티','카자흐스탄'),('NQZ','아스타나','카자흐스탄'),('BSZ','비슈케크','키르기스스탄'),('ULN','울란바토르','몽골'),('MLE','말레','몰디브'),('BWN','반다르스리브가완','브루나이')]: F[code] = P(c, city)
KRSET = set(KR)

def norm(route):
    r = re.sub(r'\s*V[.,]V\s*$', '', str(route).strip()); r = re.sub(r'V\.V$', '', r).strip()
    return r
def trim_partial_days(df):
    """월 끝쪽에서 행 수가 평소(앞 7일 중앙값)의 70% 미만인 날은 아직 다 안 들어온 날로 보고 뺀다."""
    if '일' not in df.columns: return df, None
    keep = df.copy(); keep['일'] = keep['일'].astype(int); cnt = keep.groupby('일').size(); last = int(cnt.index.max())
    while last > 8 and cnt[last] < 0.7 * cnt[[d for d in cnt.index if d < last][-7:]].median(): last -= 1
    return keep[keep['일'] <= last], last
def merge_out(old, new):
    """기존 data/loadfactor.json(old)에 새 엑셀로 만든 월(new)을 덮어써 합친다. 새 엑셀에 없는 노선의 그 달은 0."""
    months = sorted(set(old['months']) | set(new['months'])); mi = {m: i for i, m in enumerate(months)}
    rows = {}
    for src in (old, new):
        for x in src['routes']:
            e = rows.setdefault(x['r'], {'r': x['r'], 'c': x['c'], 'city': x['city'], **{k: [0]*len(months) for k in ('fl','se','px','na','so','po')}})
            for k in ('fl','se','px','na','so','po'):
                for j, m in enumerate(src['months']):
                    if src is new or m not in new['months']: e[k][mi[m]] = x[k][j]
            if src is new: e['c'], e['city'] = x['c'], x['city']
    routes = sorted(rows.values(), key=lambda x: -sum(x['px']))
    return {'months': months, 'partial': new['partial'], 'routes': routes}
def main(paths, merge=False):
    df = pd.concat([pd.read_excel(p) for p in paths], ignore_index=True)
    last_day = None
    if merge: df, last_day = trim_partial_days(df)
    df['월'] = df['월'].astype(int); df['ym'] = df['년'].astype(int).astype(str) + '-' + df['월'].astype(str).str.zfill(2)
    df['r'] = df['노선'].map(norm)
    months = sorted(df['ym'].unique()); mi = {m: i for i, m in enumerate(months)}
    routes, unmapped = [], {}
    for r, g in df.groupby('r'):
        a, b = (r.split('-') + [''])[:2]
        if a in KRSET and b in KRSET: c, city, dom = '한국', f'{KR[a]}-{KR[b]}', True
        else:
            f = a if b in KRSET else b if a in KRSET else None
            if f is None or f not in F: unmapped[r] = int(g['수송석'].sum()); c, city = '기타', r
            else: c, city = F[f]
            dom = False
        n = len(months); fl = [0]*n; se = [0]*n; px = [0]*n; na = [0]*n; so = [0]*n; po = [0]*n
        for ym, h in g.groupby('ym'):
            i = mi[ym]; fl[i] = int(h['운항편수'].sum()); se[i] = int(h['공급석'].sum()); px[i] = int(h['수송석'].sum()); na[i] = int(h['항공사코드'].nunique()); o = h[h['Bound'] == 'Outbound']; so[i] = int(o['공급석'].sum()); po[i] = int(o['수송석'].sum())
        routes.append({'r': r, 'c': c, 'city': city, 'fl': fl, 'se': se, 'px': px, 'na': na, 'so': so, 'po': po})
    routes.sort(key=lambda x: -sum(x['px']))
    # 마지막 달이 월 일부만 들어온 경우(공급석이 직전 3개월 평균의 60% 미만) 잠정 표시
    tot = [sum(x['se'][i] for x in routes) for i in range(len(months))]
    partial = [months[-1]] if len(months) > 3 and tot[-1] < 0.6 * sum(tot[-4:-1]) / 3 else []
    out = {'months': months, 'partial': partial, 'routes': routes}
    if merge:
        import calendar
        y, m = (int(v) for v in months[-1].split('-')); partial = [months[-1]] if last_day and last_day < calendar.monthrange(y, m)[1] else []
        out = merge_out(json.loads((ROOT / 'data/loadfactor.json').read_text(encoding='utf-8')), {'months': months, 'partial': partial, 'routes': routes}); months = out['months']; partial = out['partial']; routes = out['routes']
    (ROOT / 'data/loadfactor.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'노선 {len(routes)}개 / 월 {months[0]}~{months[-1]} / 잠정 {partial} / 미분류 {len(unmapped)}개', unmapped)
if __name__ == '__main__':
    a = sys.argv[1:]; mg = '--merge' in a
    main([x for x in a if x != '--merge'], mg)
