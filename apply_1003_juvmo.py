# -*- coding: utf-8 -*-
"""apply_1003_juvmo.py -- audit 2026-10-03, Tier 0 item 0.1: publish the JUVMO approval (verified).

ABBV tavapadon (TEMPO), row pdufa_abbv_2026-12-31 (month-only "December 2026", goal never stated
by AbbVie in any filing -- see the row's date_note):

  Drugs@FDA (openFDA, last_updated 2026-10-02), read 2026-10-03:
    NDA 220415, ABBVIE INC, brand JUVMO, ORIG-1, submission_status AP, status date 20260925,
    review priority TYPE 1 (new molecular entity),
    letter https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/220415Orig1s000ltr.pdf
  AbbVie, PR Newswire, Sept. 28, 2026 (news.abbvie.com, read 2026-10-03):
    "the U.S. Food and Drug Administration (FDA) has approved JUVMO(TM) (tavapadon) tablets as the
     first and only selective D1/D5 receptor agonist for the treatment of adults with Parkinson's
     disease"; "AbbVie expects to make JUVMO available to patients in the U.S. in October 2026."

So: Decided / Approved. The FDA acted Friday 2026-09-25 (letter); the first public word was
AbbVie's Monday 2026-09-28 release, so dcd (first public day, the site's convention, as on
Lipfendra and WINREVAIR) is 2026-09-28 and fda_action_date is 2026-09-25. goal_unsourced: AbbVie
never published a goal date, so no early/late margin is computed (site_windows.earliness_allowed).
Facts only; not investment advice.
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

LETTER = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/220415Orig1s000ltr.pdf"
REL = "https://news.abbvie.com/2026-09-28-U-S-FDA-Approves-AbbVies-JUVMO-TM-tavapadon-for-Parkinsons-Disease"

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
n = 0
for r in rows:
    if r["id"] != "pdufa_abbv_2026-12-31":
        continue
    if r["st"] == "Decided":
        print("  pdufa_abbv_2026-12-31: already Decided"); break
    assert r["st"] == "Upcoming" and r["t"] == "ABBV", r
    r["st"], r["oc"], r["dcd"] = "Decided", "Approved", "2026-09-28"
    r["name"] = "JUVMO (tavapadon)"
    r["ta"] = r.get("ta") or "Neurology"
    r["ua"] = NOW
    d = r.setdefault("_d", {})
    d.update({
        "brand": "JUVMO",
        "inn": "tavapadon",
        "indication": "Parkinson's disease in adults (once daily, with or without levodopa)",
        "indication_short": "Parkinson's disease in adults",
        "decision_source": "FDA approval letter, NDA 220415, September 25, 2026 (Drugs@FDA)",
        "decision_source_url": LETTER,
        "announcement_url": REL,
        "announcement_date": "2026-09-28",
        "decision_quote": ("the U.S. Food and Drug Administration (FDA) has approved JUVMO (tavapadon) tablets "
                           "as the first and only selective D1/D5 receptor agonist for the treatment of adults "
                           "with Parkinson's disease"),
        "fda_action_date": "2026-09-25",
        "fda_action_source_url": LETTER,
        "fda_action_record": "NDA 220415 ORIG-1",
        "goal_unsourced": True,
        "goal_note": ("AbbVie never published a PDUFA goal date for tavapadon: EDGAR full-text search for "
                      "\"tavapadon\" with \"target action date\" returns no filings, and the day we once carried "
                      "was withdrawn on 2026-09-10. The approval is sourced to the FDA's letter; no early/late "
                      "margin is computed."),
        "review": ("NDA 220415, approved September 25, 2026 (FDA letter); AbbVie announced it September 28, 2026. "
                   "AbbVie describes JUVMO as the first selective D1/D5 receptor agonist approved for adults with "
                   "Parkinson's disease, taken once daily with or without levodopa, and expects U.S. availability "
                   "in October 2026. Supported by the Phase 3 TEMPO program (TEMPO-1, -2 and -3, with the "
                   "TEMPO-4 open-label extension)."),
    })
    n += 1
    print("  pdufa_abbv_2026-12-31: Upcoming -> Decided/Approved; FDA 2026-09-25 (NDA 220415), announced 2026-09-28")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print(f"{n} row(s) updated")
