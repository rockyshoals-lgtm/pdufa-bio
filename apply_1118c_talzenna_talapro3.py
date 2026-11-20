# -*- coding: utf-8 -*-
"""apply_1118c_talzenna_talapro3.py -- Talzenna (talazoparib) with Xtandi (enzalutamide), HRR gene-mutated metastatic
castration-sensitive prostate cancer (TALAPRO-3), FDA approval October 26, 2026.

Found 2026-11-18: the FDA reconciliation listed it as unverifiable by name, and no row or decision page existed. Pfizer is
a tracked sponsor (PFE), and the application had a stated PDUFA window, so it belongs in the archive.
Verified 2026-11-18 (UTC; Pacific machine, Eastern market -- RULE 1), each page read itself:
  FDA, Resources for Information | Approved Drugs, "FDA approves talazoparib with enzalutamide for metastatic androgen
    pathway modulation-naive or -sensitive prostate cancer with HRR gene mutations" (content current as of 10/26/2026):
    "On October 26, 2026, the Food and Drug Administration (FDA) approved talazoparib (Talzenna, Pfizer Inc.) ..." with
    enzalutamide, for adults with HRR gene-mutated disease detected by an FDA-authorized test. TALAPRO-3 (NCT04821622):
    599 patients randomized 1:1; rPFS HR 0.48 (95% CI 0.36, 0.65), p<0.0001; median not reached vs 45.8 months.
    0.5 mg orally once daily with enzalutamide. Priority review; Project Orbis.
  Pfizer release (Business Wire), Monday October 26, 2026, 1:41 PM Eastern: the FDA "has expanded approval of" Talzenna
    with Xtandi for HRR gene-mutated metastatic hormone-sensitive prostate cancer.
  Goal: Pfizer release, July 22, 2026, 4:30 PM Eastern: "The FDA has set a Prescription Drug User Fee Act (PDUFA) action
    date in the last quarter of 2026." Stated to the quarter only, so no early or late margin is computed.
PFE closes: FMP historical-price-eod-light, read 2026-11-18; they match the cached closes through 2026-10-16.
Facts only; not investment advice.
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
DAY = "2026-10-26"
RID = "pdufa_pfe_2026-12-31"
PAGE_URL = "/fda-decision/PFE-2026-10-26"
FDA = ("https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-talazoparib-enzalutamide-"
       "metastatic-androgen-pathway-modulation-naive-or-sensitive")
PFE_REL = ("https://www.pfizer.com/news/press-release/press-release-detail/"
           "pfizers-talzenna-plus-xtandi-fda-approved-earlier")
GOAL = ("https://www.pfizer.com/news/press-release/press-release-detail/"
        "fda-grants-priority-review-pfizers-talzenna-plus-xtandi")
QUOTE = ("On October 26, 2026, the Food and Drug Administration (FDA) approved talazoparib (Talzenna, Pfizer Inc.) in "
         "combination with enzalutamide for the treatment of adults with metastatic androgen pathway modulation-na\u00efve "
         "or -sensitive (mAPMN/S) prostate cancer with homologous recombination repair (HRR) gene mutations, as "
         "detected by an FDA-authorized test.")
PFE_CLOSES = {"2026-10-19": 29.44, "2026-10-20": 30.11, "2026-10-21": 29.85, "2026-10-22": 30.42, "2026-10-23": 30.03,
              "2026-10-26": 29.79, "2026-10-27": 29.8, "2026-10-28": 29.45, "2026-10-29": 29.95, "2026-10-30": 30.52,
              "2026-11-02": 30.67, "2026-11-03": 30.0, "2026-11-04": 30.79, "2026-11-05": 29.88, "2026-11-06": 29.39,
              "2026-11-09": 29.23, "2026-11-10": 29.36, "2026-11-11": 29.45, "2026-11-12": 28.83, "2026-11-13": 28.89,
              "2026-11-16": 28.86, "2026-11-17": 28.46}


def jload(p, default=None):
    p = os.path.join(HERE, p)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else default


def jsave(p, d):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
if not any(r["id"] == RID for r in rows):
    new = ({
        "id": RID, "t": "PFE", "company": "Pfizer Inc.", "d": "2026-12-31", "dp": "quarter",
        "name": "Talzenna (talazoparib) with Xtandi (enzalutamide) - HRR-mutated metastatic castration-sensitive prostate cancer",
        "type": "PDUFA", "ta": "Oncology", "cap": "Large", "st": "Decided", "url": PAGE_URL, "ua": NOW,
        "oc": "Approved", "dcd": DAY,
        "_d": {
            "nct_id": "NCT04821622", "trial": "TALAPRO-3",
            "brand": "Talzenna", "inn": "talazoparib",
            "indication": ("Metastatic androgen pathway modulation-naive or -sensitive prostate cancer with HRR gene "
                           "mutations (with enzalutamide)"),
            "indication_short": "HRR gene-mutated metastatic castration-sensitive prostate cancer, with enzalutamide",
            "title_indication": "Prostate Cancer",
            "seo_desc": ("Talzenna (talazoparib) with Xtandi was approved by the FDA on October 26, 2026 for HRR "
                         "gene-mutated metastatic castration-sensitive prostate cancer, on TALAPRO-3."),
            "source": "Pfizer press release, July 22, 2026 (sNDA accepted for priority review)", "source_url": GOAL,
            "source_quote": ("The FDA has set a Prescription Drug User Fee Act (PDUFA) action date in the last quarter "
                             "of 2026."),
            "source_note": ("Pfizer stated the goal date to the quarter only (Q4 2026), so no early or late margin is "
                            "computed against the October 26, 2026 action day."),
            "decision_source": "FDA approval notification, October 26, 2026 (Resources for Information | Approved Drugs)",
            "decision_source_url": FDA,
            "fda_notice_title": ("FDA approves talazoparib with enzalutamide for metastatic androgen pathway "
                                 "modulation-na\u00efve or -sensitive prostate cancer with HRR gene mutations"),
            "decision_quote": QUOTE,
            "fda_action_date": DAY, "fda_action_source_url": FDA,
            "fda_action_record": "FDA approval notification, October 26, 2026 (NDA 211651 supplement)",
            "decision_date_note": ("The FDA's notification states the approval was granted on October 26, 2026. Pfizer "
                                   "announced it at 1:41 PM Eastern the same day, during the trading session."),
            "announcement_url": PFE_REL, "announcement": "Pfizer press release, October 26, 2026",
            "review": ("Supplemental NDA under Priority Review, reviewed under Project Orbis. Per the FDA, TALAPRO-3 "
                       "(NCT04821622) randomized 599 patients with HRR gene-mutated disease 1:1 to talazoparib or "
                       "placebo, each with enzalutamide and continuous androgen deprivation; radiographic "
                       "progression-free survival hazard ratio 0.48 (95% CI 0.36 to 0.65), p<0.0001, median not "
                       "reached versus 45.8 months. Talazoparib 0.5 mg orally once daily with enzalutamide."),
        }})
    # insert after the last row that sorts at or before it; the rest keep their order (a full re-sort moved ~200 rows)
    key = (new["d"], new["t"])
    at = max([k + 1 for k, r in enumerate(rows) if (str(r.get("d") or ""), str(r.get("t") or "")) <= key], default=0)
    rows.insert(at, new)
    print(f"  + {RID} Talzenna + Xtandi TALAPRO-3, Decided/Approved {DAY} (FDA notification; goal Q4 2026, no margin)")
asc = all(ord(ch) < 128 for ch in src)   # the file is stored ASCII-escaped; keep it that way
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=asc) + src[j:])

c = jload("_drug_approvals_confirmed.json")
if not any(a.get("slug") == "talzenna" and a.get("date") == DAY for a in c["approvals"]):
    c["approvals"].append({"slug": "talzenna", "date": DAY, "brand": "Talzenna", "source": FDA})
    jsave("_drug_approvals_confirmed.json", c)

faq = jload("_decision_extra_faq.json", {})
faq["PFE-2026-10-26"] = [
    ["Was Talzenna with Xtandi approved for castration-sensitive prostate cancer?",
     "Yes. The FDA approved talazoparib (Talzenna) with enzalutamide on October 26, 2026 for adults with metastatic "
     "androgen pathway modulation-naive or -sensitive prostate cancer with HRR gene mutations detected by an "
     "FDA-authorized test, per the FDA's own notification. Pfizer announced it the same day."],
    ["Was the Talzenna TALAPRO-3 decision early?",
     "Pfizer's July 22, 2026 release gave the PDUFA action date only as the last quarter of 2026, so pdufa.bio does "
     "not publish an early or late margin. The FDA acted on October 26, 2026, inside that quarter."],
    ["What did TALAPRO-3 show?",
     "Per the FDA, among 599 patients with HRR gene-mutated disease, adding talazoparib to enzalutamide cut the risk of "
     "radiographic progression or death (hazard ratio 0.48, 95% CI 0.36 to 0.65); median radiographic "
     "progression-free survival was not reached versus 45.8 months with placebo."]]
jsave("_decision_extra_faq.json", faq)

A = 'rel="noopener" style="color:#e3ba5e"'
spec = [{
    "ticker": "PFE", "date": DAY, "fda_action_date": DAY, "outcome": "Approved",
    "drug": "Talzenna (talazoparib) with Xtandi (enzalutamide)",
    "indication": "HRR gene-mutated metastatic castration-sensitive prostate cancer (TALAPRO-3)",
    "company": "Pfizer Inc.", "cap": "Large",
    "headline": ("The FDA approved Talzenna (talazoparib) with Xtandi (enzalutamide) on October 26, 2026 for HRR "
                 "gene-mutated metastatic castration-sensitive prostate cancer, on TALAPRO-3."),
    "pdufa_note": (f'The FDA\'s notification states that on October 26, 2026 it approved talazoparib (Talzenna, Pfizer '
                   f'Inc.) with enzalutamide for adults with metastatic androgen pathway modulation-naive or -sensitive '
                   f'prostate cancer with HRR gene mutations detected by an FDA-authorized test '
                   f'(<a href="{FDA}" {A}>FDA, October 26, 2026</a>). Pfizer announced the approval at 1:41 PM Eastern '
                   f'the same day (<a href="{PFE_REL}" {A}>Pfizer\'s announcement</a>). Pfizer had said the PDUFA '
                   f'action date fell in the last quarter of 2026 (<a href="{GOAL}" {A}>Pfizer, July 22, 2026</a>), a '
                   f'quarter rather than a day, so no early or late margin is given. Per the FDA, TALAPRO-3 '
                   f'(NCT04821622) randomized 599 patients; adding talazoparib to enzalutamide gave a radiographic '
                   f'progression-free survival hazard ratio of 0.48 (95% CI 0.36 to 0.65), with the median not reached '
                   f'versus 45.8 months. The application had Priority Review and was reviewed under Project Orbis.'),
    "source": FDA, "source_label": "FDA approval notification, October 26, 2026",
    "h1": ('Talzenna (talazoparib) with Xtandi <span class="g">FDA approval for HRR-mutated mCSPC</span>: '
           'Oct 26, 2026'),
}]
jsave("decision_pages_2026_10_26_pfe.json", spec)

PX = os.path.join(HERE, "_chart_pxcache.json")
px = json.load(open(PX))
for dd, cl in PFE_CLOSES.items():
    px.setdefault("PFE", {}).setdefault(dd, cl)
json.dump(px, open(PX, "w"))
import build_decision_page as bdp  # noqa: E402
for e in spec:
    bdp.build(e, px)
print(f"  built {PAGE_URL}; ledger + FAQ + page spec written")
