#!/usr/bin/env python3
"""
SURGE STUDY - PHASE 2: intraday 30-min volume vs SAME-DAY continuation.
Reads surge_events_2yr.csv (Phase 1). For each surge event:
  - pulls that day's 30-min bars (regular session),
  - computes early-session volume normalized by point-in-time 20-day ADV (trailing, pre-surge),
  - computes intraday continuation labels (did it hold / extend / close near high).
Writes surge_intraday_features.csv for Phase 3 analysis.

Point-in-time ADV mirrors what the live scanner sees at the open (its avgVolume ~= trailing ADV),
so the volume rule we learn here is directly usable live.

Informational / educational only - not investment advice. Odin Catalyst LLC.
"""
import os, csv, json, time, datetime as dt
import requests
from collections import defaultdict

FMP = os.getenv("FMP_API_KEY", "")
B   = "https://financialmodelingprep.com/stable"
IN_, OUT, PROG = "surge_events_2yr.csv", "surge_intraday_features.csv", "_phase2_progress.json"

def g(path, **p):
    p["apikey"] = FMP
    for _ in range(3):
        try:
            r = requests.get(f"{B}/{path}", params=p, timeout=30)
            if r.status_code == 200: return r.json()
            if r.status_code == 429: time.sleep(2.0); continue
            return None
        except Exception:
            time.sleep(1.0)
    return None

def adv_map(symbol, years=2):
    end = dt.date.today(); start = (end - dt.timedelta(days=int(365 * years))).isoformat()
    rows = g("historical-price-eod/full", symbol=symbol, **{"from": start, "to": end.isoformat()})
    if not isinstance(rows, list) or len(rows) < 21: return {}
    rows = sorted(rows, key=lambda r: r.get("date", ""))
    vols = [float(r.get("volume") or 0) for r in rows]; dates = [r.get("date") for r in rows]
    adv = {}
    for i in range(len(rows)):
        window = vols[max(0, i-20):i]          # 20 days BEFORE the surge day
        adv[dates[i]] = (sum(window)/len(window)) if window else 0
    return adv

def intraday(symbol, date):
    bars = g("historical-chart/30min", symbol=symbol, **{"from": date, "to": date})
    if not isinstance(bars, list) or len(bars) < 3: return None
    bars = sorted([b for b in bars if " " in b.get("date", "")], key=lambda b: b.get("date", ""))
    bars = [b for b in bars if "09:30" <= b["date"][11:16] <= "16:00"]
    if len(bars) < 3: return None
    o = float(bars[0].get("open") or 0)
    highs = [float(b.get("high") or 0) for b in bars]; lows = [float(b.get("low") or 0) for b in bars]
    closes = [float(b.get("close") or 0) for b in bars]; vols = [float(b.get("volume") or 0) for b in bars]
    dh, dl, dc = max(highs), min(lows), closes[-1]
    pre, post = max(highs[:2]), max(highs[2:]) if len(bars) > 2 else 0
    return dict(open=o, day_high=dh, day_low=dl, day_close=dc,
                first30_vol=int(vols[0]), first60_vol=int(sum(vols[:2])), total_vol=int(sum(vols)),
                n_bars=len(bars),
                close_in_range=round((dc-dl)/(dh-dl), 3) if dh > dl else 0,
                close_vs_open_pct=round(((dc-o)/o*100) if o > 0 else 0, 2),
                up_close=1 if dc > o else 0,
                new_high_after_1h=1 if post >= pre else 0,
                held_first_hour=1 if dc >= closes[1] else 0)

def main():
    if not FMP: raise SystemExit("set FMP_API_KEY")
    with open(IN_, encoding="utf-8") as f:
        events = list(csv.DictReader(f))
    by_sym = defaultdict(list)
    for e in events: by_sym[e["symbol"]].append(e)
    print(f"PHASE2: {len(events)} surge events across {len(by_sym)} tickers", flush=True)

    out, t0, n = [], time.time(), 0
    for si, (sym, evs) in enumerate(by_sym.items(), 1):
        adv = adv_map(sym)
        for e in evs:
            n += 1
            feat = intraday(sym, e["date"])
            if feat:
                a = adv.get(e["date"], 0) or 0
                out.append(dict(symbol=sym, date=e["date"], day_chg_pct=e["day_chg_pct"],
                    mcap_now=e.get("mcap_now"), sector=e.get("sector"), adv20=int(a),
                    first30_vol_x_adv=round(feat["first30_vol"]/a, 2) if a > 0 else "",
                    first60_vol_x_adv=round(feat["first60_vol"]/a, 2) if a > 0 else "",
                    total_vol_x_adv=round(feat["total_vol"]/a, 2) if a > 0 else "", **feat))
            time.sleep(0.08)
        if si % 25 == 0 or si == len(by_sym):
            with open(OUT, "w", newline="", encoding="utf-8") as f:
                if out:
                    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
            json.dump({"tickers_done": si, "tickers_total": len(by_sym), "events_done": n, "rows": len(out)},
                      open(PROG, "w"))
            print(f"  {si}/{len(by_sym)} tickers | {n} events | {len(out)} rows | {time.time()-t0:.0f}s", flush=True)
    print(f"DONE: {len(out)} intraday feature rows -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
