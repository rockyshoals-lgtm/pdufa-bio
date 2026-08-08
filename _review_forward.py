"""Review the fresh readout_forward.csv and compare to the earlier run + our full coverage."""
import csv
import collections
import datetime as dt
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))


def load(p):
    if not os.path.exists(p):
        return []
    return list(csv.DictReader(open(p, encoding="utf-8-sig")))


cur = load(os.path.join(HERE, "readout_forward.csv"))
prev = load(os.path.join(HERE, "readout_forward_v2.csv"))  # the earlier run I saved
print(f"CURRENT readout_forward.csv : {len(cur)} rows")
print(f"earlier readout_forward_v2  : {len(prev)} rows\n")

kind = collections.Counter(r.get("kind", "") for r in cur)
withwin = [r for r in cur if (r.get("window") or "").strip()]
print(f"by kind: {dict(kind)}")
print(f"with a window: {len(withwin)} of {len(cur)}\n")

print("=" * 88)
print("  ROWS WITH AN EXTRACTED WINDOW (the tradeable output)")
print("=" * 88)
for r in sorted(withwin, key=lambda r: r.get("filed", ""), reverse=True):
    print(f"  {r.get('ticker',''):<6} {r.get('filed',''):<11} "
          f"{(r.get('window') or '')[:22]:<22} {(r.get('company') or '')[:32]}")

# quarter-bucket check: did the new fix relabel any to Q#?
qwin = [r for r in withwin if (r.get("window") or "").strip().upper().startswith("Q")
        or "H2" in (r.get("window") or "").upper() or "H1" in (r.get("window") or "").upper()]
print(f"\n  windows that are quarter/half periods: {len(qwin)}")

# tickers new vs previous run
cur_t = {r.get("ticker", "") for r in cur if r.get("ticker")}
prev_t = {r.get("ticker", "") for r in prev if r.get("ticker")}
print("\n" + "=" * 88)
print("  CHANGE VS THE EARLIER RUN")
print("=" * 88)
print(f"  new tickers this run : {sorted(cur_t - prev_t)}")
print(f"  dropped since        : {sorted(prev_t - cur_t)}")

# coverage: is each forward name already in our augmented list?
aug = os.path.join(HERE, "phase_readouts_2026H2_cornerstone_augmented.csv")
ours = set()
if os.path.exists(aug):
    for r in csv.DictReader(open(aug, encoding="utf-8-sig")):
        if r.get("ticker"):
            ours.add(r["ticker"].upper())
new_to_us = [r for r in withwin if (r.get("ticker") or "").upper() not in ours]
print("\n" + "=" * 88)
print("  OF THE WINDOWED ROWS, WHICH ARE NEW TO OUR COVERAGE?")
print("=" * 88)
print(f"  {len(new_to_us)} of {len(withwin)} windowed names are NOT in our augmented list:")
for r in new_to_us:
    print(f"    {r.get('ticker',''):<6} {(r.get('window') or '')[:20]:<20} {(r.get('company') or '')[:34]}")

# blank-window rows: names we found but couldn't date (the improvement target)
blank = [r for r in cur if not (r.get("window") or "").strip()]
print("\n" + "=" * 88)
print(f"  BLANK-WINDOW ROWS — found the filing, could NOT extract a date: {len(blank)}")
print("=" * 88)
print("  these are the miss target — we know a readout filing exists but got no window.")
for r in sorted(blank, key=lambda r: r.get("filed", ""), reverse=True)[:20]:
    print(f"    {r.get('ticker',''):<6} {r.get('filed',''):<11} "
          f"{(r.get('phrases') or r.get('context') or '')[:52]}")
