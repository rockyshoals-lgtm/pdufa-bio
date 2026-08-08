"""Independent recompute of the headline numbers, a different way than _hist_reactions.py.

David acts on these, so recompute from the saved reactions JSON with plain arithmetic and a
weekly bucketing (not a span/7 average) to confirm the per-week figure is not an artifact of
how the window was divided.
"""
import collections
import datetime as dt
import json
import os
import statistics
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
res = json.load(open(os.path.join(HERE, "Momentum Scanner", "_DATA", "_hist_reactions.json")))
print(f"n = {len(res)} readouts with price history\n")

pct = [r["pct"] for r in res]
print("RECHECK — reaction distribution:")
print(f"  median |move|  {statistics.median([abs(p) for p in pct]):.1f}%")
print(f"  mean signed    {statistics.mean(pct):+.1f}%")
for thr in (15, 25):
    print(f"  P(up>={thr}%)     {sum(1 for p in pct if p>=thr)/len(pct)*100:.1f}%")
print(f"  P(crash<=-25%) {sum(1 for p in pct if p<=-25)/len(pct)*100:.1f}%")

# weekly bucketing — count winners per ISO week, then average. Robust to span math.
def wk(dstr):
    d = dt.date(*map(int, dstr.split("-")))
    return d.isocalendar()[:2]
w15 = collections.Counter(wk(r["d"]) for r in res if r["pct"] >= 15)
w25 = collections.Counter(wk(r["d"]) for r in res if r["pct"] >= 25)
allw = collections.Counter(wk(r["d"]) for r in res)
nwk = len(allw)
print(f"\nWEEKLY (bucketed over {nwk} distinct ISO weeks):")
print(f"  >=15% pops: {sum(w15.values())} total -> {sum(w15.values())/nwk:.1f}/week")
print(f"  >=25% pops: {sum(w25.values())} total -> {sum(w25.values())/nwk:.1f}/week")
print(f"  median winners(>=15%) in a week: {statistics.median(list(w15.values()) or [0]):.0f}")
print(f"  weeks with ZERO >=15% pop: {nwk - len(w15)} of {nwk}")

# reconcile: this is the SAMPLE (346 of 611 tickers). Scale to full universe.
print(f"\nSCALING NOTE: this is 346 of 611 tickers (~57%). The true market-wide rate is")
print(f"  roughly {sum(w15.values())/nwk/0.57:.1f}/week for >=15% and "
      f"{sum(w25.values())/nwk/0.57:.1f}/week for >=25% — a linear scale-up, so treat as a")
print(f"  ballpark, not a precise count.")
