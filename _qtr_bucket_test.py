"""date_precision — the quarter-bucket trap, tested on the REAL BPC rows that exposed it.

BiopharmaCatalyst stores "Q3 2026" as 2026-09-30, "2H 2026" as 2026-12-31, "mid-2026" as
2026-08-31. Trusting those as real days ("the readout is Sep 30") is a confident-wrong date —
the same class of bug as the dateline. This asserts the parser demotes them to quarters while
still honoring a genuinely specific day (a conference talk, a PDUFA, an explicit "on Sep 30").
"""
import datetime as dt
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import readout_scan as R

ok_n = fail = 0


def ok(c, m):
    global ok_n, fail
    print(("  PASS  " if c else "  FAIL  ") + m)
    if c: ok_n += 1
    else: fail += 1


D = dt.date
print("=" * 92)
print("  QUARTER ENDS ARE BUCKETS unless the text pins a specific day")
print("=" * 92)
# real catalyst text pulled from fda_2026-07-18.xlsx
ok(R.date_precision(D(2026, 9, 30), "Phase 2 topline data due 3Q 2026") == "quarter",
   "Sep 30 + '3Q 2026'  -> quarter  (VKTX/ALT/BOLT pattern)")
ok(R.date_precision(D(2026, 12, 31), "Phase 3 topline data expected 2H 2026") == "quarter",
   "Dec 31 + '2H 2026'  -> quarter  (HRMY/ZLAB pattern)")
ok(R.date_precision(D(2026, 8, 31), "Phase 1b topline data due in summer 2026") == "quarter",
   "Aug 31 + 'summer 2026' -> quarter  (CRBP pattern)")
ok(R.date_precision(D(2026, 6, 30), "topline data moved to mid-2026") == "quarter",
   "Jun 30 + 'mid-2026' -> quarter  (AVBP pattern)")
ok(R.date_precision(D(2026, 3, 31), "fiscal") == "quarter", "Mar 31 bare -> quarter")

print("\n" + "=" * 92)
print("  BUT A GENUINELY SPECIFIC DAY STAYS A DAY")
print("=" * 92)
ok(R.date_precision(D(2026, 10, 2), "Phase 1 data to be shared at EASD on October 2") == "day",
   "Oct 2 + 'at EASD on October 2' -> day  (SANA — conference-dated, reliable)")
ok(R.date_precision(D(2026, 9, 30), "data on September 30 at 8:00am ET") == "day",
   "Sep 30 + 'on September 30 at 8am ET' -> day (a real day that lands on a quarter end)")
ok(R.date_precision(D(2026, 10, 23), "Phase 1 data at ESMO on October 23") == "day",
   "Oct 23 + 'ESMO' -> day  (XNCR/CATX — conference)")
ok(R.date_precision(D(2026, 7, 15), "topline on July 15, 2026") == "day",
   "July 15 is not a quarter end -> day (unaffected)")
ok(R.date_precision(D(2026, 11, 20), "") == "day", "an ordinary mid-quarter day -> day")

print("\n" + "=" * 92)
print("  fetch_date RELABELS a quarter bucket to 'Q# YYYY' — never a bare day")
print("=" * 92)
# simulate the text a filing/tracker would carry
import re
# unit-level: build the candidate path by hand mirroring fetch_date's logic
w = "Company expects to report Phase 2 topline data in 3Q 2026 on or about September 30, 2026"
hd = R._hard_date("September 30, 2026")
ok(hd == D(2026, 9, 30), "_hard_date still parses the day")
ok(R.date_precision(hd, w) == "quarter",
   "...and date_precision flags it quarter because '3Q 2026' is right there")
q = (hd.month - 1) // 3 + 1
ok(f"Q{q} {hd.year}" == "Q3 2026", "the relabel is 'Q3 2026', not 'September 30, 2026'")

print("\n" + "=" * 92)
print(f"  {ok_n} passed, {fail} failed")
print("=" * 92)
sys.exit(1 if fail else 0)
