"""
Conference Run-up Study — price fetch + compute.
RUN THIS ON THE LOCAL MACHINE where FMP_API_KEY is set (300 calls/min => ~2 min).
  python RUN_LOCALLY_build_study.py
Outputs: conference_runup_FULL.csv  +  CONFERENCE_RUNUP_RESULTS.txt
Facts and historical statistics only. No scores, no win rates, no recommendations.
"""
import os, time, json, requests, pandas as pd, numpy as np

KEY=os.environ.get('FMP_API_KEY')
assert KEY, "FMP_API_KEY not set"
EV=pd.read_csv('MASTER_conference_events_ENRICHED.csv', parse_dates=['anchor'])
tks=sorted(EV['ticker'].astype(str).unique())
print(f'{len(EV)} events / {len(tks)} tickers')

# ---------- 1. price fetch ----------
CACHE='px_fmp.json'
px=json.load(open(CACHE)) if os.path.exists(CACHE) else {}
for i,t in enumerate(tks):
    if t in px: continue
    try:
        r=requests.get('https://financialmodelingprep.com/stable/historical-price-eod/light',
                       params={'symbol':t,'from':'2016-06-01','to':'2026-12-31','apikey':KEY}, timeout=25)
        d=r.json()
        if isinstance(d,list) and d:
            px[t]={x['date']:x['price'] for x in d if x.get('price')}
    except Exception as e:
        print('fail',t,e)
    if i%25==0:
        json.dump(px,open(CACHE,'w')); print(f'  {i}/{len(tks)} cached={len(px)}')
    time.sleep(0.21)          # 300/min limit
json.dump(px,open(CACHE,'w'))
print('priced tickers:',len(px))

# ---------- 2. run-up computation ----------
def series(t):
    d=px.get(t) or {}
    if not d: return None
    s=pd.Series(d); s.index=pd.to_datetime(s.index); return s.sort_index().astype(float)

rows=[]
for _,r in EV.iterrows():
    s=series(str(r['ticker']))
    if s is None or len(s)<60: continue
    i=s.index.searchsorted(r['anchor'])          # trading-day position of the anchor
    if i<35 or i+11>=len(s): continue
    P=lambda k: float(s.iloc[i+k])
    d1=P(-1)
    if d1<=0: continue
    rec=r.to_dict()
    for lbl,k in [('runup_30d',-30),('runup_20d',-20),('runup_10d',-10),('runup_5d',-5)]:
        base=P(k); rec[lbl]=round((d1/base-1)*100,2) if base>0 else np.nan
    rec['event_day']=round((P(1)/d1-1)*100,2)
    rec['post_5d']  =round((P(5)/d1-1)*100,2)
    rec['post_10d'] =round((P(10)/d1-1)*100,2)
    rec['price_d1'] =round(d1,2)
    rows.append(rec)
df=pd.DataFrame(rows)
df.to_csv('conference_runup_FULL.csv',index=False)
print('events with full price window:',len(df))

# ---------- 3. report (medians + n only; NO win rates / scores) ----------
def st(s):
    s=pd.Series(s).dropna()
    return None if len(s)<3 else dict(n=len(s),med=round(s.median(),2),p25=round(s.quantile(.25),2),
                                      p75=round(s.quantile(.75),2),mean=round(s.mean(),2))
L=[f'CONFERENCE RUN-UP STUDY — n={len(df)} events, {df.year.min()}–{df.year.max()}','']
L.append('HEADLINE (median % into the presentation)')
for w in ['runup_30d','runup_20d','runup_10d','runup_5d','event_day','post_5d','post_10d']:
    x=st(df[w]);  L.append(f'  {w:<11} n={x["n"]:<5} med={x["med"]:>7}%  p25={x["p25"]:>7}%  p75={x["p75"]:>7}%  mean={x["mean"]:>7}%') if x else None
for dim in ['cap_tier_final','conf','year','pres_type','ta_bucket_v2']:
    if dim not in df.columns: continue
    L.append(''); L.append(f'BY {dim.upper()} (30d run-up, n>=5)')
    for k,g in df.groupby(dim):
        x=st(g['runup_30d'])
        if x and x['n']>=5: L.append(f'  {str(k)[:22]:<24} n={x["n"]:<5} med={x["med"]:>7}%  p25={x["p25"]:>7}%  p75={x["p75"]:>7}%')
# designation cuts
for flag in ['btd','orphan','priority_review','fast_track','gene_therapy','had_adcom']:
    if flag in df.columns:
        L.append(''); L.append(f'BY {flag}')
        for k,g in df.groupby(df[flag].fillna(0).astype(float)>0):
            x=st(g['runup_30d'])
            if x: L.append(f'  {flag}={bool(k)}  n={x["n"]:<5} med={x["med"]:>7}%  p75={x["p75"]:>7}%')
# tails
a=df['runup_30d'].dropna()
L+=['','TAIL DISTRIBUTION (30d)']
for thr in [50,25,10,0,-25]:
    L.append(f'  >= {thr:>4}% : {(a>=thr).mean()*100:5.1f}%  (n={int((a>=thr).sum())})')
L.append(f'  MEAN {a.mean():.2f}%  vs  MEDIAN {a.median():.2f}%   std {a.std():.1f}%')
open('CONFERENCE_RUNUP_RESULTS.txt','w').write('\n'.join(L))
print('\n'.join(L))
