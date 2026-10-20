# -*- coding: utf-8 -*-
"""apply_1019_jemperli_larc.py -- Jemperli (dostarlimab-gxly) accelerated approval, dMMR/MSI-H locally advanced
rectal cancer, FDA action day October 19, 2026. Resolves the two held watcher leads of 2026-10-19.

Verified 2026-10-19 22:30 UTC (18:30 Eastern, 15:30 Pacific), primary sources only:
  FDA, Resources for Information | Approved Drugs, "FDA grants accelerated approval to dostarlimab for locally
    advanced rectal cancer": "On October 19, 2026, the Food and Drug Administration granted accelerated approval to
    dostarlimab (Jemperli, GSK) for adults with Stage II/III locally advanced rectal cancer (LARC) that is
    microsatellite instability high (MSI-H) or mismatch repair deficient (dMMR)". AZUR-1 (NCT05723562), 154 patients,
    single-arm; cCR12 per ICR 47% (95% CI 27-56) in 116 evaluable; investigator cCR12 68% (95% CI 60-76) in 144;
    ORR per ICR 79%; median follow-up 26.3 months. The FDA states the action day, so fda_action_date is FDA-sourced.
  FDA press announcement, October 19, 2026 (the item the fda_drugs_feed watcher raised against pdufa_ino_2026-10-30,
    which is INO-3107 for recurrent respiratory papillomatosis, a different sponsor and application):
    fda.gov/news-events/press-announcements/fda-approves-immunotherapy-may-allow-certain-patients-rectal-cancer-...
  GSK US release, "Issued: Philadelphia, PA", October 19, 2026: "GSK plc (LSE/NYSE: GSK) today announced the US Food
    and Drug Administration (FDA) has approved Jemperli (dostarlimab-gxly) as the first and only immunotherapy for
    adults with stage II and III ... locally advanced rectal cancer under the accelerated approval pathway." Priority
    Review; Commissioner's National Priority Voucher; "ahead of the PDUFA date". Fast Track and Breakthrough Therapy.
  Goal date: GSK US release of August 24, 2026 (sBLA accepted for priority review): "The FDA has assigned a PDUFA
    action date of February 2027." Month precision only, so NO early or late margin is computed (the rule: a margin
    needs a day-precision goal date and an action date, both from documents that state them). The row was not on the
    calendar before today: the Aug 24 acceptance was missed by the GSK newsroom watcher (no RSS on gsk.com).
  Drugs@FDA: openFDA last_updated 2026-10-16 carries no BLA 761174 supplement for this action yet; the letter will be
    swapped in by sync_fda_action_dates.py when posted.
  The aficamten lead (drug_pages, sponsor:CYTK:2026-10-19) is Cytokinetics' release "Cytokinetics Announces Health
    Canada Approval of MYQORZO (aficamten) ..." of October 19, 2026: a Health Canada action, not an FDA one. The FDA
    sNDA (MAPLE-HCM, pdufa_cytk_2026-11-14) is unchanged. Acked with that reason.
Facts only; not investment advice.
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
TODAY = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
FDA = ("https://www.fda.gov/drugs/resources-information-approved-drugs/"
       "fda-grants-accelerated-approval-dostarlimab-locally-advanced-rectal-cancer")
FDA_PRESS = ("https://www.fda.gov/news-events/press-announcements/"
             "fda-approves-immunotherapy-may-allow-certain-patients-rectal-cancer-avoid-chemotherapy-radiation-and")
REL = ("https://us.gsk.com/en-us/media/press-releases/jemperli-dostarlimab-gxly-approved-in-us-as-first-and-only-"
       "immunotherapy-for-adults-with-msi-hdmmr-locally-advanced-rectal-cancer/")
GOAL = "https://us.gsk.com/en-us/media/press-releases/jemperli-dostarlimab-gxly-accepted-for-priority-review-by-the-us-fda/"
RID = "pdufa_gsk_2027-02-28"


def jload(p):
    return json.load(io.open(os.path.join(HERE, p), encoding="utf-8"))


def jsave(p, d):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
if any(r["id"] == RID for r in rows):
    print(f"  {RID} already present")
else:
    rows.append({
        "id": RID, "t": "GSK", "company": "GSK plc", "d": "2027-02-28", "dp": "month", "dm": "2027-02",
        "name": "Jemperli (dostarlimab-gxly) - locally advanced rectal cancer",
        "type": "PDUFA", "ta": "Oncology", "cap": "Large", "st": "Decided", "url": "/fda-decision/GSK-2026-10-19",
        "ua": NOW, "oc": "Approved", "dcd": "2026-10-19",
        "_d": {
            "nct_id": "NCT05723562", "trial": "AZUR-1",
            "brand": "Jemperli", "inn": "dostarlimab-gxly",
            "indication": ("Adults with Stage II/III locally advanced rectal cancer that is microsatellite instability "
                           "high (MSI-H) or mismatch repair deficient (dMMR), as determined by an FDA-authorized test "
                           "(accelerated approval)"),
            "indication_short": "dMMR/MSI-H locally advanced rectal cancer",
            "title_indication": "Locally Advanced Rectal Cancer",
            "seo_desc": ("Jemperli (dostarlimab-gxly) was approved by the FDA on October 19, 2026 (accelerated approval) "
                         "for dMMR/MSI-H locally advanced rectal cancer, on AZUR-1."),
            "source": "GSK press release, August 24, 2026 (sBLA accepted for priority review)", "source_url": GOAL,
            "source_quote": "The FDA has assigned a PDUFA action date of February 2027.",
            "source_note": ("GSK stated the goal date to the month only (February 2027), so no early or late margin is "
                            "computed against the October 19, 2026 action day."),
            "decision_source": "FDA accelerated approval notification, October 19, 2026 (Resources for Information | Approved Drugs)",
            "decision_source_url": FDA,
            "fda_notice_title": "FDA grants accelerated approval to dostarlimab for locally advanced rectal cancer",
            "decision_quote": ("On October 19, 2026, the Food and Drug Administration granted accelerated approval to "
                               "dostarlimab (Jemperli, GSK) for adults with Stage II/III locally advanced rectal cancer "
                               "(LARC) that is microsatellite instability high (MSI-H) or mismatch repair deficient "
                               "(dMMR), as determined by an FDA-authorized test for solid tumors."),
            "fda_action_date": "2026-10-19", "fda_action_source_url": FDA,
            "fda_action_record": "FDA accelerated approval notification (sBLA, BLA 761174; letter not yet on Drugs@FDA)",
            "decision_date_note": ("The FDA's notification is dated October 19, 2026 and states the approval was granted "
                                   "that day; GSK's release of the same day says the approval came ahead of the PDUFA "
                                   "date. The goal date is from GSK's August 24, 2026 release and is stated as a month "
                                   "(February 2027), so no margin is published."),
            "announcement_url": REL, "announcement": "GSK press release (Philadelphia), October 19, 2026",
            "review": ("Supplemental BLA under the accelerated approval pathway, Priority Review, with a Commissioner's "
                       "National Priority Voucher; Fast Track and Breakthrough Therapy designations. AZUR-1 "
                       "(NCT05723562): single-arm, open-label, 154 previously untreated patients, dostarlimab 500 mg IV "
                       "every 3 weeks for nine cycles. Per the FDA, sustained clinical complete response at 12 months "
                       "(cCR12) per independent central review was 47% (95% CI 27 to 56) in 116 evaluable patients and "
                       "68% (95% CI 60 to 76) by investigator in 144; ORR per ICR 79%; with a median follow-up of 26.3 "
                       "months, no patient with cCR12, cCR or near CR had progressed. Continued approval may be "
                       "contingent on a confirmatory trial."),
        }})
    rows.sort(key=lambda r: (str(r.get("d") or "9999"), str(r.get("t") or "")))
    print(f"  + {RID} Jemperli dMMR/MSI-H LARC, Decided/Approved 2026-10-19 (FDA notification; goal February 2027, no margin)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])

c = jload("_drug_approvals_confirmed.json")
if not any(a.get("slug") == "jemperli" and a.get("date") == "2026-10-19" for a in c["approvals"]):
    c["approvals"].append({"slug": "jemperli", "date": "2026-10-19", "brand": "Jemperli", "source": FDA})
    jsave("_drug_approvals_confirmed.json", c)

faq = jload("_decision_extra_faq.json")
faq["GSK-2026-10-19"] = [
    ["Was Jemperli approved for locally advanced rectal cancer?",
     "Yes. The FDA granted accelerated approval on October 19, 2026 to dostarlimab-gxly (Jemperli) for adults with "
     "Stage II/III locally advanced rectal cancer that is mismatch repair deficient or microsatellite instability "
     "high, per the FDA's own notification. GSK announced it the same day. Continued approval may depend on a "
     "confirmatory trial."],
    ["Was the Jemperli rectal cancer decision early?",
     "The FDA acted on October 19, 2026. GSK's August 24, 2026 release stated the goal date as February 2027, a month "
     "rather than a day, so pdufa.bio does not publish an early or late margin for this decision. GSK's release "
     "says the approval came ahead of the PDUFA date; the application carried Priority Review and a Commissioner's "
     "National Priority Voucher."],
    ["What did AZUR-1 show?",
     "Per the FDA, AZUR-1 (NCT05723562) enrolled 154 previously untreated patients who received dostarlimab alone "
     "for nine cycles. Sustained clinical complete response at 12 months was 47% by independent central review in "
     "116 evaluable patients and 68% by investigator assessment in 144; overall response by central review was 79%. "
     "With a median follow-up of 26.3 months, no patient with a complete or near-complete response had progressed."]]
jsave("_decision_extra_faq.json", faq)

# watcher acks: the FDA press item was raised against INO-3107's row (wrong row); the CYTK item is Health Canada.
ack = jload("_fda_drugs_feed_ack.json")
k = "pdufa_ino_2026-10-30|http://www.fda.gov/news-events/press-announcements/fda-approves-immunotherapy-may-allow-certain-patients-rectal-cancer-avoid-chemotherapy-radiation-and"
if k not in ack["acked"]:
    ack["acked"].append(k)
    ack["reasons"][k] = ("Not this row: the item is the FDA's October 19, 2026 accelerated approval of Jemperli (dostarlimab-gxly, "
                         "GSK) for dMMR/MSI-H locally advanced rectal cancer, published 2026-10-19 as /fda-decision/GSK-2026-10-19 "
                         "(row pdufa_gsk_2027-02-28). INO-3107 (Inovio, RRP) is a different application; its goal date stands.")
    jsave("_fda_drugs_feed_ack.json", ack)
dack = jload("_drug_watch_ack.json")
if not any(a.get("slug") == "aficamten" and a.get("source") == "sponsor:CYTK:2026-10-19" for a in dack["acks"]):
    dack["acks"].append({"slug": "aficamten", "source": "sponsor:CYTK:2026-10-19",
                         "reason": ("Cytokinetics release of 2026-10-19 is a Health Canada approval of MYQORZO (aficamten), "
                                    "not an FDA action. The FDA sNDA for MAPLE-HCM (pdufa_cytk_2026-11-14) is unchanged."),
                         "acked": TODAY})
    jsave("_drug_watch_ack.json", dack)
print("  side stores: approvals_confirmed (jemperli, dostarlimab), extra FAQ (3), feed ack (INO), drug-watch ack (aficamten)")
