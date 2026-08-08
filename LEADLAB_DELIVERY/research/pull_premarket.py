#!/usr/bin/env python3
"""LEADLAB — pull FMP 1-min EXTENDED-hours bars for a sample of gap-up ticker-days
(winners AND losers from universe.csv) and extract LEADING signals that are known
BEFORE the regular-session move: pre-market gap/high, pre-market rel-vol, and the
opening 1/5-minute velocity. FMP has no harsh rate limit, so this is fast.

Writes premarket_features.csv keyed by (symbol,date) for the sampled events."""
import os, sys, json, csv, time, urllib.request, urllib.error, datetime

HERE = os.path.dirname(os.path.abspath(__file__))

def load_key():
    p = os.path.join(HERE, "..", "..", "..", "Odin Perfection", ".env_master")
    for line in open(p):
        if line.startswith("FMP_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("no fmp key")

FMP = load_key()
CACHE = os.path.join(HERE, "cache_fmp1min")
os.makedirs(CACHE, exist_ok=True)

def bars(sym, date):
    fn = os.path.join(CACHE, "%s_%s.json" % (sym, date))
    if os.path.exists(fn):
        return json.load(open(fn))
    url = ("https://financialmodelingprep.com/stable/historical-chart/1min?symbol="
           + sym + "&from=" + date + "&to=" + date + "&extended=true&apikey=" + FMP)
    for attempt in range(2):
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                d = json.load(r)
            if isinstance(d, list):
                json.dump(d, open(fn, "w"))
                return d
            return []
        except Exception:
            time.sleep(1)
    return []

def hhmm(bar):
    return bar["date"][11:16]

def feats(sym, date, prev_close):
    """Return leading features computable pre-open + at the open, all vs prev_close."""
    b = bars(sym, date)
    if not b:
        return None
    b = sorted(b, key=lambda x: x["date"])  # ascending time
    pm = [x for x in b if hhmm(x) < "09:30"]        # pre-market 04:00-09:29
    rg = [x for x in b if "09:30" <= hhmm(x) < "16:00"]  # regular session
    if not rg:
        return None
    pm_vol = sum(x["volume"] for x in pm)
    pm_high = max((x["high"] for x in pm), default=0)
    pm_last = pm[-1]["close"] if pm else None            # ~09:29 price
    # snapshots at fixed pre-open clocks (what a scanner would see live)
    def price_at(cut):
        elig = [x for x in pm if hhmm(x) <= cut]
        return elig[-1]["close"] if elig else None
    def vol_by(cut):
        return sum(x["volume"] for x in pm if hhmm(x) <= cut)
    p0800, p0900 = price_at("08:00"), price_at("09:00")
    v0800, v0900 = vol_by("08:00"), vol_by("09:00")
    open_px = rg[0]["open"]
    # opening velocity: first 1 and 5 minutes of regular session
    first1 = rg[0]
    first5 = rg[:5]
    r1_ret = (first1["close"] / open_px - 1.0) if open_px else 0
    r5_ret = (first5[-1]["close"] / open_px - 1.0) if open_px and first5 else 0
    r5_vol = sum(x["volume"] for x in first5)
    def pct(a):
        return round((a / prev_close - 1.0) * 100, 2) if (prev_close and a) else ""
    return {
        "symbol": sym, "date": date, "prev_close": prev_close,
        "pm_bars": len(pm), "pm_vol": int(pm_vol),
        "pm_high_pct": pct(pm_high),
        "pm_0800_pct": pct(p0800), "pm_0900_pct": pct(p0900),
        "pm_vol_0800": int(v0800), "pm_vol_0900": int(v0900),
        "pm_last_pct": pct(pm_last),
        "open_pct": pct(open_px),
        "r1_ret_pct": round(r1_ret * 100, 2), "r5_ret_pct": round(r5_ret * 100, 2),
        "r5_vol": int(r5_vol),
    }

def main():
    src = os.path.join(HERE, "sample_events.csv")
    rows = list(csv.DictReader(open(src)))
    out = os.path.join(HERE, "premarket_features.csv")
    done = set()
    if os.path.exists(out):
        for r in csv.DictReader(open(out)):
            done.add((r["symbol"], r["date"]))
    fields = ["symbol", "date", "prev_close", "pm_bars", "pm_vol", "pm_high_pct",
              "pm_0800_pct", "pm_0900_pct", "pm_vol_0800", "pm_vol_0900",
              "pm_last_pct", "open_pct", "r1_ret_pct", "r5_ret_pct", "r5_vol"]
    write_header = not os.path.exists(out)
    f = open(out, "a", newline="")
    w = csv.DictWriter(f, fieldnames=fields)
    if write_header:
        w.writeheader()
    n = 0
    limit = int(os.environ.get("LIMIT", "10000"))
    for r in rows:
        key = (r["symbol"], r["date"])
        if key in done:
            continue
        ft = feats(r["symbol"], r["date"], float(r["prev_close"]))
        if ft:
            w.writerow(ft); f.flush(); n += 1
        done.add(key)
        if n >= limit:
            break
    print("pulled premarket features for %d new events" % n)

main()
