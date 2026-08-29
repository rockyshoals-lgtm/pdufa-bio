"""Unit-test _norm_period / _precision against the exact prose companies actually file.

Every case here is a real string shape pulled from readout_forward.csv or the EDGAR
contexts. The bar the old code failed: "OTHER" on 143 of 279 windows because it only
matched three tidy regexes.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import readout_scan as R

CASES = [
    # (input,                              expect_norm,        expect_precision)
    ("Q4 2026",                            "Q4 2026",          "QUARTER"),
    ("fourth quarter of 2026",             "Q4 2026",          "QUARTER"),
    ("the fourth quarter of 2026",         "Q4 2026",          "QUARTER"),
    ("4Q 2026",                            "Q4 2026",          "QUARTER"),
    ("first quarter 2027",                 "Q1 2027",          "QUARTER"),
    ("3Q26",                               "",                 ""),        # no 4-digit year
    ("second half of 2026",                "2H 2026",          "HALF"),
    ("2H 2026",                            "2H 2026",          "HALF"),
    ("2H26",                               "2H 2026",          "HALF"),
    ("1H 2027",                            "1H 2027",          "HALF"),
    ("mid-2026",                           "MID 2026",         "HALF"),
    ("September 2026",                     "September 2026",   "MONTH"),
    ("Sept. 2026",                         "September 2026",   "MONTH"),
    ("on September 30, 2026",              "September 30, 2026", "MONTH"),  # qtr-end -> bucket
    ("September 30, 2026 at 8:00am ET",    "September 30, 2026", "DAY"),    # named time = real
    ("October 23, 2026",                   "October 23, 2026", "DAY"),
    ("December 31, 2026",                  "December 31, 2026", "MONTH"),   # NYE = the tell
    ("2026",                               "2026",             "YEAR"),
    ("",                                   "",                 ""),
    ("as soon as practicable",             "",                 ""),
]

bad = 0
print(f"{'input':<38}{'norm':<22}{'prec':<10}{'expected':<22}ok")
print("-" * 104)
for s, en, ep in CASES:
    n, p = R._norm_period(s), R._precision(s)
    ok = (n == en and p == ep)
    bad += 0 if ok else 1
    print(f"{s[:37]:<38}{n[:21]:<22}{p:<10}{(en + ' / ' + ep)[:21]:<22}{'OK' if ok else 'FAIL'}")
print(f"\n{len(CASES)-bad}/{len(CASES)} pass")

# ---- now replay against the REAL windows in last night's output
import csv, collections
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "readout_forward.csv")
if os.path.exists(p):
    rows = list(csv.DictReader(open(p, encoding="utf-8", errors="replace", newline="")))
    ws = [(r.get("window") or "").strip() for r in rows]
    have = [w for w in ws if w]
    c = collections.Counter(R._precision(w) or "(ungraded)" for w in have)
    print(f"\nreplayed over {len(have)} non-blank windows from last night's run "
          f"({len(ws)-len(have)} blank):")
    for k, n in c.most_common():
        print(f"    {k:<14}{n:>5}  {100*n/len(have):>5.1f}%")
    ung = sorted({w for w in have if not R._precision(w)})
    if ung:
        print(f"\n  still ungraded ({len(ung)} distinct) -- these are the next fix:")
        for w in ung[:25]:
            print(f"    {w[:80]}")
sys.exit(1 if bad else 0)
