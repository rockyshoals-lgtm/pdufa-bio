#!/usr/bin/env python3
"""LEADLAB — build the UNBIASED whole-market gap-up universe + outcomes from the
Polygon grouped-daily cache. This is the control group the old surge study lacked:
every ticker-day, winners AND losers, so we can measure the real base rate
P(surge | early signal) instead of only describing winners.

Outputs universe.csv: one row per (small/micro) ticker-day with an open gap,
trailing 20d ADV, rel-vol, and forward outcomes (did it become a big intraday/close move)."""
import os, json, csv, glob, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache_grouped")

# study universe filters (small/micro proxy without needing shares outstanding)
MIN_PRICE = 0.30
MAX_PRICE = 60.0          # most small/micro runners are low-priced; drops mega/large caps
MIN_DOLLAR_VOL = 50_000   # tradeable-ish liquidity floor on the event day
MIN_GAP = 0.03            # >=3% open gap to be a "gap-up" candidate a scanner would see
ADV_WINDOW = 20

def load_days():
    days = {}
    for fn in sorted(glob.glob(os.path.join(CACHE, "*.json"))):
        d = json.load(open(fn))
        if d.get("n", 0) == 0:
            continue
        days[d["date"]] = {r["T"]: r for r in d["results"]}
    return days

def main():
    days = load_days()
    dates = sorted(days.keys())
    print("loaded %d trading days: %s .. %s" % (len(dates), dates[0], dates[-1]))

    # trailing volume history per ticker for ADV
    rows = []
    for i, dt in enumerate(dates):
        if i < ADV_WINDOW:
            continue  # need trailing ADV and a prev close
        prev = dates[i - 1]
        window = dates[i - ADV_WINDOW:i]
        today = days[dt]
        for tkr, r in today.items():
            pr = days[prev].get(tkr)
            if not pr:
                continue
            prev_close = pr["c"]
            o, h, l, c, v = r["o"], r["h"], r["l"], r["c"], r["v"]
            if prev_close <= 0 or o <= 0:
                continue
            if not (MIN_PRICE <= o <= MAX_PRICE):
                continue
            dvol = c * v
            if dvol < MIN_DOLLAR_VOL:
                continue
            gap = o / prev_close - 1.0
            if gap < MIN_GAP:
                continue
            # trailing ADV (shares)
            vols = [days[w][tkr]["v"] for w in window if tkr in days[w]]
            if len(vols) < ADV_WINDOW // 2:
                continue
            adv = statistics.mean(vols)
            relvol = v / adv if adv > 0 else None
            # outcomes (all vs prev_close, the reference a gap scanner uses)
            hi_move = h / prev_close - 1.0        # best intraday move
            day_move = c / prev_close - 1.0       # close move
            intraday_from_open = c / o - 1.0      # open->close (the "ride the wave" trade)
            hi_from_open = h / o - 1.0
            rows.append({
                "date": dt, "symbol": tkr, "prev_close": round(prev_close, 4),
                "open": round(o, 4), "high": round(h, 4), "low": round(l, 4),
                "close": round(c, 4), "volume": int(v), "adv20": int(adv),
                "dollar_vol": int(dvol),
                "gap_pct": round(gap * 100, 2), "relvol": round(relvol, 2) if relvol else "",
                "hi_move_pct": round(hi_move * 100, 2),
                "day_move_pct": round(day_move * 100, 2),
                "intraday_open_pct": round(intraday_from_open * 100, 2),
                "hi_from_open_pct": round(hi_from_open * 100, 2),
                # outcome labels
                "surge25": int(hi_move >= 0.25),        # hit +25% vs prev close intraday
                "close_up": int(day_move > 0),
                "close_up15": int(day_move >= 0.15),
                "open_green_close": int(intraday_from_open > 0),
            })
    out = os.path.join(HERE, "universe.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("wrote %d gap-up ticker-days -> universe.csv" % len(rows))
    # quick base-rate sanity
    n = len(rows)
    s25 = sum(r["surge25"] for r in rows)
    print("base rate: P(intraday +25%% | >=3%% gap-up) = %.1f%% (n=%d)" % (100 * s25 / n, n))

main()
