# -*- coding: utf-8 -*-
"""apply_1021_hibsago_and_fda_days.py -- Hibsago (bepirovirsen) approved October 20, 2026; Enspryng and RYZUMVI get
their FDA action days from Drugs@FDA. Resolves the five held leads of the 23:32 UTC Oct 20 run (#38 to #42).

Verified 2026-10-21 12:40 UTC (08:40 Eastern, 05:40 Pacific), primary sources only:
  FDA press announcement, "For Immediate Release: October 20, 2026": "The U.S. Food and Drug Administration today
    approved Hibsago (bepirovirsen) injection, in combination with existing antiviral therapy, to treat chronic
    hepatitis B virus (HBV) infection in certain adults without cirrhosis. Hibsago is the first FDA-approved
    antisense oligonucleotide to treat chronic hepatitis B." Two placebo-controlled trials; 24% met the criteria
    to stop existing therapy vs none on placebo; 19% had HBsAg undetectable 24 weeks after stopping all treatment.
    Boxed warning: serious liver reactions and low platelet counts. The FDA states the action day, so
    fda_action_date is FDA-sourced; the letter is not on Drugs@FDA yet (openFDA last updated 2026-10-20).
  GSK US release, "Issued: Philadelphia, PA", October 20, 2026: "GSK plc (LSE/NYSE: GSK) today announced that the
    US Food and Drug Administration (FDA) has approved Hibsago (bepirovirsen) ..." Priority Review and Breakthrough
    Therapy Designation; B-Well phase III functional cure 19% vs <1% historical standard of care.
  Goal date already on the row: Ionis 8-K EX-99.1 of 2026-07-29, "PDUFA target action date of October 26, 2026".
    FDA day Oct 20 and goal Oct 26 both come from documents that state them: 6 days early.
  Drugs@FDA (openFDA, last updated 2026-10-20), applied tonight by sync_fda_action_dates.py before this script:
    BLA 761149 SUPPL-8 EFFICACY AP 2026-10-15 (Enspryng TED; letter 761149Orig1s008ltr.pdf): FDA day = goal day,
      on goal date, 0 days. NDA 217064 SUPPL-5 EFFICACY AP 2026-10-16 (RYZUMVI presbyopia): goal Oct 17, 1 day
      early. Both rows lose decision_date_unsourced and enter the timing statistic (32 -> 34: 22 early, 11 on, 1
      late), which is the figure /research/fda-decision-timing already carried in the blocked run.
  Watcher leads: fda_press and fda_drugs_feed on pdufa_gsk_2026-10-26 and the two drug_pages leads are this
    approval (REAL). drugs_at_fda RHHBY|2026-10-15 was raised against the MOGAD row (pdufa_rhhby_2027-01-10): it is
    the TED supplement, already published as RHHBY-2026-10-15; MOGAD (goal 2027-01-10) stays pending.
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
FDA = "https://www.fda.gov/news-events/press-announcements/fda-approves-first-its-kind-chronic-hepatitis-b-treatment"
FDA_HTTP = "http://www.fda.gov/news-events/press-announcements/fda-approves-first-its-kind-chronic-hepatitis-b-treatment"
REL = "https://us.gsk.com/en-us/media/press-releases/hibsago-bepirovirsen-approved-in-the-us-for-the-treatment-of-chronic-hepatitis-b-chb/"


def jload(p):
    return json.load(io.open(os.path.join(HERE, p), encoding="utf-8"))


def jsave(p, d):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
by = {r["id"]: r for r in rows}

# ---- 1. Hibsago
r = by["pdufa_gsk_2026-10-26"]
if r.get("st") != "Decided":
    r.update({"st": "Decided", "oc": "Approved", "dcd": "2026-10-20", "url": "/fda-decision/GSK-2026-10-20", "ua": NOW,
              "name": "Hibsago (bepirovirsen) - chronic hepatitis B", "ta": "Infectious Disease"})
    d = r.setdefault("_d", {})
    d.update({
        "brand": "Hibsago", "inn": "bepirovirsen", "trial": "B-Well 1, B-Well 2",
        "indication": ("Chronic hepatitis B virus infection, in combination with nucleos(t)ide analogue therapy, in adults "
                       "without cirrhosis on that therapy for at least 6 months with suppressed HBV DNA and HBsAg of "
                       "3,000 IU/mL or less (FDA-authorized test)"),
        "indication_short": "chronic hepatitis B (adults without cirrhosis, HBsAg 3,000 IU/mL or less)",
        "title_indication": "Chronic Hepatitis B",
        "seo_desc": ("Hibsago (bepirovirsen) was approved by the FDA on October 20, 2026 for chronic hepatitis B, "
                     "6 days before its October 26, 2026 goal date (B-Well trials)."),
        "decision_source": "FDA press announcement, October 20, 2026", "decision_source_url": FDA,
        "fda_notice_title": "FDA Approves First-of-Its-Kind Chronic Hepatitis B Treatment",
        "decision_quote": ("The U.S. Food and Drug Administration today approved Hibsago (bepirovirsen) injection, in "
                           "combination with existing antiviral therapy, to treat chronic hepatitis B virus (HBV) infection "
                           "in certain adults without cirrhosis."),
        "fda_action_date": "2026-10-20", "fda_action_source_url": FDA,
        "fda_action_record": "FDA press announcement, October 20, 2026 (letter not yet on Drugs@FDA)",
        "decision_date_note": ("The FDA's press announcement is dated October 20, 2026 and states the approval was made "
                               "that day; GSK announced it the same day from Philadelphia. The goal date, October 26, "
                               "2026, is from Ionis's 8-K exhibit of July 29, 2026."),
        "announcement_url": REL, "announcement": "GSK press release (Philadelphia), October 20, 2026",
        "review": ("Priority Review with Breakthrough Therapy Designation; first FDA-approved antisense oligonucleotide "
                   "for chronic hepatitis B. Per the FDA, two placebo-controlled trials (B-Well): Hibsago injected "
                   "subcutaneously for up to 24 weeks alongside existing antiviral therapy; 24% of Hibsago patients met "
                   "the criteria to stop their existing therapy versus none on placebo, and 19% still had the virus "
                   "controlled with undetectable HBsAg 24 weeks after stopping all treatment. Boxed warning for serious "
                   "liver reactions and low platelet counts; warnings for kidney function, vasculitis and injection "
                   "errors. The FDA also authorized the Roche Elecsys HBsAg II quant II RxDx companion diagnostic."),
    })
    print("  ~ pdufa_gsk_2026-10-26: Decided / Approved, FDA day 2026-10-20 (6 days before 2026-10-26)")
else:
    print("  pdufa_gsk_2026-10-26 already Decided")

# ---- 2. Enspryng / RYZUMVI: descriptions and notes now that the FDA day is on record (sync ran first)
for rid, desc, note in (
    ("pdufa_rhhby_2026-10-15",
     "Enspryng (satralizumab-mwge) was approved by the FDA on October 15, 2026 for thyroid eye disease, its goal date, per "
     "the FDA letter; based on SatraGO-1 and 2.",
     "The FDA's letter for BLA 761149 supplement 8 is dated October 15, 2026 (Drugs@FDA), the goal date; Genentech "
     "announced the approval the same day and Roche's Basel release followed on October 16."),
    ("pdufa_ird_2026-10-17",
     "RYZUMVI (phentolamine 0.75%) was approved by the FDA on October 16, 2026 for presbyopia, 1 day before its October "
     "17 goal date; Opus Genetics announced it.",
     "Drugs@FDA records NDA 217064 supplement 5 approved October 16, 2026, one day before the October 17 goal date; Opus "
     "Genetics announced it the same day."),
    ("pdufa_vtrs_2026-10-17",
     "RYZUMVI (phentolamine 0.75%) was approved by the FDA on October 16, 2026 for presbyopia, 1 day before its October "
     "17 goal date; Viatris holds U.S. rights.",
     "Drugs@FDA records NDA 217064 supplement 5 approved October 16, 2026, one day before the October 17 goal date; Opus "
     "Genetics announced it the same day."),
):
    x = by.get(rid)
    if not x:
        continue
    d = x.setdefault("_d", {})
    if not d.get("fda_action_date"):
        print(f"  !! {rid}: no fda_action_date yet; run sync_fda_action_dates.py first")
        continue
    if len(desc) <= 158:
        d["seo_desc"] = desc
    d["decision_date_note"] = note
    print(f"  ~ {rid}: seo_desc ({len(desc)}) and decision_date_note updated for FDA day {d['fda_action_date']}")

io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])

# ---- 3. the hand-written sentence on the three existing pages said the letter was not posted; it is now.
import re as _re
REWRITE = {
    "RHHBY-2026-10-15": (
        r"The release does not state the day the FDA acted, and the FDA's letter for BLA 761149 had not been posted on "
        r"Drugs@FDA when this page was published, so pdufa\.bio holds no FDA record of the action day yet and computes no "
        r"early or late margin\.",
        'Drugs@FDA now records the FDA\'s approval letter for BLA 761149 supplement 8 dated October 15, 2026 '
        '(<a href="https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/761149Orig1s008ltr.pdf" rel="noopener" '
        'style="color:#e3ba5e">FDA letter</a>), the goal date, so the decision came on its goal date; this page carried '
        'the announcement day alone until the letter was posted.'),
    "IRD-2026-10-16": (
        r"The release does not state the day the FDA acted, and the FDA's letter for NDA 217064 had not been posted on "
        r"Drugs@FDA when this page was published, so pdufa\.bio holds no FDA record of the action day yet and computes no "
        r"early or late margin\.",
        'Drugs@FDA now records NDA 217064 supplement 5 as approved on October 16, 2026 '
        '(<a href="https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&amp;ApplNo=217064" '
        'rel="noopener" style="color:#e3ba5e">Drugs@FDA</a>), one day before the October 17 goal date; this page carried '
        'the announcement day alone until the record was posted.'),
}
REWRITE["VTRS-2026-10-16"] = REWRITE["IRD-2026-10-16"]
for slug, (old, new) in REWRITE.items():
    p = os.path.join(SITE, "fda-decision", slug, "index.html")
    if not os.path.exists(p):
        continue
    doc = io.open(p, encoding="utf-8", errors="replace").read()
    doc2, n = _re.subn(old, new, doc)
    if n:
        io.open(p, "w", encoding="utf-8").write(doc2)
    print(f"  ~ /fda-decision/{slug}: {n} stale 'letter not posted' sentence(s) rewritten")

# ---- side stores
c = jload("_drug_approvals_confirmed.json")
for slug in ("bepirovirsen",):            # the drug page is /drug/bepirovirsen (INN slug)
    if not any(a.get("slug") == slug and a.get("date") == "2026-10-20" for a in c["approvals"]):
        c["approvals"].append({"slug": slug, "date": "2026-10-20", "brand": "Hibsago", "source": FDA})
jsave("_drug_approvals_confirmed.json", c)

faq = jload("_decision_extra_faq.json")
faq["GSK-2026-10-20"] = [
    ["Was bepirovirsen approved?",
     "Yes. The FDA approved Hibsago (bepirovirsen) on October 20, 2026, per the FDA's own press announcement of that "
     "day, for chronic hepatitis B in combination with existing antiviral therapy in certain adults without cirrhosis. "
     "GSK announced it the same day. It is the first antisense oligonucleotide approved for hepatitis B."],
    ["Was the Hibsago decision early?",
     "Yes, by 6 days. The goal date was October 26, 2026 (Ionis's 8-K of July 29, 2026, under Priority Review) and the "
     "FDA's announcement is dated October 20, 2026."],
    ["What did the B-Well trials show?",
     "Per the FDA, across the two placebo-controlled trials 24% of patients on Hibsago met the criteria to stop their "
     "existing hepatitis B therapy versus none on placebo, and 19% still had the virus under control with undetectable "
     "HBsAg 24 weeks after stopping all treatment. Hibsago carries a boxed warning for serious liver reactions and low "
     "platelet counts."]]
# Enspryng / RYZUMVI FAQ answers said the FDA record was not yet posted; they are rewritten from the record.
if "RHHBY-2026-10-15" in faq:
    faq["RHHBY-2026-10-15"][0] = ["Was Enspryng approved for thyroid eye disease?",
        "Yes. Drugs@FDA records the approval letter for BLA 761149 supplement 8 dated October 15, 2026, the goal date. "
        "Genentech announced it the same day and describes Enspryng as the first and only at-home subcutaneous "
        "treatment for TED."]
for k in ("IRD-2026-10-16", "VTRS-2026-10-16"):
    if k in faq:
        faq[k] = [q for q in faq[k] if "not yet" not in q[1] and "no FDA record" not in q[1]] or faq[k]
jsave("_decision_extra_faq.json", faq)

# ---- watcher acks
fa = jload("_fda_watch_ack.json")
for tk, ap, why in (("RHHBY", "2026-10-15",
                     "Enspryng TED supplement (BLA 761149 S-008), already published as RHHBY-2026-10-15 and now FDA-dated from "
                     "the letter. The hit was raised against the SEPARATE MOGAD row (goal 2027-01-10), which stays pending."),
                    ("GSK", "press:" + FDA_HTTP,
                     "REAL: Hibsago (bepirovirsen) approved 2026-10-20, published as /fda-decision/GSK-2026-10-20.")):
    if not any(a.get("ticker") == tk and a.get("ap_date") == ap for a in fa["acks"]):
        fa["acks"].append({"ticker": tk, "ap_date": ap, "reason": why})
jsave("_fda_watch_ack.json", fa)
ff = jload("_fda_drugs_feed_ack.json")
k = "pdufa_gsk_2026-10-26|" + FDA_HTTP
if k not in ff["acked"]:
    ff["acked"].append(k)
    ff["reasons"][k] = "REAL: published 2026-10-21 as /fda-decision/GSK-2026-10-20 (FDA press announcement of 2026-10-20)."
jsave("_fda_drugs_feed_ack.json", ff)
dack = jload("_drug_watch_ack.json")
for srcid in ("fda-press:fda-approves-first-its-kind-chronic-hepatitis-b-treatment", "sponsor:GSK:2026-10-20"):
    if not any(a.get("slug") == "bepirovirsen" and a.get("source") == srcid for a in dack["acks"]):
        dack["acks"].append({"slug": "bepirovirsen", "source": srcid, "acked": TODAY,
                             "reason": "REAL: Hibsago approved 2026-10-20; published as /fda-decision/GSK-2026-10-20 and recorded in _drug_approvals_confirmed.json."})
jsave("_drug_watch_ack.json", dack)
print("  side stores: approvals_confirmed, FAQ (GSK-2026-10-20 + rewrites), fda_watch ack (2), feed ack (1), drug-watch ack (2)")
