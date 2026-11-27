# -*- coding: utf-8 -*-
"""apply_1127c_zynyz_crl.py -- 2026-11-27: the Zynyz NSCLC Complete Response Letter was dated to a day nothing happened.

Two decision pages, /fda-decision/INCY-2026-04-08 and /fda-decision/MGNX-2026-04-08, said Zynyz (retifanlimab-dlwr)
"received a Complete Response Letter on April 8, 2026; no source is cited for it yet." Both were archive pages first
recorded 2026-07-25 (commit 07d961e), marked "unverified" with no evidence in _decision_verification.json, and the
run-up study already excluded them for want of a source.

Primary source, read 2026-11-27: Incyte Form 8-K, Date of Report February 27, 2026, signed March 6, 2026
(https://www.sec.gov/Archives/edgar/data/879169/000087916926000013/incy-20260227.htm):
  "On February 27, 2026, the U.S. Food and Drug Administration ("FDA") issued a Complete Response Letter ("CRL")
   for the supplemental Biologics License Application ("sBLA") for Zynyz(R) (retifanlimab-dlwr) injection (375mg)
   for an additional indication for the treatment of adult patients with metastatic non-small cell lung cancer
   ("NSCLC") in combination with platinum-based chemotherapy."
  "The CRL cited the regulatory compliance of Catalent Indiana as the sole approvability issue, and did not cite
   other approvability concerns, including Zynyz's efficacy and safety data in NSCLC or the third-party drug
   substance manufacturer."
No FDA CRL file for this sBLA is in openFDA's CRL corpus (checked against CRL_corpus_openFDA_2026-11-25.json).
The 8-K does not mention MacroGenics. Incyte is the applicant (per Incyte's Q3 2026 10-Q, MacroGenics licensed
retifanlimab to it and is owed milestones), so the MacroGenics page is retired, as apply_1126b_misfiled_decisions.py
retired pages filed under a company that is not the applicant. The first public disclosure found is the 8-K itself,
filed March 6, 2026; no Incyte release was found, and Incyte gave no PDUFA date for this sBLA.

What this does: builds /fda-decision/INCY-{PAGE_DATE} from price data with build_decision_page.py
(decision_pages_2026_11_27_zynyz.json), then retires both April 8 pages through apply_1118_retire_decisions.main()
(page deleted, 301 to the new page, every link and JSON-LD list item removed, ledgers pruned, verification entry
marked retracted, /corrections entry). runup_study_excluded.csv keeps its rows (removed rows are never deleted). Idempotent.
Facts only, not investment advice.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

EIGHTK = "https://www.sec.gov/Archives/edgar/data/879169/000087916926000013/incy-20260227.htm"
LETTER = "2026-02-27"          # the FDA's letter, per Incyte's 8-K
PAGE_DATE = "2026-03-06"       # the day it became public: the 8-K, signed and filed March 6, 2026. No earlier Incyte
                               # release was found (businesswire, investor.incyte.com, EDGAR searched 2026-11-27)
NEW = f"/fda-decision/INCY-{PAGE_DATE}"
TODAY = "2026-11-27"

EVENTS_FILE = os.path.join(HERE, "decision_pages_2026_11_27_zynyz.json")
EVENTS = [{
    "ticker": "INCY",
    "date": PAGE_DATE,
    "fda_action_date": LETTER,
    "outcome": "CRL",
    "drug": "Zynyz (retifanlimab-dlwr) - metastatic NSCLC with platinum chemotherapy (POD1UM-304)",
    "indication": ("Adults with metastatic non-small cell lung cancer (NSCLC), in combination with platinum-based "
                   "chemotherapy (supplemental BLA)"),
    "company": "Incyte Corporation",
    "cap": "Large",
    "headline": None,       # set below
    "pdufa_note": None,     # set below
    "source": EIGHTK,
    "source_label": "Incyte Form 8-K, date of report February 27, 2026, filed March 6, 2026",
    "h1": 'Zynyz (retifanlimab-dlwr) <span class="g">FDA Complete Response Letter in NSCLC</span>: Feb 27, 2026',
}]
A = 'rel="noopener" style="color:#e3ba5e"'
EVENTS[0]["headline"] = (
    "The FDA issued a Complete Response Letter on February 27, 2026 for Incyte's supplemental BLA for Zynyz "
    "(retifanlimab-dlwr) in adults with metastatic non-small cell lung cancer, in combination with platinum-based "
    "chemotherapy. Per Incyte, the letter's only approvability issue was inspection findings at Catalent Indiana, "
    "the third-party fill-finish site; it cited no other approvability concerns, including Zynyz's efficacy and safety "
    "data. Incyte disclosed the letter in a Form 8-K "
    "filed on March 6, 2026.")
EVENTS[0]["pdufa_note"] = (
    "Incyte's Form 8-K (date of report February 27, 2026, signed March 6, 2026) states that the FDA issued the "
    "Complete Response Letter on February 27, 2026, that the letter cited inspection findings, not specific to "
    "Zynyz, at Catalent Indiana, LLC, part of Novo Nordisk, the fill-finish facility referenced in the sBLA, and "
    "that it cited that site's regulatory compliance as the sole approvability issue and did not cite other "
    "approvability concerns, including Zynyz's efficacy and safety data in NSCLC or the third-party drug substance "
    "manufacturer "
    f'(<a href="{EIGHTK}" {A}>Incyte 8-K</a>). The sBLA was supported by the Phase 3 POD1UM-304 trial. Incyte said '
    "it is working with the FDA and Catalent Indiana toward a potential resubmission. No FDA letter for this "
    "supplement is published in openFDA's CRL files. Correction, November 27, 2026: earlier pages on this site "
    "dated this letter April 8, 2026 with no source (see /corrections).")

# retired slug -> (destination, why, source, what the page said)
RETIRE = {
    "INCY-2026-04-08": (NEW,
                        "Incyte's 8-K dates the Zynyz NSCLC Complete Response Letter February 27, 2026. Nothing "
                        "happened on April 8, 2026, and the page cited no source. The decision now has its page at "
                        "February 27 with Incyte's filing as its source.",
                        "Incyte Form 8-K, date of report February 27, 2026",
                        "An Incyte FDA decision page dated 2026-04-08 saying Zynyz (retifanlimab-dlwr) received a "
                        "Complete Response Letter that day, with no source cited."),
    "MGNX-2026-04-08": (NEW,
                        "A second page, under MacroGenics, for the Zynyz NSCLC Complete Response Letter. Incyte is "
                        "the applicant (MacroGenics licensed retifanlimab to Incyte and is owed milestones), and "
                        "Incyte's 8-K dates the letter February 27, 2026; nothing happened on April 8. The decision "
                        "has one page, under Incyte.",
                        "Incyte Form 8-K, date of report February 27, 2026",
                        "A MacroGenics FDA decision page dated 2026-04-08 saying Zynyz (retifanlimab-dlwr) received a "
                        "Complete Response Letter that day, with no source cited."),
}


def build_page():
    io.open(EVENTS_FILE, "w", encoding="utf-8").write(json.dumps(EVENTS, indent=1, ensure_ascii=False) + "\n")
    import build_decision_page as bdp
    px = json.load(open(bdp.PX))
    for e in EVENTS:
        bdp.build(e, px)


def retire():
    import apply_1118_retire_decisions as r
    r.RETIRE = RETIRE
    r.TODAY = TODAY
    argv, sys.argv = sys.argv, [sys.argv[0]]
    try:
        r.main()
    finally:
        sys.argv = argv


def unlink_badged():
    """apply_1118's patterns take a link's text as [^<]*; these links carry a provenance badge (<span> inside the
    anchor), so a list item or a "&middot;"-separated neighbour link is matched here with any markup but another <a>."""
    import re
    site = os.path.join(HERE, "pdufa_site_src")
    a = r'<a [^>]*href="{h}"[^>]*>(?:(?!<a\b|</a>).)*</a>'
    n = 0
    for root, _, files in os.walk(site):
        for f in files:
            if not f.endswith(".html"):
                continue
            pth = os.path.join(root, f)
            rel = os.path.relpath(pth, site).replace("\\", "/")
            if rel in ("corrections/index.html", "changelog/index.html"):
                continue
            doc = io.open(pth, encoding="utf-8", errors="replace").read()
            if not any(x in doc for x in RETIRE):
                continue
            new = doc
            for slug in RETIRE:
                h = re.escape(f"/fda-decision/{slug}")
                one = a.format(h=h)
                for pat in (rf'<li[^>]*>\s*{one}\s*</li>', rf'\s*&middot;\s*{one}', rf'{one}\s*&middot;\s*'):
                    new = re.sub(pat, "", new, flags=re.S)
            if new != doc:
                io.open(pth, "w", encoding="utf-8", newline="").write(new)
                n += 1
            for slug in RETIRE:
                if f"/fda-decision/{slug}" in new:
                    print("   STILL LINKED", rel, slug)
    print(f"badged links removed from {n} file(s)")


if __name__ == "__main__":
    build_page()
    retire()
    unlink_badged()
