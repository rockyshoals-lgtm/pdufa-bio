import pandas as pd, yfinance as yf, warnings, pickle, sys
warnings.filterwarnings('ignore')
ev=pd.read_csv('conference_events_raw.csv', parse_dates=['anchor'])
tks=sorted(ev['ticker'].unique())
px={}
B=20
for i in range(0,len(tks),B):
    batch=tks[i:i+B]
    try:
        d=yf.download(batch, start='2021-10-01', end='2026-07-11', progress=False,
                      auto_adjust=True, group_by='ticker', threads=True)
        for t in batch:
            try:
                s=(d[t]['Close'] if len(batch)>1 else d['Close']).dropna()
                if len(s)>60: px[t]=s
            except Exception: pass
    except Exception as e:
        print('batchfail',e,flush=True)
    print('progress',min(i+B,len(tks)),'/',len(tks),'ok',len(px),flush=True)
pickle.dump(px, open('px.pkl','wb'))
print('DONE',len(px),flush=True)
