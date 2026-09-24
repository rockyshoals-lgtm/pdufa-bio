# -*- coding: utf-8 -*-
"""MRK WINREVAIR (sotatercept-csrk) HYPERION label update: approved, announced 2026-09-22.

Read first-hand before writing (Merck news release, September 22, 2026, 6:45 am EDT):
  "Merck ... today announced the U.S. Food and Drug Administration (FDA) has approved an update
  to the U.S. product label for WINREVAIR (sotatercept-csrk) for injection, 45mg, 60mg, based on
  the Phase 3 HYPERION trial ... Today's approval updates the WINREVAIR label to include efficacy
  and safety data from the HYPERION trial evaluating adults newly diagnosed with PAH".

The release says "today's approval", so the action date is taken as September 22, 2026, one day
after the sourced September 21 goal date (Merck 10-Q Q2 2026 / 8-K 2026-02-03). No FDA press
release and no 8-K (a label supplement); Drugs@FDA will carry the supplement action letter later
and the row says the margin follows the letter if it differs. This is the row that had CI blocked
since the morning of 09-22 ("MRK 2026-09-21 goal date passed, unmarked") -- verify-then-publish
working as designed.
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
PR = ("https://www.merck.com/news/u-s-fda-approves-update-to-the-label-for-winrevair-sotatercept-csrk-"
      "to-include-data-from-the-phase-3-hyperion-trial-evaluating-adults-recently-diagnosed-with-"
      "pulmonary-arterial-hypertensio/")

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
n = 0
for r in rows:
    if r["id"] != "pdufa_mrk_2026-09-21":
        continue
    assert r["d"] == "2026-09-21" and r["dp"] == "day" and r["st"] == "Upcoming", r
    r["st"], r["oc"], r["dcd"] = "Decided", "Approved", "2026-09-22"
    r["ua"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    dd = r.setdefault("_d", {})
    dd["brand"] = "WINREVAIR"
    dd["decision_source"] = "Merck news release 2026-09-22 (6:45 am EDT)"
    dd["decision_source_url"] = PR
    dd["decision_quote"] = ("Merck ... today announced the U.S. Food and Drug Administration (FDA) has approved an "
                            "update to the U.S. product label for WINREVAIR (sotatercept-csrk) for injection, 45mg, "
                            "60mg, based on the Phase 3 HYPERION trial.")
    dd["decision_date_note"] = ("2026-09-22 is the date of Merck's release, which calls it \"today's approval\"; the "
                                "FDA's supplement action letter is not yet in Drugs@FDA. If the letter is dated "
                                "earlier, the margin against the September 21 goal date will be corrected.")
    dd["review"] = ("Label update (supplemental application) approved September 22, 2026, one day after the "
                    "September 21 PDUFA goal date, adding HYPERION efficacy and safety data in adults newly "
                    "diagnosed with PAH (WHO Group 1) at intermediate to high risk. Not a new indication: the "
                    "approved indication is unchanged; the label gains HYPERION data and additional "
                    "hypersensitivity safety language.")
    n += 1
    print(f"  {r['id']}: Upcoming -> Decided/Approved 2026-09-22 (goal 2026-09-21 sourced, +1 day)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print(f"{n} row(s)")
