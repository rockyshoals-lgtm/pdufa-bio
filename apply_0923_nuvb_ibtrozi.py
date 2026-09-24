# -*- coding: utf-8 -*-
"""NUVB IBTROZI (taletrectinib) sNDA S-004: approved 2026-09-16, 110 days before its 2027-01-04 goal.

Lead: CI's early-approval watch (run 35941216525, 2026-09-24 01:04 UTC) -- Drugs@FDA shows
NDA 219713 SUPPL-4 AP 2026-09-16, class EFFICACY. Verified against two primary documents:

  FDA approval letter 219713Orig1s004ltr.pdf (posted 2026-09-21, signed 09/16/2026 01:15 PM):
    "Please refer to your supplemental new drug application (sNDA) dated and received March 4,
    2026 ... This Prior Approval sNDA provides for updated response rates and duration of
    response data for patients in the TRUST-I and TRUST-II studies ... It is approved, effective
    on the date of this letter."
  Nuvation Bio release, dateline NEW YORK, Sept. 16, 2026 (PRNewswire): "today announced that
    the U.S. Food and Drug Administration (FDA) has approved a supplemental New Drug Application
    (sNDA) for IBTROZI ... Approval comes four months ahead of PDUFA date."

Same application as our row: the 8-K of 2026-08-06 describes the sNDA "with updated efficacy
data in TKI-naive and TKI-pretreated advanced ROS1+ NSCLC, with a target action date of
January 4, 2027" -- March 4, 2026 + a 10-month standard clock = January 4, 2027. FDA action
date and announcement day coincide (09-16), so the margin is measurable: -110 days.
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
LETTER = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/219713Orig1s004ltr.pdf"
PR = ("https://www.prnewswire.com/news-releases/nuvation-bio-announces-fda-approval-of-supplemental-new-drug-"
      "application-for-ibtrozi-taletrectinib-with-updated-duration-of-response-in-tki-naive-advanced-ros1-"
      "positive-non-small-cell-lung-cancer-302881232.html")

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
n = 0
for r in rows:
    if r["id"] != "pdufa_nuvb_2027-01-04":
        continue
    assert r["d"] == "2027-01-04" and r["dp"] == "day" and r["st"] == "Upcoming", r
    r["st"], r["oc"], r["dcd"] = "Decided", "Approved", "2026-09-16"
    r["ua"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    dd = r.setdefault("_d", {})
    dd["brand"] = "IBTROZI"
    dd["fda_action_date"] = "2026-09-16"
    dd["decision_source"] = "FDA approval letter NDA 219713/S-004 dated September 16, 2026 (Drugs@FDA)"
    dd["decision_source_url"] = LETTER
    dd["decision_quote"] = ("This Prior Approval sNDA provides for updated response rates and duration of "
                            "response data for patients in the TRUST-I and TRUST-II studies. ... It is approved, "
                            "effective on the date of this letter.")
    dd["announcement_url"] = PR
    dd["review"] = ("Supplemental NDA (S-004, submitted March 4, 2026) approved September 16, 2026, 110 days "
                    "before the January 4, 2027 goal date. Label update only: the TRUST-I TKI-naive median "
                    "duration of response (49.7 months) and longer follow-up from TRUST-I and TRUST-II enter "
                    "the label; the indication and the safety sections are unchanged.")
    n += 1
    print(f"  {r['id']}: Upcoming -> Decided/Approved 2026-09-16 (goal 2027-01-04 sourced, -110 days)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print(f"{n} row(s)")
