# -*- coding: utf-8 -*-
"""apply_1125_currency.py -- the currency pass of 2026-11-25: Capricor brought up to date, and 15 decision pages that
called a date a Complete Response Letter when the page itself said it was not one are retired.

David, 2026-11-25 02:53 UTC (Nov 24, 9:53 PM ET; 6:53 PM PT): "ensure that CAPr is up to date, everything is up to
date, keep increasing our moat."

1. CAPR deramiocel. Sources read 2026-11-25 between 03:00 and 03:30 UTC (Nov 24, 10:00-10:30 PM ET; RULE 1):
   * Capricor 8-K accepted 2026-11-20 20:15 ET (filed 2026-11-23), EX-99.1 the Nov 20 release: the CRL "states that
     the FDA does not consider the data sufficient to establish substantial evidence of effectiveness and cites certain
     other clinical deficiencies." No letter date, no deficiency named beyond that, no next-step date.
   * Capricor release, GlobeNewswire, "November 23, 2026 06:30 ET": the conference call planned for that day is
     rescheduled, details "will be shared shortly", and "The Company is actively preparing its regulatory response".
   * FMP end-of-day closes (Eastern trading days): Nov 20 $7.59, Nov 23 $1.92, Nov 24 $2.02.
   Stale lines fixed: the dataset row's review note still said "The application remains under review" (shown on
   /drug/deramiocel); /crl/capricor-deramiocel showed the second CRL's first close after as "not yet traded"; the
   timeline stopped at November 20.
   A law-firm notice of 2026-11-23 says the second CRL cites "data-integrity issues". Neither Capricor's release nor
   its 8-K says so, so nothing here repeats it.

2. Fifteen decision pages carried the old archive's CRL mark beside their own CRL-reason line saying it was not one
   ("Mislabel: Phase 3 EQUATOR readout miss, no CRL"). Twelve were indexed with titles such as "IBRX FDA Decision:
   CRL Jan 16, 2026", descriptions saying the company "received a Complete Response Letter", FAQ answers saying the
   same, and rows on /decisions and the /ticker hubs. Each linked source was re-read on 2026-11-25 (above window):
   none announces a CRL; eleven are trial-data releases or filings with no FDA action, and Savara's is a refusal-to-
   file letter. The three noindexed ones (CYTK, PHIO 07-28, URGN) state the same on the page. They are retired the
   way apply_1118_retire_decisions.py retires a page: page deleted, permanent redirect (to the real decision where
   there is one, otherwise the ticker hub), every link removed, ledgers pruned, a /corrections entry, and a
   run-up-study exclusion. The slugs join RETRACTED in tests/test_no_retracted_claims.py.

Idempotent. Facts only; not investment advice.

    python apply_1125_currency.py [--dry-run]
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
DRY = "--dry-run" in sys.argv
TODAY = "2026-11-24"   # Eastern (RULE 1): the work ran Nov 24, 10:00-11:00 PM ET

CAPR_1123 = ("https://www.globenewswire.com/news-release/2026/11/23/3408177/0/en/capricor-therapeutics-reschedules-"
             "conference-call-to-provide-deramiocel-update.html")

# slug -> (redirect destination, what the date was, source): the shape tests/test_no_retracted_claims.py reads
RETIRE = {
    "ALLO-2025-02-14": ("/ticker/ALLO", "Allogene announced the journal publication of Phase 1 ALPHA and ALPHA2 data "
                        "that day (release dated February 13, 2025). No FDA action; no CRL.",
                        "Allogene release of February 13, 2025 (GlobeNewswire)"),
    "ENGN-2025-11-11": ("/ticker/ENGN", "enGene reported a 62% complete response rate at 6 months for detalimogene in "
                        "the LEGEND trial; \"complete response\" there is the trial's clinical measure, not an FDA "
                        "letter. No CRL.", "enGene release of November 11, 2025 (Business Wire)"),
    "EQ-2025-03-27": ("/ticker/EQ", "Equillium reported topline results of the Phase 3 EQUATOR study of itolizumab. No "
                      "FDA action; no CRL.", "Equillium release of March 27, 2025 (Business Wire)"),
    "ESLA-2025-11-03": ("/ticker/ESLA", "Estrella's 8-K reported completion of the second dose cohort of the Phase I "
                        "STARLIGHT-1 study. No FDA action; no CRL.", "Estrella Immunopharma 8-K, report date "
                        "November 3, 2025"),
    "IBRX-2026-01-16": ("/ticker/IBRX", "ImmunityBio reported discussions with the FDA about information to support a "
                        "potential resubmission of an ANKTIVA supplemental BLA (release dated January 20, 2026). No "
                        "CRL that day.", "ImmunityBio release, January 2026 (ir.immunitybio.com)"),
    "JSPR-2025-01-08": ("/ticker/JSPR", "Jasper reported preliminary data from the Phase 1b/2a BEACON study of "
                        "briquilimab. No FDA action; no CRL.",
                        "Jasper Therapeutics release of January 8, 2025 (GlobeNewswire)"),
    "JSPR-2025-07-07": ("/ticker/JSPR", "Jasper reported a briquilimab clinical data update. No FDA action; no CRL.", "Jasper Therapeutics release of July 7, 2025 (GlobeNewswire)"),
    "LSTA-2025-01-22": ("/ticker/LSTA", "Lisata reported preliminary Phase 2b ASCEND cohort data for certepetide; "
                        "\"complete responses\" is the trial's clinical measure. No FDA action; no CRL.",
                        "Lisata Therapeutics release of January 22, 2025"),
    "PHIO-2025-01-13": ("/ticker/PHIO", "Phio reported results from the second cohort of its PH-762 clinical study. "
                        "No FDA action; no CRL.", "Phio Pharmaceuticals release of January 13, 2025"),
    "PHIO-2025-07-28": ("/ticker/PHIO", "The page's own record said Phio had no PDUFA date on this date and that the "
                        "CRL label was an error.",
                        "the retired page's own CRL-reason line"),
    "SNSE-2025-10-17": ("/ticker/SNSE", "Sensei reported clinical results for solnerstotug at ESMO 2025. No FDA action; "
                        "no CRL.", "Sensei Biotherapeutics release of October 17, 2025 (GlobeNewswire)"),
    "SVRA-2025-05-27": ("/ticker/SVRA", "Savara announced a refusal-to-file letter for the MOLBREEVI BLA: the FDA "
                        "declined to file the application for review, which is not a Complete Response Letter.",
                        "Savara release of May 27, 2025 (Business Wire)"),
    "TRAW-2025-06-03": ("/ticker/TRAW", "The page's only cited source, Traws's 10-K for 2024, reports no Complete "
                        "Response Letter, and no source we found records an FDA action for Traws on this date.", "Traws Pharma 10-K for the year ended "
                        "December 31, 2024"),
    "CYTK-2025-11-07": ("/fda-decision/CYTK-2025-12-19", "Aficamten was not refused on this date; the FDA approved it "
                        "as MYQORZO on December 19, 2025, which has its own page.",
                        "the retired page's own CRL-reason line; the MYQORZO decision page"),
    "URGN-2025-04-27": ("/fda-decision/URGN-2025-06-12", "UroGen had no CRL in April 2025; the FDA approved ZUSDURI "
                        "(UGN-102) on June 12, 2025, which has its own page.",
                        "the retired page's own CRL-reason line; the ZUSDURI decision page"),
}


def was_line(slug):
    tk, d = slug.split("-", 1)
    return f"A decision page for {tk} dated {d}, titled and listed as a Complete Response Letter."


def rd(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def wr(p, s):
    if not DRY:
        io.open(p, "w", encoding="utf-8", newline="").write(s)


def capr():
    # 1a. the dataset row's review note
    src = rd(DATASET)
    old = ("CBER accepted it, classified it a major amendment, and added three months to review it. The application "
           "remains under review: this is an extension, not a Complete Response Letter.")
    new = ("CBER accepted it, classified it a major amendment, and added three months to review it. That review ended "
           "in a Complete Response Letter, announced by Capricor on November 20, 2026.")
    if old in src:
        wr(DATASET, src.replace(old, new))
        print("  dataset pdufa_capr_2026-08-22: review note past tense")
    # the drug page carries the same sentence until build_drug_pages.py redraws it
    p = os.path.join(SITE, "drug", "deramiocel", "index.html")
    d = rd(p)
    if old in d:
        wr(p, d.replace(old, new))
        print("  /drug/deramiocel: review note past tense")

    # 1b. the case file behind /crl/capricor-deramiocel
    cp = os.path.join(HERE, "_crl_capricor_case.json")
    case = json.load(io.open(cp, encoding="utf-8"))
    ch = False
    m = next(x for x in case["moves"] if x["what"] == "Second CRL announced")
    if m.get("after") is None:
        assert m["before"] == ["2026-11-20", 7.59], "Nov 20 close changed; re-read before publishing"
        m["after"] = ["2026-11-23", 1.92]
        ch = True
    if not any(e.get("date") == "2026-11-23" for e in case["events"]):
        case["events"].append({
            "date": "2026-11-23", "time": "6:30 a.m.", "who": "Capricor",
            "what": ("Capricor reschedules the conference call it had planned for that day and says details will "
                     "follow. It says it \"is actively preparing its regulatory response\"; the release gives no date "
                     "for a response or for the call."),
            "url": CAPR_1123, "src": "Capricor release"})
        ch = True
    if case.get("read") != "2026-11-21, 2026-11-22 and 2026-11-25":
        case["read"] = "2026-11-21, 2026-11-22 and 2026-11-25"
        ch = True
    if ch and not DRY:
        io.open(cp, "w", encoding="utf-8").write(json.dumps(case, indent=1, ensure_ascii=False) + "\n")
    print(f"  _crl_capricor_case.json: {'updated' if ch else 'already current'}")


def retire():
    import apply_1118_retire_decisions as R
    R.TODAY = TODAY
    R.RETIRE = {s: (dst, why, src, was_line(s)) for s, (dst, why, src) in RETIRE.items()}
    R.main()
    if DRY:
        return
    p = os.path.join(HERE, "runup_study_exclusions.json")
    ex = json.load(io.open(p, encoding="utf-8"))
    pages = ex.setdefault("pages", {})
    n = 0
    for s, (_dst, why, src) in RETIRE.items():
        e = {"reason": "not an FDA decision: " + why, "document": src,
             "finding": "the page's CRL mark came from the old archive; its own CRL-reason line said it was not one",
             "checked": TODAY}
        if pages.get(s) != e:
            pages[s] = e
            n += 1
    if n:
        io.open(p, "w", encoding="utf-8").write(json.dumps(ex, indent=1, ensure_ascii=False))
    print(f"runup_study_exclusions.json: {n} entr(ies) added")


if __name__ == "__main__":
    capr()
    retire()
    print("apply_1125_currency: done")
