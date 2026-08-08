import csv
import datetime as dt
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import readout_scan as R

rows = list(csv.DictReader(open("readout_forward_v3.csv", encoding="utf-8-sig")))
win = [r for r in rows if (r.get("window") or "").strip()]
dupes = len(rows) - len({r["ticker"] for r in rows})
print(f"{len(rows)} rows, {len(win)} windowed ({len(win)/len(rows)*100:.0f}%), "
      f"duplicate tickers: {dupes}\n")

# past-quarter check using the scanner's own _period_end
bad = []
for r in win:
    try:
        fd = dt.date(*map(int, r["filed"].split("-")))
    except Exception:
        continue
    pe = R._period_end(r["window"]) or R._hard_date(r["window"])
    if pe and pe < fd:
        bad.append((r["ticker"], r["filed"], r["window"]))
print(f"PAST windows still present (should be 0): {len(bad)}  {bad[:6]}\n")

print("THE FINAL LIST (one row per ticker, nearest forward window):")
for r in sorted(win, key=lambda r: r["filed"], reverse=True):
    print(f"  {r['ticker']:<6} {r['filed']:<11} n={r.get('n_filings','1'):<2} "
          f"{r['window'][:26]:<28} {(r.get('company') or '')[:28]}")
blank = [r for r in rows if not (r.get("window") or "").strip()]
print(f"\n  + {len(blank)} names found but no window extractable (guidance was vague, "
      f"e.g. 'in the coming months')")
