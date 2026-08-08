#!/usr/bin/env python3
"""PHASE 7: strategy slices on the morning gap-up dataset (CSV-only, no API calls).
Reads morning_events.csv (Phase 5). Tests three ideas the user asked for:
  1) Confirmation entry - only take trades still green at 10:00 (open->10:00 > 0).
  2) Subset slicing - by gap size and early relative volume, to find any bucket that pays.
  3) Short side - shorting the open and covering intraday (= negated long returns).
Writes morning_slices_report.md. Informational/educational only - not investment advice."""
import csv, statistics as st
IN_, REPORT = "morning_events.csv", "morning_slices_report.md"

rows = []
for r in csv.DictReader(open(IN_, encoding="utf-8")):
    d = {}
    for k, v in r.items():
        try: d[k] = float(v)
        except Exception: d[k] = v
    rows.append(d)
n = len(rows)

def agg(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals: return None
    return (round(st.mean(vals), 2), round(st.median(vals), 2),
            round(100*sum(1 for x in vals if x > 0)/len(vals), 1), len(vals))
def line(label, vals):
    a = agg(vals)
    return f"| {label} | {a[0]:+} | {a[1]:+} | {a[2]}% | {a[3]} |" if a else f"| {label} | - | - | - | 0 |"
def col(k): return [r.get(k) for r in rows]

b = agg(col("exit_1200"))
L = ["# Morning-Runner strategy slices", "", "_Informational/educational only - not investment advice._", "",
     f"Sample: {n} gap-up events. Baseline (buy 9:30 open, exit noon): mean {b[0]:+}%, median {b[1]:+}%, win {b[2]}%.", ""]

# 1) confirmation entry
conf = [r for r in rows if isinstance(r.get("exit_1000"), (int, float)) and r["exit_1000"] > 0]
L += ["## 1) Confirmation entry (only trade if still green at 10:00)",
      f"Confirmed subset: {len(conf)}/{n} ({round(100*len(conf)/n) if n else 0}%).", "",
      "**Open-entry exits, confirmed subset only:**",
      "| exit | mean % | median % | win | n |", "|---|---|---|---|---|",
      line("exit 10:00", [r["exit_1000"] for r in conf]),
      line("exit noon", [r["exit_1200"] for r in conf]),
      line("+10% target else noon", [r["target_10"] for r in conf]),
      line("hold to close", [r["hold_to_close"] for r in conf]), ""]
def r1000(r, T):
    a, bb = r.get("exit_1000"), r.get(T)
    if isinstance(a, (int, float)) and isinstance(bb, (int, float)) and (1+a/100) != 0:
        return ((1+bb/100)/(1+a/100)-1)*100
    return None
L += ["**Enter AT 10:00 on confirmation, fixed-time exits:**",
      "| exit | mean % | median % | win | n |", "|---|---|---|---|---|",
      line("-> 10:30", [r1000(r, "exit_1030") for r in conf]),
      line("-> 11:00", [r1000(r, "exit_1100") for r in conf]),
      line("-> noon", [r1000(r, "exit_1200") for r in conf]), ""]

# 2) subsets
L += ["## 2) Subset slicing - does any bucket pay? (exit at 10:00, fast scalp)",
      "**By opening gap:**", "| gap | mean % | median % | win | n |", "|---|---|---|---|---|"]
for lo, hi, lab in [(20,40,"20-40%"),(40,70,"40-70%"),(70,120,"70-120%"),(120,9e9,"120%+")]:
    L.append(line(lab, [r["exit_1000"] for r in rows if isinstance(r.get("gap_pct"), (int,float)) and lo <= r["gap_pct"] < hi]))
L += ["", "**By first-hour volume x ADV:**", "| vol xADV | mean % | median % | win | n |", "|---|---|---|---|---|"]
for lo, hi, lab in [(0,1,"<1x"),(1,3,"1-3x"),(3,5,"3-5x"),(5,10,"5-10x"),(10,9e9,"10x+")]:
    L.append(line(lab, [r["exit_1000"] for r in rows if isinstance(r.get("fh_vol_x_adv"), (int,float)) and lo <= r["fh_vol_x_adv"] < hi]))

# 3) short side
L += ["", "## 3) Short side (short the 9:30 open, cover intraday = negated long, GROSS)",
      "| cover at | mean % | median % | win | n |", "|---|---|---|---|---|",
      line("cover 10:00", [-r["exit_1000"] for r in rows if isinstance(r.get("exit_1000"), (int,float))]),
      line("cover noon", [-r["exit_1200"] for r in rows if isinstance(r.get("exit_1200"), (int,float))]),
      line("cover at close", [-r["hold_to_close"] for r in rows if isinstance(r.get("hold_to_close"), (int,float))]),
      "", "**Heavy caveat:** shorting micro-cap runners needs locatable borrow (often unavailable, or 100-1000%+ "
      "annual fees), faces violent squeezes and LULD halts, and these GROSS figures ignore borrow cost, spread, "
      "and slippage. Realizable short returns are far lower with severe tail risk. Not a recommendation."]
L += ["", "**Overall caveats:** survivorship (currently-listed only); before costs; open/stop/confirmation fills "
      "optimistic on thin micro-caps."]
open(REPORT, "w", encoding="utf-8").write("\n".join(str(x) for x in L) + "\n")
print("DONE phase7 slices ->", REPORT)
