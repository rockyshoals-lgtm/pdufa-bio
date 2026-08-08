"""Look at the ACTUAL context behind the problem rows before changing anything."""
import csv
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "readout_forward.csv"), encoding="utf-8-sig")))
cols = rows[0].keys() if rows else []
print("columns:", list(cols), "\n")


def show(tk, note):
    print("=" * 90)
    print(f"  {tk}  — {note}")
    print("=" * 90)
    for r in rows:
        if r.get("ticker") == tk:
            print(f"  filed {r.get('filed','')}  window='{r.get('window','')}'  "
                  f"form={r.get('form','')}")
            ctx = (r.get("context") or r.get("phrases") or "")
            print(f"  context: {ctx[:280]}")
            print(f"  url: {r.get('url','')}")
            print()


# the false-positive suspect
show("GLMD", "'December 31, 2026' — fiscal year end, or a real readout date?")
# the duplicates
show("HELP", "appears 3x — dedupe target")
show("STTK", "appears 3x with 3 different windows")

# a few blank-window rows — why did the date extraction miss?
print("=" * 90)
print("  BLANK-WINDOW ROWS — we found the filing but got no date. WHY?")
print("=" * 90)
blank = [r for r in rows if not (r.get("window") or "").strip()]
print(f"  {len(blank)} blank of {len(rows)} total\n")
for r in sorted(blank, key=lambda r: r.get("filed", ""), reverse=True)[:12]:
    ctx = (r.get("context") or r.get("phrases") or "")
    print(f"  {r.get('ticker',''):<6} {r.get('filed','')}  {r.get('form','')}")
    print(f"     phrases: {(r.get('phrases') or '')[:70]}")
    print(f"     context: {ctx[:150]}")
    print()
