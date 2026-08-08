import json,urllib.request,time,os,sys
from concurrent.futures import ThreadPoolExecutor
BASE=os.path.dirname(os.path.abspath(__file__))
items=json.load(open(os.path.join(BASE,'readout_ncts.json')))
OUT=os.path.join(BASE,'status.json'); res=json.load(open(OUT)) if os.path.exists(OUT) else {}
BUDGET=float(sys.argv[1]) if len(sys.argv)>1 else 38; W=int(sys.argv[2]) if len(sys.argv)>2 else 10
todo=[n for n in items if n not in res]
def f(nct):
    url=f"https://clinicaltrials.gov/api/v2/studies/{nct}?fields=protocolSection.statusModule"
    for a in range(3):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
            d=json.load(urllib.request.urlopen(req,timeout=15))
            sm=(d.get('protocolSection') or {}).get('statusModule') or {}
            return nct,{'status':sm.get('overallStatus'),'pcd':(sm.get('primaryCompletionDateStruct') or {}).get('date'),'pcd_type':(sm.get('primaryCompletionDateStruct') or {}).get('type'),'updated':(sm.get('lastUpdatePostDateStruct') or {}).get('date')}
        except Exception as e:
            if '429' in str(e): time.sleep(2+a)
            elif a==2: return nct,{'status':'ERR'}
    return nct,{'status':'ERR'}
t0=time.time();i=0;done=0
while i<len(todo) and time.time()-t0<BUDGET:
    b=todo[i:i+W];i+=W
    with ThreadPoolExecutor(max_workers=W) as ex:
        for nct,st in ex.map(f,b): res[nct]=st;done+=1
    json.dump(res,open(OUT,'w'))
print(f"done {done} | total {len(res)}/{len(items)} | remaining {len(items)-len(res)}")
