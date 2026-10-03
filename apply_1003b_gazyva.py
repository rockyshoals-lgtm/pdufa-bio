# -*- coding: utf-8 -*-
"""apply_1003b_gazyva.py -- audit 2026-10-03, Tier 2 item 2.6: Gazyva (obinutuzumab), idiopathic nephrotic syndrome.

Verified 2026-10-03 before writing:
  FDA, CDER "News & Events for Human Drugs", published Fri 09/25/2026 13:51 (Eastern):
    https://www.fda.gov/drugs/news-events-human-drugs/fda-approves-drug-treat-idiopathic-nephrotic-syndrome-patients-2-years-and-older
    "FDA has approved Gazyva (obinutuzumab) injection to reduce the risk of relapse in adult and pediatric
     patients 2 years of age and older with frequently relapsing or steroid-dependent, childhood-onset,
     idiopathic nephrotic syndrome who are in remission."  Breakthrough Therapy, Orphan Drug and Priority
     Review designations; INShore (NCT05627557), 85 patients, vs mycophenolate mofetil.
  Drugs@FDA (openFDA, last_updated 2026-10-02): BLA 125486, GENENTECH, SUPPL-43, class EFFICACY, AP 20260925,
    letter https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/125486Orig1s043ltr.pdf

The FDA letter and the FDA notice carry the same day, so the action date is FDA-sourced. pdufa.bio holds no
goal date for this supplement (Roche is not an SEC registrant and we hold no release stating one), so
goal_unsourced and no early/late margin. Same row shape as Lipfendra (pdufa_mrk_2026-07-16). Facts only.
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
NOTICE = ("https://www.fda.gov/drugs/news-events-human-drugs/"
          "fda-approves-drug-treat-idiopathic-nephrotic-syndrome-patients-2-years-and-older")
LETTER = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/125486Orig1s043ltr.pdf"

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
RID = "pdufa_rhhby_2026-09-25"
if any(r["id"] == RID for r in rows):
    print(f"  {RID} already present")
else:
    rows.append({
        "id": RID, "t": "RHHBY", "company": "Roche Holding AG", "d": "2026-09-25", "dp": "day",
        "name": "Gazyva (obinutuzumab) - idiopathic nephrotic syndrome", "type": "PDUFA", "ta": "Nephrology",
        "cap": "Large", "st": "Decided", "url": "/fda-decision/RHHBY-2026-09-25", "ua": NOW,
        "oc": "Approved", "dcd": "2026-09-25",
        "_d": {
            "nct_id": "NCT05627557",
            "brand": "Gazyva", "inn": "obinutuzumab",
            "indication": ("Frequently relapsing or steroid-dependent, childhood-onset idiopathic nephrotic syndrome "
                           "in patients 2 years and older who are in remission (reduce the risk of relapse)"),
            "indication_short": "idiopathic nephrotic syndrome (ages 2+)",
            "source": "FDA notice 2026-09-25 (CDER News & Events for Human Drugs)", "source_url": NOTICE,
            "decision_source": "FDA approval letter, BLA 125486 supplement 043, September 25, 2026 (Drugs@FDA)",
            "decision_source_url": LETTER,
            "announcement_url": NOTICE,
            "fda_notice_title": "FDA Approves Drug to Treat Idiopathic Nephrotic Syndrome in Patients 2 Years and Older",
            "decision_quote": ("FDA has approved Gazyva (obinutuzumab) injection to reduce the risk of relapse in adult "
                               "and pediatric patients 2 years of age and older with frequently relapsing or "
                               "steroid-dependent, childhood-onset, idiopathic nephrotic syndrome who are in remission."),
            "fda_action_date": "2026-09-25", "fda_action_source_url": LETTER,
            "fda_action_record": "BLA 125486 SUPPL-43",
            "goal_unsourced": True,
            "goal_note": ("pdufa.bio holds no goal date for this supplemental BLA: Roche is not an SEC registrant and we "
                          "hold no release stating one. The approval is sourced to the FDA's letter and notice; no "
                          "early/late margin is computed."),
            "review": ("Supplemental BLA (efficacy) approved September 25, 2026 with Breakthrough Therapy, Orphan Drug "
                       "and Priority Review designations (FDA notice). Phase 3 INShore (NCT05627557), 85 patients aged 2 "
                       "and older, Gazyva versus mycophenolate mofetil. Gazyva was previously approved for certain "
                       "cancers and for adults with active lupus nephritis."),
        }})
    rows.sort(key=lambda r: (str(r.get("d") or "9999"), str(r.get("t") or "")))
    print(f"  + {RID} Gazyva INS, Decided/Approved 2026-09-25 (BLA 125486 S-043 letter + FDA notice)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
