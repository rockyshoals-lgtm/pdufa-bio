# -*- coding: utf-8 -*-
"""polygon_enrich.py — make the forward calendar's market data GENUINELY current.

WHY THIS EXISTS
The site advertised "live" data whose every row was stamped 2026-07-11 for twelve days. The badge
was honest-ified to show the real "data through" date, but the real fix is to actually refresh the
data. This does that for the half Polygon can supply: price, market cap -> cap tier, and average
daily volume, for the FORWARD catalysts.

HARD RULE — FORWARD ONLY.
It refreshes ONLY upcoming PDUFA catalysts (status != Decided, date >= today). A decided event's
market_cap is a HISTORICAL snapshot the run-up cohort study depends on; overwriting it with today's
value would corrupt that study. Decided rows are never touched.

WHAT POLYGON CAN'T DO — it has no PDUFA dates, drugs, or approval/CRL outcomes. Catalyst DISCOVERY
stays with catalyst_crawler.py (SEC/FDA/CT.gov). This script only refreshes quantitative fields on
catalysts that already exist.

WRITES (both surfaces, kept in agreement):
  pdufa_site_src/api/data.js         -> SLATE[].price/mcap/cap/adv, SLATE.as_of = today
  pdufa_site_src/api/v1/dataset.mjs  -> forward PDUFA records: _d.market_cap_usd, cap, ua = now

Backs up both first (.bak_polygon). Idempotent — safe to run hourly. Never invents a value: if
Polygon has no data for a ticker (e.g. an unsponsored ADR), the existing value is kept unchanged.

    python polygon_enrich.py [--dry-run] [--tickers MNKD CAPR ...]
"""
import os, re, sys, json, time, argparse
import datetime as dt
import urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, 'pdufa_site_src')
DATA_JS = os.path.join(SITE, 'api', 'data.js')
DATASET = os.path.join(SITE, 'api', 'v1', 'dataset.mjs')
BASE = 'https://api.polygon.io'
TODAY = dt.date.today()
NOW_ISO = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def load_key():
    for p in (os.path.join(HERE, 'Odin Perfection', '.env_master'), os.path.join(HERE, '.env')):
        if os.path.exists(p):
            for line in open(p, encoding='utf-8', errors='ignore'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    k = os.environ.get('POLYGON_API_KEY')
    if not k:
        sys.exit('No POLYGON_API_KEY in Odin Perfection/.env_master')
    return k


def cap_tier(mcap):
    if not mcap:
        return None
    m = float(mcap)
    if m < 50e6:  return 'Nano'
    if m < 300e6: return 'Micro'
    if m < 2e9:   return 'Small'
    if m < 10e9:  return 'Mid'
    return 'Large'


class Poly:
    def __init__(self, key):
        self.key = key

    def _get(self, path, params=None):
        params = dict(params or {}); params['apiKey'] = self.key
        url = BASE + path + '?' + urllib.parse.urlencode(params)
        for attempt in range(5):
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    return json.loads(r.read().decode('utf-8', 'replace'))
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    time.sleep(min(15, 2 ** attempt)); continue
                return None
            except Exception:
                time.sleep(min(10, 2 ** attempt))
        return None

    def price_adv(self, t):
        """Last close + ~20-session average daily volume, from daily bars."""
        start = (TODAY - dt.timedelta(days=45)).isoformat()
        j = self._get(f'/v2/aggs/ticker/{t}/range/1/day/{start}/{TODAY.isoformat()}',
                      {'adjusted': 'true', 'sort': 'asc', 'limit': 60})
        rows = (j or {}).get('results') or []
        if not rows:
            return None, None
        price = rows[-1].get('c')
        vols = [r.get('v') for r in rows[-20:] if r.get('v')]
        adv = round(sum(vols) / len(vols)) if vols else None
        return price, adv

    def mcap(self, t):
        j = self._get(f'/v3/reference/tickers/{t}')
        return ((j or {}).get('results') or {}).get('market_cap')


def read_slate(txt):
    i = txt.find('const SLATE=')
    obj, end = json.JSONDecoder().raw_decode(txt[i + len('const SLATE='):])
    span = (i + len('const SLATE='), i + len('const SLATE=') + end)
    return obj, span


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--tickers', nargs='+')
    a = ap.parse_args()
    poly = Poly(load_key())

    djs = open(DATA_JS, encoding='utf-8').read()
    slate, span = read_slate(djs)
    cats = slate['catalysts']
    tickers = [c['ticker'] for c in cats if c.get('ticker')]
    if a.tickers:
        want = {t.upper() for t in a.tickers}
        tickers = [t for t in tickers if t.upper() in want]

    print(f'Polygon enrich: {len(tickers)} forward catalysts, as of {TODAY}')
    fresh = {}
    ok = fail = 0
    for t in tickers:
        price, adv = poly.price_adv(t)
        mc = poly.mcap(t)
        if price is None and mc is None:
            fail += 1; print(f'  {t:6s} no Polygon data — keeping existing'); continue
        fresh[t] = {'price': price, 'adv': adv, 'mcap': mc}
        ok += 1
        tier = cap_tier(mc)
        mcs = f'{round(mc/1e6)}M' if mc else 'kept'
        print(f'  {t:6s} price={price} mcap={mcs} tier={tier or "kept"} adv={adv}')

    # ---- patch data.js SLATE (forward only; keep any field Polygon couldn't supply) ----
    changed = 0
    for c in cats:
        f = fresh.get(c.get('ticker'))
        if not f:
            continue
        if f['price'] is not None: c['price'] = round(float(f['price']), 2)
        if f['adv']   is not None: c['adv'] = f['adv']
        if f['mcap']  is not None:
            c['mcap'] = float(f['mcap']); c['cap'] = cap_tier(f['mcap']) or c.get('cap')
        changed += 1
    slate['as_of'] = TODAY.isoformat()
    new_djs = djs[:span[0]] + json.dumps(slate, separators=(',', ':')) + djs[span[1]:]

    # ---- patch dataset.mjs (forward PDUFA records only: mcap + cap + ua) ----
    dtxt = open(DATASET, encoding='utf-8').read()
    s = dtxt.index('['); e = dtxt.rindex(']') + 1
    arr = json.loads(dtxt[s:e])
    drecs = 0
    for r in arr:
        if r.get('type') != 'PDUFA' or r.get('st') == 'Decided':
            continue
        d = str(r.get('d', ''))[:10]
        if d < TODAY.isoformat():
            continue
        f = fresh.get(r.get('t'))
        if not f:
            continue
        if f['mcap'] is not None:
            r.setdefault('_d', {})['market_cap_usd'] = float(f['mcap'])
            r['cap'] = cap_tier(f['mcap']) or r.get('cap')
        r['ua'] = NOW_ISO          # this record's market data was genuinely refreshed just now
        drecs += 1
    new_dtxt = dtxt[:s] + json.dumps(arr, separators=(',', ':')) + dtxt[e:]

    print(f'\nrefreshed: {ok} tickers ok, {fail} no-data | data.js rows {changed} | '
          f'dataset.mjs forward PDUFA rows {drecs}')
    if a.dry_run:
        print('DRY RUN — nothing written'); return

    for path, new in ((DATA_JS, new_djs), (DATASET, new_dtxt)):
        open(path + '.bak_polygon', 'w', encoding='utf-8').write(open(path, encoding='utf-8').read())
        open(path, 'w', encoding='utf-8').write(new)
    print(f'wrote data.js + dataset.mjs (backups: *.bak_polygon). ua stamped {NOW_ISO}')


if __name__ == '__main__':
    main()
