# -*- coding: utf-8 -*-
"""price_source.py -- the ONE place the site gets daily closes, quotes and market caps (audit 2026-11-09 §4).

Before: eleven scripts each called Polygon's free tier (5 calls a minute, end-of-day). The price step took ~25 minutes,
and a 429 on 2026-10-22 failed three runs; the Bing AI citation series shows each frozen night costs ~80% of the next
day's citations. Now:

  primary   FMP /stable/ (paid key, already a repo secret): historical-price-eod/full, batch-quote-short,
            market-capitalization-batch. One batch call covers every forward ticker.
  Polygon   REMOVED 2026-11-13 (David). Closes Polygon recorded before the 2026-11-10 cutover stay in the caches as
            the series of record; nothing fetches from Polygon any more (tests/test_prices_fmp_only.py).
  fallback  Alpaca market data (free, IEX feed) when ALPACA_KEY_ID and ALPACA_SECRET_KEY exist. Dormant until David
            adds the two secrets; closes only (IEX volumes are partial, so Alpaca volume is never published).

Price convention, unchanged from Polygon's `adjusted=true`: closes are SPLIT-adjusted, NOT dividend-adjusted. FMP's
historical-price-eod/full `close` is the same convention (checked close-by-close against the Polygon cache before
cutover; see _price_cutover_diff.json). Dividend-adjusted closes would silently move every run-up figure on dividend
payers (AZN, MRK, BMY, GILD...) against the 1,879-event study, so they are not used.

Every series is [(iso_date, close, volume)] ascending; the date is the Eastern trading date (RULE 1).

    daily(ticker, start, end)    -> [(date, close, volume)]
    quotes(tickers)              -> {ticker: {"price": float, "volume": int}}
    market_caps(tickers)         -> {ticker: float}
    source_of(ticker)            -> "FMP" | "Alpaca" | None   (which feed served the last daily() call)
"""
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "pdufa.bio-research-script/1.0"}
FMP = "https://financialmodelingprep.com/stable/"
_cache = {}
_served = {}
STATS = {"FMP": 0, "Alpaca": 0, "miss": 0, "calls": 0}


def _env():
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"), os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_env()


def _get(url, headers=None, tries=4, timeout=30):
    h = dict(UA); h.update(headers or {})
    for i in range(tries):
        STATS["calls"] += 1
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(min(20, 2 ** i)); continue
            return None
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


def _fmp_symbol(t):
    return str(t).upper().replace(".", "-")


def _fmp_key():
    return os.environ.get("FMP_API_KEY")


def _fmp_daily(t, start, end):
    k = _fmp_key()
    if not k:
        return []
    j = _get(f"{FMP}historical-price-eod/full?symbol={urllib.parse.quote(_fmp_symbol(t))}&from={start}&to={end}&apikey={k}")
    rows = j if isinstance(j, list) else (j or {}).get("historical") or []
    out = [(str(x["date"])[:10], float(x["close"]), int(x.get("volume") or 0)) for x in rows
           if x.get("date") and x.get("close") is not None]
    return sorted(out)


def _alpaca_daily(t, start, end):
    kid, sec = os.environ.get("ALPACA_KEY_ID"), os.environ.get("ALPACA_SECRET_KEY")
    if not (kid and sec):
        return []
    out, token = [], None
    for _ in range(20):
        q = {"timeframe": "1Day", "start": start, "end": end, "adjustment": "split", "feed": "iex", "limit": 10000}
        if token:
            q["page_token"] = token
        j = _get(f"https://data.alpaca.markets/v2/stocks/{t}/bars?" + urllib.parse.urlencode(q),
                 headers={"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec}, tries=3)
        for b in (j or {}).get("bars") or []:
            # IEX volume is a fraction of consolidated volume: report 0 so no page publishes it as real volume
            out.append((str(b["t"])[:10], float(b["c"]), 0))
        token = (j or {}).get("next_page_token")
        if not token:
            break
    return sorted(out)


# Cutover diff 2026-11-10 (_price_cutover_diff.json): 17,349 common closes on 63 tickers; 87 differ by >0.5%.
# 86 are AZN, every one dated 2025-07-29 .. 2026-01-30 (up to 5.0%), and none after AstraZeneca's ordinary shares
# replaced its ADRs on the NYSE on 2026-02-02: FMP's pre-listing series is not the traded ADR close that Polygon
# recorded. Before the date below, AZN closes come ONLY from the recorded Polygon series in stock_runup_cache.json;
# a day it lacks is dropped (a window that needs it is then incomplete and skipped, never filled from the bad series).
# The 87th is one BAYRY day (-0.56%, OTC ADR) and is left as FMP reports it.
RECORDED_BEFORE = {"AZN": "2026-02-02"}


def _recorded(t):
    try:
        c = json.load(open(os.path.join(HERE, "stock_runup_cache.json"), encoding="utf-8")).get(t) or []
        return {d: float(x) for d, x, *_ in c}
    except Exception:  # noqa: BLE001
        return {}


def _apply_recorded(t, rows):
    cut = RECORDED_BEFORE.get(str(t).upper())
    if not cut or not rows:
        return rows
    rec = _recorded(str(t).upper())
    out = [(d, rec[d], v) for d, c, v in rows if d < cut and d in rec]
    return out + [r for r in rows if r[0] >= cut]


def daily(ticker, start, end=None):
    """[(iso_date, close, volume)] ascending, split-adjusted. [] only when every configured feed returns nothing."""
    start = str(start)[:10]
    end = str(end or _eastern_today().isoformat())[:10]
    key = (str(ticker).upper(), start, end)
    if key in _cache:
        return _cache[key]
    for name, fn in (("FMP", _fmp_daily), ("Alpaca", _alpaca_daily)):
        rows = fn(ticker, start, end)
        rows = _apply_recorded(ticker, rows)
        if rows:
            STATS[name] += 1
            _served[key[0]] = name
            _cache[key] = rows
            return rows
    STATS["miss"] += 1
    _served[key[0]] = None
    _cache[key] = []
    return []


def closes(ticker, start, end=None):
    return [(d, c) for d, c, _ in daily(ticker, start, end)]


def source_of(ticker):
    return _served.get(str(ticker).upper())


def quotes(tickers):
    """{ticker: {"price", "volume"}} from one FMP batch call per 100 symbols."""
    k, out, ts = _fmp_key(), {}, [t for t in dict.fromkeys(str(t).upper() for t in tickers if t)]
    if not k:
        return out
    for i in range(0, len(ts), 100):
        chunk = ts[i:i + 100]
        back = {_fmp_symbol(t): t for t in chunk}
        j = _get(f"{FMP}batch-quote-short?symbols={','.join(back)}&apikey={k}") or []
        for x in j if isinstance(j, list) else []:
            t = back.get(str(x.get("symbol", "")).upper())
            if t and x.get("price") is not None:
                out[t] = {"price": float(x["price"]), "volume": int(x.get("volume") or 0)}
    return out


def market_caps(tickers):
    k, out, ts = _fmp_key(), {}, [t for t in dict.fromkeys(str(t).upper() for t in tickers if t)]
    if not k:
        return out
    for i in range(0, len(ts), 100):
        chunk = ts[i:i + 100]
        back = {_fmp_symbol(t): t for t in chunk}
        j = _get(f"{FMP}market-capitalization-batch?symbols={','.join(back)}&apikey={k}") or []
        for x in j if isinstance(j, list) else []:
            t = back.get(str(x.get("symbol", "")).upper())
            if t and x.get("marketCap"):
                out[t] = float(x["marketCap"])
    return out


def _eastern_today():
    try:
        from site_dates import eastern_today
        return eastern_today()
    except Exception:  # noqa: BLE001
        return dt.date.today()


def summary():
    return (f"price_source: {STATS['FMP']} series from FMP, {STATS['Alpaca']} Alpaca fallback, "
            f"{STATS['miss']} with no data; {STATS['calls']} HTTP calls")
