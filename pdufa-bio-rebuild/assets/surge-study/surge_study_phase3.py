#!/usr/bin/env python3
"""
SURGE STUDY - PHASE 3: analysis + report.
Reads surge_intraday_features.csv (Phase 2). Answers: does higher EARLY-session volume (relative to the
stock's normal 20-day volume) predict the surge CONTINUING up the same day? Bins events by early-volume
multiple and reports continuation rates, then writes a chart + markdown report.

Informational / educational only - not investment advice. Odin Catalyst LLC.
"""
import csv, json, math, statistics as st

IN_ = "surge_intraday_features.csv"
REPORT = "surge_study_report.md"
CHART = "surge_volume_vs_continuation.png"
SUMMARY = "surge_study_summary.json"

def num(x):
    try: return float(x)
    except: return None

def main():
    rows = []
    with open(IN_, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            v = num(r.get("first60_vol_x_adv"))
            if v is None: continue
            r["_v60"] = v
            r["_up"] = int(r.get("up_close") or 0)
            r["_held"] = int(r.get("held_first_hour") or 0)
            r["_ext"] = int(r.get("new_high_after_1h") or 0)
            r["_cir"] = num(r.get("close_in_range")) or 0
            r["_cvo"] = num(r.get("close_vs_open_pct")) or 0
            rows.append(r)
    N = len(rows)
    if N == 0:
        print("no rows"); return

    bins = [(0,0.5),(0.5,1),(1,2),(2,5),(5,10),(10,1e9)]
    labels = ["<0.5x","0.5-1x","1-2x","2-5x","5-10x","10x+"]
    table = []
    for (lo,hi),lab in zip(bins,labels):
        sub = [r for r in rows if lo <= r["_v60"] < hi]
        if not sub: table.append(dict(bin=lab,n=0)); continue
        table.append(dict(bin=lab, n=len(sub),
            pct_up_close=round(100*sum(r["_up"] for r in sub)/len(sub),1),
            pct_held_1h=round(100*sum(r["_held"] for r in sub)/len(sub),1),
            pct_new_high_after_1h=round(100*sum(r["_ext"] for r in sub)/len(sub),1),
            mean_close_in_range=round(st.mean(r["_cir"] for r in sub),3),
            mean_close_vs_open_pct=round(st.mean(r["_cvo"] for r in sub),2)))

    overall = dict(n=N,
        pct_up_close=round(100*sum(r["_up"] for r in rows)/N,1),
        pct_held_1h=round(100*sum(r["_held"] for r in rows)/N,1),
        mean_close_in_range=round(st.mean(r["_cir"] for r in rows),3),
        mean_close_vs_open_pct=round(st.mean(r["_cvo"] for r in rows),2))

    # simple correlation: early volume multiple vs close_in_range
    xs = [r["_v60"] for r in rows]; ys = [r["_cir"] for r in rows]
    try:
        mx, my = st.mean(xs), st.mean(ys)
        cov = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
        corr = cov / (math.sqrt(sum((x-mx)**2 for x in xs)) * math.sqrt(sum((y-my)**2 for y in ys)) + 1e-9)
    except Exception:
        corr = float("nan")

    json.dump({"overall": overall, "by_early_volume_bin": table, "corr_v60_vs_close_in_range": round(corr,3)},
              open(SUMMARY,"w"), indent=2)

    # chart (optional)
    chart_line = ""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        labs = [t["bin"] for t in table if t.get("n")]
        held = [t["pct_held_1h"] for t in table if t.get("n")]
        newh = [t["pct_new_high_after_1h"] for t in table if t.get("n")]
        x = range(len(labs))
        plt.figure(figsize=(9,5))
        plt.plot(list(x), held, "o-", label="% held first-hour gain")
        plt.plot(list(x), newh, "s-", label="% new high after 1st hour")
        plt.xticks(list(x), labs); plt.ylim(0,100)
        plt.xlabel("First-hour volume vs 20-day ADV (x)"); plt.ylabel("continuation %")
        plt.title("Surge continuation vs early-session volume  (informational only)")
        plt.legend(); plt.grid(alpha=0.3); plt.tight_layout(); plt.savefig(CHART, dpi=110)
        chart_line = f"\n![chart]({CHART})\n"
    except Exception as e:
        chart_line = f"\n_(chart skipped: {e})_\n"

    # markdown report
    hdr = "| early-vol (1st hr / ADV) | n | % up close | % held 1h gain | % new high after 1h | mean close-in-range | mean close vs open % |\n"
    hdr += "|---|---|---|---|---|---|---|\n"
    for t in table:
        if not t.get("n"): 
            hdr += f"| {t['bin']} | 0 | - | - | - | - | - |\n"; continue
        hdr += (f"| {t['bin']} | {t['n']} | {t['pct_up_close']} | {t['pct_held_1h']} | "
                f"{t['pct_new_high_after_1h']} | {t['mean_close_in_range']} | {t['mean_close_vs_open_pct']} |\n")

    with open(REPORT,"w",encoding="utf-8") as f:
        f.write(f"""# Surge Volume -> Continuation Study

_Informational and educational only - not investment advice._

**Sample:** {N} single-day surge events (>= 30% close-to-close) in small/micro-cap US stocks over ~2 years,
with intraday 30-min bars and point-in-time 20-day average daily volume (ADV).

## Question
Does heavier **early-session volume** (first hour, relative to the stock's normal ADV) predict the surge
**continuing up the same day** rather than fading?

## Result — continuation by first-hour volume (x ADV)
{hdr}
**Overall:** {overall['pct_up_close']}% closed above the open; {overall['pct_held_1h']}% held their first-hour gain;
mean close-in-range {overall['mean_close_in_range']} (0=low, 1=high). Correlation(first-hour vol x ADV, close-in-range) = {round(corr,3)}.
{chart_line}
## How to read it
"Held first-hour gain" and "new high after the first hour" are the continuation signals. If continuation %
rises with the early-volume multiple, that multiple is the "volume it takes to keep trending up" — the live
scanner can flag names crossing that threshold near the open.

## Red-team caveats (read before trusting this)
- **Survivorship:** the universe is *currently active* small/micro names, so surges from since-delisted tickers
  (many pump-and-dumps that faded) are missing. Real continuation rates are likely **lower** than shown.
- **No guarantee:** these are historical base rates, not promises. Regime, liquidity, and news dominate any
  single event.
- **Look-ahead:** ADV is trailing (pre-surge) and intraday is same-day, so the signal is usable at the open;
  but slippage/spread on micro names can erase edge. Verify tradeable liquidity per name.
- **Split artifacts:** a few "surges" may be raw-price split effects; these show no real intraday volume ramp.
""")
    print(f"DONE: wrote {REPORT}, {SUMMARY}" + (f", {CHART}" if "png" in chart_line else ""), flush=True)
    print(json.dumps({"overall": overall, "bins": table}, indent=2))

if __name__ == "__main__":
    main()
