# -*- coding: utf-8 -*-
"""BAYRY KERENDIA (finerenone) sNDA S-011, CKD associated with type 1 diabetes: approved 2026-09-16.

Lead: CI's drug-page approval watch (run 35941781377, 2026-09-24 01:12 UTC) -- Drugs@FDA shows
NDA 215341 SUPPL-11 AP 2026-09-16, class EFFICACY. Verified against two primary documents:

  FDA approval letter 215341Orig1s011ltr.pdf (signed 09/16/2026 03:37 PM): "Please refer to your
    supplemental new drug application (sNDA) dated March 16, 2026, received March 16, 2026 ...
    This Prior Approval supplemental new drug application provides for the following new
    indication: To reduce urinary albumin-to-creatinine ratio, which is expected to reduce the
    risk of sustained estimated glomerular filtration rate decline and end-stage kidney disease in
    adults with chronic kidney disease associated with Type 1 diabetes mellitus ... It is
    approved, effective on the date of this letter."
  Bayer release, Berlin, September 17, 2026 (08:30 CEST): "Bayer announced today that the U.S. Food
    and Drug Administration (FDA) has approved Kerendia (finerenone) ... for the treatment of adult
    patients with chronic kidney disease (CKD) associated with type 1 diabetes (T1D)."

Goal date: Bayer never published one. Its May 21, 2026 release states acceptance and Priority
Review only. The "December 2026" the row carried was month-precision and unbacked (one of the five
rows the 09-20 audit listed for a ruling). A priority clock from a March 16 receipt would land on
September 16 -- the action date -- but that is an inference, not a sponsor statement, so no margin
is published: goal_unsourced. The FDA action date (09-16) precedes the announcement (09-17) and is
the decision date.
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
LETTER = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/215341Orig1s011ltr.pdf"
PR = ("https://www.bayer.com/media/en-us/us-fda-approves-finerenone-for-new-indication-in-patients-with-"
      "chronic-kidney-disease-associated-with-type-1-diabetes/")

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
n = 0
for r in rows:
    if r["id"] != "pdufa_bayry_2026-12-31":
        continue
    assert r["st"] == "Upcoming" and r["dp"] == "month", r
    r["st"], r["oc"], r["dcd"] = "Decided", "Approved", "2026-09-16"
    r["name"] = "KERENDIA (finerenone), T1D-CKD"
    r["ua"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    dd = r.setdefault("_d", {})
    dd["brand"] = "KERENDIA"
    dd["indication"] = "Chronic kidney disease associated with type 1 diabetes (new indication)"
    dd["fda_action_date"] = "2026-09-16"
    dd["goal_unsourced"] = True
    dd["goal_note"] = ("Bayer never published a PDUFA goal date for this sNDA: its May 21, 2026 release states "
                       "acceptance and Priority Review only, and the December 2026 this row carried was an "
                       "unbacked month. The approval stands and is sourced to the FDA's own letter; no goal-date "
                       "margin is published.")
    dd["decision_source"] = "FDA approval letter NDA 215341/S-011 dated September 16, 2026 (Drugs@FDA)"
    dd["decision_source_url"] = LETTER
    dd["decision_quote"] = ("This Prior Approval supplemental new drug application provides for the following new "
                            "indication: To reduce urinary albumin-to-creatinine ratio ... in adults with chronic "
                            "kidney disease associated with Type 1 diabetes mellitus. ... It is approved, effective "
                            "on the date of this letter.")
    dd["announcement_url"] = PR
    dd["review"] = ("Supplemental NDA (S-011, submitted March 16, 2026, Priority Review) approved September 16, "
                    "2026: a third U.S. indication, CKD associated with type 1 diabetes, based on the Phase III "
                    "FINE-ONE study. Bayer announced it on September 17, 2026.")
    n += 1
    print(f"  {r['id']}: Upcoming (Dec 2026, unbacked) -> Decided/Approved 2026-09-16 (goal unsourced, no margin)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print(f"{n} row(s)")

# the drug-page watch's ledger of verified approvals
P = os.path.join(HERE, "_drug_approvals_confirmed.json")
led = json.load(io.open(P, encoding="utf-8"))
if not any(a.get("slug") == "kerendia" and a.get("date") == "2026-09-16" for a in led["approvals"]):
    led["approvals"].append({"slug": "kerendia", "date": "2026-09-16", "brand": "KERENDIA",
                             "source": LETTER, "note": "sNDA S-011, CKD associated with type 1 diabetes; Bayer release 2026-09-17"})
    io.open(P, "w", encoding="utf-8", newline="\n").write(json.dumps(led, indent=1, ensure_ascii=False) + "\n")
    print("  _drug_approvals_confirmed.json: + kerendia 2026-09-16")
