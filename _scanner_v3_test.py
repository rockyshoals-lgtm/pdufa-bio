"""readout_scan v3 improvements — fiscal rejection, broadened recall, nearest-forward selection.

Built on the REAL text that produced the bad rows in the 2026-07-18 readout_forward.csv:
  GLMD  window "December 31, 2026"  <- from "year ending December 31, 2026 ... accounting policies"
  STTK  3 rows, one "first half of 2028"  <- a different trial's milestone beat the real Q3 2026
  34/67 blank  <- because NEAR did not include "results", so "results anticipated in 2H 2026" missed
"""
import datetime as dt
import os
import re
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


print("=" * 92)
print("  RECALL — NEAR now catches 'results' (the 34-blank cause)")
print("=" * 92)
ok(R.NEAR.search("topline results anticipated in the second half of 2026"),
   "NEAR matches 'results' (was missed -> blank window)")
ok(R.NEAR.search("proof-of-concept data expected"), "NEAR matches 'proof-of-concept'")
ok(R.NEAR.search("efficacy and safety data in 3Q"), "NEAR matches 'efficacy'/'safety data'")
ok(R.NEAR.search("the primary endpoint analysis"), "NEAR matches 'analysis'")

print("\n" + "=" * 92)
print("  ACCURACY — FISCAL_RX rejects the financial/offering contexts the broadening lets in")
print("=" * 92)
GLMD = ("results are to be expected for the year ending December 31, 2026. Note 2 - Summary of "
        "significant accounting policies")
ok(R.FISCAL_RX.search(GLMD), "GLMD 'year ending ... accounting policies' -> fiscal, REJECT")
HELP = ("The Company intends to use the net proceeds from the Offering to progress the "
        "Company's pipeline with data in the fourth quarter of 2026")
ok(R.FISCAL_RX.search(HELP), "HELP 'net proceeds from the Offering' -> offering, REJECT")
ok(R.FISCAL_RX.search("a registered direct offering priced at $2.00 per share"),
   "registered direct / per share -> reject")
# must NOT reject a real clinical readout
CLEAN = ("The Company expects to report topline data from its Phase 3 trial in the third "
         "quarter of 2026")
ok(not R.FISCAL_RX.search(CLEAN), "a clean clinical readout is NOT rejected")

print("\n" + "=" * 92)
print("  _period_start — for nearest-forward sorting")
print("=" * 92)
ok(R._period_start("Q3 2026") == dt.date(2026, 7, 1), "Q3 2026 -> Jul 1")
ok(R._period_start("first half of 2028") == dt.date(2028, 1, 1), "1H 2028 -> Jan 1 2028")
ok(R._period_start("2H 2026") == dt.date(2026, 7, 1), "2H 2026 -> Jul 1")
ok(R._period_start("mid-2026") == dt.date(2026, 5, 1), "mid-2026 -> May 1")
ok(R._period_start("banana") is None, "junk -> None")

print("\n" + "=" * 92)
print("  SELECTION — nearest forward wins (STTK: Q3 2026 over 1H 2028)")
print("=" * 92)
# simulate fetch_date's candidate scoring on STTK-like text: two forward periods in one doc
# uses the SAME _sort_date the scanner uses (midpoint for periods, exact for hard dates)
cands = [(3, "first half of 2028", "ctx"), (3, "Q3 2026", "ctx")]
cands.sort(key=lambda c: (R._sort_date(c[1]), -c[0]))
ok(cands[0][1] == "Q3 2026", "Q3 2026 (nearer) is selected over 'first half of 2028'")
# 2H 2026 expected-midpoint ~mid-September; a concrete Aug 15 lands sooner -> Aug 15 wins
cands2 = [(3, "2H 2026", "c"), (2, "August 15, 2026", "c")]
cands2.sort(key=lambda c: (R._sort_date(c[1]), -c[0]))
ok(cands2[0][1] == "August 15, 2026",
   "a specific Aug 15 beats '2H 2026' — periods sort by expected MIDPOINT, not optimistic start")

print("\n" + "=" * 92)
print("  PAST-PERIOD REJECTION — a quarter already closed at filing is NOT a forecast")
print("=" * 92)
ok(R._period_end("Q1 2026") == dt.date(2026, 3, 31), "Q1 2026 ends Mar 31")
ok(R._period_end("2H 2026") == dt.date(2026, 12, 31), "2H 2026 ends Dec 31")
ok(R._period_end("third quarter of 2026") == dt.date(2026, 9, 30), "Q3 2026 ends Sep 30")
# a filing on 2026-07-01 that mentions "Q1 2026" -> that quarter is CLOSED -> reject
filed = dt.date(2026, 7, 1)
ok(R._period_end("Q1 2026") < filed, "Q1 2026 is closed before a July-2026 filing (reject)")
ok(R._period_end("Q4 2026") >= filed, "Q4 2026 is still open at a July-2026 filing (keep)")
ok(R._period_end("banana") is None, "junk period -> None (no false reject)")

print("\n" + "=" * 92)
print("  END-TO-END on the GLMD document text (the false positive must vanish)")
print("=" * 92)
# reproduce fetch_date's inner loop on the real GLMD paragraph
txt = ("Corbus and others report results. GLMD financial results are to be expected for the "
       "year ending December 31, 2026. Note 2 - Summary of significant accounting policies "
       "that have been applied in the preparation of these financial statements.")
picked = None
for m in R.NEAR.finditer(txt):
    w = txt[max(0, m.start() - 260):m.end() + 260]
    if not R.FWD_NEAR.search(w):
        continue
    if R.FISCAL_RX.search(w):
        continue                      # <- GLMD dies here
    picked = w
ok(picked is None, "GLMD: every readout-ish match sits in fiscal context -> NO window (was "
                   "'December 31, 2026')")

print("\n" + "=" * 92)
print(f"  {ok_n} passed, {fail} failed")
print("=" * 92)
sys.exit(1 if fail else 0)
