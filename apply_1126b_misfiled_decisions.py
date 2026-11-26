# -*- coding: utf-8 -*-
"""apply_1126b_misfiled_decisions.py -- six FDA decision pages filed under a company that had nothing to do with the drug.

David, 2026-11-26 ("Continue"), with his standing hand-off for site fixes ("just do it, red team everything"). Found by
the decision-timing census of 2026-11-26 (decision_timing_2024_2025.json, cids C181 C199 C209 C231 C240 C323), which
compared each tracked decision's ticker with the applicant Drugs@FDA names. Applicants read from Drugs@FDA
(_fda_approvals_months.json, openFDA, each with its FDA approval letter):

  GILD-2025-12-16  Exdensur (depemokimab), BLA 761458, applicant GlaxoSmithKline LLC. Approved 2025-12-16 (Original 1,
                   severe eosinophilic asthma); same-day CRL for Original 2 (nasal polyps). Gilead has no part in it.
                   -> new page /fda-decision/GSK-2025-12-16 (decision_pages_2026_11_26_gsk.json, build_decision_page.py)
  ABBV-2025-04-02  Vanrafia (atrasentan), NDA 219208, applicant Novartis. -> /fda-decision/NVS-2025-04-03, which already
                   records the same approval.
  HOTH-2025-06-16  Andembry (garadacimab), BLA 761367, applicant CSL Behring LLC. -> /fda-decision/CSLLY-2025-06-17, which
                   already records the same approval.
  TURN-2025-02-14  Romvimza (vimseltinib), NDA 219304, applicant Deciphera (Ono Pharmaceutical group).
  EXEL-2025-07-02  Zegfrovy (sunvozertinib), NDA 219839, applicant Dizal.
  ANTE-2025-04-23  penpulimab-kcqx, BLA 761258, applicant Akeso Biopharma.
                   The last three applicants have no ticker on pdufa.bio, so there is no right ticker to move the page to;
                   each redirects to /decisions/approvals.

Each misfiled page carried the wrong company's share price as its run-up. Retired the way apply_1118_retire_decisions.py
retires a page (that script's main): page deleted, permanent redirect, every link removed, verification entry marked
retracted, ledgers pruned, /corrections entry. Run-up study exclusions are added so curate_runup_study.py drops the rows.
The new GSK page gets the ledger entries a census-matched page has. RETIRE joins RETRACTED in
tests/test_no_retracted_claims.py. Idempotent. Facts only, not investment advice.

    python apply_1126b_misfiled_decisions.py [--dry-run]
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TODAY = "2026-11-26"
DAF = "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo="


def _why(drug, appl, applicant, date, wrong, where):
    return (f"The FDA approved {drug} on {date} under {appl}, whose applicant is {applicant}, not {wrong}. "
            f"{wrong} had no FDA action that day. {where}")


# slug -> (redirect destination, one-line reason, source, what the page was): the shape tests/test_no_retracted_claims.py reads
RETIRE = {
    "GILD-2025-12-16": ("/fda-decision/GSK-2025-12-16",
                        _why("Exdensur (depemokimab)", "BLA 761458", "GlaxoSmithKline", "December 16, 2025", "Gilead",
                             "The decision now has its page under GSK."),
                        "Drugs@FDA, BLA 761458 (applicant GlaxoSmithKline LLC, approved 2025-12-16) " + DAF + "761458",
                        "A decision page for GILD dated 2025-12-16 recording GSK's Exdensur approval as a Gilead approval."),
    "ABBV-2025-04-02": ("/fda-decision/NVS-2025-04-03",
                        _why("Vanrafia (atrasentan)", "NDA 219208", "Novartis", "April 2, 2025", "AbbVie",
                             "The decision already has its page under Novartis."),
                        "Drugs@FDA, NDA 219208 (applicant Novartis, approved 2025-04-02) " + DAF + "219208",
                        "A decision page for ABBV dated 2025-04-02 recording Novartis's Vanrafia approval as an AbbVie approval."),
    "HOTH-2025-06-16": ("/fda-decision/CSLLY-2025-06-17",
                        _why("Andembry (garadacimab)", "BLA 761367", "CSL Behring", "June 16, 2025", "Hoth Therapeutics",
                             "The decision already has its page under CSL."),
                        "Drugs@FDA, BLA 761367 (applicant CSL Behring LLC, approved 2025-06-16) " + DAF + "761367",
                        "A decision page for HOTH dated 2025-06-16 recording CSL's Andembry approval as a Hoth approval."),
    "TURN-2025-02-14": ("/decisions/approvals",
                        _why("Romvimza (vimseltinib)", "NDA 219304", "Deciphera Pharmaceuticals (Ono Pharmaceutical group)",
                             "February 14, 2025", "TURN", "Deciphera has no ticker on pdufa.bio."),
                        "Drugs@FDA, NDA 219304 (applicant Deciphera, approved 2025-02-14) " + DAF + "219304",
                        "A decision page for TURN dated 2025-02-14 recording Deciphera's Romvimza approval under TURN."),
    "EXEL-2025-07-02": ("/decisions/approvals",
                        _why("Zegfrovy (sunvozertinib)", "NDA 219839", "Dizal", "July 2, 2025", "Exelixis",
                             "Dizal has no ticker on pdufa.bio."),
                        "Drugs@FDA, NDA 219839 (applicant Dizal, approved 2025-07-02) " + DAF + "219839",
                        "A decision page for EXEL dated 2025-07-02 recording Dizal's Zegfrovy approval as an Exelixis approval."),
    "ANTE-2025-04-23": ("/decisions/approvals",
                        _why("penpulimab-kcqx", "BLA 761258", "Akeso Biopharma", "April 23, 2025", "ANTE",
                             "Akeso has no ticker on pdufa.bio."),
                        "Drugs@FDA, BLA 761258 (applicant Akeso Biopharma, approved 2025-04-23) " + DAF + "761258",
                        "A decision page for ANTE dated 2025-04-23 recording Akeso's penpulimab approval under ANTE."),
}

NEW = "GSK-2025-12-16"
NEW_ARCHIVE = {"basis": "decision-timing census 2026-11-26: FDA record read", "checked": TODAY, "cid": "C323",
               "date": "2025-12-16", "letter": "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2025/761458Orig1s000ltr.pdf",
               "name": "Exdensur (depemokimab)", "oc": "Approved", "record": "BLA 761458 Original 1",
               "source_url": DAF + "761458"}


def jload(p):
    return json.load(io.open(os.path.join(HERE, p), encoding="utf-8"))


def jsave(p, d, indent=1):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8", newline="").write(
        json.dumps(d, indent=indent, ensure_ascii=False) + "\n")


def new_page_ledgers(dry):
    """Give GSK-2025-12-16 the entries GILD-2025-12-16 had, under the right ticker. Runs before the retirement prunes them."""
    ver = jload("_decision_verification.json")
    old = ver["results"].get("GILD-2025-12-16")
    if NEW not in ver["results"] and old and old.get("status") != "retracted":
        e = json.loads(json.dumps(old))
        e["ticker"] = "GSK"
        ver["results"][NEW] = e
        if not dry:
            jsave("_decision_verification.json", ver)
        print(f"_decision_verification.json: {NEW} added")
    arch = jload("_fda_action_archive.json")
    if arch.get(NEW) != NEW_ARCHIVE:
        arch[NEW] = NEW_ARCHIVE
        if not dry:
            jsave("_fda_action_archive.json", arch)
        print(f"_fda_action_archive.json: {NEW} set")
    pub = jload("_decision_published.json")
    if NEW not in pub:
        pub[NEW] = TODAY
        if not dry:
            jsave("_decision_published.json", pub, indent=0)
        print(f"_decision_published.json: {NEW} added")


# Drug pages. /drug/andembry, /drug/romvimza, /drug/zegfrovy and /drug/penpulimab were built only from a misfiled page,
# so build_drug_pages.py drops them; each redirects where the decision now lives. Three pages that keep a decision are
# patched to what build_drug_pages.py now writes for them (checked against its output on 2026-11-26).
DRUG_REDIRECTS = {"/drug/andembry": "/drug/garadacimab", "/drug/romvimza": "/decisions/approvals",
                  "/drug/zegfrovy": "/decisions/approvals", "/drug/penpulimab": "/decisions/approvals"}
GSK_ROW = ('<a class="row" href="/fda-decision/GSK-2025-12-16"><span class="t">FDA decision &middot; Dec 16, 2025 '
           '<span class="ok">&#10003; Approved</span></span><span class="d">GSK</span></a>')
DRUG_PATCH = {
    "exdensur": [('<a class="lit" href="/ticker/GILD">GILD catalyst hub</a>', '<a class="lit" href="/ticker/GSK">GSK catalyst hub</a>'),
                 ("<h2>Catalyst history</h2>", "<h2>Catalyst history</h2>" + GSK_ROW)],
    "vanrafia": [("2 FDA decisions on record below.", "1 FDA decision on record below."),
                 ('<a class="lit" href="/ticker/ABBV">ABBV catalyst hub</a> &middot; ', ""),
                 ("We track 2 catalyst events for this program: 0 upcoming and 2 in the record.",
                  "We track 1 catalyst event for this program: 0 upcoming and 1 in the record."),
                 ("2 FDA decisions are on record below.", "1 FDA decision is on record below.")],
    "garadacimab": [("2 FDA decisions on record below.", "1 FDA decision on record below."),
                    (' &middot; <a class="lit" href="/ticker/HOTH">HOTH catalyst hub</a>', ""),
                    ('Garadacimab is marketed as <a class="lit" href="/drug/andembry">Andembry (garadacimab-gxii)</a>; the events '
                     'below include those tracked under the brand name. We track 2 catalyst events for this program: 0 upcoming '
                     'and 2 in the record.', "We track 1 catalyst event for this program: 0 upcoming and 1 in the record."),
                    ("2 FDA decisions are on record below.", "1 FDA decision is on record below.")],
}


def drug_pages(dry):
    import re
    import shutil
    site = os.path.join(HERE, "pdufa_site_src")
    for src in DRUG_REDIRECTS:
        d = os.path.join(site, src.strip("/"))
        if os.path.isdir(d) and not dry:
            shutil.rmtree(d)
    vp = os.path.join(site, "vercel.json")
    v = json.load(io.open(vp, encoding="utf-8"))
    have = {r["source"] for r in v["redirects"]}
    n = 0
    for src, dst in DRUG_REDIRECTS.items():
        if src not in have:
            v["redirects"].append({"source": src, "destination": dst, "permanent": True})
            n += 1
    if n and not dry:
        io.open(vp, "w", encoding="utf-8").write(json.dumps(v, indent=1, ensure_ascii=False) + "\n")
    print(f"drug redirects added: {n}")
    for slug, reps in DRUG_PATCH.items():
        p = os.path.join(site, "drug", slug, "index.html")
        doc = io.open(p, encoding="utf-8").read()
        new = doc
        for a, b in reps:
            if b and b in new and a not in new:
                continue
            if a == "<h2>Catalyst history</h2>" and "GSK-2025-12-16" in new:
                continue
            new = new.replace(a, b)
        if slug == "vanrafia":       # 13F block about AbbVie holders: AbbVie has no part in Vanrafia
            new = re.sub(r"<!--F13:BEGIN-->.*?<!--F13:END-->", "", new, flags=re.S)
        if new != doc and not dry:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
        print(f"/drug/{slug}: {'patched' if new != doc else 'already current'}")


def main():
    dry = "--dry-run" in sys.argv
    if not os.path.exists(os.path.join(HERE, "pdufa_site_src", "fda-decision", NEW, "index.html")):
        raise SystemExit(f"build {NEW} first: python build_decision_page.py --events decision_pages_2026_11_26_gsk.json")
    new_page_ledgers(dry)
    import apply_1118_retire_decisions as R
    R.TODAY = TODAY
    R.RETIRE = dict(RETIRE)
    R.main()
    if dry:
        return
    p = os.path.join(HERE, "runup_study_exclusions.json")
    ex = json.load(io.open(p, encoding="utf-8"))
    pages = ex.setdefault("pages", {})
    n = 0
    for s, (_dst, why, src, _was) in RETIRE.items():
        e = {"reason": "wrong company: " + why, "document": src,
             "finding": "the tracked list filed the approval under a ticker that is not the applicant's", "checked": TODAY}
        if pages.get(s) != e:
            pages[s] = e
            n += 1
    if n:
        io.open(p, "w", encoding="utf-8").write(json.dumps(ex, indent=1, ensure_ascii=False))
    print(f"runup_study_exclusions.json: {n} entr(ies) added")
    drug_pages(dry)


if __name__ == "__main__":
    main()
