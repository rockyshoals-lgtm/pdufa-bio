# -*- coding: utf-8 -*-
"""apply_1004_jaypirca.py -- Jaypirca (pirtobrutinib), previously untreated CLL/SLL, approved 2026-10-02.

David, 2026-10-04: "yes, publish the page". Verified before writing (2026-10-04, Pacific):
  FDA, Oncology/Hematologic Malignancies approval notification, published Fri 10/02/2026 15:31 (Eastern):
    https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-pirtobrutinib-previously-untreated-chronic-lymphocytic-leukemia-or-small-lymphocytic
    "On October 2, 2026, the Food and Drug Administration approved pirtobrutinib (Jaypirca, Eli Lilly and
     Company) for adult patients with previously untreated chronic lymphocytic leukemia (CLL) or small
     lymphocytic lymphoma (SLL) with no known 17p deletion."
    BRUIN CLL-313 (NCT05023980): randomized, open-label, active-controlled; 282 patients, 1:1 pirtobrutinib
    (n=141) vs bendamustine plus a rituximab product (n=141, six cycles). IRC-assessed PFS: median not
    estimable vs 33.5 months; HR 0.20 (95% CI 0.11-0.37), p<0.0001; median PFS follow-up 28 months; OS
    immature. Dose 200 mg orally once daily. Orphan drug designation.
  Lilly release, PR Newswire, INDIANAPOLIS Oct. 2, 2026 (lilly.mediaroom.com, listed on Lilly's own news index).
  Drugs@FDA (openFDA last_updated 2026-10-02): NDA 216059 shows no 2026-10-02 supplement yet; the letter is
    not posted. The FDA notice itself states the action day, so fda_action_date is FDA-sourced (the notice);
    sync_fda_action_dates.py swaps in the letter when Drugs@FDA posts it.
  Goal date: Lilly guided only "second half of 2026"; pdufa.bio holds no goal day -> goal_unsourced, no margin.
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
NOTICE = ("https://www.fda.gov/drugs/resources-information-approved-drugs/"
          "fda-approves-pirtobrutinib-previously-untreated-chronic-lymphocytic-leukemia-or-small-lymphocytic")
LILLY = ("https://lilly.mediaroom.com/2026-10-02-Lillys-Jaypirca-pirtobrutinib-,-the-first-and-only-approved-"
         "non-covalent-BTK-inhibitor,-receives-expanded-indication-from-U-S-FDA-for-certain-patients-with-"
         "previously-untreated-CLL-SLL")

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
RID = "pdufa_lly_2026-10-02"
company = next((r["company"] for r in rows if r.get("t") == "LLY" and r.get("company")), "Eli Lilly and Company")
if any(r["id"] == RID for r in rows):
    print(f"  {RID} already present")
else:
    rows.append({
        "id": RID, "t": "LLY", "company": company, "d": "2026-10-02", "dp": "day",
        "name": "Jaypirca (pirtobrutinib) - previously untreated CLL/SLL", "type": "PDUFA", "ta": "Oncology",
        "cap": "Large", "st": "Decided", "url": "/fda-decision/LLY-2026-10-02", "ua": NOW,
        "oc": "Approved", "dcd": "2026-10-02",
        "_d": {
            "nct_id": "NCT05023980", "brand": "Jaypirca", "inn": "pirtobrutinib",
            "indication": ("Adult patients with previously untreated chronic lymphocytic leukemia (CLL) or small "
                           "lymphocytic lymphoma (SLL) with no known 17p deletion"),
            "indication_short": "adults with previously untreated chronic lymphocytic leukemia (CLL) or small lymphocytic lymphoma (SLL) with no known 17p deletion",
            "title_indication": "First-Line CLL/SLL",
            "seo_desc": ("Jaypirca (pirtobrutinib) was approved by the FDA on October 2, 2026 for previously untreated "
                         "CLL/SLL with no known 17p deletion, based on BRUIN CLL-313."),
            "source": "FDA approval notification 2026-10-02 (Oncology/Hematologic Malignancies)", "source_url": NOTICE,
            "decision_source": "FDA approval notification, October 2, 2026", "decision_source_url": NOTICE,
            "announcement_url": LILLY,
            "decision_quote": ("On October 2, 2026, the Food and Drug Administration approved pirtobrutinib (Jaypirca, "
                               "Eli Lilly and Company) for adult patients with previously untreated chronic lymphocytic "
                               "leukemia (CLL) or small lymphocytic lymphoma (SLL) with no known 17p deletion."),
            "fda_action_date": "2026-10-02", "fda_action_source_url": NOTICE,
            "fda_action_record": "FDA approval notification, NDA 216059",
            "goal_unsourced": True,
            "goal_note": ("Lilly guided a U.S. decision only to the second half of 2026; pdufa.bio holds no goal day "
                          "for this supplement, so no early or late margin is computed."),
            "review": ("Supplemental NDA 216059 for first-line use. BRUIN CLL-313 (NCT05023980): 282 previously untreated "
                       "patients without 17p deletion, randomized 1:1 to pirtobrutinib or bendamustine plus rituximab; "
                       "IRC-assessed PFS hazard ratio 0.20 (95% CI 0.11 to 0.37), median PFS not estimable vs 33.5 "
                       "months at a median follow-up of 28 months; OS immature. 200 mg orally once daily. Orphan drug "
                       "designation (FDA notification)."),
        }})
    rows.sort(key=lambda r: (str(r.get("d") or "9999"), str(r.get("t") or "")))
    print(f"  + {RID} Jaypirca first-line CLL/SLL, Decided/Approved 2026-10-02 (FDA notification states the day)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
