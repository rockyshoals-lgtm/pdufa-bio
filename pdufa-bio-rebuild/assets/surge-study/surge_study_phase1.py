#!/usr/bin/env python3
"""
SURGE STUDY - PHASE 1 (v2): per-ticker daily scan
Find every small/micro-cap US name that jumped >= 30% in a single day over the last ~2 years.

Universe: FMP company-screener (mcap $10M-$2B, price >= $0.50, non-ETF, actively trading, NASDAQ/NYSE/AMEX).
Detection: FMP historical-price-eod/full (per-ticker, NOT the rate-limited bulk endpoint) -> consecutive
close-to-close daily moves >= 30%.

CAVEATS (see report): universe is CURRENTLY active + currently small/micro -> excludes delisted names that
surged then died (survivorship bias) and names that were small during a past surge but are large now.
Split artifacts are possible from raw close; real surges are confirmed by Phase 2 intraday volume.

Informational / educational only - not investment advice. Odin Catalyst LLC.
"""
import os, csv, json, time, argparse, datetime as dt
import requests

FMP = os.getenv("FMP_API_KEY", "")
B   = "https://financialmodelingprep.com/stable"
SURGE = 0.30
MIN_PRICE = 0.50
MIN_DOLLAR_VOL = 100_000
MCAP_MIN, MCAP_MAX = 10_000_000, 2_000_000_000
OUT, UNIV, PROG = "surge_events_2yr.csv", "surge_universe.csv", "_phase1_progress.json"

def g(path, **p):
    p["apikey"] = FMP
    try:
        r = requests.get(f"{B}/{path}", params=p, timeout=30)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def build_universe():
    uni = {}
    for exch in ("NASDAQ", "NYSE", "AMEX"):
        j = g("company-screener", marketCapLowerThan=MCAP_MAX, marketCapMoreThan=MCAP_MIN,
              priceMoreThan=MIN_PRICE, isEtf="false", isFund="false",
              isActivelyTrading="true", exchange=exch, limit=10000) or []
        for x in j:
            s = x.get("symbol", "")
            if s and s not in uni:
                uni[s] = dict(symbol=s, name=x.get("companyName", ""), mcap=x.get("marketCap"),
                              sector=x.get("sector", ""), industry=x.get("industry", ""),
                              exch=x.get("exchangeShortName", ""))
    return uni

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=float, default=2.0)
    ap.add_argument("--max-tickers", type=int, default=0, help="0 = all (test with small N)")
    a = ap.parse_args()
    if not FMP: raise SystemExit("set FMP_API_KEY")

    end = dt.date.today(); start = (end - dt.timedelta(days=int(365 * a.years))).isoformat(); end = end.isoformat()
    uni = build_universe()
    with open(UNIV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "name", "mcap", "sector", "industry", "exch"])
        w.writeheader(); [w.writerow(v) for v in uni.values()]
    syms = list(uni)[: a.max_tickers] if a.max_tickers else list(uni)
    print(f"universe: {len(uni)} small/micro US tickers; scanning {len(syms)}", flush=True)

    events, t0 = [], time.time()
    for i, s in enumerate(syms, 1):
        rows = g("historical-price-eod/full", symbol=s, **{"from": start, "to": end})
        if isinstance(rows, list) and len(rows) > 1:
            rows = sorted(rows, key=lambda r: r.get("date", ""))
            for j in range(1, len(rows)):
                c0 = float(rows[j-1].get("close") or 0)
                r1 = rows[j]; c1 = float(r1.get("close") or 0); o1 = float(r1.get("open") or 0)
                v1 = float(r1.get("volume") or 0)
                if c0 > 0 and c1 >= MIN_PRICE and (c1 * v1) >= MIN_DOLLAR_VOL:
                    chg = (c1 - c0) / c0
                    if chg >= SURGE:
                        events.append(dict(symbol=s, date=r1.get("date"), prev_close=round(c0, 4),
                            open=o1, high=float(r1.get("high") or 0), low=float(r1.get("low") or 0),
                            close=c1, volume=int(v1), dollar_vol=round(c1 * v1),
                            day_chg_pct=round(chg * 100, 1),
                            intraday_pct=round(((c1 - o1) / o1 * 100) if o1 > 0 else 0, 1),
                            mcap_now=uni[s]["mcap"], sector=uni[s]["sector"], exch=uni[s]["exch"]))
        if i % 100 == 0 or i == len(syms):
            with open(OUT, "w", newline="", encoding="utf-8") as f:
                if events:
                    w = csv.DictWriter(f, fieldnames=list(events[0].keys())); w.writeheader(); w.writerows(events)
            json.dump({"i": i, "total": len(syms), "events": len(events)}, open(PROG, "w"))
            print(f"  {i}/{len(syms)} tickers | {len(events)} surges | {time.time()-t0:.0f}s", flush=True)
        time.sleep(0.1)
    print(f"DONE: {len(events)} surge events (>= {int(SURGE*100)}% single-day) -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
