#!/usr/bin/env python3
import urllib.request, json, time, datetime, os, sys, random
from concurrent.futures import ThreadPoolExecutor, as_completed
BASE=os.path.dirname(os.path.abspath(__file__))
CACHE=os.path.join(BASE,'t120_2020plus.json'); EVENTS=os.path.join(BASE,'events.json')
BUDGET=float(sys.argv[1]) if len(sys.argv)>1 else 38.0
WORKERS=int(sys.argv[2]) if len(sys.argv)>2 else 6
events=json.load(open(EVENTS)); cache=json.load(open(CACHE)) if os.path.exists(CACHE) else {}
todo=[k for k in events if k not in cache]

def fetch(k):
    e=events[k]; ev=datetime.datetime.strptime(e['date'],'%Y-%m-%d').date()
    p1=int(time.mktime((ev-datetime.timedelta(days=210)).timetuple()))
    p2=int(time.mktime((ev+datetime.timedelta(days=16)).timetuple()))
    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{e['ticker'].replace('.','-')}?period1={p1}&period2={p2}&interval=1d"
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req,timeout=15) as r: d=json.load(r)
            res=d['chart']['result'][0]; ts=res['timestamp']; cl=res['indicators']['quote'][0]['close']
            days=[(datetime.date.fromtimestamp(t),c) for t,c in zip(ts,cl) if c is not None]
            idx=max((i for i,(dt,_) in enumerate(days) if dt<=ev), default=None)
            if idx is None: return k,{}
            return k,{str(i-idx):round(float(c),4) for i,(dt,c) in enumerate(days) if -120<=i-idx<=5}
        except Exception as ex:
            if '429' in str(ex): time.sleep(2+attempt*2+random.random())
            else: 
                if attempt==2: return k,None
                time.sleep(1)
    return k,None
t0=time.time(); done=0; fail=0; i=0
while i<len(todo) and time.time()-t0<BUDGET:
    batch=todo[i:i+WORKERS]; i+=WORKERS
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for k,path in ex.map(fetch,batch):
            cache[k]={'path':path or {},'ok':bool(path)}; done+=1
            if not path: fail+=1
    json.dump(cache,open(CACHE,'w'))
    time.sleep(0.15)
print(f"run done {done} fail {fail} | cache {len(cache)}/{len(events)} | remaining {len(events)-len(cache)}")
