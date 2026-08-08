#!/usr/bin/env python3
"""pdufa.bio LIVE current-PDUFA tracker - logs day-by-day prices for every remaining-2026
PDUFA (twice daily: midday + close) and rebuilds a private dashboard. Original data, for investing."""
import urllib.request, json, time, datetime, os, re, sys
from concurrent.futures import ThreadPoolExecutor
BASE=os.path.dirname(os.path.abspath(__file__))
SLATE_JS=os.path.join(BASE,'..','pdufa_site_src','api','data.js')
LOG=os.path.join(BASE,'daily_log.csv'); BASE_J=os.path.join(BASE,'baselines.json')
SNAP=sys.argv[1] if len(sys.argv)>1 else 'close'   # 'midday' or 'close'
today=datetime.date.today()

def current_pdufas():
    s=open(SLATE_JS,encoding='utf-8').read()
    seg=s[s.find('"catalysts":'):s.find('const HIST')]
    outk=set(re.findall(r'"([A-Z0-9.\-]+)":\{o:', s[s.find('const OUT='):s.find('const REG=')]))
    ev={}
    skipped=[]
    for tk,d,drug,cap in re.findall(r'"ticker":"(.*?)".*?"date":"(.*?)".*?"drug":"(.*?)".*?"cap":"(.*?)"',seg):
        # slate sometimes carries quarter placeholders (e.g. "2026-Q4") for undated PDUFAs.
        # those have no T-120 anchor and no business-day countdown, so they are not trackable - skip.
        try:
            dt=datetime.date.fromisoformat(d)
        except ValueError:
            skipped.append("%s(%s)"%(tk,d)); continue
        if dt>=today and tk not in outk and tk not in ev:
            ev[tk]={'ticker':tk,'date':d,'drug':drug[:44],'cap':cap}
    if skipped: print("  skipped %d undated slate entries: %s"%(len(skipped),', '.join(skipped)))
    return ev

def yfetch(tk, rng, interval):
    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{tk.replace('.','-')}?range={rng}&interval={interval}"
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    d=json.load(urllib.request.urlopen(req,timeout=15)); return d['chart']['result'][0]

def latest(tk):
    try:
        r=yfetch(tk,'1d','1m'); cl=[c for c in r['indicators']['quote'][0]['close'] if c is not None]
        prev=r['meta'].get('chartPreviousClose') or r['meta'].get('previousClose')
        px=cl[-1] if cl else r['meta'].get('regularMarketPrice')
        chg=(px/prev-1)*100 if (px and prev) else None
        return round(px,4) if px else None, round(chg,2) if chg is not None else None
    except Exception: return None,None

def baseline(tk, ev_date):
    """price ~120 business days before PDUFA (T-120 anchor), cached."""
    ev=datetime.date.fromisoformat(ev_date)
    try:
        p1=int(time.mktime((ev-datetime.timedelta(days=215)).timetuple())); p2=int(time.mktime((ev-datetime.timedelta(days=150)).timetuple()))
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{tk.replace('.','-')}?period1={p1}&period2={p2}&interval=1d"
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}); d=json.load(urllib.request.urlopen(req,timeout=15))
        r=d['chart']['result'][0]; cl=[c for c in r['indicators']['quote'][0]['close'] if c is not None]
        return round(cl[0],4) if cl else None
    except Exception: return None

import numpy as np
def bdays(a,b): return int(np.busday_count(a.isoformat(), b.isoformat()))

ev=current_pdufas()
bl=json.load(open(BASE_J)) if os.path.exists(BASE_J) else {}
# fetch baselines for new tickers
for tk,e in ev.items():
    k=f"{tk}|{e['date']}"
    if k not in bl: bl[k]=baseline(tk,e['date']); time.sleep(0.3)
json.dump(bl,open(BASE_J,'w'))

# fetch latest prices concurrently
rows=[]
def one(item):
    tk,e=item; px,chg=latest(tk); return tk,e,px,chg
with ThreadPoolExecutor(max_workers=8) as exx:
    for tk,e,px,chg in exx.map(one, ev.items()):
        rows.append((tk,e,px,chg))

ts=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')
new=os.path.exists(LOG)
with open(LOG,'a') as f:
    if not new: f.write("ts_utc,snapshot,ticker,pdufa_date,days_to_pdufa,price,chg_pct,runup_idx\n")
    for tk,e,px,chg in rows:
        k=f"{tk}|{e['date']}"; b=bl.get(k); idx=round(px/b*100,2) if (px and b) else ''
        dtp=bdays(today, datetime.date.fromisoformat(e['date']))
        f.write(f"{ts},{SNAP},{tk},{e['date']},{dtp},{px if px else ''},{chg if chg is not None else ''},{idx}\n")
print(f"[{ts} {SNAP}] logged {len(rows)} current PDUFAs -> daily_log.csv")
# hand off to dashboard builder
os.system(f"python3 {os.path.join(BASE,'build_tracker.py')}")
