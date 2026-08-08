#!/usr/bin/env python3
"""
Rebuild the conference run-up study from a CLEAN base + the corrected crawler output.

    python rebuild_conference_study.py --hist catalysts_out/<rebuilt_history>.csv

WHY NOT JUST APPEND:
  The study was layered v2 (1,425 curated) -> v3 (+130 crawler) -> v4 (+431 crawler), and both
  crawler layers were priced with the OLD extractor, which could put a presentation in the wrong
  YEAR (it defaulted an unreadable year to the filing year). The study's identity key is
  (ticker, conference, year). So re-running the fixed crawler would not correct those rows —
  it would file the SAME presentation a second time under a different year. Double-counted.

  So we throw away every crawler-derived row and re-derive them from the fixed output, keeping
  only the curated v2 base. Slower, but it cannot double-count.

Cap tier is POINT-IN-TIME (SEC shares outstanding at the presentation date x the split-UNADJUSTED
close). Today's market cap would be a look-ahead error, and split-adjusted prices against
as-reported share counts overstate historical caps by the split factor (~208 reverse splits here).
"""
import os, sys, json, time, argparse, datetime as dt
import urllib.request as ur
import concurrent.futures as cf
import pandas as pd, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'pdufa.bio research contact@pdufa.bio'}
YF = {'User-Agent': 'Mozilla/5.0'}
BASE = os.path.join(HERE, 'conf_study', 'conference_runup_FULL_v2.csv')   # curated, pre-crawler
OUT  = os.path.join(HERE, 'conf_study', 'conference_runup_FULL_v5.csv')
SHCACHE = os.path.join(HERE, 'conf_study', 'sec_shares_outstanding.json')

def series(tk):
    p1 = int(dt.datetime(2016,1,1).timestamp()); p2 = int(time.time())
    u = (f'https://query1.finance.yahoo.com/v8/finance/chart/{tk}'
         f'?period1={p1}&period2={p2}&interval=1d&events=split')
    for a in range(3):
        try:
            j = json.loads(ur.urlopen(ur.Request(u, headers=YF), timeout=25).read())
            r = j['chart']['result'][0]
            px = {dt.datetime.utcfromtimestamp(t).date(): c
                  for t, c in zip(r['timestamp'], r['indicators']['quote'][0]['close']) if c}
            sp = [(dt.datetime.utcfromtimestamp(e['date']).date(),
                   float(e['numerator'])/float(e['denominator']))
                  for e in (r.get('events', {}).get('splits', {}) or {}).values()]
            return tk, (px, sorted(sp))
        except Exception as e:
            if '429' in str(e): time.sleep(2 + a*3)
            else: break
    return tk, None

TAGS = ['EntityCommonStockSharesOutstanding','CommonStockSharesOutstanding','CommonStockSharesIssued']
def shares(tk, t2c, cache):
    if tk in cache: return tk, cache[tk]
    cik = t2c.get(tk)
    if not cik: return tk, None
    for a in range(3):
        try:
            j = json.loads(ur.urlopen(ur.Request(
                f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json', headers=UA), timeout=30).read())
            pts = []
            for ns in ('dei','us-gaap'):
                for tag in TAGS:
                    for _, arr in j.get('facts',{}).get(ns,{}).get(tag,{}).get('units',{}).items():
                        for e in arr:
                            if e.get('end') and e.get('val'): pts.append((e['end'], float(e['val'])))
            return tk, sorted(set(pts))
        except Exception as e:
            if '429' in str(e) or '403' in str(e): time.sleep(1 + a*2)
            else: break
    return tk, None

# ---------------------------------------------------------------------------
# Conference labels in the curated base are NOT clean. Left alone, a rebuild would
# quietly reintroduce them:
#   ANE (n=47)  -- a garbled letter-order of ENA (AACR-NCI-EORTC, an OCTOBER meeting).
#                  Real conference, mangled code, and two corrupt stored dates dragged
#                  unrelated presentations into the bucket. October anchors are genuine
#                  ENA; the rest we cannot vouch for.
#   case variants (ObesityWeek/OBESITYWEEK, AD/PD vs ADPD, IDWeek vs IDWEEK)
#   PRE-RELEA, AAI, SID, ESCMID -- codes we cannot tie to any conference.
#
# Rule: if we cannot name the conference with confidence, we label it UNKNOWN. The event
# keeps its prices and stays in the headline sample; it just never appears under a
# conference heading we cannot stand behind.
# ---------------------------------------------------------------------------
CASE_FIX = {"ObesityWeek": "OBESITYWEEK", "AD/PD": "ADPD", "IDWeek": "IDWEEK"}

def canonicalize_conf(df, registry):
    df = df.copy()
    anchor_month = pd.to_datetime(df["anchor"], errors="coerce").dt.month
    is_ane = df["conf"].eq("ANE")
    df.loc[is_ane & anchor_month.isin([10, 11]), "conf"] = "ENA"      # genuine October ENA
    df.loc[df["conf"].eq("ANE"), "conf"] = "UNKNOWN"                  # everything else: unverifiable
    df["conf"] = df["conf"].replace(CASE_FIX)
    df.loc[~df["conf"].isin(registry) & df["conf"].ne("UNKNOWN"), "conf"] = "UNKNOWN"
    return df


def tier(mc):
    if mc is None or mc != mc or mc < 1e6: return None
    return ('nano' if mc<50e6 else 'micro' if mc<300e6 else
            'small' if mc<2e9 else 'mid' if mc<10e9 else 'large')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hist', required=True, help='rebuilt crawler history CSV')
    args = ap.parse_args()
    for p in (BASE, args.hist):
        if not os.path.exists(p): sys.exit(f'ERROR: missing {p}')

    registry = set(json.load(open(os.path.join(HERE, 'conf_registry.json'))))
    base = pd.read_csv(BASE)
    n_ane = int(base['conf'].eq('ANE').sum())
    base = canonicalize_conf(base, registry)
    print(f'curated base (v2, pre-crawler): {len(base)} events')
    print(f"  labels canonicalised: ANE({n_ane}) -> ENA/UNKNOWN · case variants folded · "
          f"unverifiable -> UNKNOWN  [now {int(base['conf'].eq('UNKNOWN').sum())} UNKNOWN]")
    h = pd.read_csv(args.hist)
    print(f'rebuilt crawler history       : {len(h)} rows')

    h = h[h.date_precision.eq('day')].copy()
    h['anchor'] = pd.to_datetime(h.catalyst_date, errors='coerce')
    h = h[h.anchor.notna() & (h.anchor < pd.Timestamp(dt.date.today()))]
    h['year'] = h.anchor.dt.year
    h['TK'] = h.ticker.astype(str).str.upper()
    h = h[h.TK.str.strip() != '']
    h = h.drop_duplicates(subset=['TK','conference','anchor'])
    print(f'  priceable (day precision, already happened): {len(h)}')

    k = lambda df,t,c,y: df[t].astype(str).str.upper()+'|'+df[c].astype(str)+'|'+df[y].astype(str)
    new = h[~k(h,'TK','conference','year').isin(set(k(base,'ticker','conf','year')))]
    print(f'  NEW vs curated base: {len(new)}')

    tks = sorted(set(new.TK) | set(base.ticker.astype(str).str.upper()))
    print(f'\npricing {len(tks)} tickers (base + new, so cap tiers are consistent) ...')
    m = json.loads(ur.urlopen(ur.Request('https://www.sec.gov/files/company_tickers.json', headers=UA), timeout=30).read())
    t2c = {v['ticker'].upper(): str(v['cik_str']).zfill(10) for v in m.values()}
    cache = json.load(open(SHCACHE)) if os.path.exists(SHCACHE) else {}

    PX = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for tk, v in ex.map(series, tks):
            if v: PX[tk] = v
    SH = dict(cache)
    need = [t for t in tks if t not in SH]
    with cf.ThreadPoolExecutor(6) as ex:
        for tk, v in ex.map(lambda t: shares(t, t2c, cache), need):
            if v: SH[tk] = v
            time.sleep(0.02)
    json.dump(SH, open(SHCACHE,'w'))
    print(f'  prices {len(PX)}/{len(tks)} · shares {len(SH)}/{len(tks)}')

    def raw_price(tk, d):
        px, sp = PX[tk]
        prior = [x for x in sorted(px) if x < d]
        if not prior: return None
        adj = px[prior[-1]]; f = 1.0
        for sd, ratio in sp:
            if sd > d: f *= ratio            # un-adjust every split AFTER the event
        return adj * f

    def pit_mcap(tk, a):
        if tk not in PX or tk not in SH: return None
        sh = [v for e, v in SH[tk] if e <= a.isoformat()]
        rp = raw_price(tk, a)
        return rp * sh[-1] if (sh and rp) else None

    # --- price the new crawler events ---
    rows = []
    for _, r in new.iterrows():
        tk = r.TK
        if tk not in PX: continue
        a = r.anchor.date(); px, _ = PX[tk]
        days = sorted(px); prior = [d for d in days if d < a]; post = [d for d in days if d >= a]
        if len(prior) < 31: continue
        p1 = px[prior[-1]]
        f = lambda x, y: round((x/y-1)*100, 2) if (x and y) else None
        mc = pit_mcap(tk, a)
        rows.append(dict(ticker=tk, conf=r.conference, anchor=str(a), year=int(r.year),
            pres_type=r.get('pres_type'), cap_tier_pit=tier(mc), mcap_pit=mc,
            runup_30d=f(p1,px[prior[-31]]), runup_20d=f(p1,px[prior[-21]]),
            runup_10d=f(p1,px[prior[-11]]), runup_5d=f(p1,px[prior[-6]]),
            event_day=f(px[post[0]],p1) if post else None,
            post_5d=f(px[post[4]],p1) if len(post)>4 else None,
            post_10d=f(px[post[9]],p1) if len(post)>9 else None))
    add = pd.DataFrame(rows)
    if len(add):
        add = canonicalize_conf(add, registry)
    print(f'\npriced {len(add)} new crawler events')

    # --- recompute POINT-IN-TIME cap tiers on the curated base too (v2 used today's mcap) ---
    pit = []
    for _, r in base.iterrows():
        tk = str(r.ticker).upper()
        try: a = dt.date.fromisoformat(str(r.anchor)[:10])
        except Exception: pit.append(None); continue
        pit.append(pit_mcap(tk, a))
    base = base.copy()
    base['mcap_pit'] = pit
    base['cap_tier_pit'] = base.mcap_pit.map(tier)
    print(f'base cap tiers recomputed point-in-time: {base.cap_tier_pit.notna().sum()}/{len(base)}')

    merged = pd.concat([base, add.reindex(columns=base.columns)], ignore_index=True)
    merged = merged.drop_duplicates(subset=['ticker','conf','anchor'], keep='first')
    if len(merged) < len(base): sys.exit('ABORT: rebuild would shrink below the base. Nothing written.')
    merged.to_csv(OUT, index=False)
    print(f'\nSTUDY -> {len(merged)} events  (base {len(base)} + {len(merged)-len(base)} crawler)  -> {OUT}')
    v = merged.runup_30d.dropna()
    print(f'  headline D-30 median {v.median():+.2f}%  n={len(v)}  positive {(v>0).mean()*100:.1f}%')
    for t in ['nano','micro','small','mid','large']:
        x = merged[merged.cap_tier_pit==t].runup_30d.dropna()
        if len(x): print(f'  {t:6s} n={len(x):4d}  median {x.median():+6.2f}%')

if __name__ == '__main__':
    main()
