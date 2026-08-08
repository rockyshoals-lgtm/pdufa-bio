#!/usr/bin/env python3
"""
Take whatever the conference crawler found, keep the events that are NEW to the study and
have already happened, price them, and merge into the study.

    python price_new_conference_events.py

Reads : catalysts_out/conference_presentations_history.csv   (crawler output)
        conf_study/conference_runup_FULL_v3.csv              (current study)
Writes: conf_study/conference_runup_FULL_v4.csv              (deepened study)

Two things this gets right, because earlier versions got them wrong:
  * cap tier is POINT-IN-TIME  - SEC shares outstanding as of the presentation date x the
    close on that date. Using today's market cap is a look-ahead error: it files companies
    that later collapsed under 'nano' and makes the nano bucket look worse than it was.
  * prices are SPLIT-UNADJUSTED before multiplying by as-reported share counts. Yahoo closes
    are split-adjusted; this universe has ~208 reverse splits. Mixing the two overstates
    historical market caps by the split factor.
"""
import os, sys, json, time, datetime as dt
import urllib.request as ur
import concurrent.futures as cf
import pandas as pd, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
UA   = {'User-Agent': 'pdufa.bio research contact@pdufa.bio'}
YF   = {'User-Agent': 'Mozilla/5.0'}
HIST  = os.path.join(HERE, 'catalysts_out', 'conference_presentations_history_FRESH.csv')
STUDY = os.path.join(HERE, 'conf_study', 'conference_runup_FULL_v3.csv')
OUT   = os.path.join(HERE, 'conf_study', 'conference_runup_FULL_v4.csv')

def series(tk):
    """split-adjusted closes + the split events needed to UN-adjust them."""
    p1 = int(dt.datetime(2016, 1, 1).timestamp()); p2 = int(time.time())
    u = (f'https://query1.finance.yahoo.com/v8/finance/chart/{tk}'
         f'?period1={p1}&period2={p2}&interval=1d&events=split')
    for a in range(3):
        try:
            j = json.loads(ur.urlopen(ur.Request(u, headers=YF), timeout=25).read())
            r = j['chart']['result'][0]
            px = {dt.datetime.utcfromtimestamp(t).date(): c
                  for t, c in zip(r['timestamp'], r['indicators']['quote'][0]['close']) if c}
            sp = [(dt.datetime.utcfromtimestamp(e['date']).date(),
                   float(e['numerator']) / float(e['denominator']))
                  for e in (r.get('events', {}).get('splits', {}) or {}).values()]
            return tk, (px, sorted(sp))
        except Exception as e:
            if '429' in str(e): time.sleep(2 + a * 3)
            else: break
    return tk, None

SHARE_TAGS = ['EntityCommonStockSharesOutstanding', 'CommonStockSharesOutstanding', 'CommonStockSharesIssued']
def shares(tk, t2c):
    cik = t2c.get(tk)
    if not cik: return tk, None
    for a in range(3):
        try:
            j = json.loads(ur.urlopen(ur.Request(
                f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json', headers=UA), timeout=30).read())
            pts = []
            for ns in ('dei', 'us-gaap'):
                for tag in SHARE_TAGS:
                    for _, arr in j.get('facts', {}).get(ns, {}).get(tag, {}).get('units', {}).items():
                        for e in arr:
                            if e.get('end') and e.get('val'): pts.append((e['end'], float(e['val'])))
            return tk, sorted(set(pts))
        except Exception as e:
            if '429' in str(e) or '403' in str(e): time.sleep(1 + a * 2)
            else: break
    return tk, None

def tier(mc):
    if mc is None or mc != mc or mc < 1e6: return None
    return ('nano' if mc < 50e6 else 'micro' if mc < 300e6 else
            'small' if mc < 2e9 else 'mid' if mc < 10e9 else 'large')

def main():
    for p in (HIST, STUDY):
        if not os.path.exists(p): sys.exit(f'ERROR: missing {p}')
    h = pd.read_csv(HIST); s = pd.read_csv(STUDY)
    print(f'crawler history : {len(h)} rows')
    print(f'current study   : {len(s)} events')

    h = h[h.get('date_precision').eq('day')].copy()      # need an exact anchor to price
    h['anchor'] = pd.to_datetime(h.catalyst_date, errors='coerce')
    today = pd.Timestamp(dt.date.today())
    h = h[h.anchor.notna() & (h.anchor < today)]         # already happened
    h['year'] = h.anchor.dt.year
    h['TK'] = h.ticker.astype(str).str.upper()
    h = h[h.TK.str.strip() != '']
    key = lambda df, t, c, y: df[t].astype(str).str.upper() + '|' + df[c].astype(str) + '|' + df[y].astype(str)
    new = h[~key(h, 'TK', 'conference', 'year').isin(set(key(s, 'ticker', 'conf', 'year')))].copy()
    new = new.drop_duplicates(subset=['TK', 'conference', 'anchor'])
    print(f'day-precision, already happened, NEW to the study: {len(new)}')
    if not len(new):
        print('nothing new to price.'); return

    tks = sorted(new.TK.unique())
    print(f'pricing {len(tks)} tickers ...')
    m = json.loads(ur.urlopen(ur.Request('https://www.sec.gov/files/company_tickers.json', headers=UA), timeout=30).read())
    t2c = {v['ticker'].upper(): str(v['cik_str']).zfill(10) for v in m.values()}

    PX, SH = {}, {}
    with cf.ThreadPoolExecutor(8) as ex:
        for tk, v in ex.map(series, tks):
            if v: PX[tk] = v
    with cf.ThreadPoolExecutor(6) as ex:
        for tk, v in ex.map(lambda t: shares(t, t2c), tks):
            if v: SH[tk] = v
            time.sleep(0.02)
    print(f'  prices {len(PX)}/{len(tks)} · shares {len(SH)}/{len(tks)}')

    def raw_price(tk, d):
        px, sp = PX[tk]
        prior = [x for x in sorted(px) if x < d]
        if not prior: return None
        adj = px[prior[-1]]
        f = 1.0
        for sd, ratio in sp:
            if sd > d: f *= ratio        # undo every split AFTER the event
        return adj * f

    rows = []
    for _, r in new.iterrows():
        tk = r.TK
        if tk not in PX: continue
        a = r.anchor.date()
        px, _ = PX[tk]
        days = sorted(px)
        prior = [d for d in days if d < a]
        post  = [d for d in days if d >= a]
        if len(prior) < 31: continue
        p1 = px[prior[-1]]
        f = lambda x, y: round((x / y - 1) * 100, 2) if (x and y) else None
        mc = None
        if tk in SH:
            sh = [v for e, v in SH[tk] if e <= a.isoformat()]
            rp = raw_price(tk, a)
            if sh and rp: mc = rp * sh[-1]
        rows.append(dict(
            ticker=tk, conf=r.conference, anchor=str(a), year=int(r.year),
            pres_type=r.get('pres_type'),
            cap_tier_pit=tier(mc), mcap_pit=mc,
            runup_30d=f(p1, px[prior[-31]]), runup_20d=f(p1, px[prior[-21]]),
            runup_10d=f(p1, px[prior[-11]]), runup_5d=f(p1, px[prior[-6]]),
            event_day=f(px[post[0]], p1) if post else None,
            post_5d=f(px[post[4]], p1) if len(post) > 4 else None,
            post_10d=f(px[post[9]], p1) if len(post) > 9 else None))
    add = pd.DataFrame(rows)
    print(f'priced {len(add)} new events')
    if not len(add): return

    merged = pd.concat([s, add.reindex(columns=s.columns)], ignore_index=True)
    if len(merged) < len(s):
        sys.exit('ABORT: merge would shrink the study. Nothing written.')
    merged.to_csv(OUT, index=False)
    print(f'\nSTUDY {len(s)} -> {len(merged)}  (+{len(add)})  -> {OUT}')
    v = merged.runup_30d.dropna()
    print(f'  headline D-30 median {v.median():+.2f}%   n={len(v)}')
    for t in ['nano', 'micro', 'small', 'mid', 'large']:
        vv = merged[merged.cap_tier_pit == t].runup_30d.dropna()
        if len(vv): print(f'  {t:6s} n={len(vv):4d}  median {vv.median():+6.2f}%')

if __name__ == '__main__':
    main()
