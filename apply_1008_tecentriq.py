# -*- coding: utf-8 -*-
"""apply_1008_tecentriq.py -- Tecentriq (atezolizumab) adjuvant Stage III dMMR colon cancer, approved 2026-10-08.

Resolves the two held watcher leads of 2026-10-08 (GitHub quarantine notice, held since 2026-10-08T18:33:04Z UTC):
  [drug_pages]     tecentriq|fda-oncology-notifications
  [fda_drugs_feed] pdufa_rhhby_2026-10-09|http://www.fda.gov/drugs/resources-information-approved-drugs/
                   fda-approves-atezolizumab-combination-chemotherapy-stage-iii-mismatch-repair-deficient-colon-cancer
Both are the same real event. Verified 2026-10-08 (Pacific) against primary sources before writing:

  FDA, Oncology/Hematologic Malignancies approval notification, published Thu 10/08/2026 13:44 (Eastern):
    "On October 8, 2026, the Food and Drug Administration approved atezolizumab (Tecentriq, Genentech, Inc.)
     in combination with a fluoropyrimidine and oxaliplatin for the adjuvant treatment of adult and pediatric
     patients two years of age and older with Stage III mismatch repair deficient (dMMR) colon cancer."
    Also Tecentriq Hybreza (atezolizumab and hyaluronidase-tqjs), patients 12+ weighing >= 40 kg.
    ATOMIC/ML39057 (NCT02912559): 711 adults + 1 pediatric patient, 1:1 atezolizumab + mFOLFOX6 (12 cycles)
    then atezolizumab 6 months vs mFOLFOX6 alone; investigator DFS HR 0.50 (95% CI 0.35, 0.73), p 0.0001,
    median DFS not reached in either arm. Priority review; Project Orbis (TGA, Health Canada, Israel MoH,
    Swissmedic). Letter not yet on Drugs@FDA ("will be posted").
  Goal date: Genentech release 2026-06-10 (already the row's source): "The FDA has granted Priority Review
    and is expected to make a decision on the approval by October 9, 2026."
  Both dates come from documents that state them -> the 1-day-early margin is allowed (standing rule).
  Genentech had posted no approval release on gene.com when this was written.
The row keeps d = goal date (2026-10-09), dcd = action date (2026-10-08): the Atebrioz pattern.
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
CONF = os.path.join(HERE, "_drug_approvals_confirmed.json")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
NOTICE = ("https://www.fda.gov/drugs/resources-information-approved-drugs/"
          "fda-approves-atezolizumab-combination-chemotherapy-stage-iii-mismatch-repair-deficient-colon-cancer")
RID = "pdufa_rhhby_2026-10-09"

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
r = next(x for x in rows if x["id"] == RID)
r.update({"name": "Tecentriq (atezolizumab) - adjuvant Stage III dMMR colon cancer", "ta": "Oncology",
          "st": "Decided", "oc": "Approved", "dcd": "2026-10-08",
          "url": "/fda-decision/RHHBY-2026-10-08", "ua": NOW})
d = r.setdefault("_d", {})
d.update({
    "nct_id": "NCT02912559", "brand": "Tecentriq", "inn": "atezolizumab",
    "indication": ("In combination with a fluoropyrimidine and oxaliplatin, adjuvant treatment of adult and pediatric "
                   "patients two years of age and older with Stage III mismatch repair deficient (dMMR) colon cancer"),
    "indication_short": "adjuvant treatment of Stage III mismatch repair deficient (dMMR) colon cancer, with chemotherapy",
    "title_indication": "dMMR Colon Cancer",
    "seo_desc": ("Tecentriq (atezolizumab) was approved by the FDA on October 8, 2026 with chemotherapy as adjuvant "
                 "treatment for Stage III dMMR colon cancer, based on ATOMIC."),
    "decision_source": "FDA approval notification, October 8, 2026 (Oncology/Hematologic Malignancies)",
    "decision_source_url": NOTICE,
    "fda_notice_title": ("FDA approves atezolizumab in combination with chemotherapy for Stage III mismatch repair "
                         "deficient colon cancer"),
    "decision_quote": ("On October 8, 2026, the Food and Drug Administration approved atezolizumab (Tecentriq, Genentech, "
                       "Inc.) in combination with a fluoropyrimidine and oxaliplatin for the adjuvant treatment of adult "
                       "and pediatric patients two years of age and older with Stage III mismatch repair deficient (dMMR) "
                       "colon cancer."),
    "fda_action_date": "2026-10-08", "fda_action_source_url": NOTICE,
    "fda_action_record": "FDA approval notification (sBLA; letter not yet on Drugs@FDA)",
    "decision_date_note": ("The FDA's notification is dated October 8, 2026 and states the approval was made that day. "
                           "The goal date, October 9, 2026, is from Genentech's release of June 10, 2026."),
    "review": ("Supplemental BLA, Priority Review, reviewed under Project Orbis. ATOMIC/ML39057 (NCT02912559): 711 adults "
               "and one pediatric patient with resected Stage III dMMR colon cancer, randomized 1:1 to atezolizumab plus "
               "mFOLFOX6 for 12 cycles then atezolizumab for 6 months, or mFOLFOX6 alone; investigator-assessed DFS hazard "
               "ratio 0.50 (95% CI 0.35 to 0.73; p 0.0001), median DFS not reached in either arm. Tecentriq Hybreza "
               "(atezolizumab and hyaluronidase-tqjs) approved for the same use in patients 12 and older weighing at "
               "least 40 kg (FDA notification)."),
})
d.pop("goal_unsourced", None)
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print(f"  {RID}: Decided/Approved, dcd 2026-10-08 (FDA notification), goal 2026-10-09 (Genentech 2026-06-10)")

c = json.load(io.open(CONF, encoding="utf-8"))
if not any(a.get("slug") == "tecentriq" and a.get("date") == "2026-10-08" for a in c["approvals"]):
    c["approvals"].append({"slug": "tecentriq", "date": "2026-10-08", "brand": "Tecentriq", "source": NOTICE})
    io.open(CONF, "w", encoding="utf-8").write(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
    print("  + _drug_approvals_confirmed: tecentriq 2026-10-08")
