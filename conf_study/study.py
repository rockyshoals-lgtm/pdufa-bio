import pandas as pd, json, numpy as np
mom=json.load(open('readout_momentum_cache.json'))
prc=json.load(open('readout_price_cache.json'))
ev=pd.read_csv('conf_study/conference_events_raw.csv', parse_dates=['anchor'])
ra=pd.read_csv('gungnir_readout_analysis.csv', low_memory=False)
ra['date']=pd.to_datetime(ra['date'],errors='coerce')
def key(t,d): return f"{t}|{d.strftime('%Y-%m-%d')}"
def runups(t,d):
    k=key(t,d); m=mom.get(k); p=prc.get(k)
    if not m: return None
    d1=m.get('d_m1')
    if not d1 or d1<=0: return None
    out={}
    for lbl,fld in [('runup_30d','d_m30'),('runup_20d','d_m20'),('runup_10d','d_m10'),('runup_5d','d_m5')]:
        v=m.get(fld); out[lbl]=(d1/v-1)*100 if v and v>0 else np.nan
    out['event_day']=np.nan; out['post_5d']=np.nan
    if p and p.get('d_minus_1'):
        dm1=p['d_minus_1']
        if dm1>0:
            if p.get('d_plus_1'): out['event_day']=(p['d_plus_1']/dm1-1)*100
            if p.get('d_plus_5'): out['post_5d']=(p['d_plus_5']/dm1-1)*100
    return out
rows=[]
for _,r in ev.iterrows():
    u=runups(r['ticker'], r['anchor'])
    if u: rows.append({**r.to_dict(), **u})
conf=pd.DataFrame(rows)
ckeys=set(key(r['ticker'],r['anchor']) for _,r in ev.iterrows())
brows=[]
for _,r in ra.iterrows():
    k=key(r['ticker'],r['date'])
    if k in ckeys: continue
    u=runups(r['ticker'],r['date'])
    if u:
        tier='micro/nano' if r.get('is_micro')==1 else 'small' if r.get('is_small')==1 else 'mid' if r.get('is_mid')==1 else 'large'
        brows.append({'ticker':r['ticker'],'cap_tier':tier,**u})
base=pd.DataFrame(brows)
def stat(s):
    s=pd.Series(s).dropna()
    if len(s)<3: return None
    return dict(n=int(len(s)),median=round(float(s.median()),2),p25=round(float(s.quantile(.25)),2),p75=round(float(s.quantile(.75)),2),mean=round(float(s.mean()),2))
L=[]
L.append('CONFERENCE RUN-UP STUDY (2022-06 -> 2026-02)')
L.append(f'Conference presenter events: {len(conf)} | Baseline (non-conference readouts): {len(base)}')
L.append('')
L.append('HEADLINE - median % move INTO the presentation (D-1 vs D-N)')
L.append(f"{'window':<11}{'n':>5}{'median':>9}{'p25':>9}{'p75':>9}{'mean':>9} | {'base n':>7}{'base med':>9}")
for w in ['runup_30d','runup_20d','runup_10d','runup_5d']:
    c=stat(conf[w]); b=stat(base[w])
    L.append(f"{w:<11}{c['n']:>5}{c['median']:>9}{c['p25']:>9}{c['p75']:>9}{c['mean']:>9} | {b['n']:>7}{b['median']:>9}")
L.append('')
L.append('30-DAY RUN-UP BY CAP TIER (conference presenters vs baseline)')
L.append(f"{'cap tier':<13}{'n':>5}{'median':>9}{'p25':>9}{'p75':>9} | {'base n':>7}{'base med':>9}")
for t in ['micro/nano','small','mid','large']:
    c=stat(conf[conf.cap_tier==t]['runup_30d']); b=stat(base[base.cap_tier==t]['runup_30d'])
    if c: L.append(f"{t:<13}{c['n']:>5}{c['median']:>9}{c['p25']:>9}{c['p75']:>9} | {b['n'] if b else '-':>7}{b['median'] if b else '-':>9}")
L.append('')
L.append('5-DAY RUN-UP BY CAP TIER')
for t in ['micro/nano','small','mid','large']:
    c=stat(conf[conf.cap_tier==t]['runup_5d'])
    if c: L.append(f"{t:<13}n={c['n']:<4} median={c['median']:>7} p25={c['p25']:>7} p75={c['p75']:>7}")
L.append('')
L.append('BY CONFERENCE (30d run-up, n>=5)')
for cf,g in conf.groupby('conf'):
    s=stat(g['runup_30d'])
    if s and s['n']>=5: L.append(f"{cf:<9}n={s['n']:<4} median={s['median']:>7} p25={s['p25']:>7} p75={s['p75']:>7}")
L.append('')
L.append('BY YEAR (30d run-up)')
for y,g in conf.groupby('year'):
    s=stat(g['runup_30d'])
    if s: L.append(f"{int(y)} n={s['n']:<4} median={s['median']:>7}")
L.append('')
L.append('ON / AFTER THE EVENT (all conference presenters)')
for w in ['event_day','post_5d']:
    c=stat(conf[w])
    if c: L.append(f"{w:<10}n={c['n']:<4} median={c['median']:>7} p25={c['p25']:>7} p75={c['p75']:>7}")
L.append('')
L.append('EVENT-DAY MOVE BY CAP TIER (D-1 -> D+1)')
for t in ['micro/nano','small','mid','large']:
    c=stat(conf[conf.cap_tier==t]['event_day'])
    if c: L.append(f"{t:<13}n={c['n']:<4} median={c['median']:>7} p25={c['p25']:>7} p75={c['p75']:>7}")
txt='\n'.join(L)
open('conf_study/RESULTS.txt','w').write(txt)
conf.to_csv('conf_study/conference_runup_events.csv',index=False)
base.to_csv('conf_study/baseline_runup_events.csv',index=False)
print(txt)
