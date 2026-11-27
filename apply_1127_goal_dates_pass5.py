# -*- coding: utf-8 -*-
"""apply_1127_goal_dates_pass5.py -- 14 more FDA actions since 2024 get a sourced goal date (pass 5).

2026-11-27 (David, "Continue" at 02:53 UTC, carrying on his 2026-11-26 06:51 UTC ask: "keep building our databases
... most accurate dates").

Pass 5 of the decision-timing census (decision_timing_2024_2025.json) re-searched 144 of the 199 candidates left out
for want of a goal date, using sources the earlier passes had not read: the other documents of each FDA approval
package (Medical, Other, Summary and Administrative Correspondence files, where the FDA prints "PDUFA Goal Date" on a
review cover sheet or memo), the regulatory history in the next cycle's review for complete response letters, and one
fresh sponsor search. 13 rows were found; a separate check re-read each at source (both dates, the application and the
cycle): 12 confirmed, 1 corrected (insulin icodec: Novo Nordisk's Q4 2023 report says the FDA extended the review by
three months after a major amendment, so July 10, 2024 is the extended goal; the original is not stated, so it is
left null).

Dedupe: the June 18, 2024 Vyalev complete response is one FDA action listed twice (tracked row C077 and FDA-letter
row L035); it is counted once, as C077 with both members.

Tevimbra second-line ESCC (C027) is added as a late decision, like penpulimab's first cycle (L004) in pass 4: the
FDA review cover sheet confirms the July 12, 2022 goal, the FDA deferred action pending inspections without setting a
new date (BeiGene 8-K, July 14, 2022), and approval came on March 13, 2024.

Relacorilant (C333) enters as a complete response on its goal date. Its only FDA-published letter
(CRL_NDA219398_20260128.pdf, e-signed January 28, 2026) is headed "CORRECTED COMPLETE RESPONSE" and says, on its first
page as held in the openFDA CRL corpus (CRL_corpus_openFDA_2026-06-22.json): "We also refer to our complete response
letter dated December 30, 2025 ... The effective action date will remain December 30, 2025, the date of the original
letter." Corcept's November 4, 2025 release (8-K Ex. 99.1) gave the PDUFA date as December 30, 2025. The site's
decision page already used December 30 (apply_1118d_decision_sources.py); only the census had it out.

Tickers: penpulimab's applicant is Akeso (Hong Kong listed), not ANTE, so it carries none, as its CRL row does;
Orexo is ORX.ST; CSL is CSLLY, as on its other rows.

Idempotent. Facts only, not investment advice.

    python apply_1127_goal_dates_pass5.py [--dry-run]
"""
import argparse
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "decision_timing_2024_2025.json")
P5 = "/mnt/project-files/pdufa-bio/decision-timing/pass5"
ROWS = os.path.join(HERE, "decision_timing_pass5_rows.json")   # frozen copy of the 13 red-teamed rows, kept in git
RT = "Pass 5 (2026-11-27): goal and action dates re-read at source by a separate check; confirmed."
RT_C086 = ("Pass 5 (2026-11-27): goal and action dates re-read at source by a separate check; corrected: the review "
           "was extended three months after a major amendment (Novo Nordisk Q4 2023 report), so July 10, 2024 is the "
           "extended goal.")
ORDER = ["C044", "C090", "C209", "L042", "C077", "C132", "C086", "C161", "C136", "C179", "C308", "L050", "C027"]
MEMBERS = {"C077": ["C077", "L035"]}
TICKER_FIX = {"C209": [], "L042": ["ORX.ST"], "L050": ["CSLLY"]}
# C308 is Keytruda's approval in the Padcev combination: its goal date is Merck's, so it
# belongs on Merck's decision page only, not on the Astellas and Pfizer Padcev pages.
DECISION_PAGES = {"C308": ["MRK-2025-11-21"]}
ARCHIVE = os.path.join(HERE, "_fda_action_archive.json")
# C179 (Evrysdi tablets) is NDA 219285; the RHHBY page held the oral-solution NDA 213535 record.
ARCHIVE_ADD = {"RHHBY-2025-02-12": {
    "basis": "decision-timing census 2026-11-27 (pass 5): FDA record read", "checked": "2026-11-27",
    "cid": "C179", "date": "2025-02-11", "name": "EVRYSDI (risdiplam) 5 mg tablets, original NDA",
    "oc": "Approved", "record": "NDA 219285 ORIG-1",
    "source_url": "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo=219285"}}
FIX = {
    "L042": {"extended": None},   # no document states it; the CRL coming on the goal day is not proof
    "C086": {"goal_date_original": None, "goal_original_url": None, "goal_original_doc_date": None,
             "goal_original_quote": None, "extended": True, "goal_date_extended": "2024-07-10",
             "goal_extended_url": "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/761326Orig2s000OtherR.pdf",
             "goal_extended_doc_date": "2024-05-09",
             "goal_extended_quote": "PDUFA Date: 7/10/2024 (FDA Decision Support and Analysis Memorandum, May 9, 2024)",
             "extension_reason": ("major amendment: Novo Nordisk's Q4 2023 report (6-K, January 31, 2024, "
                                  "https://www.sec.gov/Archives/edgar/data/353278/000162828024002639/caq42023.htm) "
                                  "says data it submitted during the review 'is considered to constitute a major "
                                  "amendment' and 'the regulatory review is extended with three months'")},
}
C027_NOTE = ("Deferred action: the FDA deferred action at the July 12, 2022 goal pending inspections in China and gave "
             "no new anticipated action date (BeiGene 8-K, July 14, 2022, "
             "https://www.sec.gov/Archives/edgar/data/1651308/000165130822000124/ax14jul2022xex991xtisle2le.htm); "
             "approval came March 13, 2024, about 20 months after the goal. Counted as late, as penpulimab's first "
             "cycle (L004) is.")
C333_ROW = {
    "cid": "C333", "drug": "relacorilant - hypertension secondary to hypercortisolism (endogenous Cushing's syndrome)",
    "application": "NDA 219398", "sponsor": "Corcept Therapeutics", "tickers": "CORT",
    "goal_date_original": "2025-12-30",
    "goal_original_url": "https://www.sec.gov/Archives/edgar/data/1088856/000162828025048814/cort110425ex991pressrelease.htm",
    "goal_original_doc_date": "2025-11-04",
    "goal_original_quote": ("Our New Drug Application (NDA) for relacorilant in hypercortisolism has a Prescription Drug "
                            "User Fee Act (PDUFA) date of December 30, 2025."),
    "extended": None, "goal_date_extended": None, "goal_extended_url": None, "goal_extended_doc_date": None,
    "goal_extended_quote": None, "extension_reason": None, "goal_in_effect": "2025-12-30", "goal_verified_by": "fetched",
    "action_date": "2025-12-30", "action_basis": "fda_record",
    "action_url": "https://download.open.fda.gov/crl/CRL_NDA219398_20260128.pdf",
    "action_quote": ("NDA 219398 CORRECTED COMPLETE RESPONSE ... We also refer to our complete response letter dated "
                     "December 30, 2025 ... The effective action date will remain December 30, 2025, the date of the "
                     "original letter."),
    "announcement_date": "2025-12-31", "announcement_url": None, "outcome": "CRL", "goal_source_type": "sponsor",
    "goal_fda_doc_title": None,
    "notes": ("Pass 5: the FDA's corrected CRL (e-signed 01/28/2026) states the original letter was dated December 30, "
              "2025 and that the effective action date stays December 30, 2025 (first page as held in the openFDA CRL "
              "corpus; the PDF copy served today starts at page 2). Corcept announced the CRL on December 31, 2025. "
              "Goal from Corcept's November 4, 2025 release (fetched 2026-11-27). CRL on the goal date (a Tuesday)."),
}
RT_C333 = ("Pass 5 (2026-11-27): goal re-read in Corcept's November 4, 2025 release; action date read in the FDA's "
           "corrected letter text (openFDA CRL corpus); confirmed.")
KEEP = ["cid", "drug", "application", "sponsor", "tickers", "goal_date_original", "goal_original_url",
        "goal_original_doc_date", "goal_original_quote", "extended", "goal_date_extended", "goal_extended_url",
        "goal_extended_doc_date", "goal_extended_quote", "extension_reason", "goal_in_effect", "goal_verified_by",
        "action_date", "action_basis", "action_url", "action_quote", "announcement_date", "announcement_url",
        "outcome", "goal_source_type", "goal_fda_doc_title", "notes"]


def frozen_rows():
    if os.path.exists(ROWS):
        return json.load(io.open(ROWS, encoding="utf-8"))
    found = {}
    for i in range(1, 7):
        for x in json.load(io.open(os.path.join(P5, f"out_{i}.json"), encoding="utf-8")):
            if x.get("cid") in ORDER:
                found[x["cid"]] = x
    ok = {}
    for i in (1, 2, 3):
        for v in json.load(io.open(os.path.join(P5, "redteam", f"rt_out_{i}.json"), encoding="utf-8")):
            ok[v["cid"]] = v["verdict"]
    out = []
    for cid in ORDER:
        assert ok.get(cid) in ("confirmed", "corrected"), f"{cid}: {ok.get(cid)}"
        r = {k: found[cid].get(k) for k in KEEP}
        r.update(FIX.get(cid, {}))
        if cid == "C027":
            r["notes"] = (r.get("notes") or "") + " " + C027_NOTE
        out.append(r)
    out.append(dict(C333_ROW))
    io.open(ROWS, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    doc = json.load(io.open(DATA, encoding="utf-8"))
    have = {x["cid"] for x in doc["actions"]}
    ex = {x["cid"]: x for x in doc["excluded_rows"]}
    added = 0
    for r in frozen_rows():
        cid = r["cid"]
        if cid in have:
            continue
        e = ex.get(cid)
        assert e, f"{cid}: not among the excluded rows"
        tk = TICKER_FIX.get(cid, [t for t in str(e.get("tickers") or "").split("/") if t and t != "None"])
        row = dict(r)
        row.update({
            "tickers": tk, "members": MEMBERS.get(cid, [cid]), "origin": e["origin"], "excluded": None,
            "scope_note": None, "red_team": {"C086": RT_C086, "C333": RT_C333}.get(cid, RT),
            "extended": True if r.get("extended") else (False if r.get("extended") is False else None),
            "goal_verified_by": r.get("goal_verified_by") or "fetched",
        })
        nt = (r.get("notes") or "").strip()
        row["notes"] = nt if nt.startswith("Pass ") else ("Pass 5. " + nt).strip()
        doc["actions"].append(row)
        gone = set(row["members"])
        doc["excluded_rows"] = [x for x in doc["excluded_rows"] if x["cid"] not in gone]
        added += 1
    for x in doc["actions"]:
        if x["cid"] in DECISION_PAGES and x.get("decision_pages") != DECISION_PAGES[x["cid"]]:
            x["decision_pages"] = DECISION_PAGES[x["cid"]]
    doc["about"] = doc["about"].replace("(four research passes)", "(five research passes)")
    print(f"census: +{added} actions -> {len(doc['actions'])} actions, {len(doc['excluded_rows'])} excluded")
    if a.dry_run:
        return
    io.open(DATA, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    arc = json.load(io.open(ARCHIVE, encoding="utf-8"))
    if any(arc.get(k) != v for k, v in ARCHIVE_ADD.items()):
        arc.update(ARCHIVE_ADD)
        io.open(ARCHIVE, "w", encoding="utf-8", newline="\n").write(
            json.dumps(dict(sorted(arc.items())), indent=1, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
