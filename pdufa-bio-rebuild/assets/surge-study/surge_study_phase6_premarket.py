#!/usr/bin/env python3
"""
SURGE STUDY - PHASE 6: PRE-MARKET edge test
Reads gap-up events (from Phase 5's morning_events.csv), pulls EXTENDED-HOURS 30-min bars
(FMP historical-chart/30min?extended=true), and asks: is the advantage in pre-market?

Per event (prev_close derived from open & gap):
  pm_high_pct        : pre-market peak move vs prior close
  pm_vol_x_adv       : pre-market volume / 20-day ADV
  pm_share_of_move   : % of the whole prev_close->day-high move already made by the PRE-MARKET high
  pm0900_to_open     : return from ~09:00 pre-market price to the 09:30 open (the "get in early" leg)
  pm0900_to_mornhigh : return from ~09:00 to the morning (<=12:00) high (ideal early-entry upper bound)
  open_to_mornhigh   : return from the 09:30 open to the morning high (open-entry upper bound, for comparison)

Big caveat baked into the report: micro-cap PRE-MARKET liquidity is thin - prints can be a few shares,
spreads are huge, and fills/exits are often impossible. These are theoretical, before-cost, upper-bound
numbers. Informational / educational only - not investment advice. Odin Catalyst LLC.
"""
import os, csv, json, time, argparse
import requests

FMP = os.getenv("FMP_API_KEY", "")
B = "https://financialmodelingprep.com/stable"
OUT, REPORT, PROG = "premarket_events.csv", "premarket_report.md", "_phase6_progress.json"

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

def ext_bars(sym, date):
    j = g("historical-chart/30min", symbol=sym, **{"from": date, "to": date, "extended": "true"})
    if not isinstance(j, list): return None
    return sorted([b for b in j if " " in b.get("date", "")], key=lambda b: b["date"])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events-file", default="morning_events.csv")
    ap.add_argument("--max-events", type=int, default=0)
    a = ap.parse_args()
    if not FMP: raise SystemExit("set FMP_API_KEY")
    ev = list(csv.DictReader(open(a.events_file, encoding="utf-8")))
    if a.max_events: ev = ev[:a.max_events]
    print(f"PHASE6: {len(ev)} events, pulling extended-hours bars", flush=True)

    out, t0, ncov = [], time.time(), 0
    for i, e in enumerate(ev, 1):
        sym, date = e["symbol"], e["date"]
        try:
            op = float(e["open"]); gap = float(e["gap_pct"]); adv = float(e.get("adv20") or 0)
        except Exception:
            continue
        prev_close = op / (1 + gap/100) if gap > -100 else 0
        bars = ext_bars(sym, date)
        if bars:
            pm = [b for b in bars if b["date"][11:16] < "09:30"]
            reg = [b for b in bars if "09:30" <= b["date"][11:16] <= "15:30"]
            if reg and prev_close > 0:
                openp = float(reg[0].get("open") or 0)
                pm_high = max((float(b.get("high") or 0) for b in pm), default=0)
                pm_vol = sum(float(b.get("volume") or 0) for b in pm)
                day_high = max(float(b.get("high") or 0) for b in reg)
                morn = [b for b in reg if b["date"][11:16] <= "11:30"]
                morn_high = max((float(b.get("high") or 0) for b in morn), default=openp)
                px0900 = next((float(b.get("open") or 0) for b in pm if b["date"][11:16] == "09:00"), None)
                if px0900 is None and pm:
                    px0900 = float(pm[-1].get("close") or 0)
                if openp > 0:
                    ncov += 1 if pm else 0
                    out.append(dict(
                        symbol=sym, date=date, has_pm=1 if pm else 0,
                        pm_high_pct=round((pm_high-prev_close)/prev_close*100, 1) if pm_high > 0 else "",
                        pm_vol_x_adv=round(pm_vol/adv, 2) if adv > 0 else "",
                        pm_share_of_move=round((pm_high-prev_close)/(day_high-prev_close)*100, 1) if (day_high-prev_close) > 0 and pm_high > 0 else "",
                        pm0900_to_open=round((openp-px0900)/px0900*100, 2) if px0900 else "",
                        pm0900_to_mornhigh=round((morn_high-px0900)/px0900*100, 2) if px0900 else "",
                        open_to_mornhigh=round((morn_high-openp)/openp*100, 2)))
        if i % 50 == 0 or i == len(ev):
            with open(OUT, "w", newline="", encoding="utf-8") as f:
                if out:
                    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
            json.dump({"done": i, "total": len(ev), "rows": len(out), "with_pm": ncov}, open(PROG, "w"))
            print(f"  {i}/{len(ev)} | {len(out)} rows | {ncov} w/ pre-mkt | {time.time()-t0:.0f}s", flush=True)
        time.sleep(0.05)

    import statistics as st
    def med(k, sub):
        v = [r[k] for r in sub if isinstance(r.get(k), (int, float))]
        return round(st.median(v), 1) if v else None
    def mean(k, sub):
        v = [r[k] for r in sub if isinstance(r.get(k), (int, float))]
        return round(st.mean(v), 1) if v else None
    def winr(k, sub):
        v = [r[k] for r in sub if isinstance(r.get(k), (int, float))]
        return round(100*sum(1 for x in v if x > 0)/len(v), 1) if v else None
    pmrows = [r for r in out if r["has_pm"] == 1]
    n, npm = len(out), len(pmrows)
    L = ["# Pre-market edge test", "", "_Informational / educational only - not investment advice._", "",
         f"Sample: {n} gap-up events; {npm} ({round(100*npm/n,0) if n else 0}%) had usable pre-market prints.", "",
         "## Is the move already spent by 9:30?",
         f"- Median **pre-market share of the whole move** (prev close -> day high): **{med('pm_share_of_move',pmrows)}%** "
         "(how much of the run is already done before the open).",
         "", "## Does getting in pre-market beat buying the open?",
         "| Entry -> exit | mean % | median % | win rate |", "|---|---|---|---|",
         f"| ~09:00 pre-mkt -> 09:30 open | {mean('pm0900_to_open',pmrows):+} | {med('pm0900_to_open',pmrows):+} | {winr('pm0900_to_open',pmrows)}% |",
         f"| ~09:00 pre-mkt -> morning high (ideal) | {mean('pm0900_to_mornhigh',pmrows):+} | {med('pm0900_to_mornhigh',pmrows):+} | {winr('pm0900_to_mornhigh',pmrows)}% |",
         f"| 09:30 open -> morning high (ideal) | {mean('open_to_mornhigh',out):+} | {med('open_to_mornhigh',out):+} | {winr('open_to_mornhigh',out)}% |",
         "", "**Read:** if 'pre-mkt -> open' is solidly positive and pre-market share of move is high, the run is "
         "mostly a pre-market event and the open-buyer is late. But the morning-high columns are *unattainable* "
         "upper bounds (you can't sell the exact high).",
         "", "**Hard caveat:** micro-cap PRE-MARKET is extremely thin - quotes can be a few shares wide, many "
         "'prints' aren't executable size, and you frequently can't get in or out at these prices. Treat pre-market "
         "numbers as the most optimistic/least-realizable in the whole study. Plus survivorship (currently-listed only)."]
    open(REPORT, "w", encoding="utf-8").write("\n".join(str(x) for x in L) + "\n")
    print(f"DONE phase6: {n} events ({npm} w/ pre-mkt) -> {OUT}, {REPORT}", flush=True)

if __name__ == "__main__":
    main()
