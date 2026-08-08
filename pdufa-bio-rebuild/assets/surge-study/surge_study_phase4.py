#!/usr/bin/env python3
"""
SURGE STUDY - PHASE 4: FORWARD continuation from the first-hour decision point.
For each surge event, re-pull 30-min bars and compute what you could actually act on at ~10:30:
  fh_ret_pct    = first-hour return (open -> 10:30 close)
  fh_vol_x_adv  = first-hour volume / 20-day ADV
  fwd_ret_pct   = forward return 10:30 close -> day close  (what an entry at 10:30 would capture)
  continued     = fwd_ret_pct > 0
Bins by first-hour volume and first-hour move; writes surge_forward_report.md.

IMPORTANT: events are still selected on close >= 30% (a same-day outcome), so this shows forward
dynamics WITHIN eventual big up-days and over-represents winners. The fully unbiased forward dataset is
built PROSPECTIVELY by the live scanner logging first-hour movers + outcomes (see SURGE_RADAR.md).
Informational / educational only - not investment advice.
"""
import os, csv, json, time, datetime as dt
import requests
from collections import defaultdict

FMP = os.getenv("FMP_API_KEY", "")
B = "https://financialmodelingprep.com/stable"
IN_, OUT, REPORT, PROG = "surge_events_2yr.csv", "surge_forward_features.csv", "surge_forward_report.md", "_phase4_progress.json"

def g(path, **p):
    p["apikey"] = FMP
    for _ in range(3):
        try:
            r = requests.get(f"{B}/{path}", params=p, timeout=30)
            if r.status_code == 200: return r.json()
            if r.status_code == 429: time.sleep(2); continue
            return None
        except Exception:
            time.sleep(1)
    return None

def adv_map(symbol, years=2):
    end = dt.date.today(); start = (end - dt.timedelta(days=int(365*years))).isoformat()
    rows = g("historical-price-eod/full", symbol=symbol, **{"from": start, "to": end.isoformat()})
    if not isinstance(rows, list) or len(rows) < 21: return {}
    rows = sorted(rows, key=lambda r: r.get("date", "")); vols = [float(r.get("volume") or 0) for r in rows]; dates = [r.get("date") for r in rows]
    return {dates[i]: (sum(vols[max(0, i-20):i]) / max(1, len(vols[max(0, i-20):i])) if i > 0 else 0) for i in range(len(rows))}

def bars_for(symbol, date):
    bars = g("historical-chart/30min", symbol=symbol, **{"from": date, "to": date})
    if not isinstance(bars, list): return None
    bars = sorted([b for b in bars if " " in b.get("date", "")], key=lambda b: b.get("date", ""))
    bars = [b for b in bars if "09:30" <= b["date"][11:16] <= "16:00"]
    return bars if len(bars) >= 3 else None

def main():
    if not FMP: raise SystemExit("set FMP_API_KEY")
    events = list(csv.DictReader(open(IN_, encoding="utf-8")))
    by = defaultdict(list); [by[e["symbol"]].append(e) for e in events]
    out, t0, n = [], time.time(), 0
    print(f"PHASE4: {len(events)} events / {len(by)} tickers", flush=True)
    for si, (sym, evs) in enumerate(by.items(), 1):
        adv = adv_map(sym)
        for e in evs:
            n += 1; bars = bars_for(sym, e["date"])
            if not bars: continue
            o = float(bars[0].get("open") or 0); fh_close = float(bars[1].get("close") or 0)
            fh_vol = sum(float(b.get("volume") or 0) for b in bars[:2]); dc = float(bars[-1].get("close") or 0)
            if o <= 0 or fh_close <= 0: continue
            a = adv.get(e["date"], 0) or 0
            out.append(dict(symbol=sym, date=e["date"],
                fh_ret_pct=round((fh_close-o)/o*100, 2),
                fh_vol_x_adv=round(fh_vol/a, 2) if a > 0 else "",
                fwd_ret_pct=round((dc-fh_close)/fh_close*100, 2),
                continued=1 if dc > fh_close else 0,
                continued_2pct=1 if (dc-fh_close)/fh_close*100 > 2 else 0,
                day_chg_pct=e["day_chg_pct"]))
            time.sleep(0.08)
        if si % 25 == 0 or si == len(by):
            with open(OUT, "w", newline="", encoding="utf-8") as f:
                if out:
                    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
            json.dump({"tickers": si, "total": len(by), "rows": len(out)}, open(PROG, "w"))
            print(f"  {si}/{len(by)} | {len(out)} rows | {time.time()-t0:.0f}s", flush=True)

    rows = [r for r in out if r["fh_vol_x_adv"] != ""]
    L = ["# Surge FORWARD study - continuation from the ~10:30 decision point", "",
         "_Informational / educational only - not investment advice._", "",
         f"Sample: {len(rows)} surge events. Question: entering at the first-hour mark on the observed "
         "move + volume, did price continue UP to the close?", "",
         "## By first-hour volume (x ADV)",
         "| 1st-hr vol / ADV | n | % continued | mean forward return % |", "|---|---|---|---|"]
    for lo, hi, lab in [(0,1,"<1x"),(1,2,"1-2x"),(2,5,"2-5x"),(5,10,"5-10x"),(10,9e9,"10x+")]:
        s = [r for r in rows if lo <= r["fh_vol_x_adv"] < hi]
        L.append(f"| {lab} | {len(s)} | {100*sum(r['continued'] for r in s)/len(s):.1f} | {sum(r['fwd_ret_pct'] for r in s)/len(s):.2f} |" if s else f"| {lab} | 0 | - | - |")
    L += ["", "## By first-hour move", "| 1st-hr move | n | % continued | mean forward return % |", "|---|---|---|---|"]
    for lo, hi, lab in [(-1e9,10,"<10%"),(10,25,"10-25%"),(25,50,"25-50%"),(50,1e9,"50%+")]:
        s = [r for r in rows if lo <= r["fh_ret_pct"] < hi]
        if s: L.append(f"| {lab} | {len(s)} | {100*sum(r['continued'] for r in s)/len(s):.1f} | {sum(r['fwd_ret_pct'] for r in s)/len(s):.2f} |")
    L += ["", "**Caveat:** still selected on close >= 30% (over-represents winners). The unbiased forward "
          "dataset is built prospectively by the live scanner logging first-hour movers + outcomes."]
    open(REPORT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"DONE phase4 -> {OUT}, {REPORT}", flush=True)

if __name__ == "__main__":
    main()
