#!/usr/bin/env python3
"""
SURGE STUDY - PHASE 5: MORNING RUNNER + EXIT-TIMING (open-triggered, no close-selection bias)
Strategy tested: catch a gap-up small-cap near the OPEN, ride it, sell fast (by ~noon).

Trigger (observable at 9:30 -> NO look-ahead): open gaps up >= GAP_MIN vs prior close.
For each event (entry = 09:30 open) we (a) map the morning path 09:30->12:00 and (b) simulate exit rules:
  - sell_30m_high     : exit at the first 30-min bar's high (optimistic upper bound)
  - exit_1000..1200   : exit at the close of each 30-min bar (fixed-time)
  - target_10 / _20   : take profit at +10% / +20% if tagged, else exit at noon
  - trail_10 / _15    : trailing stop of 10% / 15% off the running high
  - stop10_hold_noon  : hard -10% stop, else hold to noon
  - bracket_15_10     : take +15% or stop -10%, whichever first (stop checked first = conservative)
  - hold_to_close     : baseline (hold all day)
Reports mean/median/win-rate per rule so we can see which exit actually makes money, and how fast.

Universe: reuses surge_universe.csv (small/micro US <= $2B). Survivorship caveat: currently-listed only.
FMP 30-min bar 'date' = interval START (bar starting 09:30 closes at 10:00, etc.).
Trailing/stop fills are approximated at the stop level on 30-min bars (documented simplification).
Informational / educational only - not investment advice. Odin Catalyst LLC.
"""
import os, csv, json, time, argparse, datetime as dt
import requests

FMP = os.getenv("FMP_API_KEY", "")
B = "https://financialmodelingprep.com/stable"
GAP_MIN = 0.20
MIN_PRICE = 0.50
MIN_DOLLAR_ADV = 100_000
UNIV_FILE = "surge_universe.csv"
OUT, REPORT, PROG, CHART = "morning_events.csv", "morning_report.md", "_phase5_progress.json", "morning_exit_timing.png"
CKPTS  = ["10:00", "10:30", "11:00", "11:30", "12:00"]
STARTS = ["09:30", "10:00", "10:30", "11:00", "11:30"]
EXIT_ORDER = ["sell_30m_high","exit_1000","exit_1030","exit_1100","exit_1130","exit_1200",
              "target_10","target_20","trail_10","trail_15","stop10_hold_noon","bracket_15_10","hold_to_close"]

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

def daily(sym, years=2):
    end = dt.date.today(); start = (end - dt.timedelta(days=int(365*years))).isoformat()
    rows = g("historical-price-eod/full", symbol=sym, **{"from": start, "to": end.isoformat()})
    return sorted(rows, key=lambda r: r.get("date", "")) if isinstance(rows, list) else []

def intraday(sym, date):
    bars = g("historical-chart/30min", symbol=sym, **{"from": date, "to": date})
    if not isinstance(bars, list): return None
    bars = sorted([b for b in bars if " " in b.get("date", "")], key=lambda b: b.get("date", ""))
    bars = [b for b in bars if "09:30" <= b["date"][11:16] <= "15:30"]
    return bars if len(bars) >= 5 else None

def exit_rules(ohlc, entry, day_close):
    """ohlc = ordered list of (o,h,l,c) for morning bars (closes -> 10:00..12:00)."""
    highs = [b[1] for b in ohlc]; lows = [b[2] for b in ohlc]; closes = [b[3] for b in ohlc]
    noon = closes[-1]
    r = {}
    r["sell_30m_high"] = (highs[0]-entry)/entry*100
    for i, lab in enumerate(CKPTS):
        r["exit_"+lab.replace(":","")] = (closes[i]-entry)/entry*100 if i < len(closes) else (noon-entry)/entry*100
    for tgt in (10, 20):
        hit = any(h >= entry*(1+tgt/100) for h in highs)
        r[f"target_{tgt}"] = float(tgt) if hit else (noon-entry)/entry*100
    for tr in (10, 15):
        run, out_r = entry, None
        for (o, h, l, c) in ohlc:
            run = max(run, h)
            stop = run*(1-tr/100)
            if l <= stop: out_r = (stop-entry)/entry*100; break
        r[f"trail_{tr}"] = out_r if out_r is not None else (noon-entry)/entry*100
    st = next((-10.0 for (o, h, l, c) in ohlc if l <= entry*0.90), None)
    r["stop10_hold_noon"] = st if st is not None else (noon-entry)/entry*100
    br = None
    for (o, h, l, c) in ohlc:
        if l <= entry*0.90: br = -10.0; break
        if h >= entry*1.15: br = 15.0; break
    r["bracket_15_10"] = br if br is not None else (noon-entry)/entry*100
    r["hold_to_close"] = (day_close-entry)/entry*100
    return r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-tickers", type=int, default=0)
    ap.add_argument("--gap-min", type=float, default=GAP_MIN)
    a = ap.parse_args()
    if not FMP: raise SystemExit("set FMP_API_KEY")
    gmin = a.gap_min
    syms = [r["symbol"] for r in csv.DictReader(open(UNIV_FILE, encoding="utf-8"))]
    if a.max_tickers: syms = syms[:a.max_tickers]
    print(f"PHASE5: {len(syms)} tickers, gap >= {gmin*100:.0f}%, entry=open, exit-timing sim ON", flush=True)

    out, t0, ngap = [], time.time(), 0
    for si, sym in enumerate(syms, 1):
        rows = daily(sym)
        if len(rows) < 25: continue
        vols = [float(r.get("volume") or 0) for r in rows]
        for i in range(1, len(rows)):
            prev_c = float(rows[i-1].get("close") or 0); op = float(rows[i].get("open") or 0)
            if prev_c <= 0 or op < MIN_PRICE: continue
            gap = (op - prev_c)/prev_c
            adv = sum(vols[max(0, i-20):i]) / max(1, len(vols[max(0, i-20):i]))
            if gap < gmin or adv*op < MIN_DOLLAR_ADV: continue
            ngap += 1
            date = rows[i].get("date"); day_close = float(rows[i].get("close") or 0)
            bars = intraday(sym, date)
            if not bars: continue
            bt = {b["date"][11:16]: b for b in bars}
            morn = [bt[st] for st in STARTS if st in bt]
            if len(morn) < 3: continue
            o = float(morn[0].get("open") or 0)
            if o <= 0: continue
            ohlc = [(float(b.get("open") or 0), float(b.get("high") or 0),
                     float(b.get("low") or 0), float(b.get("close") or 0)) for b in morn]
            highs = [b[1] for b in ohlc]; lows = [b[2] for b in ohlc]
            fh_vol = sum(float(bt[st].get("volume") or 0) for st in ("09:30", "10:00") if st in bt)
            hi = max(highs); hi_idx = highs.index(hi)
            row = dict(symbol=sym, date=date, open=round(o, 4), gap_pct=round(gap*100, 1), adv20=int(adv),
                       fh_vol_x_adv=round(fh_vol/adv, 2) if adv > 0 else "",
                       mfe_open_pct=round((hi-o)/o*100, 2), mfe_by=CKPTS[hi_idx] if hi_idx < len(CKPTS) else "12:00",
                       mae_open_pct=round((min(lows)-o)/o*100, 2),
                       green_noon=1 if (len(ohlc) >= 5 and ohlc[4][3] > o) else 0)
            row.update({k: round(v, 2) for k, v in exit_rules(ohlc, o, day_close).items()})
            out.append(row)
            time.sleep(0.05)
        if si % 25 == 0 or si == len(syms):
            with open(OUT, "w", newline="", encoding="utf-8") as f:
                if out:
                    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
            json.dump({"tickers": si, "total": len(syms), "gap_events": ngap, "rows": len(out)}, open(PROG, "w"))
            print(f"  {si}/{len(syms)} | {ngap} gap-ups | {len(out)} rows | {time.time()-t0:.0f}s", flush=True)

    # ---------------- analysis ----------------
    import statistics as st
    rows = out
    n = len(rows)
    def agg(key):
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        if not vals: return None
        return dict(mean=round(st.mean(vals), 2), median=round(st.median(vals), 2),
                    win=round(100*sum(1 for v in vals if v > 0)/len(vals), 1))
    exit_stats = {k: agg(k) for k in EXIT_ORDER}

    L = ["# Morning-Runner + Exit-Timing study", "",
         "_Informational / educational only - not investment advice._", "",
         f"Trigger: open gaps up >= {gmin*100:.0f}% vs prior close (seen at 9:30, no close-selection bias). "
         f"Entry = 09:30 open. Sample: {n} gap-up events, small/micro US, ~2 yrs.", "",
         "## Which exit made money? (return per trade, entry at the open)",
         "| Exit rule | mean % | median % | win rate |", "|---|---|---|---|"]
    nice = {"sell_30m_high":"Sell at 30-min high (ideal cap)","exit_1000":"Exit 10:00","exit_1030":"Exit 10:30",
            "exit_1100":"Exit 11:00","exit_1130":"Exit 11:30","exit_1200":"Exit 12:00 (noon)",
            "target_10":"+10% target, else noon","target_20":"+20% target, else noon",
            "trail_10":"10% trailing stop","trail_15":"15% trailing stop",
            "stop10_hold_noon":"-10% stop, else noon","bracket_15_10":"+15% / -10% bracket",
            "hold_to_close":"Hold to close (baseline)"}
    for k in EXIT_ORDER:
        s = exit_stats[k]
        if s: L.append(f"| {nice[k]} | {s['mean']:+} | {s['median']:+} | {s['win']}% |")
    # best by mean (exclude the idealized sell_30m_high)
    real = [(k, exit_stats[k]["mean"]) for k in EXIT_ORDER if k != "sell_30m_high" and exit_stats[k]]
    real.sort(key=lambda x: -x[1])
    if real:
        L += ["", f"**Best realistic expectancy:** {nice[real[0][0]]} ({real[0][1]:+}% mean/trade). "
              f"Worst: {nice[real[-1][0]]} ({real[-1][1]:+}%)."]
    from collections import Counter
    tc = Counter(r["mfe_by"] for r in rows if r.get("mfe_by"))
    L += ["", "## When the morning high (best exit) happens",
          "| by | share |", "|---|---|"]
    for ck in CKPTS:
        L.append(f"| {ck} | {round(100*tc.get(ck,0)/n,1) if n else 0}% |")
    L += ["", "**Caveats:** survivorship (currently-listed only -> real numbers likely lower); entry at the exact "
          "open and stop/trail fills are optimistic on micro-caps (spreads, gaps, halts); the idealized "
          "'sell at 30-min high' is an unattainable upper bound shown only for reference. Before-cost figures."]
    open(REPORT, "w", encoding="utf-8").write("\n".join(L) + "\n")

    # chart: mean return per exit rule
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        ks = [k for k in EXIT_ORDER if exit_stats[k]]
        means = [exit_stats[k]["mean"] for k in ks]
        cols = ["#2f9e44" if m > 0 else "#e03131" for m in means]
        plt.figure(figsize=(9, 4.2), dpi=140)
        plt.bar([nice[k] for k in ks], means, color=cols, zorder=3)
        plt.axhline(0, color="#333", lw=0.8)
        plt.ylabel("mean return per trade (%)"); plt.title("Morning exit rules: mean return per trade (before costs)")
        plt.xticks(rotation=45, ha="right", fontsize=7.5); plt.grid(axis="y", alpha=0.3, zorder=0)
        plt.tight_layout(); plt.savefig(CHART); plt.close()
    except Exception as e:
        print("chart skipped:", e, flush=True)
    print(f"DONE phase5: {n} events -> {OUT}, {REPORT}", flush=True)

if __name__ == "__main__":
    main()
