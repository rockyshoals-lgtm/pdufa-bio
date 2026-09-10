# -*- coding: utf-8 -*-
"""Audit 2026-09-10b, ORDER items 1 to 3: source what is sourceable, downgrade what is not.

Every quote below was read first-hand in the filing named, not taken from the audit.

ITEM 2, VRTX povetacicept (2026-11-30). Vertex 8-K 2026-08-03, EX-99.1, accession
0000875320-26-000256: headline bullet "povetacicept PDUFA date November 30th", body "The U.S.
FDA accepted the BLA submission for accelerated approval of povetacicept for adults with IgAN
and assigned a PDUFA target action date of November 30, 2026." A self-sourced forward row
becomes a filing-sourced one.

ITEM 3, MIRM/INCY zilurgisertib (2026-09-26). Mirum 8-K 2026-05-06, EX-99.1, accession
0001759425-26-000036: "The FDA has accepted the NDA for zilurgisertib in FOP under Priority
Review with a Prescription Drug User Fee Act (PDUFA) date of September 26, 2026. Mirum
licensed zilurgisertib from Incyte for development and commercialization globally." Both rows
gain the indication; the INCY row stops implying Incyte holds the application, because it does
not -- Mirum is the applicant and Incyte the licensor.

ITEM 1, the four December 31 PDUFA rows. None is supported by a sponsor filing:
  "tavapadon" + "target action date"  -> 0 hits in EDGAR full-text
  "CagriSema" + "target action date"  -> 0 hits
  AZN Ultomiris in IgAN               -> no AstraZeneca filing (they file 6-K/20-F, so EDGAR
                                         would see one)
  BAYRY finerenone                    -> Bayer is not an SEC registrant; EDGAR cannot settle
                                         it either way, which is not the same as a negative
So the day is withdrawn and the month kept: dp "month", dm "2026-12", date null in the API by
the mechanism shipped on 09-09. This is the same treatment as the 325 manufactured day-15
dates. A day returns only with a sponsor source, and `_unsourced_day_dates.json` plus its
guard stop it returning silently.

NOT a shape argument. Month-end goal dates are ordinary -- povetacicept's own November 30 is
real and is being sourced in the same commit. The criterion is the missing source, not the
date.
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

VRTX_8K = ("https://www.sec.gov/Archives/edgar/data/875320/000087532026000256/"
           "ex-991_q22026.htm")
MIRM_8K = ("https://www.sec.gov/Archives/edgar/data/1759425/000175942526000036/"
           "mirm-20260506xexx991.htm")
FOP = "Fibrodysplasia ossificans progressiva (FOP)"

DOWNGRADE = {
    ("ABBV", "2026-12-31"): 'EDGAR full-text: "tavapadon" + "target action date" returns 0 '
                            'filings; AbbVie names tavapadon in 8-K/10-K but never states an '
                            "FDA goal date. Day withdrawn 2026-09-10; month retained.",
    ("NVO", "2026-12-31"): 'EDGAR full-text: "CagriSema" + "target action date" returns 0 '
                           "filings; Novo Nordisk's 6-Ks name the NDA but state no goal date. "
                           "Day withdrawn 2026-09-10; month retained.",
    ("AZN", "2026-12-31"): "No AstraZeneca filing states a goal date for Ultomiris in IgA "
                           "nephropathy (searched Ultomiris/ravulizumab + IgA nephropathy + "
                           "PDUFA; hits are third parties and pre-2022 Alexion). AstraZeneca "
                           "files 6-K/20-F, so EDGAR would show one. Day withdrawn "
                           "2026-09-10; month retained.",
    ("BAYRY", "2026-12-31"): "Bayer is not an SEC registrant, so EDGAR cannot confirm or deny "
                             "this date; no Bayer release has been read for it either. Day "
                             "withdrawn 2026-09-10 for want of any source; month retained.",
}


def main():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    a, b = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[a:b])
    sourced = downgraded = filled = 0

    for r in rows:
        tk, d = str(r.get("t") or "").upper(), str(r.get("d") or "")
        typ = str(r.get("type") or "").upper()
        dd = r.setdefault("_d", {})

        if tk == "VRTX" and d == "2026-11-30" and typ == "PDUFA":
            dd["source"] = "Vertex 8-K 2026-08-03 (EX-99.1)"
            dd["source_url"] = VRTX_8K
            dd["review"] = ("The FDA accepted the BLA for accelerated approval of "
                            "povetacicept in IgA nephropathy and assigned a PDUFA target "
                            "action date of November 30, 2026, per Vertex's own quarterly "
                            "release; the submission is supported by a pre-specified Week 36 "
                            "interim analysis of the Phase 3 RAINIER trial.")
            sourced += 1

        if d == "2026-09-26" and typ == "PDUFA" and "zilurgisertib" in str(r.get("name", "")):
            if not dd.get("indication"):
                dd["indication"] = FOP
                filled += 1
            dd["source"] = "Mirum 8-K 2026-05-06 (EX-99.1)"
            dd["source_url"] = MIRM_8K
            if tk == "MIRM":
                dd["review"] = ("The FDA accepted the NDA for zilurgisertib in FOP under "
                                "Priority Review with a PDUFA date of September 26, 2026. "
                                "Mirum licensed zilurgisertib from Incyte for development "
                                "and commercialization globally.")
                sourced += 1
            elif tk == "INCY":
                # Incyte is the LICENSOR. Keeping the row is defensible exposure; calling it
                # Incyte's PDUFA is not, and the page must not imply Incyte filed the NDA.
                r["name"] = "Zilurgisertib (licensed to Mirum; MIRM holds the NDA)"
                dd["review"] = ("Incyte discovered zilurgisertib and licensed it to Mirum "
                                "for development and commercialization globally. The NDA is "
                                "Mirum's and the September 26, 2026 PDUFA date is Mirum's; "
                                "this row tracks Incyte's economic exposure to that decision, "
                                "not an Incyte application.")
                dd["applicant"] = "Mirum Pharmaceuticals, Inc. (MIRM)"
                sourced += 1

        key = (tk, d)
        if key in DOWNGRADE and typ == "PDUFA" and str(r.get("dp")) == "day":
            r["dp"] = "month"
            r["dm"] = d[:7]
            dd["date_note"] = DOWNGRADE[key]
            downgraded += 1

    io.open(DATASET, "w", encoding="utf-8").write(
        src[:a] + json.dumps(rows, indent=1, ensure_ascii=False) + src[b:])

    io.open(LEDGER, "w", encoding="utf-8").write(json.dumps({
        "note": ("Rows whose published day was withdrawn for want of a sponsor source. A day "
                 "may return ONLY with _d.source_url pointing at a filing or company release "
                 "that states it. tests/test_no_unsourced_day_dates.py enforces this."),
        "withdrawn_on": "2026-09-10",
        "rows": [{"ticker": k[0], "was_date": k[1], "month_kept": k[1][:7], "why": v}
                 for k, v in sorted(DOWNGRADE.items())],
    }, indent=1, ensure_ascii=False) + "\n")

    print(f"sourced {sourced} row(s), filled {filled} indication(s), "
          f"downgraded {downgraded} unsourced day date(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
