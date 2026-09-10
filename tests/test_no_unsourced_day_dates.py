# -*- coding: utf-8 -*-
"""CI guard: a PDUFA day we cannot source must not be published as a day.

WHAT HAPPENED
Audit 09-10b named four day-precision PDUFAs on 2026-12-31 with no source. Extending the same
check to every quarter-end surfaced nine more on 06-30 and 09-30, and reading the filings split
them three ways:

  REAL      IONS olezarsen (Jun 30), VRDN veligrotug (Jun 30), SRRK apitegromab (Sep 30) --
            each stated as an exact day by the sponsor. Month-end is NOT the defect.
  QUARTER   PFE + ROIV brepocitinib, TAK oveporexton, PTGX rusfertide -- the sponsor said
            "third quarter of calendar year 2026" and we published the last day of it.
  NOTHING   AZN Truqap, NVO denecimig -- no sponsor statement of a day at any granularity.

The blast radius reached a published statistic. /research/fda-decision-timing gated on the goal
date's FORMAT, so 2026-09-30 passed; the four quarter placeholders were its four largest "early"
margins and moved the median from -1.0 to -2.5 days. A quarter-end placeholder is the LAST day
of the stated quarter, so it can only bias one way -- the flattering one.

THE INVARIANTS
1. Every row in `_unsourced_day_dates.json` must still be non-day precision, unless it has
   regained a real `_d.source_url`. A withdrawn day may come back, but only with a source.
2. Any day-precision PDUFA landing on a quarter end (03-31, 06-30, 09-30, 12-31) must carry a
   `_d.source_url`. These four dates are where "we don't know, use the end of the period"
   lands, so they carry the burden of proof. Other days do not -- this is deliberately narrow.
3. build_early_decisions.py must gate its inclusion rule on `dp == "day"`, not on the date's
   format, in BOTH collect() and the audit path.
4. _lib.mjs must not derive `date_month` from a year-precision row's year-end sentinel.

    python tests/test_no_unsourced_day_dates.py
"""
import io
import json
import os
import sys

DATASET = os.path.join("pdufa_site_src", "api", "v1", "dataset.mjs")
LIB = os.path.join("pdufa_site_src", "api", "v1", "_lib.mjs")
LEDGER = "_unsourced_day_dates.json"
EARLY = "build_early_decisions.py"
QUARTER_ENDS = {"03-31", "06-30", "09-30", "12-31"}


def load():
    s = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    return json.loads(s[s.index("["):s.rindex("]") + 1])


def main():
    if not os.path.exists(DATASET):
        print(f"  SKIP {DATASET} not found")
        return 0
    rows = load()
    fail = 0

    # 1. the ledger holds
    if os.path.exists(LEDGER):
        led = json.loads(io.open(LEDGER, encoding="utf-8").read())
        by_tk = {}
        for r in rows:
            by_tk.setdefault(str(r.get("t") or "").upper(), []).append(r)
        for entry in led.get("rows", []):
            tk, was = entry["ticker"], entry["was_date"]
            for r in by_tk.get(tk, []):
                if r.get("type") != "PDUFA" or r.get("dp") != "day":
                    continue
                if str(r.get("d") or "") != was:
                    continue
                if not (r.get("_d") or {}).get("source_url"):
                    print(f"  FAIL {tk} {was} is day-precision again with no _d.source_url. "
                          f"It was withdrawn because: {entry['why'][:110]}")
                    fail += 1

    # 2. quarter-end days carry the burden of proof
    for r in rows:
        if r.get("type") != "PDUFA" or r.get("dp") != "day":
            continue
        d = str(r.get("d") or "")
        if d[5:] not in QUARTER_ENDS:
            continue
        if not (r.get("_d") or {}).get("source_url"):
            print(f"  FAIL {r.get('t')} {d} is a day-precision PDUFA on a quarter end with no "
                  f"_d.source_url. Quarter ends are where a rounded 'sometime in Qn' lands, so "
                  f"they need a filing that states the day -- or set dp to quarter/month.")
            fail += 1

    # 3. the statistic gates on precision
    if os.path.exists(EARLY):
        src = io.open(EARLY, encoding="utf-8", errors="replace").read()
        n = src.count('r.get("dp") != "day"')
        if n < 2:
            print(f"  FAIL {EARLY} gates on dp in {n} place(s); both collect() and the audit "
                  f"path must skip non-day goal dates, or a manufactured 2026-09-30 re-enters "
                  f"/research/fda-decision-timing through the format check.")
            fail += 1

    # 4. a year row does not get a month
    if os.path.exists(LIB):
        lib = io.open(LIB, encoding="utf-8", errors="replace").read()
        if "e.dp === 'year' ? null" not in lib.replace('"', "'"):
            print("  FAIL _lib.mjs derives date_month from `d` for year-precision rows, which "
                  "publishes the year-end sentinel's month (e.g. '2027-12') as if the sponsor "
                  "had named December.")
            fail += 1

    if fail:
        print(f"\n{fail} unsourced-day failure(s). A day no sponsor announced is a fabricated "
              f"date, and it contaminates the timing statistic too. DO NOT PUBLISH.")
        return 1

    qe = [r for r in rows if r.get("type") == "PDUFA" and r.get("dp") == "day"
          and str(r.get("d") or "")[5:] in QUARTER_ENDS]
    print(f"OK -- {len(qe)} day-precision quarter-end PDUFA(s), every one carrying a source_url; "
          f"ledger intact; timing stat gated on precision; year rows carry no derived month.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
