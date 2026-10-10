# -*- coding: utf-8 -*-
"""apply_1010_rhapsido.py -- Rhapsido (remibrutinib), symptomatic dermographism, FDA approval 2026-10-06.

Resolves the held lead [drug_pages] remibrutinib|openfda:20261006 (held since 2026-10-10T00:27:35Z UTC).
Verified 2026-10-10 (Pacific) before writing:
  openFDA drugsfda (FDA's Drugs@FDA data, last_updated 2026-10-09), NDA218436, NOVARTIS:
    SUPPL-1, submission_status AP, submission_status_date 20261006, class EFFICACY;
    letter listed: https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/218436Orig1s001ltr.pdf
    (the URL returned 404 on 2026-10-10: listed, not yet served; sync_fda_action_dates.py swaps it in).
  Novartis US media release, East Hanover, October 7, 2026: "the U.S. Food and Drug Administration (FDA)
    approved Rhapsido(R) (remibrutinib) ... as the first treatment for adults with symptomatic dermographism
    (SD) inadequately controlled by H1 antihistamines." RemIND SD cohort: complete response at Week 12,
    29.3% vs 14.0% placebo (p=0.0229). CSU approval (ORIG-1) 2025-09-30.
  The FDA action day (Oct 6, FDA data) and the announcement day (Oct 7, Novartis) differ; the FDA's is used.
  No goal date is held for this supplement -> goal_unsourced, no early/late margin. Facts only.
"""
import datetime as dt, io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
CONF = os.path.join(HERE, "_drug_approvals_confirmed.json")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
OVERVIEW = "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo=218436"
OPENFDA = 'https://api.fda.gov/drug/drugsfda.json?search=application_number:"NDA218436"'
NVS = ("https://www.novartis.com/us-en/news/media-releases/novartis-rhapsido-remibrutinib-receives-fda-approval-"
       "first-treatment-symptomatic-dermographism-sd-expanding-its-use-beyond-chronic-spontaneous-urticaria-csu")
RID = "pdufa_nvs_2026-10-06"
src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
if not any(r["id"] == RID for r in rows):
    rows.append({
        "id": RID, "t": "NVS", "company": "Novartis Ag", "d": "2026-10-06", "dp": "day",
        "name": "Rhapsido (remibrutinib) - symptomatic dermographism", "type": "PDUFA", "ta": "Immunology",
        "cap": "Large", "st": "Decided", "url": "/fda-decision/NVS-2026-10-06", "ua": NOW,
        "oc": "Approved", "dcd": "2026-10-06",
        "_d": {
            "brand": "Rhapsido", "inn": "remibrutinib",
            "indication": "Adults with symptomatic dermographism (SD) inadequately controlled by H1 antihistamines",
            "indication_short": "adults with symptomatic dermographism inadequately controlled by H1 antihistamines",
            "title_indication": "Dermographism",
            "seo_desc": ("Rhapsido (remibrutinib) was approved by the FDA on October 6, 2026 for adults with symptomatic "
                         "dermographism not controlled by H1 antihistamines."),
            "source": "Drugs@FDA (openFDA), NDA 218436 SUPPL-1, approved 2026-10-06", "source_url": OVERVIEW,
            "decision_source": "FDA record: Drugs@FDA NDA 218436, supplement 1 (efficacy), action date October 6, 2026",
            "decision_source_url": OVERVIEW,
            "announcement_url": NVS, "announcement": "Novartis media release, October 7, 2026",
            "decision_quote": ("Novartis announced today that the U.S. Food and Drug Administration (FDA) approved "
                               "Rhapsido (remibrutinib) ... as the first treatment for adults with symptomatic "
                               "dermographism (SD) inadequately controlled by H1 antihistamines."),
            "fda_action_date": "2026-10-06", "fda_action_source_url": OVERVIEW,
            "fda_action_record": "NDA 218436 S-001 (openFDA AP 2026-10-06; letter listed, not yet posted)",
            "decision_date_note": ("The FDA's action date, October 6, 2026, is from the FDA's Drugs@FDA data (openFDA). "
                                   "Novartis announced the approval on October 7, 2026."),
            "goal_unsourced": True,
            "goal_note": ("pdufa.bio holds no goal date for this supplemental NDA; no early or late margin is computed."),
            "review": ("Efficacy supplement to NDA 218436 (Rhapsido, first approved September 30, 2025 for chronic "
                       "spontaneous urticaria). Approval based on the symptomatic dermographism cohort of the Phase III "
                       "RemIND trial: complete response at Week 12 in 29.3% of patients on Rhapsido versus 14.0% on "
                       "placebo (p=0.0229), per Novartis."),
        }})
    rows.sort(key=lambda r: (str(r.get("d") or "9999"), str(r.get("t") or "")))
    print(f"  + {RID} Rhapsido SD, Decided/Approved 2026-10-06 (FDA data)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
c = json.load(io.open(CONF, encoding="utf-8"))
if not any(a.get("slug") == "remibrutinib" and a.get("date") == "2026-10-06" for a in c["approvals"]):
    c["approvals"].append({"slug": "remibrutinib", "date": "2026-10-06", "brand": "Rhapsido", "source": OVERVIEW})
    io.open(CONF, "w", encoding="utf-8").write(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
    print("  + _drug_approvals_confirmed: remibrutinib 2026-10-06")
