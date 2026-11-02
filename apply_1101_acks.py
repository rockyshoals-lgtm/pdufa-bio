# -*- coding: utf-8 -*-
"""apply_1101_acks.py -- resolve the held leads behind issues #45-#57 (2026-11-01), each with its reason.

REAL (published this pass; the key is recorded so the lead stops holding):
  #47 #55 #56 #57  AZN Ultomiris IgAN, BLA 761108 S-046 approved 2026-10-21 (Drugs@FDA; AZN 6-K 2026-10-22)
                   -> /fda-decision/AZN-2026-10-21
  #49 #53          INO Voceryq, accelerated approval 2026-10-30 (FDA press announcement; INOVIO release)
                   -> /fda-decision/INO-2026-10-30
NOT AN EVENT FOR THE HELD ROW:
  #45  GSK 6-K 2026-10-28 names Jideytro (zidesamtinib) as approved in the quarter; the held row is NUVL/GSK
       neladalkib (goal 2026-11-27), which is still pending. Zidesamtinib's approval is already published.
  #48  NVCR 8-K 2026-10-29 (Q3 results) describes Optune Gio's existing GBM approval; the held row is the
       pancreatic-cancer PMA (Q4 2026), still pending.
  #50  BTAI 8-K 2026-10-30 exhibit 2.1 is the asset purchase agreement selling IGALMI to Teva; "approval"
       there is the existing 2022 approval. The sNDA (goal 2026-11-14) is pending; the row is now TEVA.
  #51 #52  /drug/european-respiratory was a conference name, never a drug; the page is removed this pass
       (build_drug_pages JUNK_SLUG) and the leads were the INO approval matched onto it.
Facts only; not investment advice.
"""
import datetime as dt
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = dt.date.today().isoformat()


def jload(n):
    p = os.path.join(HERE, n)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}


def jsave(n, o):
    io.open(os.path.join(HERE, n), "w", encoding="utf-8").write(json.dumps(o, indent=1, ensure_ascii=False) + "\n")


# edgar_8k
e = jload("_edgar_8k_ack.json")
e.setdefault("note", "Reviewed EDGAR 8-K/6-K hits. Key row_id|accession. Each with its reason in apply_*.py.")
e.setdefault("acked", [])
for k in ("pdufa_nuvl_2026-11-27|0001654954-26-009181", "pdufa_nvcr_2026-11-15|0001645113-26-000081",
          "pdufa_azn_2026-12-31|0001654954-26-009093"):
    if k not in e["acked"]:
        e["acked"].append(k)
jsave("_edgar_8k_ack.json", e)

# fda_watch (press / edgar keys are stored in ap_date)
f = jload("_fda_watch_ack.json")
press = "press:http://www.fda.gov/news-events/press-announcements/fda-approves-first-plasmid-dna-based-immunotherapy-adults-recurrent-respiratory-papillomatosis"
edgar = "edgar:https://www.sec.gov/Archives/edgar/data/1720893/000110465926120737/tm2624733d2_ex2-1.htm"
add = [("INO", press, "REAL: Voceryq accelerated approval 2026-10-30, published as INO-2026-10-30."),
       ("BTAI", edgar, "Asset purchase agreement (IGALMI to Teva); refers to the existing approval, not the pending sNDA."),
       ("TEVA", edgar, "Same exhibit as the BTAI ack; the row moved to TEVA on 2026-11-01.")]
have = {(a["ticker"], a["ap_date"]) for a in f["acks"]}
for t, k, why in add:
    if (t, k) not in have:
        f["acks"].append({"ticker": t, "ap_date": k, "reason": why})
jsave("_fda_watch_ack.json", f)

# sponsor newswire
n = jload("_newswire_ack.json")
k = ("pdufa_ino_2026-10-30|https://ir.inovio.com/news/news-details/2026/INOVIO-Announces-FDA-Accelerated-Approval-of-"
     "VOCERYQ-an-Immunotherapy-to-Reduce-the-Frequency-of-Surgery-in-Adults-with-Recurrent-Respiratory-Papillomatosis-RRP/default.aspx")
if k not in n["acked"]:
    n["acked"].append(k)
jsave("_newswire_ack.json", n)

# drug-page watcher
d = jload("_drug_watch_ack.json")
have = {(a["slug"], a["source"]) for a in d["acks"]}
for slug, src, why in (("ultomiris", "openfda:20261021", "REAL: IgAN approval 2026-10-21, published as AZN-2026-10-21."),
                       ("european-respiratory", "fda-press:fda-approves-first-plasmid-dna-based-immunotherapy-adults-re",
                        "Not a drug: conference name; page removed 2026-11-01. The match is INO's Voceryq approval."),
                       ("european-respiratory", "sponsor:INO:2026-10-30", "Not a drug: conference name; page removed 2026-11-01.")):
    if (slug, src) not in have:
        d["acks"].append({"slug": slug, "source": src, "reason": why, "acked": TODAY})
jsave("_drug_watch_ack.json", d)

# verified approvals the drug-page render guard must hold
c = jload("_drug_approvals_confirmed.json")
have = {a["slug"] for a in c["approvals"]}
for slug, date, brand, src in (
        ("ultomiris", "2026-10-21", "Ultomiris", "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo=761108"),
        ("ino-3107-dna", "2026-10-30", "Voceryq", "https://www.fda.gov/news-events/press-announcements/fda-approves-first-plasmid-dna-based-immunotherapy-adults-recurrent-respiratory-papillomatosis")):
    if slug not in have:
        c["approvals"].append({"slug": slug, "date": date, "brand": brand, "source": src})
jsave("_drug_approvals_confirmed.json", c)
print("acks written: edgar_8k, fda_watch, newswire, drug_watch; confirmed approvals: ultomiris, ino-3107-dna")
