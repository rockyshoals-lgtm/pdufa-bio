# -*- coding: utf-8 -*-
"""apply_1118c_kygevvi.py -- the AGIO 2025-11-03 decision page recorded UCB's Kygevvi approval as an Agios approval.

2026-11-18 (David, 2026-11-18 Eastern: "Yes, fix Kygevvi"). Found by the design red team (change 4): /decisions,
/fda-decision/AGIO-2025-11-03, /drug/kygevvi and the run-up study listed Kygevvi (doxecitine and doxribtimine),
approved November 3, 2025, as an Agios (AGIO) approval. Drugs@FDA names the applicant of NDA 219792 as UCB Inc
(_fda_approvals_months.json, from openFDA, with the FDA approval letter), and FDA's Drug Trials Snapshot names UCB.
verify_decisions.py had matched the drug name and the action date and never compared the sponsor. Agios had no FDA
action that day; its Aqvesme (mitapivat) approval of December 23, 2025 keeps its own page.

Retired the same way as apply_1118_retire_decisions.py retires a page (that script's main, with this one slug):
page deleted, a permanent redirect to /ticker/AGIO, every link removed, the verification entry marked retracted,
the ledgers pruned and a /corrections entry added. runup_study_exclusions.json lists the page, so
curate_runup_study.py moves the row out of the run-up study with the reason. RETIRE joins RETRACTED in
tests/test_no_retracted_claims.py. The redirect goes to /ticker/AGIO, as the earlier retirements go to the ticker's
hub: /drug/kygevvi was built only from this row, so the next rebuild drops it and it cannot be the destination.
Idempotent. Facts only, not investment advice.

    python apply_1118c_kygevvi.py [--dry-run]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

WHY = ("FDA approved Kygevvi (doxecitine and doxribtimine) on November 3, 2025 under NDA 219792, whose applicant is "
       "UCB, not Agios. Agios had no FDA action that day; its Aqvesme (mitapivat) approval of December 23, 2025 has "
       "its own page.")
SRC = ("Drugs@FDA, NDA 219792 (applicant UCB Inc, approved 2025-11-03), and the FDA approval letter "
       "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2025/219792Orig1000ltr.pdf")
WAS = "A decision page for AGIO dated 2025-11-03 recording UCB's Kygevvi approval as an Agios approval."

# slug -> (redirect destination, one-line reason, source): the shape tests/test_no_retracted_claims.py reads
RETIRE = {"AGIO-2025-11-03": ("/ticker/AGIO", WHY, SRC)}

EXCLUSION = {
    "reason": "the decision is UCB's (Kygevvi, NDA 219792), not Agios's; no Agios FDA action on this date",
    "cited_source": "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2025/219792Orig1000ltr.pdf",
    "document": "FDA approval letter, NDA 219792 (Kygevvi), applicant UCB Inc",
    "finding": "Drugs@FDA lists UCB Inc as the applicant; the page and the study row had put the approval on AGIO.",
    "checked": "2026-11-18",
}


def main():
    import apply_1118_retire_decisions as R
    R.RETIRE = {s: (dst, why, src, WAS) for s, (dst, why, src) in RETIRE.items()}
    R.main()
    if "--dry-run" in sys.argv:
        return
    p = os.path.join(HERE, "runup_study_exclusions.json")
    ex = json.load(open(p, encoding="utf-8"))
    pages = ex.setdefault("pages", {})
    n = 0
    for s in RETIRE:
        if pages.get(s) != EXCLUSION:
            pages[s] = EXCLUSION
            n += 1
    if n:
        open(p, "w", encoding="utf-8").write(json.dumps(ex, indent=1, ensure_ascii=False))
    print(f"runup_study_exclusions.json: {n} entr(ies) added")


if __name__ == "__main__":
    main()
