# -*- coding: utf-8 -*-
"""Quarter-end PDUFA days: source the real ones, withdraw the manufactured ones.

FOUND WHILE EXTENDING THE 09-10b GUARD. The ORDER named four unsourced day-precision PDUFAs on
2026-12-31. Extending the check to every quarter-end day surfaced NINE more on 06-30 and 09-30
with no source_url. Each was settled against EDGAR full-text first-hand; the verdicts split
three ways, which is the point -- "month-end" is not itself the defect.

REAL, and now sourced (day precision KEPT):
  IONS 2026-06-30 olezarsen  -- Ionis 8-K 2026-04-29 EX-99.1: "sNDA accepted by the FDA for
      Priority Review for the treatment of sHTG with a Prescription Drug User Fee Act (PDUFA)
      target action date of June 30, 2026."
  VRDN 2026-06-30 veligrotug -- Viridian 8-K 2026-05-05 EX-99.1: "PDUFA target action date of
      June 30, 2026 for veligrotug in thyroid eye disease (TED)."
  SRRK 2026-09-30 apitegromab -- Scholar Rock 8-K 2026-05-07 EX-99.1: "FDA accepted apitegromab
      Biologics License Application (BLA) ... with September 30, 2026 Prescription Drug User Fee
      Act (PDUFA) action date." Repeated in the 10-Q of the same date and again on 2026-08-06.
      (A resubmission clock: BLA resubmitted 2026-03-31, six-month review.)

MANUFACTURED -- the sponsor stated a QUARTER and we published the last day of it:
  PFE  + ROIV 2026-09-30 brepocitinib -- Priovant/Roivant 8-K 2026-03-03: "FDA assigns PDUFA
      target action date in the third quarter of calendar year 2026."
  TAK  2026-09-30 oveporexton -- Takeda 6-K 2026-02-10: "The Prescription Drug User Fee Act
      (PDUFA) Target Action Date is the Third Quarter of this Calendar Year."
  PTGX 2026-09-30 rusfertide  -- Takeda/Protagonist 6-K 2026-03-02: "Prescription Drug User Fee
      Act (PDUFA) Target Action Date is in the Third Quarter of this Calendar Year."
  -> dp "quarter", dm "2026-09". The API already nulls `date` for non-day precision (09-09), so
     these stop asserting a day the sponsor never gave.

NO SOURCE AT ALL:
  AZN 2026-06-30 Truqap (capivasertib) -- no AstraZeneca filing states a goal date for it.
      AstraZeneca files 6-K/20-F and names capivasertib often, but as portfolio narrative; it
      does not publish PDUFA goal dates. Day withdrawn. Month retained ONLY because our own
      sourced decision page puts the action in June 2026 -- the month is not independently
      sourced to a goal-date statement and the note says so.
  NVO 2026-09-30 denecimig (Mim8) -- Novo names denecimig in five 2026 filings and never gives a
      day, a month or a quarter. The 6-K of 2026-08-04 lists "Denecimig US EU decision" in its
      R&D milestone table and the Q4 6-K says only "for this year ... regulatory decisions ...
      such as Mim8". The sourced granularity is the YEAR, so dp "year" on the year-end sentinel,
      matching the existing TYRA convention.

WHY THIS MATTERS BEYOND THE ROW. /research/fda-decision-timing counts how many sourced decisions
landed before their goal date. Its inclusion rule tests the goal date's FORMAT, not its
PRECISION, so 2026-09-30 passed. The four quarter placeholders were the four largest "early"
margins in that statistic (-34, -33, -34, -56 days) and moved the published median from -1.0 to
-2.5 days. A quarter-end placeholder is the LATEST day in the stated quarter, so it can only
ever bias in the flattering direction. build_early_decisions.py is gated on precision in the
same commit.
"""
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
LEDGER = os.path.join(HERE, "_unsourced_day_dates.json")

IONS = ("https://www.sec.gov/Archives/edgar/data/874015/000114036126017637/"
        "ef20071749_ex99-1.htm")
VRDN = ("https://www.sec.gov/Archives/edgar/data/1590750/000119312526205010/"
        "d149508dex991.htm")
SRRK = ("https://www.sec.gov/Archives/edgar/data/1727196/000110465926056655/"
        "srrk-20260507xex99d1.htm")
ROIV = ("https://www.sec.gov/Archives/edgar/data/1635088/000114036126007447/"
        "ef20066998_ex99-1.htm")
TAK = ("https://www.sec.gov/Archives/edgar/data/1395064/000139506426000005/"
       "form6k_021026.htm")
PTGX = ("https://www.sec.gov/Archives/edgar/data/1395064/000139506426000007/"
        "form6k_030226.htm")

# ticker, date -> (source label, url, review sentence)
SOURCE_KEEP_DAY = {
    ("IONS", "2026-06-30"): (
        "Ionis 8-K 2026-04-29 (EX-99.1)", IONS,
        "Ionis states the FDA accepted the sNDA for olezarsen in severe hypertriglyceridemia "
        "under Priority Review with a PDUFA target action date of June 30, 2026."),
    ("VRDN", "2026-06-30"): (
        "Viridian 8-K 2026-05-05 (EX-99.1)", VRDN,
        "Viridian states a PDUFA target action date of June 30, 2026 for veligrotug in thyroid "
        "eye disease, with the company describing itself as launch-ready."),
    ("SRRK", "2026-09-30"): (
        "Scholar Rock 8-K 2026-05-07 (EX-99.1)", SRRK,
        "Scholar Rock resubmitted the apitegromab BLA on March 31, 2026 after a September 2025 "
        "CRL tied to a third-party fill-finish facility, not to the drug. The FDA accepted the "
        "resubmission with a September 30, 2026 PDUFA action date, and the company notes "
        "approval may be granted at any time up to it."),
}

# ticker, date -> (new precision, new d, new dm, source label, url, note)
DOWNGRADE = {
    ("PFE", "2026-09-30"): (
        "quarter", "2026-09-30", "2026-09", "Priovant/Roivant 8-K 2026-03-03 (EX-99.1)", ROIV,
        'Roivant states the FDA "assigns PDUFA target action date in the third quarter of '
        'calendar year 2026". The sponsor gave a QUARTER; our 2026-09-30 was the last day of '
        "it, not an announced day. Day withdrawn 2026-09-10; quarter is the sourced precision."),
    ("ROIV", "2026-09-30"): (
        "quarter", "2026-09-30", "2026-09", "Priovant/Roivant 8-K 2026-03-03 (EX-99.1)", ROIV,
        'Roivant states the FDA "assigns PDUFA target action date in the third quarter of '
        'calendar year 2026". The sponsor gave a QUARTER; our 2026-09-30 was the last day of '
        "it, not an announced day. Day withdrawn 2026-09-10; quarter is the sourced precision."),
    ("TAK", "2026-09-30"): (
        "quarter", "2026-09-30", "2026-09", "Takeda 6-K 2026-02-10", TAK,
        'Takeda states "The Prescription Drug User Fee Act (PDUFA) Target Action Date is the '
        'Third Quarter of this Calendar Year" for oveporexton in narcolepsy type 1. The sponsor '
        "gave a QUARTER. Day withdrawn 2026-09-10; quarter is the sourced precision."),
    ("PTGX", "2026-09-30"): (
        "quarter", "2026-09-30", "2026-09", "Takeda/Protagonist 6-K 2026-03-02", PTGX,
        'Takeda and Protagonist state "Prescription Drug User Fee Act (PDUFA) Target Action '
        'Date is in the Third Quarter of this Calendar Year" for rusfertide in polycythemia '
        "vera. The sponsor gave a QUARTER. Day withdrawn 2026-09-10."),
    ("AZN", "2026-06-30"): (
        "month", "2026-06-30", "2026-06", None, None,
        "No AstraZeneca filing states a PDUFA goal date for Truqap (capivasertib) in this "
        "indication. AstraZeneca names capivasertib in many 6-K/20-F filings but as portfolio "
        "narrative; it does not publish goal dates. The June 30 day is unsourced and is "
        "withdrawn. The month is retained only because our own sourced decision page places the "
        "FDA action in June 2026 -- it is NOT independently sourced to a goal-date statement."),
    ("NVO", "2026-09-30"): (
        "year", "2026-12-31", None, None, None,
        "Novo Nordisk names denecimig (Mim8) in five 2026 filings and never states a day, month "
        "or quarter for the US decision. The 6-K of 2026-08-04 lists \"Denecimig US EU "
        "decision\" among R&D milestones and the Q4 6-K says only that the company looks "
        "forward this year to decisions \"such as Mim8\". The YEAR is the sourced granularity, "
        "so the row moves to year precision on the year-end sentinel (the TYRA convention). "
        "Day withdrawn 2026-09-10."),
}


def main():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    a, b = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[a:b])
    sourced = downgraded = fixed_dm = 0

    for r in rows:
        tk, d = str(r.get("t") or "").upper(), str(r.get("d") or "")
        key = (tk, d)
        dd = r.setdefault("_d", {})

        if key in SOURCE_KEEP_DAY and r.get("type") == "PDUFA":
            label, url, review = SOURCE_KEEP_DAY[key]
            dd["source"], dd["source_url"], dd["review"] = label, url, review
            sourced += 1

        elif key in DOWNGRADE and r.get("type") == "PDUFA":
            dp, nd, dm, label, url, note = DOWNGRADE[key]
            r["dp"], r["d"] = dp, nd
            if dm:
                r["dm"] = dm
            else:
                r.pop("dm", None)
            if label:
                dd["source"], dd["source_url"] = label, url
            dd["date_note"] = note
            downgraded += 1

        # a quarter row with no dm leaves consumers nothing but the year-end sentinel
        if r.get("dp") == "quarter" and not r.get("dm") and len(d) >= 7:
            r["dm"] = d[:7]
            fixed_dm += 1

    io.open(DATASET, "w", encoding="utf-8").write(
        src[:a] + json.dumps(rows, indent=1, ensure_ascii=False) + src[b:])

    led = json.loads(io.open(LEDGER, encoding="utf-8").read())
    have = {(x["ticker"], x["was_date"]) for x in led["rows"]}
    for (tk, d), v in sorted(DOWNGRADE.items()):
        if (tk, d) not in have:
            led["rows"].append({"ticker": tk, "was_date": d, "month_kept": v[2],
                                "new_precision": v[0], "why": v[5]})
    led["rows"].sort(key=lambda x: (x["ticker"], x["was_date"]))
    io.open(LEDGER, "w", encoding="utf-8").write(
        json.dumps(led, indent=1, ensure_ascii=False) + "\n")

    print(f"sourced {sourced} real quarter-end day(s); downgraded {downgraded} manufactured "
          f"one(s); filled dm on {fixed_dm} quarter row(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
