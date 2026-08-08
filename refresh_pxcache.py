# -*- coding: utf-8 -*-
"""Refresh _chart_pxcache.json from FMP daily closes, through today.

The chart builders READ this cache but nothing WRITES it — it had gone stale to 2026-06-18,
~26 days old, so every 'runup-so-far' on the upcoming charts was a month out of date. This
brings every tracked ticker current from FMP EOD closes.

Usage:
    python refresh_pxcache.py            # refresh every ticker already in the cache + events
    python refresh_pxcache.py CELC ABCL  # refresh only these
"""
import os, sys, json, time, datetime as dt
import requests

HERE = os.path.dirname(os.path.abspath(__file__))

def load_env():
    for p in (os.path.join(HERE, 'Odin Perfection', '.env_master'), os.path.join(HERE, '.env')):
        if os.path.exists(p):
            for line in open(p, encoding='utf-8', errors='ignore'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    k = k.strip(); v = v.strip().strip('"').strip("'")
                    os.environ.setdefault(k, v)
load_env()
KEY = os.environ['FMP_API_KEY']
CACHE = os.path.join(HERE, '_chart_pxcache.json')
TODAY = dt.date.today()

def eod(sym, start):
    """List of (date, close) for sym from `start` through today, or [] on failure.

    FMP, not Polygon. Polygon is ~2 days fresher BUT its daily-bar timestamps are shifted +1
    calendar day versus FMP and UW: Polygon's "7/06=115.72" is UW's "7/07=115.72". FMP and UW
    agree exactly (7/06=108.58 in both). Using Polygon would silently mislabel every close by a
    day — a confident wrong number. FMP's ~1-week lag is harmless for a 120-day runup curve, and
    the freshest days are pinned from UW (px_pins.json).
    """
    try:
        r = requests.get('https://financialmodelingprep.com/stable/historical-price-eod/full',
                         params={'symbol': sym, 'from': start, 'to': TODAY.isoformat(), 'apikey': KEY},
                         timeout=25)
        if r.status_code != 200:
            return []
        d = r.json()
        rows = d if isinstance(d, list) else d.get('historical', [])
        out = []
        for x in rows:
            c = x.get('adjClose', x.get('close'))
            dd = x.get('date', '')[:10]
            if dd and c is not None:
                out.append((dd, round(float(c), 4)))
        return out
    except Exception:
        return []

def main():
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    # who to refresh
    if len(sys.argv) > 1:
        tickers = [t.upper() for t in sys.argv[1:]]
    else:
        tickers = set(cache)
        evp = os.path.join(HERE, '_chart2026_events.json')
        if os.path.exists(evp):
            tickers |= {e['ticker'] for e in json.load(open(evp)) if e.get('ticker')}
        tickers = sorted(tickers)

    before = max((d for t in cache.values() for d in (t or {})), default='none')
    print(f'refreshing {len(tickers)} tickers · cache latest was {before} · today {TODAY}')
    upd = new = fail = 0
    for i, tk in enumerate(tickers, 1):
        have = cache.get(tk) or {}
        # only fetch the gap: from the day after our newest close (or 200d back if new)
        start = (max(have) if have else (TODAY - dt.timedelta(days=200)).isoformat())
        rows = eod(tk, start)
        if not rows:
            fail += 1
        else:
            if tk not in cache:
                cache[tk] = {}; new += 1
            n0 = len(cache[tk])
            for dd, c in rows:
                cache[tk][dd] = c
            if len(cache[tk]) > n0:
                upd += 1
        if i % 25 == 0:
            print(f'  {i}/{len(tickers)}  (updated {upd}, new {new}, fail {fail})', flush=True)
            json.dump(cache, open(CACHE, 'w'))
        time.sleep(0.05)
    # UW-pinned overrides for closes the scriptable feeds have not posted yet. On approval day
    # Polygon/FMP lag but UW is current; these values were read from UW get_ticker_ohlc and are
    # the authoritative decision-day closes. Verified, not guessed.
    PIN = os.path.join(HERE, 'px_pins.json')
    if os.path.exists(PIN):
        pins = json.load(open(PIN))
        for tk, days in pins.items():
            if tk.startswith('_') or not isinstance(days, dict):
                continue                      # skip _comment and any non-ticker keys
            cache.setdefault(tk, {})
            for dd, c in days.items():
                cache[tk][dd] = round(float(c), 4)
        print(f'applied {sum(len(v) for v in pins.values())} UW pins from px_pins.json')

    json.dump(cache, open(CACHE, 'w'))
    after = max((d for t in cache.values() for d in (t or {})), default='none')
    print(f'done. tickers now {len(cache)} · updated {upd} · new {new} · no-data {fail} · cache latest {after}')

if __name__ == '__main__':
    main()
