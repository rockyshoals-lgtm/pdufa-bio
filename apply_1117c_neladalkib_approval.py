# -*- coding: utf-8 -*-
"""apply_1117c_neladalkib_approval.py -- Nelkarmi (neladalkib) accelerated approval, FDA action day November 17, 2026.
Resolves the three held watcher leads of 2026-11-17 on row pdufa_nuvl_2026-11-27 / drug page /drug/neladalkib.

Verified 2026-11-17 ~21:00 UTC (16:00 Eastern, 13:00 Pacific; RULE 1), primary sources only, each page read itself:
  FDA, Cancer Approvals, "FDA grants accelerated approval to neladalkib for previously treated locally advanced or
    metastatic ALK-positive non-small cell lung cancer" (content current as of 11/17/2026): "On November 17, 2026, the
    Food and Drug Administration granted accelerated approval to neladalkib (Nelkarmi, Nuvalent, Inc.), a kinase
    inhibitor, for adults with locally advanced or metastatic anaplastic lymphoma kinase (ALK)-positive non-small cell
    lung cancer (NSCLC) who have previously received ... one prior ALK tyrosine kinase inhibitor (TKI) consisting of
    alectinib, or two or more prior ALK TKIs and platinum-based chemotherapy." ALKOVE-1 (NCT05384626): ORR 49% (95% CI
    37, 62) in 67 post-alectinib patients, 32% (95% CI 24, 40) in 155 after two or more TKIs and platinum chemotherapy;
    DOR >= 6 months in 76% / 69% of responders, >= 12 months in 52% / 51%. Priority review; breakthrough therapy and
    orphan drug designations. 150 mg orally once daily. The FDA states the action day, so fda_action_date is FDA-sourced.
    Also listed on the FDA's Oncology/Hematologic Malignancies Approval Notifications table dated 11/17/2026.
  GSK plc release, "Issued: London, UK", 17 November 2026: "GSK plc (LSE/NYSE: GSK) today announced the US Food and Drug
    Administration (FDA) has granted accelerated approval to Nelkarmi (neladalkib)" ... "This approval comes ahead of
    the original FDA target action date of 27 November 2026".
  Goal date: Nuvalent release of 2026-05-27 (already on the row): "assigned a PDUFA target action date of November 27,
    2026". Day precision on both ends, so the margin is published: 10 days early.
Nuvalent, Inc. (the applicant, named by the FDA) was acquired by GSK plc in July 2026; the row's ticker is GSK.
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
TODAY = "2026-11-17"
RID = "pdufa_nuvl_2026-11-27"
FDA = ("https://www.fda.gov/drugs/cancer-approvals/"
       "fda-grants-accelerated-approval-neladalkib-previously-treated-locally-advanced-or-metastatic-alk")
FDA_FEED = FDA.replace("https://", "http://")      # the key the fda_drugs_feed watcher raised
GSK = ("https://www.gsk.com/en-gb/media/press-releases/nelkarmi-neladalkib-approved-in-the-us-for-previously-treated-"
       "advanced-alk-positive-non-small-cell-lung-cancer/")
NUVL_GOAL = ("https://investors.nuvalent.com/2026-05-27-Nuvalent-Announces-Key-Program-and-Business-Updates,-"
             "Strengthening-Foundation-for-Global-Leadership-in-ROS1-and-ALK-positive-NSCLC")
PAGE_URL = "/fda-decision/GSK-2026-11-17"
QUOTE = ("On November 17, 2026, the Food and Drug Administration granted accelerated approval to neladalkib (Nelkarmi, "
         "Nuvalent, Inc.), a kinase inhibitor, for adults with locally advanced or metastatic anaplastic lymphoma kinase "
         "(ALK)-positive non-small cell lung cancer (NSCLC) who have previously received the following therapy in the "
         "unresectable locally advanced or metastatic setting: one prior ALK tyrosine kinase inhibitor (TKI) consisting "
         "of alectinib, or two or more prior ALK TKIs and platinum-based chemotherapy.")
# GSK closes, FMP historical-price-eod-full (split-adjusted), read 2026-11-17 21:01 UTC; Eastern trading days.
GSK_CLOSES = {"2026-10-19": 49.46, "2026-10-20": 50.63, "2026-10-21": 50.02, "2026-10-22": 51.21, "2026-10-23": 50.75,
              "2026-10-26": 51.1, "2026-10-27": 50.94, "2026-10-28": 48.74, "2026-10-29": 48.68, "2026-10-30": 49.51,
              "2026-11-02": 49.13, "2026-11-03": 48.7, "2026-11-04": 51.15, "2026-11-05": 50.41, "2026-11-06": 50.33,
              "2026-11-09": 51.54, "2026-11-10": 51.23, "2026-11-11": 50.6, "2026-11-12": 50.64, "2026-11-13": 50.45,
              "2026-11-16": 50.41, "2026-11-17": 49.24}


def jload(p, default=None):
    p = os.path.join(HERE, p)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else default


def jsave(p, d):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


# 1. the row
src = io.open(DATASET, encoding="utf-8").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
asc = src[i:j] == json.dumps(rows, indent=1, ensure_ascii=True)
r = next(x for x in rows if x["id"] == RID)
assert r["d"] == "2026-11-27" and r.get("dp") == "day", "goal day changed; re-verify before publishing"
if r.get("st") != "Decided":
    r.update({"st": "Decided", "oc": "Approved", "dcd": TODAY, "url": PAGE_URL, "ua": NOW})
    d = r.setdefault("_d", {})
    d.update({
        "brand": "Nelkarmi", "inn": "neladalkib", "trial": "ALKOVE-1",
        "indication": ("Adults with locally advanced or metastatic ALK-positive NSCLC previously treated with one prior "
                       "ALK TKI consisting of alectinib, or with two or more prior ALK TKIs and platinum-based "
                       "chemotherapy (accelerated approval)"),
        "decision_source": "FDA accelerated approval notification, November 17, 2026 (Cancer Approvals)",
        "decision_source_url": FDA,
        "fda_notice_title": ("FDA grants accelerated approval to neladalkib for previously treated locally advanced or "
                             "metastatic ALK-positive non-small cell lung cancer"),
        "decision_quote": QUOTE,
        "decision_note": ("Accelerated approval on November 17, 2026, 10 days before the November 27, 2026 goal date "
                          "(Nuvalent, May 27, 2026). GSK's release says the approval came ahead of the original target "
                          "action date of 27 November 2026."),
        "fda_action_date": TODAY, "fda_action_source_url": FDA,
        "fda_action_record": "FDA accelerated approval notification, November 17, 2026 (letter not yet on Drugs@FDA)",
        "announcement": "GSK plc press release (London), November 17, 2026",
        "announcement_url": GSK,
        "review": ("NDA under the accelerated approval pathway with Priority Review; Breakthrough Therapy and Orphan Drug "
                   "designations. Per the FDA, ALKOVE-1 (NCT05384626) is a single-arm, open-label, multi-cohort trial: "
                   "confirmed ORR by blinded independent central review was 49% (95% CI 37 to 62) in 67 patients after "
                   "alectinib alone and 32% (95% CI 24 to 40) in 155 patients after two or more ALK TKIs and "
                   "platinum-based chemotherapy. Recommended dose 150 mg orally once daily. Continued approval may be "
                   "contingent on a confirmatory trial."),
    })
    print(f"  {RID}: Decided / Approved {TODAY} -> {PAGE_URL} (FDA day; goal 2026-11-27 day-sourced; 10 days early)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=asc) + src[j:])

# 2. the render ledger, so /drug/neladalkib may never show pending again
c = jload("_drug_approvals_confirmed.json")
if not any(a.get("slug") == "neladalkib" and a.get("date") == TODAY for a in c["approvals"]):
    c["approvals"].append({"slug": "neladalkib", "date": TODAY, "brand": "Nelkarmi", "source": FDA})
    jsave("_drug_approvals_confirmed.json", c)

# 3. FAQ
faq = jload("_decision_extra_faq.json", {})
faq["GSK-2026-11-17"] = [
    ["Was neladalkib approved by the FDA?",
     "Yes. The FDA granted accelerated approval on November 17, 2026 to neladalkib (Nelkarmi) for adults with locally "
     "advanced or metastatic ALK-positive non-small cell lung cancer previously treated with alectinib as the only ALK "
     "inhibitor, or with two or more ALK inhibitors and platinum-based chemotherapy, per the FDA's own notification. "
     "GSK announced it the same day. Continued approval may depend on a confirmatory trial."],
    ["Was the neladalkib decision early?",
     "Yes, by 10 days. The FDA acted on November 17, 2026; the goal date was November 27, 2026, as stated by Nuvalent "
     "when the application was accepted with Priority Review (May 27, 2026). GSK's release also says the approval came "
     "ahead of the original target action date."],
    ["What did ALKOVE-1 show?",
     "Per the FDA, confirmed overall response by blinded independent central review was 49% in 67 patients whose only "
     "prior ALK inhibitor was alectinib and 32% in 155 patients after two or more ALK inhibitors and platinum-based "
     "chemotherapy. Among responders, 52% and 51% respectively had responses lasting at least 12 months."]]
jsave("_decision_extra_faq.json", faq)

# 4. the decision page spec (built by build_decision_page.py)
A = 'rel="noopener" style="color:#e3ba5e"'
spec = [{
    "ticker": "GSK", "date": TODAY, "fda_action_date": TODAY, "outcome": "Approved",
    "drug": "Nelkarmi (neladalkib)",
    "indication": ("Previously treated locally advanced or metastatic ALK-positive NSCLC: after alectinib as the only ALK "
                   "TKI, or after two or more ALK TKIs and platinum chemotherapy (accelerated approval)"),
    "company": "GSK plc", "cap": "Large",
    "headline": ("The FDA granted accelerated approval to Nelkarmi (neladalkib) on November 17, 2026 for adults with "
                 "previously treated locally advanced or metastatic ALK-positive non-small cell lung cancer, on the "
                 "single-arm ALKOVE-1 study, 10 days before its November 27 goal date."),
    "pdufa_note": (f'The FDA\'s notification states that on November 17, 2026 it granted accelerated approval to '
                   f'neladalkib (Nelkarmi, Nuvalent, Inc.) for adults with locally advanced or metastatic ALK-positive '
                   f'NSCLC who previously received one prior ALK TKI consisting of alectinib, or two or more prior ALK '
                   f'TKIs and platinum-based chemotherapy (<a href="{FDA}" {A}>FDA, November 17, 2026</a>). GSK, which '
                   f'acquired Nuvalent in July 2026, announced the approval the same day from London '
                   f'(<a href="{GSK}" {A}>GSK\'s announcement</a>). The PDUFA goal date was November 27, 2026, assigned '
                   f'when the NDA was accepted with Priority Review (<a href="{NUVL_GOAL}" {A}>Nuvalent, May 27, '
                   f'2026</a>); the FDA acted 10 days early. The FDA\'s letter had not been posted on Drugs@FDA when '
                   f'this page was published. Per the FDA, in ALKOVE-1 (NCT05384626) confirmed overall response by '
                   f'blinded independent central review was 49% (95% CI 37 to 62) in 67 patients after alectinib and '
                   f'32% (95% CI 24 to 40) in 155 patients after two or more ALK TKIs and platinum-based chemotherapy; '
                   f'52% and 51% of responders had a response lasting at least 12 months. Neladalkib holds Breakthrough '
                   f'Therapy and Orphan Drug designations; continued approval may be contingent on a confirmatory trial.'),
    "source": FDA, "source_label": "FDA accelerated approval notification, November 17, 2026",
    "h1": ('Nelkarmi (neladalkib) <span class="g">FDA accelerated approval for ALK-positive NSCLC</span>: '
           'Nov 17, 2026'),
}]
jsave("decision_pages_2026_11_17_gsk.json", spec)

# 5. prices (real FMP closes, never overwritten) and the page
PX = os.path.join(HERE, "_chart_pxcache.json")
px = json.load(open(PX))
for dd, cl in GSK_CLOSES.items():
    px.setdefault("GSK", {}).setdefault(dd, cl)
json.dump(px, open(PX, "w"))
import build_decision_page as bdp  # noqa: E402
for e in spec:
    bdp.build(e, px)
print(f"  built {PAGE_URL}")

# 6. watcher leads: published
ff = jload("_fda_drugs_feed_ack.json", {"acked": [], "reasons": {}})
k = f"{RID}|{FDA_FEED}"
if k not in ff["acked"]:
    ff["acked"].append(k)
ff.setdefault("reasons", {})[k] = ("Published 2026-11-17: Nelkarmi (neladalkib) accelerated approval Nov 17, 2026 "
                                   "(FDA day), /fda-decision/GSK-2026-11-17; goal Nov 27, 10 days early.")
jsave("_fda_drugs_feed_ack.json", ff)
dw = jload("_drug_watch_ack.json", {"acks": []})
for s in ("fda-oncology-notifications", "sponsor:GSK:2026-11-17"):
    if not any(a.get("slug") == "neladalkib" and a.get("source") == s for a in dw["acks"]):
        dw["acks"].append({"slug": "neladalkib", "source": s, "acked": TODAY,
                           "reason": ("Published 2026-11-17: Nelkarmi (neladalkib) accelerated approval Nov 17, 2026, "
                                      "/fda-decision/GSK-2026-11-17 (FDA notification and GSK release read).")})
jsave("_drug_watch_ack.json", dw)
print("  acks: fda_drugs_feed (1), drug_watch (2); ledger + FAQ + page spec written")
