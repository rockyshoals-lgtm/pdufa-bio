# -*- coding: utf-8 -*-
"""apply_1125b_three_approvals.py -- three FDA approvals of November 23-24, 2026 recorded; unblocks rebuild run 521
(45541304822, 2026-11-25 03:37 UTC) and issue 210, where 9 watcher leads held their rows and the guards then stopped the
commit (test_open_goal_not_in_fda_record: three COGT rows matched "FDA Novel Drug Approvals: Ekitna (bezuclastinib)
2026-11-24"; the held /pdufa/RHHBY-giredestrant page kept the old run-up study size).

Sources read 2026-11-25 between 04:05 and 04:15 UTC (Nov 24, 11:05-11:15 PM Eastern; 8:05-8:15 PM Pacific; RULE 1),
each page itself:
  1. COGT. FDA Cancer Approvals, "FDA approves bezuclastinib in combination with sunitinib for advanced gastrointestinal
     stromal tumors" (content current as of 11/24/2026): "On November 24, 2026, the Food and Drug Administration approved
     bezuclastinib (Ekitna, Cogent Biosciences, Inc)" in combination with sunitinib for adults with advanced GIST who
     have received prior treatment with imatinib. PEAK (NCT05208047), 413 patients: median PFS 16.5 vs 9.2 months, HR
     0.50 (95% CI 0.39, 0.65); ORR 46% vs 26%; OS not mature. Priority review. Listed on the FDA's Oncology/Hematologic
     Malignancies Approval Notifications table dated 11/24/2026. The FDA states the action day.
     Goal: Cogent 8-K of 2026-08-10 (already on the row): "PDUFA date of November 30, 2026" for GIST. 6 days early.
     The NonAdvSM (SUMMIT, goal Dec 30, 2026) and AdvSM (goal Jun 29, 2027) rows are separate applications for other
     indications; the FDA notice names only GIST, so they stay open and their leads are acked.
  2. RHHBY. FDA Cancer Approvals, "FDA approves giredestrant for adjuvant treatment of ER-positive, HER2-negative, Stage
     I, II, and III breast cancer at intermediate to high risk of recurrence" (content current as of 11/23/2026): "On
     November 23, 2026, the Food and Drug Administration approved giredestrant (Wilserdly, Genentech, Inc.)", as a single
     agent, adjuvant. lidERA (NCT04961996), 4,170 patients: 36-month IDFS 92.4% vs 89.6%, HR 0.70 (95% CI 0.57, 0.87;
     p=0.0014). Genentech release, November 23, 2026, announces the same approval.
     Goal: Genentech release of 2026-06-01 (already on the row): decision "by November 30, 2026". 7 days early.
  3. PYPD. PolyPid 6-K Exhibit 99.1 (SEC EDGAR, accession 0001213900-26-123719), dateline "PETACH TIKVA, Israel, Nov.
     24, 2026": the FDA "has approved the Company's New Drug Application ("NDA") for BACFENSSI (doxycycline hyclate), an
     extended-release paste, previously known as D-PLEX100", to reduce the occurrence of surgical site infections in
     adults and pediatric patients weighing 45 kg or more undergoing colorectal surgery with incision lengths greater
     than 20 cm. SHIELD II: 10.9% vs 18.1% (p=0.004) on the primary endpoint; SSI 3.8% vs 9.5% (p=0.001). Priority Review.
     No FDA record of the action day was read, so this row carries no fda_action_date and no margin, as for Welgemda;
     sync_fda_action_dates.py writes the FDA's day when Drugs@FDA posts it.
     Goal: PolyPid 6-K of 2026-07-29 (already on the row): PDUFA target action date of November 28, 2026.
  Closes: FMP historical-price-eod-light read 2026-11-25 ~04:10 UTC; Eastern trading days, Nov 24 a full session.
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
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
TODAY = "2026-11-25"   # UTC; the reads ran Nov 24, 11 PM Eastern
A = 'rel="noopener" style="color:#e3ba5e"'

COGT_FDA = ("https://www.fda.gov/drugs/cancer-approvals/"
            "fda-approves-bezuclastinib-combination-sunitinib-advanced-gastrointestinal-stromal-tumors")
COGT_GOAL = "https://www.sec.gov/Archives/edgar/data/1622229/000119312526341315/cogt-ex99_1.htm"
RHHBY_FDA = ("https://www.fda.gov/drugs/cancer-approvals/"
             "fda-approves-giredestrant-adjuvant-treatment-er-positive-her2-negative-stage-i-ii-and-iii-breast")
RHHBY_REL = "https://www.gene.com/media/press-releases/15145/2026-11-23/fda-approves-genentechs-wilserdly-girede"
RHHBY_GOAL = "https://www.gene.com/media/press-releases/15115/2026-06-01/fda-accepts-new-drug-application-for-gen"
PYPD_REL = "https://www.sec.gov/Archives/edgar/data/1611842/000121390026123719/ea031349501ex99-1.htm"
PYPD_GOAL = "https://www.sec.gov/Archives/edgar/data/1611842/000121390026082564/ea029964201ex99-1.htm"

COGT_CLOSES = {"2026-10-19": 30.01, "2026-10-20": 31.24, "2026-10-21": 31.43, "2026-10-22": 31.31, "2026-10-23": 31.21,
               "2026-10-26": 30.91, "2026-10-27": 32.01, "2026-10-28": 32.23, "2026-10-29": 31.96, "2026-10-30": 31.02,
               "2026-11-02": 29.73, "2026-11-03": 31.06, "2026-11-04": 31.49, "2026-11-05": 29.58, "2026-11-06": 31.65,
               "2026-11-09": 33.54, "2026-11-10": 31.64, "2026-11-11": 29.4, "2026-11-12": 29.14, "2026-11-13": 28.56,
               "2026-11-16": 27.44, "2026-11-17": 27.85, "2026-11-18": 27.81, "2026-11-19": 27.74, "2026-11-20": 26.72,
               "2026-11-23": 28.11, "2026-11-24": 33.01}
RHHBY_CLOSES = {"2026-11-17": 60.25, "2026-11-18": 59.52, "2026-11-19": 58.98, "2026-11-20": 58.46,
                "2026-11-23": 59.08, "2026-11-24": 61.15}
PYPD_CLOSES = {"2026-07-20": 5.15, "2026-07-21": 3.74, "2026-07-22": 4.0, "2026-07-23": 4.24, "2026-07-24": 3.9,
               "2026-07-27": 3.98, "2026-07-28": 3.75, "2026-07-29": 4.08, "2026-07-30": 4.37, "2026-07-31": 4.29,
               "2026-08-03": 4.36, "2026-08-04": 4.45, "2026-08-05": 4.6, "2026-08-06": 4.81, "2026-08-07": 4.84,
               "2026-08-10": 4.77, "2026-08-11": 4.73, "2026-08-12": 4.84, "2026-08-13": 4.78, "2026-08-14": 4.74,
               "2026-08-17": 4.77, "2026-08-18": 4.73, "2026-08-19": 5.01, "2026-08-20": 5.08, "2026-08-21": 5.1,
               "2026-08-24": 4.99, "2026-08-25": 5.1, "2026-08-26": 5.11, "2026-08-27": 5.12, "2026-08-28": 5.07,
               "2026-08-31": 5.14, "2026-09-01": 5.33, "2026-09-02": 5.3, "2026-09-03": 5.27, "2026-09-04": 5.39,
               "2026-09-08": 5.33, "2026-09-09": 5.2, "2026-09-10": 5.16, "2026-09-11": 5.15, "2026-09-14": 5.33,
               "2026-09-15": 5.16, "2026-09-16": 5.21, "2026-09-17": 5.03, "2026-09-18": 5.21, "2026-09-21": 5.17,
               "2026-09-22": 5.45, "2026-09-23": 5.27, "2026-09-24": 5.36, "2026-09-25": 5.22, "2026-09-28": 5.31,
               "2026-09-29": 5.29, "2026-09-30": 5.27, "2026-10-01": 5.37, "2026-10-02": 5.19, "2026-10-05": 5.2,
               "2026-10-06": 5.13, "2026-10-07": 4.95, "2026-10-08": 4.9, "2026-10-09": 5.07, "2026-10-12": 5.02,
               "2026-10-13": 4.88, "2026-10-14": 4.83, "2026-10-15": 4.9, "2026-10-16": 4.72, "2026-10-19": 4.88,
               "2026-10-20": 5.15, "2026-10-21": 5.07, "2026-10-22": 5.13, "2026-10-23": 5.25, "2026-10-26": 5.29,
               "2026-10-27": 5.77, "2026-10-28": 5.78, "2026-10-29": 5.59, "2026-10-30": 5.39, "2026-11-02": 5.42,
               "2026-11-03": 5.46, "2026-11-04": 5.82, "2026-11-05": 5.67, "2026-11-06": 6.14, "2026-11-09": 6.24,
               "2026-11-10": 6.31, "2026-11-11": 6.6, "2026-11-12": 6.4, "2026-11-13": 6.26, "2026-11-16": 6.15,
               "2026-11-17": 6.54, "2026-11-18": 6.56, "2026-11-19": 6.55, "2026-11-20": 6.12, "2026-11-23": 5.77,
               "2026-11-24": 5.55}

COGT_IND = ("In combination with sunitinib, adults with advanced gastrointestinal stromal tumors (GIST) who have received "
            "prior treatment with imatinib")
RHHBY_IND = ("Single agent, adjuvant treatment of adults with ER-positive, HER2-negative, stage I, II and III breast "
             "cancer at intermediate to high risk of recurrence")
PYPD_IND = ("Reduce the occurrence of surgical site infections in adults and pediatric patients weighing 45 kg or more "
            "undergoing colorectal surgery with incision lengths greater than 20 cm")

ROWS = {
    "pdufa_cogt_2026-11-30": dict(
        goal="2026-11-30", dcd="2026-11-24", url="/fda-decision/COGT-2026-11-24",
        d={"brand": "Ekitna", "inn": "bezuclastinib", "trial": "PEAK", "nct_id": "NCT05208047", "indication": COGT_IND,
           "decision_source": "FDA oncology approval notification, November 24, 2026 (Cancer Approvals)",
           "decision_source_url": COGT_FDA,
           "fda_notice_title": ("FDA approves bezuclastinib in combination with sunitinib for advanced "
                                "gastrointestinal stromal tumors"),
           "decision_quote": ("On November 24, 2026, the Food and Drug Administration approved bezuclastinib (Ekitna, "
                              "Cogent Biosciences, Inc)"),
           "decision_note": ("Approved on November 24, 2026, 6 days before the November 30, 2026 goal date Cogent "
                             "disclosed (8-K, August 10, 2026)."),
           "fda_action_date": "2026-11-24", "fda_action_source_url": COGT_FDA,
           "fda_action_record": "FDA oncology approval notification, November 24, 2026 (letter not yet on Drugs@FDA)",
           "announcement": "FDA oncology approval notification, November 24, 2026", "announcement_url": COGT_FDA,
           "review": ("NDA under Priority Review. Per the FDA, PEAK (NCT05208047) is an open-label, randomized trial in "
                      "413 patients: median progression-free survival was 16.5 months with bezuclastinib plus "
                      "sunitinib and 9.2 months with sunitinib alone (hazard ratio 0.50, 95% CI 0.39 to 0.65); "
                      "overall response rate 46% and 26%. Overall survival data were not mature.")}),
    "pdufa_rhhby_2026-11-30": dict(
        goal="2026-11-30", dcd="2026-11-23", url="/fda-decision/RHHBY-2026-11-23",
        d={"brand": "Wilserdly", "inn": "giredestrant", "trial": "lidERA", "nct_id": "NCT04961996",
           "indication": RHHBY_IND,
           "decision_source": "FDA oncology approval notification, November 23, 2026 (Cancer Approvals)",
           "decision_source_url": RHHBY_FDA,
           "fda_notice_title": ("FDA approves giredestrant for adjuvant treatment of ER-positive, HER2-negative, Stage "
                                "I, II, and III breast cancer at intermediate to high risk of recurrence"),
           "decision_quote": ("On November 23, 2026, the Food and Drug Administration approved giredestrant (Wilserdly, "
                              "Genentech, Inc.)"),
           "decision_note": ("Approved on November 23, 2026, 7 days before the November 30, 2026 decision date Genentech "
                             "disclosed (June 1, 2026). This is the adjuvant application; the metastatic use with "
                             "everolimus was approved on November 16, 2026."),
           "fda_action_date": "2026-11-23", "fda_action_source_url": RHHBY_FDA,
           "fda_action_record": "FDA oncology approval notification, November 23, 2026",
           "announcement": "Genentech press release, November 23, 2026", "announcement_url": RHHBY_REL,
           "review": ("Per the FDA, lidERA (NCT04961996) randomized 4,170 patients 1:1 to giredestrant or standard "
                      "endocrine therapy: the 36-month invasive disease-free survival rate was 92.4% and 89.6% "
                      "(hazard ratio 0.70, 95% CI 0.57 to 0.87; two-sided p=0.0014).")}),
    "pdufa_pypd_2026-11-28": dict(
        goal="2026-11-28", dcd="2026-11-24", url="/fda-decision/PYPD-2026-11-24",
        d={"brand": "Bacfenssi", "inn": "doxycycline hyclate", "trial": "SHIELD II", "indication": PYPD_IND,
           "decision_source": "PolyPid 6-K Exhibit 99.1, November 24, 2026 (SEC EDGAR)",
           "decision_source_url": PYPD_REL, "decision_date_unsourced": True,
           "decision_quote": ("the U.S. Food and Drug Administration (“FDA”) has approved the Company’s "
                              "New Drug Application (“NDA”) for BACFENSSI"),
           "decision_note": ("PolyPid announced the approval on November 24, 2026, four days before the November 28, "
                             "2026 goal date it disclosed. The FDA's own record of the action day was not read when "
                             "this row was updated, so no early or late margin is published yet."),
           "announcement": "PolyPid 6-K Exhibit 99.1, November 24, 2026 (SEC EDGAR)", "announcement_url": PYPD_REL,
           "review": ("NDA under Priority Review, PDUFA target action date November 28, 2026 (PolyPid 6-K, July 29, "
                      "2026). Per PolyPid, in the Phase 3 SHIELD II trial (798 patients in the primary analysis "
                      "population) the primary endpoint event occurred in 10.9% of patients on BACFENSSI plus standard "
                      "of care and 18.1% on standard of care alone (p=0.004); surgical site infection, a key secondary "
                      "endpoint, in 3.8% and 9.5% (p=0.001).")}),
}


def jload(p, default=None):
    p = os.path.join(HERE, p)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else default


def jsave(p, d):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


# 1. the rows
src = io.open(DATASET, encoding="utf-8").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
asc = src[i:j] == json.dumps(rows, indent=1, ensure_ascii=True)
for rid, spec in ROWS.items():
    r = next(x for x in rows if x["id"] == rid)
    assert r["d"] == spec["goal"] and r.get("dp") == "day", f"{rid}: goal day changed; re-verify before publishing"
    if r.get("st") != "Decided":
        r.update({"st": "Decided", "oc": "Approved", "dcd": spec["dcd"], "url": spec["url"], "ua": NOW})
        r.setdefault("_d", {}).update(spec["d"])
        print(f"  {rid}: Decided / Approved {spec['dcd']} -> {spec['url']}")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=asc) + src[j:])

# 2. the render ledger, so the drug pages never show pending for these approvals again
c = jload("_drug_approvals_confirmed.json")
for slug, date, brand, s in (("bezuclastinib", "2026-11-24", "Ekitna", COGT_FDA),
                             ("giredestrant", "2026-11-23", "Wilserdly", RHHBY_FDA),
                             ("d-plex100", "2026-11-24", "Bacfenssi", PYPD_REL)):
    if not any(a.get("slug") == slug and a.get("date") == date for a in c["approvals"]):
        c["approvals"].append({"slug": slug, "date": date, "brand": brand, "source": s})
jsave("_drug_approvals_confirmed.json", c)

# 3. FAQ
faq = jload("_decision_extra_faq.json", {})
faq["COGT-2026-11-24"] = [
    ["Was bezuclastinib approved by the FDA?",
     "Yes. The FDA approved bezuclastinib (Ekitna) on November 24, 2026, in combination with sunitinib, for adults with "
     "advanced gastrointestinal stromal tumors who have received prior treatment with imatinib, per the FDA's own "
     "notification."],
    ["Was the Ekitna decision early?",
     "Yes, by 6 days. The FDA acted on November 24, 2026; the goal date was November 30, 2026, as stated by Cogent in "
     "its 8-K of August 10, 2026."],
    ["Does this approval cover systemic mastocytosis?",
     "No. The FDA notice names only GIST with sunitinib. Cogent's applications in nonadvanced systemic mastocytosis "
     "(goal date December 30, 2026) and advanced systemic mastocytosis (goal date June 29, 2027) are tracked "
     "separately and remain open."],
    ["What did the PEAK trial show?",
     "Per the FDA, in 413 patients median progression-free survival was 16.5 months with bezuclastinib plus sunitinib "
     "and 9.2 months with sunitinib alone (hazard ratio 0.50). Overall survival data were not mature."]]
faq["RHHBY-2026-11-23"] = [
    ["Was giredestrant approved for early breast cancer?",
     "Yes. The FDA approved giredestrant (Wilserdly) on November 23, 2026 as a single agent for the adjuvant treatment "
     "of adults with ER-positive, HER2-negative, stage I, II and III breast cancer at intermediate to high risk of "
     "recurrence, per the FDA's own notification. Genentech announced it the same day."],
    ["Was the adjuvant Wilserdly decision early?",
     "Yes, by 7 days. The FDA acted on November 23, 2026; Genentech had said on June 1, 2026 that the FDA was expected "
     "to decide by November 30, 2026."],
    ["Is this the same approval as Wilserdly with everolimus?",
     "No. The FDA approved Wilserdly with everolimus for ESR1-mutated advanced or metastatic breast cancer on November "
     "16, 2026. The November 23 approval is the separate adjuvant use, on the lidERA trial."]]
faq["PYPD-2026-11-24"] = [
    ["Was D-PLEX100 approved by the FDA?",
     "Yes. PolyPid announced on November 24, 2026 that the FDA approved its NDA for BACFENSSI (doxycycline hyclate), "
     "previously known as D-PLEX100, to reduce the occurrence of surgical site infections in adults and pediatric "
     "patients weighing 45 kg or more undergoing colorectal surgery with incisions longer than 20 cm."],
    ["Was the Bacfenssi decision early?",
     "PolyPid announced the approval on November 24, 2026, four days before the November 28, 2026 goal date it had "
     "disclosed. pdufa.bio publishes a margin only from the FDA's own record of the action day, which had not been read "
     "when this page was published."]]
jsave("_decision_extra_faq.json", faq)

# 4. decision page specs (built by build_decision_page.py)
specs = [
    {"ticker": "COGT", "date": "2026-11-24", "fda_action_date": "2026-11-24", "outcome": "Approved",
     "drug": "Ekitna (bezuclastinib)",
     "indication": "Advanced GIST after imatinib, in combination with sunitinib",
     "company": "Cogent Biosciences", "cap": "Mid",
     "headline": ("The FDA approved Ekitna (bezuclastinib) with sunitinib on November 24, 2026 for adults with "
                  "advanced GIST previously treated with imatinib, on the PEAK trial, 6 days before its November 30 "
                  "goal date."),
     "pdufa_note": (f'The FDA\'s notification states that on November 24, 2026 it approved bezuclastinib (Ekitna, Cogent '
                    f'Biosciences, Inc) in combination with sunitinib for adults with advanced gastrointestinal stromal '
                    f'tumors who have received prior treatment with imatinib (<a href="{COGT_FDA}" {A}>FDA, November '
                    f'24, 2026</a>). Cogent had disclosed a PDUFA goal date of November 30, 2026 for GIST '
                    f'(<a href="{COGT_GOAL}" {A}>Cogent 8-K, August 10, 2026</a>); the FDA acted 6 days early. The '
                    f'FDA\'s letter had not been posted on Drugs@FDA when this page was published. Per the FDA, in PEAK '
                    f'(NCT05208047), 413 patients, median progression-free survival was 16.5 months with bezuclastinib '
                    f'plus sunitinib and 9.2 months with sunitinib alone (hazard ratio 0.50, 95% CI 0.39 to 0.65); '
                    f'overall survival data were not mature. Cogent\'s systemic mastocytosis applications are separate '
                    f'and remain open.'),
     "source": COGT_FDA, "source_label": "FDA oncology approval notification, November 24, 2026",
     "h1": 'Ekitna (bezuclastinib) <span class="g">FDA approval for GIST, with sunitinib</span>: Nov 24, 2026'},
    {"ticker": "RHHBY", "date": "2026-11-23", "fda_action_date": "2026-11-23", "outcome": "Approved",
     "drug": "Wilserdly (giredestrant)",
     "indication": "Adjuvant ER-positive, HER2-negative stage I to III breast cancer, intermediate to high risk",
     "company": "Roche (Genentech)", "cap": "Large",
     "headline": ("The FDA approved Wilserdly (giredestrant) on November 23, 2026 as adjuvant treatment for "
                  "ER-positive, HER2-negative early breast cancer at intermediate to high risk of recurrence, on the "
                  "lidERA trial, 7 days before its November 30 decision date."),
     "pdufa_note": (f'The FDA\'s notification states that on November 23, 2026 it approved giredestrant (Wilserdly, '
                    f'Genentech, Inc.) as a single agent for the adjuvant treatment of adults with ER-positive, '
                    f'HER2-negative, stage I, II and III breast cancer at intermediate to high risk of recurrence '
                    f'(<a href="{RHHBY_FDA}" {A}>FDA, November 23, 2026</a>). Genentech announced it the same day '
                    f'(<a href="{RHHBY_REL}" {A}>Genentech\'s announcement</a>). Genentech had said the FDA was expected '
                    f'to decide by November 30, 2026 (<a href="{RHHBY_GOAL}" {A}>Genentech, June 1, 2026</a>); the FDA '
                    f'acted 7 days early. Per the FDA, in lidERA (NCT04961996), 4,170 patients, the 36-month invasive '
                    f'disease-free survival rate was 92.4% with giredestrant and 89.6% with standard endocrine therapy '
                    f'(hazard ratio 0.70, 95% CI 0.57 to 0.87). The use with everolimus in ESR1-mutated advanced breast '
                    f'cancer was approved separately on November 16, 2026.'),
     "source": RHHBY_FDA, "source_label": "FDA oncology approval notification, November 23, 2026",
     "h1": ('Wilserdly (giredestrant) <span class="g">FDA approval for adjuvant early breast cancer</span>: '
            'Nov 23, 2026')},
    {"ticker": "PYPD", "date": "2026-11-24", "outcome": "Approved",
     "drug": "Bacfenssi (D-PLEX100, doxycycline hyclate)",
     "indication": "Reduce surgical site infections in colorectal surgery with incisions longer than 20 cm",
     "company": "PolyPid", "cap": "Micro",
     "headline": ("PolyPid announced on November 24, 2026 that the FDA approved Bacfenssi (D-PLEX100) to reduce "
                  "surgical site infections in colorectal surgery, on the Phase 3 SHIELD II trial."),
     "pdufa_note": (f'PolyPid announced on November 24, 2026 that the FDA approved its NDA for BACFENSSI (doxycycline '
                    f'hyclate), an extended-release paste previously known as D-PLEX100, to reduce the occurrence of '
                    f'surgical site infections in adults and pediatric patients weighing 45 kg or more undergoing '
                    f'colorectal surgery with incision lengths greater than 20 cm (<a href="{PYPD_REL}" {A}>PolyPid '
                    f'6-K, Exhibit 99.1</a>). PolyPid had disclosed a PDUFA target action date of November 28, 2026 '
                    f'under Priority Review (<a href="{PYPD_GOAL}" {A}>PolyPid 6-K, July 29, 2026</a>), so the '
                    f'announcement came four days before it. The FDA\'s own record of the action day had not been read '
                    f'when this page was published, so no early or late margin is given yet. Per PolyPid, in SHIELD II '
                    f'the primary endpoint event occurred in 10.9% of patients on BACFENSSI plus standard of care and '
                    f'18.1% on standard of care alone (p=0.004).'),
     "source": PYPD_REL, "source_label": "PolyPid 6-K Exhibit 99.1, November 24, 2026"},
]
jsave("decision_pages_2026_11_25_three.json", specs)

# 5. prices (real FMP closes, never overwritten) and the pages
PX = os.path.join(HERE, "_chart_pxcache.json")
px = json.load(open(PX))
for tk, cl in (("COGT", COGT_CLOSES), ("RHHBY", RHHBY_CLOSES), ("PYPD", PYPD_CLOSES)):
    for dd, v in cl.items():
        px.setdefault(tk, {}).setdefault(dd, v)
json.dump(px, open(PX, "w"))
import build_decision_page as bdp  # noqa: E402
for e in specs:
    bdp.build(e, px)
print("  built /fda-decision/COGT-2026-11-24, /fda-decision/RHHBY-2026-11-23, /fda-decision/PYPD-2026-11-24")

# 6. the nine held leads of issue 210: published, or not this row's decision
FEED = COGT_FDA.replace("https://", "http://")   # the key the fda_drugs_feed watcher raised
ff = jload("_fda_drugs_feed_ack.json", {"acked": [], "reasons": {}})
for k, why in (
        (f"pdufa_cogt_2026-11-30|{FEED}", "Published 2026-11-25: Ekitna (bezuclastinib) + sunitinib, GIST, approved Nov "
         "24, 2026 (FDA day), /fda-decision/COGT-2026-11-24; goal Nov 30, 6 days early."),
        (f"pdufa_cogt_2026-12-30|{FEED}", "Not this row: the Nov 24, 2026 FDA notice approves bezuclastinib with sunitinib "
         "for GIST (PEAK) only. This row is the NonAdvSM application (SUMMIT), goal Dec 30, 2026, still open."),
        (f"pdufa_cogt_2027-06-29|{FEED}", "Not this row: the Nov 24, 2026 FDA notice approves bezuclastinib with sunitinib "
         "for GIST (PEAK) only. This row is the AdvSM application, goal Jun 29, 2027, still open.")):
    if k not in ff["acked"]:
        ff["acked"].append(k)
    ff.setdefault("reasons", {})[k] = why
jsave("_fda_drugs_feed_ack.json", ff)

dw = jload("_drug_watch_ack.json", {"acks": []})
for slug, s, why in (
        ("bezuclastinib", "fda-oncology-notifications",
         "Published 2026-11-25: Ekitna (bezuclastinib) + sunitinib approved for GIST Nov 24, 2026, "
         "/fda-decision/COGT-2026-11-24 (FDA notification read)."),
        ("bezuclastinib-summit", "fda-oncology-notifications",
         "Not this drug page's application: the FDA's Nov 24, 2026 notice is the GIST approval with sunitinib (PEAK). "
         "The SUMMIT NonAdvSM application (goal Dec 30, 2026) has no FDA action."),
        ("rap-219-long-acting", "fda-press:fda-approves-first-treatment-limb-girdle-muscular-dystrophy-",
         "Not this drug: the FDA press item is about the first limb-girdle muscular dystrophy treatment (the Welgemda "
         "approval of Nov 23, 2026, published as /fda-decision/BBIO-2026-11-23). RAP-219 is not named; matched only on "
         "the word 'acting'.")):
    if not any(a.get("slug") == slug and a.get("source") == s for a in dw["acks"]):
        dw["acks"].append({"slug": slug, "source": s, "acked": TODAY, "reason": why})
jsave("_drug_watch_ack.json", dw)

nw = jload("_newswire_ack.json", {"acked": [], "reasons": {}})
k = f"pdufa_rhhby_2026-11-30|{RHHBY_REL}"
if k not in nw["acked"]:
    nw["acked"].append(k)
nw.setdefault("reasons", {})[k] = ("REAL: published 2026-11-25 as /fda-decision/RHHBY-2026-11-23 (adjuvant Wilserdly "
                                   "approval, FDA notification of Nov 23, 2026 read; Genentech release the same day).")
jsave("_newswire_ack.json", nw)

fw = jload("_fda_watch_ack.json", {"acks": []})
ap = "edgar:" + PYPD_REL
if not any(a.get("ticker") == "PYPD" and a.get("ap_date") == ap for a in fw["acks"]):
    fw["acks"].append({"ticker": "PYPD", "ap_date": ap,
                       "reason": ("REAL: published 2026-11-25 as /fda-decision/PYPD-2026-11-24 (Bacfenssi, D-PLEX100, "
                                  "approval announced in PolyPid's 6-K of Nov 24, 2026).")})
jsave("_fda_watch_ack.json", fw)

ek = jload("_edgar_8k_ack.json", {"acked": []})
if "pdufa_pypd_2026-11-28|0001213900-26-123719" not in ek["acked"]:
    ek["acked"].append("pdufa_pypd_2026-11-28|0001213900-26-123719")
jsave("_edgar_8k_ack.json", ek)

# 7. the guard's exception file: the Ekitna novel-approval row is a different indication for the two SM rows
fr = jload("_fda_record_ack.json")
for rid, what in (("pdufa_cogt_2026-12-30", "the nonadvanced systemic mastocytosis application (SUMMIT), goal date "
                   "December 30, 2026"),
                  ("pdufa_cogt_2027-06-29", "the advanced systemic mastocytosis application, goal date June 29, 2027")):
    if not any(a["id"] == rid and a["appl_no"] == "novel:Ekitna" for a in fr["acks"]):
        fr["acks"].append({"id": rid, "appl_no": "novel:Ekitna", "checked": TODAY,
                           "why": ("Ekitna (bezuclastinib) was approved on November 24, 2026 in combination with "
                                   "sunitinib for advanced GIST after imatinib (PEAK; FDA notice). This row is " + what
                                   + "; the FDA notice names no mastocytosis use.")})
jsave("_fda_record_ack.json", fr)
print("  acks: fda_drugs_feed (3), drug_watch (3), newswire (1), fda_watch (1), edgar_8k (1), fda_record (2)")
