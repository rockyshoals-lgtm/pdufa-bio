# -*- coding: utf-8 -*-
"""apply_1111_decisions.py -- three FDA actions of Nov 9-10, 2026 recorded, and the false held leads acked.

Audit 2026-11-11 order 0. Every fact below was read from the primary source on 2026-11-11 (Pacific evening):
  * Sunharbo (asundexian), Bayer: FDA press announcement dated November 9, 2026, "The U.S. Food and Drug
    Administration today approved Sunharbo (asundexian) 50 mg tablets, the first factor XIa (FXIa) inhibitor..."
    Bayer stated no PDUFA goal date (Priority Review accepted May 2026), so no margin is computed.
  * Pimjetmi (pimicotinib), EMD Serono / Merck KGaA: FDA oncology notification, "On November 10, 2026, the Food and
    Drug Administration approved pimicotinib (Pimjetmi, EMD Serono, Inc.)..." No goal date tracked.
  * Optune Mya (NVCR): Novocure 8-K EX-99.1 dated November 9, 2026: the FDA issued a Not Approvable Letter on the PMA
    for brain metastases from NSCLC. A device PMA letter, recorded as such (never as a CRL). The letter's own date is
    not public; the row carries the announcement day and says so.
Acked as non-events (reasons stored): ENFLONSIA S-3 (adverse-reaction rates label update, letter 2026-10-14);
entrectinib and Darzalex Faspro feed items (2023 / 2021 notices the FDA's feed republished with a Nov 10 pubDate);
the CAPR Q3 8-K (Nov 10; says "if approved", PDUFA still pending).
Facts only, not investment advice.
"""
import datetime as dt
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
TODAY = "2026-11-11"
FDA_ASU = ("https://www.fda.gov/news-events/press-announcements/"
           "fda-approves-first-factor-xla-inhibitor-help-prevent-stroke-certain-adults-high-risk")
FDA_PIM = "https://www.fda.gov/drugs/cancer-approvals/fda-approves-pimicotinib-symptomatic-tenosynovial-giant-cell-tumor"
NVCR_8K = "https://www.sec.gov/Archives/edgar/data/1645113/000164511326000085/myadecisionpr.htm"

# ---------------- dataset
P = os.path.join(SITE, "api", "v1", "dataset.mjs")
s = io.open(P, encoding="utf-8").read()
i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
by = {r["id"]: r for r in rows}

if "pdufa_bayry_2026-11-09_asundexian" not in by:
    rows.append({
        "id": "pdufa_bayry_2026-11-09_asundexian", "t": "BAYRY", "company": "Bayer AG", "d": "2026-11-09", "dp": "day",
        "name": "Sunharbo (asundexian) - secondary stroke prevention", "type": "PDUFA", "ta": "Neurology", "cap": "Large",
        "st": "Decided", "oc": "Approved", "dcd": "2026-11-09", "url": "/fda-decision/BAYRY-2026-11-09", "ua": NOW,
        "_d": {"indication": ("With antiplatelet therapy, to reduce the risk of stroke after a recent mild-to-moderate "
                              "non-cardioembolic ischemic stroke or high-risk transient ischemic attack (adults)"),
               "brand": "Sunharbo", "inn": "asundexian", "trial": "OCEANIC-STROKE",
               "indication_short": "secondary stroke prevention", "title_indication": "Secondary Stroke Prevention",
               "goal_unsourced": True,
               "date_note": ("Bayer stated no PDUFA goal date (Priority Review granted May 2026). The row's date is the "
                             "FDA's action day, not a goal date; no early or late margin is computed."),
               "census_note": "Not in the decision-timing census: no sponsor-stated goal date.",
               "source": "FDA press announcement, November 9, 2026", "source_url": FDA_ASU,
               "decision_source": "FDA press announcement, November 9, 2026", "decision_source_url": FDA_ASU,
               "fda_action_date": "2026-11-09", "fda_action_source_url": FDA_ASU,
               "fda_action_record": "FDA press announcement, November 9, 2026",
               "announcement": "FDA press announcement, November 9, 2026", "announcement_url": FDA_ASU,
               "decision_quote": ("The U.S. Food and Drug Administration today approved Sunharbo (asundexian) 50 mg "
                                  "tablets, the first factor XIa (FXIa) inhibitor for use in combination with "
                                  "antiplatelet therapy to reduce the risk of stroke"),
               "seo_desc": ("Sunharbo (asundexian), Bayer, was approved by the FDA on November 9, 2026, the first factor "
                            "XIa inhibitor, for secondary stroke prevention.")}})

if "pdufa_mkkgy_2026-11-10_pimicotinib" not in by:
    rows.append({
        "id": "pdufa_mkkgy_2026-11-10_pimicotinib", "t": "MKKGY", "company": "Merck KGaA (EMD Serono)", "d": "2026-11-10",
        "dp": "day", "name": "Pimjetmi (pimicotinib) - tenosynovial giant cell tumor", "type": "PDUFA", "ta": "Oncology",
        "cap": "Large", "st": "Decided", "oc": "Approved", "dcd": "2026-11-10", "url": "/fda-decision/MKKGY-2026-11-10",
        "ua": NOW,
        "_d": {"indication": ("Adults with symptomatic tenosynovial giant cell tumor (TGCT) for which surgical resection "
                              "may cause worsening functional limitation or severe morbidity"),
               "brand": "Pimjetmi", "inn": "pimicotinib", "trial": "MANEUVER",
               "indication_short": "tenosynovial giant cell tumor", "title_indication": "Tenosynovial Giant Cell Tumor",
               "goal_unsourced": True,
               "date_note": "No PDUFA goal date tracked; the row's date is the FDA's action day.",
               "census_note": "Not in the decision-timing census: no sponsor-stated goal date on file.",
               "source": "FDA oncology approval notification, November 10, 2026", "source_url": FDA_PIM,
               "decision_source": "FDA oncology approval notification, November 10, 2026", "decision_source_url": FDA_PIM,
               "fda_action_date": "2026-11-10", "fda_action_source_url": FDA_PIM,
               "fda_action_record": "FDA oncology approval notification, November 10, 2026",
               "announcement": "FDA oncology approval notification, November 10, 2026", "announcement_url": FDA_PIM,
               "decision_quote": ("On November 10, 2026, the Food and Drug Administration approved pimicotinib (Pimjetmi, "
                                  "EMD Serono, Inc.), a kinase inhibitor, for adults with symptomatic tenosynovial giant "
                                  "cell tumor (TGCT)"),
               "seo_desc": ("Pimjetmi (pimicotinib), EMD Serono, was approved by the FDA on November 10, 2026 for "
                            "symptomatic tenosynovial giant cell tumor.")}})

r = by.get("pdufa_nvcr_2026-11-15")
if r and r.get("st") != "Decided":
    r.update({"st": "Decided", "oc": "Not approvable letter", "dcd": "2026-11-09", "ua": NOW})
    r["_d"].update({
        "decision_date_unsourced": True,
        "decision_source": "Novocure 8-K, November 9, 2026 (EX-99.1)", "decision_source_url": NVCR_8K,
        "announcement": "Novocure 8-K, November 9, 2026", "announcement_url": NVCR_8K,
        "decision_quote": ("Novocure (Nasdaq: NVCR) announced today that it has received a Not Approvable Letter from the "
                           "U.S. Food and Drug Administration (FDA) in response to its Premarket Approval (PMA) application "
                           "for Optune Mya"),
        "decision_note": ("A device PMA Not Approvable Letter, not a drug Complete Response Letter. Per Novocure, the FDA "
                          "cited uncertainty around the degree of clinical benefit and raised no safety concerns; Novocure "
                          "plans to meet the FDA. The letter's own date is not public; the date shown is Novocure's "
                          "announcement.")})

io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
print("dataset: BAYRY asundexian + MKKGY pimicotinib added (Approved); NVCR -> Not approvable letter")

# ---------------- prices for the decision charts (price_source: FMP)
import price_source as ps  # noqa: E402
PX = os.path.join(HERE, "_chart_pxcache.json")
px = json.load(open(PX))
for tk in ("BAYRY", "MKKGY", "NVCR"):
    rows_ = ps.daily(tk, "2026-03-01", TODAY)
    cur = px.setdefault(tk, {})
    added = sum(1 for d, c, _ in rows_ if d not in cur)
    for d, c, _ in rows_:
        cur.setdefault(d, c)
    print(f"  px {tk}: {len(rows_)} closes from {ps.source_of(tk)}, {added} new")
json.dump(px, open(PX, "w"))

# ---------------- decision pages
import build_decision_page as bdp  # noqa: E402
EV = [
    {"ticker": "BAYRY", "date": "2026-11-09", "outcome": "Approved", "drug": "Sunharbo (asundexian)",
     "indication": ("Secondary stroke prevention: with antiplatelet therapy, after a recent mild-to-moderate "
                    "non-cardioembolic ischemic stroke or high-risk TIA (adults)"),
     "company": "Bayer AG", "cap": "Large",
     "h1": "Sunharbo (asundexian) FDA approval: Nov 9, 2026",
     "headline": ("The FDA approved Sunharbo (asundexian) 50 mg tablets on November 9, 2026, the first factor XIa "
                  "inhibitor, for use with antiplatelet therapy to reduce the risk of stroke in adults after a recent "
                  "mild-to-moderate non-cardioembolic ischemic stroke or a high-risk transient ischemic attack."),
     "pdufa_note": ("Bayer did not publicly state a PDUFA goal date (the FDA granted Priority Review in May 2026), so this "
                    "page states no early or late margin. Per the FDA: OCEANIC-STROKE enrolled 12,327 adults; "
                    "Sunharbo reduced the risk of ischemic stroke by 26% versus placebo over a median 14.2 months; "
                    "major bleeding was similar overall but higher in patients over 75 and in the first 90 days. "
                    "Sunharbo is not approved for stroke prevention in atrial fibrillation."),
     "source": FDA_ASU, "source_label": "FDA press announcement, November 9, 2026"},
    {"ticker": "MKKGY", "date": "2026-11-10", "outcome": "Approved", "drug": "Pimjetmi (pimicotinib)",
     "indication": "Symptomatic tenosynovial giant cell tumor (TGCT) where surgery may worsen function (adults)",
     "company": "Merck KGaA (EMD Serono)", "cap": "Large",
     "h1": "Pimjetmi (pimicotinib) FDA approval: Nov 10, 2026",
     "headline": ("The FDA approved Pimjetmi (pimicotinib), EMD Serono's kinase inhibitor, on November 10, 2026 for "
                  "adults with symptomatic tenosynovial giant cell tumor for which surgical resection may cause "
                  "worsening functional limitation or severe morbidity."),
     "pdufa_note": ("No PDUFA goal date was tracked for this application, so no margin is stated. Per the FDA: in "
                    "MANEUVER, overall response at Week 25 was 56% with pimicotinib versus 3.2% with placebo. Merck KGaA's "
                    "ADR (MKKGY) trades over the counter."),
     "source": FDA_PIM, "source_label": "FDA oncology approval notification, November 10, 2026"},
]
for e in EV:
    try:
        bdp.build(e, px)
    except SystemExit as ex:
        print("  !! page not built:", e["ticker"], ex)

# ---------------- acks
def load(p, default):
    p = os.path.join(HERE, p)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else default


def save(p, o):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(o, indent=1, ensure_ascii=False) + "\n")


dw = load("_drug_watch_ack.json", {"acks": []})
for slug, src, why in (
        ("asundexian", "fda-press:fda-approves-first-factor-xla-inhibitor-help-prevent-stroke-",
         "Published 2026-11-11: Sunharbo (asundexian) approved Nov 9, 2026 (FDA press announcement); decision page "
         "/fda-decision/BAYRY-2026-11-09."),
        ("enflonsia", "openfda:20261014",
         "BLA 761432 S-3 (approved 2026-10-14) updates injection-site erythema/swelling rates in Adverse Reactions "
         "(FDA letter). Not the second-RSV-season sBLA we track (goal March 2027). Verified non-event.")):
    if not any(a.get("slug") == slug and a.get("source") == src for a in dw["acks"]):
        dw["acks"].append({"slug": slug, "source": src, "reason": why, "acked": TODAY})
save("_drug_watch_ack.json", dw)

ff = load("_fda_drugs_feed_ack.json", {"acked": [], "reasons": {}})
for k, why in (
        ("pdufa_jazz_2027-04-16|http://www.fda.gov/drugs/cancer-approvals/fda-expands-pediatric-indication-entrectinib-"
         "and-approves-new-pellet-formulation",
         "Republished 2023 notice (entrectinib pediatric pellets, Oct 20, 2023) with a Nov 10, 2026 pubDate; matched on "
         "'formulation'. Not a JAZZ action."),
        ("pdufa_bmy_2027-05-13|http://www.fda.gov/drugs/cancer-approvals/fda-grants-accelerated-approval-darzalex-faspro-"
         "newly-diagnosed-light-chain-amyloidosis",
         "Republished 2021 notice (Darzalex Faspro AL amyloidosis, Jan 15, 2021) with a Nov 10, 2026 pubDate; matched on "
         "'dexamethasone'. Not a BMY action.")):
    if k not in ff["acked"]:
        ff["acked"].append(k)
    ff.setdefault("reasons", {})[k] = why
save("_fda_drugs_feed_ack.json", ff)

fw = load("_fda_watch_ack.json", {"acks": []})
ck = "edgar:https://www.sec.gov/Archives/edgar/data/1133869/000110465926125150/capr-ex99d1.htm"
if not any(a.get("ap_date") == ck for a in fw["acks"]):
    fw["acks"].append({"ticker": "CAPR", "ap_date": ck,
                       "reason": ("Capricor Q3 2026 results (8-K Nov 10): says 'if approved' and 'as we approach our "
                                  "PDUFA date'; no approval. Nov 22, 2026 goal stands.")})
save("_fda_watch_ack.json", fw)

ek = load("_edgar_8k_ack.json", {"acked": []})
k = "pdufa_nvcr_2026-11-15|0001645113-26-000085"
if k not in ek["acked"]:
    ek["acked"].append(k)
save("_edgar_8k_ack.json", ek)
print("acks written: drug_watch 2, fda_drugs_feed 2, fda_watch 1, edgar_8k 1")
