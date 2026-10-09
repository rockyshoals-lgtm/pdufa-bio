# -*- coding: utf-8 -*-
"""apply_1009_mrk_withdrawn.py -- Merck/Daiichi Sankyo ifinatamab deruxtecan (I-DXd) BLA voluntarily withdrawn.

Audit 2026-10-08 P0 (measured 23:06 to 23:25 Eastern): the homepage, /build-info.json (next_ticker MRK,
next_days 2), /pdufa/MRK-ifinatamab-deruxtecan and API row pdufa_mrk_2026-10-10 all said the FDA decides
on I-DXd on Saturday 2026-10-10. The application was withdrawn 13 days earlier.

Verified 2026-10-08 (Pacific) against the primary source, merck.com:
  "Ifinatamab Deruxtecan Biologics License Application for Certain Patients with Previously Treated
   Extensive-Stage Small Cell Lung Cancer Voluntarily Withdrawn", September 25, 2026 4:30 pm EDT
   (Business Wire newsitemid 20260925284187):
   "The decision to withdraw the BLA is based on discussions with the U.S. Food and Drug Administration
    (FDA) that data supporting the application, including from the IDeate-Lung01 Phase 2 trial, do not
    satisfy requirements needed to support an accelerated approval for the proposed indication."
   Enrollment continues in the IDeate-Lung02 Phase 3 trial.
  Goal date 2026-10-10 stays as recorded, from the Merck 10-Q of 2026-05-04 (unchanged).

A withdrawal is neither an approval nor a CRL: st "Withdrawn", no decision date, no outcome, and it is
never in the FDA-decision timing statistic. The row also leaves api/data.js SLATE (the homepage forward
list), which is not pruned by any decision sweep. Facts only; not investment advice.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
DATAJS = os.path.join(HERE, "pdufa_site_src", "api", "data.js")
MERCK = ("https://www.merck.com/news/ifinatamab-deruxtecan-biologics-license-application-for-certain-patients-"
         "with-previously-treated-extensive-stage-small-cell-lung-cancer-voluntarily-withdrawn/")
RID = "pdufa_mrk_2026-10-10"

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
r = next(x for x in rows if x["id"] == RID)
r.update({"st": "Withdrawn", "ta": r.get("ta") or "Oncology",
          "name": "Ifinatamab deruxtecan (I-DXd)", "url": "/pdufa/MRK-ifinatamab-deruxtecan",
          "ua": "2026-10-09T04:30:00Z"})
for k in ("oc", "dcd"):
    r.pop(k, None)
d = r.setdefault("_d", {})
d.pop("days_to_decision", None)
d.update({
    "withdrawn_date": "2026-09-25",
    "withdrawn_by": "Merck and Daiichi Sankyo",
    "withdrawn_source": "Merck and Daiichi Sankyo release, September 25, 2026",
    "withdrawn_source_url": MERCK,
    "withdrawn_quote": ("The decision to withdraw the BLA is based on discussions with the U.S. Food and Drug "
                        "Administration (FDA) that data supporting the application, including from the "
                        "IDeate-Lung01 Phase 2 trial, do not satisfy requirements needed to support an "
                        "accelerated approval for the proposed indication."),
    "withdrawn_note": ("Merck and Daiichi Sankyo voluntarily withdrew the BLA (accelerated approval, ES-SCLC after "
                       "platinum-based chemotherapy) on September 25, 2026, fifteen days before its October 10, "
                       "2026 goal date. No FDA decision was issued. Enrollment continues in the IDeate-Lung02 "
                       "Phase 3 trial."),
    "trial": "IDeate-Lung01 (NCT05280470)",
})
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print(f"  {RID}: st Withdrawn, withdrawn_date 2026-09-25 (Merck release); goal 2026-10-10 kept (10-Q)")

s = io.open(DATAJS, encoding="utf-8").read()
k = s.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(s[k:])
n0 = len(slate["catalysts"])
slate["catalysts"] = [c for c in slate["catalysts"]
                      if not (c.get("ticker") == "MRK" and str(c.get("date"))[:10] == "2026-10-10")]
if len(slate["catalysts"]) != n0:
    io.open(DATAJS, "w", encoding="utf-8").write(s[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":")) + s[k + end:])
print(f"  api/data.js SLATE: {n0} -> {len(slate['catalysts'])} catalysts")
