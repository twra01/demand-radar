#!/usr/bin/env python3
"""취항지 수요 레이더 갱신 도구.
  python3 tools/radar.py check   # 검증 + 별점 재계산 결과 요약(파일 변경 없음)
  python3 tools/radar.py build   # data/*.json을 재계산해 index.html 갱신(DATA, CAL 교체)
행사는 data/events.json 의 events 배열에 추가하고, 휴일·시즌은 data/calendar.json 에 추가한 뒤 build 한다."""
import re, json, math, sys, datetime as dt, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
FREE = ['축제','눈축제','불꽃','카니발','페스티벌']          # 콘서트 외 축제류 규모 ×0.7
VENUES = [  # (정규식, 표기명, 수용인원 추정)
(r'도쿄 ?돔','도쿄돔',55000),(r'교세라','교세라돔 오사카',55000),(r'반테린','반테린돔 나고야',49000),(r'미즈호|페이페이|PayPay','미즈호 PayPay돔 후쿠오카',50000),
(r'프리미스트|프레미스트|삿포로돔','삿포로돔',54000),(r'라라 ?아레나','라라 아레나 도쿄베이',10000),(r'마린메세','마린메세 후쿠오카 A홀',15000),(r'구마모토성홀','구마모토성홀',2300),(r'그랑메세','그랑메세 구마모토',8000),
(r'KSPO|코스포','KSPO돔',15000),(r'고척','고척스카이돔',20000),(r'고양종합','고양종합운동장 주경기장',41000),(r'킨텍스 ?제1','킨텍스 제1전시장',8000),(r'킨텍스 ?(제2|9A)','킨텍스 제2전시장',10000),(r'^킨텍스$','킨텍스',10000),(r'인스파이어','인스파이어 아레나',15000),
(r'카이탁','카이탁 스타디움',50000),(r'아시아월드','아시아월드 아레나',14000),(r'타이베이 ?아레나','타이베이 아레나',15000),(r'타이베이돔','타이베이돔',40000),(r'가오슝 ?아레나','가오슝 아레나',15000),(r'가오슝 ?국가','가오슝 국가체육장',55000),
(r'갤럭시','갤럭시 아레나(마카오)',16000),(r'IMPACT','IMPACT 아레나(방콕)',11000),(r'라자망갈라','라자망갈라 스타디움',52000),(r'겔로라','겔로라 붕 카르노',77000),(r'자카르타 인터내셔널','자카르타 인터내셔널 스타디움',82000),
(r'내셔널 스타디움','내셔널 스타디움(싱가포르)',55000),(r'인도네?어|인도어','싱가포르 인도어 스타디움',12000),(r'미딘','미딘 국립경기장',40000),(r'베트남 전시','베트남 전시센터(하노이)',15000),(r'필리핀 스포츠','필리핀 스포츠 스타디움',55000),
(r'SMDC','SMDC 페스티벌 그라운드',30000),(r'마블','마블 스타디움(멜버른)',55000),(r'아코르','아코르 스타디움(시드니)',80000)]
CITYDEF = {'싱가포르':('내셔널 스타디움(싱가포르)',55000),'방콕':('라자망갈라 스타디움',52000),'자카르타':('겔로라 붕 카르노',77000),'홍콩':('카이탁 스타디움',50000),'타이베이':('타이베이돔',40000),
           '가오슝':('가오슝 국가체육장',55000),'시드니':('아코르 스타디움(시드니)',80000),'마닐라':('필리핀 스포츠 스타디움',55000),'도쿄':('도쿄돔',55000),'오사카':('교세라돔 오사카',55000)}
TOURS = [(r'BTS','BTS'),(r'빅뱅|BIGBANG','빅뱅'),(r'요아소비|YOASOBI','YOASOBI'),(r'엔하이픈|ENHYPEN','엔하이픈'),(r'스트레이 ?키즈','스트레이 키즈'),(r'TXT|TOMORROW X','TXT'),
 (r'브루노 마스','브루노 마스'),(r'이승철','이승철'),(r'BE:FIRST','BE:FIRST'),(r'Da-iCE','Da-iCE'),(r'르세라핌','르세라핌'),(r'베이비몬스터','베이비몬스터'),(r'NMIXX|엔믹스','NMIXX'),
 (r'QWER','QWER'),(r'ILLIT','ILLIT'),(r'EXO|엑소','엑소'),(r'슈퍼주니어|슈버주니어','슈퍼주니어'),(r'ITZY','ITZY'),(r'NCT','NCT'),(r'ATEEZ|에이티즈','에이티즈')]

def load():
    d = json.load(open(ROOT/'data/events.json',encoding='utf-8')); c = json.load(open(ROOT/'data/calendar.json',encoding='utf-8')); return d, c
def days(e): return (dt.date.fromisoformat(e['end'])-dt.date.fromisoformat(e['start'])).days+1
def route_map(d):
    r = {}
    for x in d['routes']: r.setdefault(x['dc'], [])
    for x in d['routes']:
        if x['o'] not in r[x['dc']]: r[x['dc']].append(x['o'])
    return r
def score(e, nroutes):
    sz = e.get('size'); sz = sz if isinstance(sz,(int,float)) and sz>0 else None
    d = days(e); sc = {}; got = mx = 0
    if sz:
        eff = sz if d<=7 else sz/d*3                       # 8일 이상은 하루 평균×3일
        p = 40*max(0,min(1,math.log10(max(eff,1)/1000)/3))
        if e['kind']!='콘서트' and any(k in e['name'] for k in FREE): p *= 0.7
        sc['size'] = round(p,1); got += p; mx += 40
    else: sc['size'] = None
    ip = {'높음':25,'중간':15,'낮음':5}.get(e.get('interest')); sc['interest'] = ip
    if ip is not None: got += ip; mx += 25
    fit = {'A':17+min(8,nroutes),'B':9,'C':0}[e['tier']]; sc['fit'] = fit; got += fit; mx += 25
    dp = 2.5 if d<=1 else 5 if d==2 else 7.5 if d==3 else 10; sc['dur'] = dp; got += dp; mx += 10
    pct = got/mx*100
    return max(0.5,min(5,math.floor(pct/20*2+0.5)/2)), sc, round(pct,1)
def finalize(d):
    rm = route_map(d); nid = max(e.get('id',0) for e in d['events'])+1; warn = []; today = dt.date.today().isoformat()
    for e in d['events']:
        if 'id' not in e: e['id'] = nid; nid += 1
        e.setdefault('area', e['city']); e.setdefault('lock', False); e.setdefault('foreign',''); e.setdefault('impact',''); e.setdefault('note',''); e.setdefault('conf','확인됨')
        if e['tier']=='A':
            if e['city'] not in rm and e['end']>=today: warn.append(f"{e['name']}: 취항지(A)인데 노선에 {e['city']} 없음")
            e['origins'] = rm.get(e['city'],[]); e['nroutes'] = len(e['origins'])
        else: e['origins'] = []; e['nroutes'] = 0
        if e['kind']=='콘서트':
            if not e.get('tour'):
                lab = next((l for rx,l in TOURS if re.search(rx,e['name'])),None)
                if lab: e['tour'] = lab
            if not e.get('cap'):
                v = e.get('venue') or ''; hit = next(((n,c) for rx,n,c in VENUES if re.search(rx,v)),None)
                if hit: e['venue'], e['cap'] = hit
                elif (v in ('','미정') or v==e['city'] or '미확인' in v) and e['city'] in CITYDEF and (e.get('interest')=='높음' or (e.get('size') or 0)>=20000):
                    e['venue'], e['cap'] = CITYDEF[e['city']]; e['venueEst'] = True
                elif e['end']>=today: warn.append(f"{e['name']}: 공연장 미확인(수용인원 비움)")
            if not e.get('size') and e.get('cap'): e['size'] = e['cap']*days(e); e['est'] = True
        e['stars'], e['score'], e['pct'] = score(e, e['nroutes'])
        if e['start']>e['end']: warn.append(f"{e['name']}: 시작일이 종료일보다 늦음")
        if e.get('conf')=='확인 필요' and not e.get('source'): warn.append(f"{e['name']}: 출처 없음")
    keys = {}
    for e in d['events']:
        k = (e['name'], e['start'])
        if k in keys and e['end']>=today: warn.append(f"중복: {e['name']} {e['start']}")
        keys[k] = 1
    return warn
def build():
    d, c = load(); warn = finalize(d)
    d['updated'] = dt.date.today().isoformat()
    json.dump(d, open(ROOT/'data/events.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
    p = ROOT/'index.html'; s = p.read_text(encoding='utf-8')
    m = re.search(r'const DATA = (\{.*?\});\n', s, re.S); s = s[:m.start(1)]+json.dumps(d,ensure_ascii=False)+s[m.end(1):]
    m = re.search(r'const CAL = (\[.*?\]);\n', s, re.S); s = s[:m.start(1)]+json.dumps(c,ensure_ascii=False)+s[m.end(1):]
    lf = ROOT/'data/loadfactor.json'                       # 탑승률 실적(tools/lf_build.py가 만든 노선·월별 합계)
    if lf.exists():
        m = re.search(r'const LF = (\{.*?\});\n', s, re.S); s = s[:m.start(1)]+lf.read_text(encoding='utf-8').strip()+s[m.end(1):]
    fx = ROOT/'data/fx.json'                               # 환율 월평균(tools/fx_build.py, 참고용)
    if fx.exists():
        m = re.search(r'const FX = (\{.*?\});\n', s, re.S)
        if m: s = s[:m.start(1)]+fx.read_text(encoding='utf-8').strip()+s[m.end(1):]
    lfd = ROOT/'data/loadfactor_daily.json'                 # 국내선 일자별 탑승률(tools/lf_daily_build.py)
    if lfd.exists():
        m = re.search(r'const LFD = (\{.*?\});\n', s, re.S)
        if m: s = s[:m.start(1)]+lfd.read_text(encoding='utf-8').strip()+s[m.end(1):]
    p.write_text(s,encoding='utf-8'); return d, warn
if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv)>1 else 'check'
    if cmd=='build': d, w = build()
    else: d, c = load(); w = finalize(d)
    today = dt.date.today().isoformat()
    up = [e for e in d['events'] if e['end']>=today]
    print(f"전체 {len(d['events'])}건 / 오늘 이후 {len(up)}건 / 별 4개 이상 {sum(e['stars']>=4 for e in up)}건 / 확인 필요 {sum(e['conf']=='확인 필요' for e in up)}건")
    for x in w: print('경고:', x)
