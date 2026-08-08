import yfinance as yf, pickle, time, os, warnings, random
warnings.filterwarnings('ignore')
tks=[t.strip() for t in open('tickers.txt') if t.strip()]
px = pickle.load(open('px2.pkl','rb')) if os.path.exists('px2.pkl') else {}
fail=set()
for i,t in enumerate(tks):
    if t in px: continue
    for attempt in range(3):
        try:
            h=yf.Ticker(t).history(start='2016-06-01', end='2026-07-11', auto_adjust=True)
            s=h['Close'].dropna()
            if len(s)>40:
                s.index=s.index.tz_localize(None)
                px[t]=s
            break
        except Exception as e:
            time.sleep(1.5*(attempt+1))
    else:
        fail.add(t)
    if i%20==0:
        pickle.dump(px, open('px2.pkl','wb'))
        print(f'{i}/{len(tks)} ok={len(px)} fail={len(fail)}', flush=True)
    time.sleep(0.4+random.random()*0.4)
pickle.dump(px, open('px2.pkl','wb'))
print('DONE ok=',len(px),'fail=',len(fail), flush=True)
open('fail.txt','w').write('\n'.join(sorted(fail)))
