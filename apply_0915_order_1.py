# -*- coding: utf-8 -*-
"""Audit 09-15 ORDER 1: the CORT relacorilant row that failed four ways, in four audits.

Live field dump on 2026-09-15:
    id              readout_cort_2026-09-15   readout_ prefix on a PDUFA; the RETIRED 15th in the key
    date            2026-12-17
    date_month      2026-09                   three months earlier than date, in the sort key we tell
                                              consumers to use ("sort on date_month first")
    therapeutic_area Infectious               for Cushing's syndrome
    indication      null
    url             clinicaltrials.gov        off-site, when /pdufa/CORT-relacorilant exists

The date itself is right and is now SOURCED, read first-hand: Corcept 8-K 2026-07-29, EX-99.1,
accession 0001628280-26-050607: "New Drug Application for relacorilant resubmitted with a
Prescription Drug User Fee Act (PDUFA) date of December 17, 2026" (Cushing's syndrome). So `d`
and `days_to_decision` stand and everything else on the row is brought into agreement with them.

Why `date_month` was wrong is this week's whole lesson in one row: the day was corrected and its
derived copy was not. ORDER 2's guard makes that impossible from here on.
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
SRC = ("https://www.sec.gov/Archives/edgar/data/1088856/000162828026050607/"
       "cort072926ex991pressrelease.htm")


def main():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    a, b = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[a:b])
    n = 0
    for r in rows:
        if r.get("id") != "readout_cort_2026-09-15":
            continue
        assert r.get("d") == "2026-12-17" and r.get("type") == "PDUFA", r
        r["id"] = "pdufa_cort_2026-12-17"
        r["dm"] = "2026-12"
        r["ta"] = "Endocrinology / Metabolic"
        r["url"] = "/pdufa/CORT-relacorilant"
        dd = r.setdefault("_d", {})
        dd["indication"] = "Cushing's syndrome (hypercortisolism)"
        dd["source"] = "Corcept 8-K 2026-07-29 (EX-99.1)"
        dd["source_url"] = SRC
        dd["nct_id"] = {"nct": "NCT06108219"}
        dd["review"] = ("Corcept resubmitted the NDA for relacorilant in Cushing's syndrome in "
                        "June 2026, after a December 2025 CRL, and states a PDUFA date of "
                        "December 17, 2026 in its second-quarter release.")
        n += 1
        print(f"  {r['id']}: dm=2026-12, ta=Endocrinology / Metabolic, indication filled, "
              f"url -> /pdufa/CORT-relacorilant, sourced to Corcept 8-K 2026-07-29")
    io.open(DATASET, "w", encoding="utf-8").write(
        src[:a] + json.dumps(rows, indent=1, ensure_ascii=False) + src[b:])
    print(f"{n} row(s) fixed")
    return 0 if n == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
