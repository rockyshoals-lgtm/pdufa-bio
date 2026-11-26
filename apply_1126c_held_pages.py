# -*- coding: utf-8 -*-
"""apply_1126c_held_pages.py -- retire held "outcome unverified" decision pages that were never FDA decisions, and
seven more decision pages filed under a company that is not the applicant.

David, 2026-11-26 ("Continue with moat ... You will ensure supreme accuracy"), with his standing hand-off for site fixes
("just do it, red team everything"). The 100 held pages (noindex, out of the sitemap, banner "outcome unverified": the
outcome was guessed from the share price, see relabel_price_only.py) were each checked against the company's own
release or SEC filing and an EDGAR full-text search of the 14 days around the page date, then red-teamed by a second
pass. 69 had no FDA decision on that drug within 14 days of the page date: they were trial readouts, conference data,
quarterly results, ethics-board approvals, a share sale, preclinical data. Those pages are retired here and redirect to
the ticker's hub. 31 were real FDA actions (several in the other direction to the guess) and stay held until each is
rebuilt as a sourced page; two were disputed in red-teaming and also stay.

Seven decision pages record a real FDA action under the wrong company (applicants from Drugs@FDA or the applicant's own
release). Four already have the right page, three of which double-counted the decision in the run-up study:
  IONI-2025-08-21  Dawnzera, NDA 219407, applicant Ionis (ticker IONS; IONI is I-ON Digital). -> IONS-2025-08-21
  INTE-2025-03-28  Qfitlia, NDA 219019, applicant Genzyme (Sanofi).                         -> SNY-2025-03-28
  AMRN-2025-12-02  albuterol ANDA 211600, applicant Amneal Ireland, approved 2025-12-01.     -> /ticker/AMRX
  ZLAB-2025-07-30  odronextamab CRL, applicant Regeneron.                                    -> REGN-2025-07-30
  ABEO-2025-07-11  UX111 CRL, applicant Ultragenyx.                                          -> RARE-2025-07-11
  IONS-2025-09-23  high-dose SPINRAZA CRL, applicant Biogen.                                 -> BIIB-2025-09-23
  RHHBY-2025-11-25 ELEVIDYS label change of 2025-11-14, applicant Sarepta.                   -> /ticker/SRPT
The last four are held pages; the first three were published as verified and carried the wrong company's share price.

Retired the way apply_1118_retire_decisions.py retires a page (its main): page deleted, permanent redirect, every link
removed, verification entry marked retracted, ledgers pruned, /corrections entry. Run-up study exclusions are added so
curate_runup_study.py drops the rows. RETIRE joins RETRACTED in tests/test_no_retracted_claims.py. Idempotent. Facts
only, not investment advice.

    python apply_1126c_held_pages.py [--dry-run]
"""
import io
import json
import os
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TODAY = "2026-11-26"
DAF = "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo="

# slug -> what the record shows happened instead (checked 2026-11-26, primary source in held_pages_2026_11_26.json)
EVENT = {
    "AAPG-2025-12-09": "That week the company presented ASH 2025 data and said the drug is not approved in the US.",
    "AURA-2025-03-24": "That day the company reported fourth-quarter 2024 results.",
    "CHRS-2025-01-22": "No company news for that day was found; trial data were presented at a medical meeting two days later.",
    "CNTA-2025-03-24": "That day the company reported fourth-quarter 2024 results, which said SerpinPC development had ended.",
    "GMAB-2025-06-15": "That weekend the company presented early trial data at the EHA 2025 congress.",
    "INBX-2025-01-21": "That day the company reported early trial data from a medical meeting.",
    "MRK-2025-12-17": "That day Astellas and Pfizer reported topline Phase 3 trial results.",
    "PFE-2025-12-17": "That day Astellas and Pfizer reported topline Phase 3 trial results.",
    "ALPMY-2025-12-17": "That day Astellas and Pfizer reported topline Phase 3 trial results.",
    "TARA-2025-11-19": "That day the company reported interim Phase 2 trial results.",
    "ALXO-2025-04-25": "That week final Phase 1 results were presented at a medical meeting.",
    "BMY-2025-05-23": "Iberdomide was still in trials, and no company news for that day was found.",
    "CING-2025-05-14": "No company news about CTx-1301 for that day was found.",
    "COCP-2025-12-18": "That day the company reported a university ethics board approval for an early trial.",
    "GLSI-2025-03-17": "That day the company reported early safety data from its Phase 3 trial.",
    "IBRX-2025-11-05": "That day the company filed third-quarter results.",
    "JSPR-2025-06-16": "That day the company filed early trial data presented at a medical meeting.",
    "MRKR-2025-08-26": "That day the company reported Phase 1 trial data.",
    "ONCY-2025-10-28": "That day the company reported trial data in a different cancer.",
    "PRTC-2025-12-05": "That day a PureTech company reported early Phase 1b trial data.",
    "ALXO-2025-12-08": "That week data from an investigator-led trial were presented at ASH 2025.",
    "AVBP-2025-06-23": "That day the company reported interim Phase 1b trial data.",
    "CGEM-2025-10-13": "The day before, the companies released early trial data ahead of a medical meeting.",
    "CMND-2025-07-03": "That day the company reported a hospital ethics board approval to enroll patients in its trial.",
    "GLSI-2026-01-22": "That day the company said the FDA cleared a manufacturing lot for use in its ongoing trial, which is not a decision on an application.",
    "INCY-2025-06-15": "That day the company presented first clinical data at the EHA 2025 congress.",
    "LYEL-2025-12-08": "That week the company presented trial data at ASH 2025.",
    "PBM-2025-12-19": "That day the company reported an ethics committee approval for a Phase 2b trial.",
    "REGN-2025-05-23": "That week the company released early combination-trial data.",
    "APTO-2025-02-20": "That day the company reported a trial safety committee's approval to raise the dose.",
    "CLDX-2025-11-06": "No company news for that day was found; four days later its quarterly results reported Phase 2 trial data.",
    "CUE-2025-07-16": "That day the company reported one patient's response in an early trial.",
    "GMAB-2025-06-02": "That day the company reported early trial data from a medical meeting.",
    "INTS-2025-06-30": "That day the company reported animal study data.",
    "KZIA-2025-11-18": "That day the company reported one patient's case and a business update.",
    "PLRX-2025-12-04": "The drug was in a Phase 1 trial, and no company news for that day was found.",
    "TARA-2025-04-26": "That day the company reported interim Phase 2 trial results at a medical meeting.",
    "BCTX-2025-05-23": "That day the company announced its abstracts for a medical meeting.",
    "CLLS-2025-02-14": "The program was in a Phase 1 trial, and no company news for that day was found.",
    "GLPG-2025-12-07": "That week the company presented Phase 2 trial data at ASH 2025.",
    "IBRX-2025-08-13": "That day the company reported early responses in a Phase 1 trial.",
    "LTRN-2025-06-16": "That day the company reported one patient's case from a Phase 2 trial.",
    "ONC-2025-12-08": "That week the company presented trial data at ASH 2025.",
    "PRTA-2025-08-27": "That day the company reported Phase 1 results.",
    "ABBV-2025-06-30": "That day the FDA accepted a device application for review, which is not a decision on it.",
    "AUTL-2025-12-08": "That week the company presented early trial data at ASH 2025.",
    "CASI-2025-12-07": "That day the company presented Phase 1 trial data at ASH 2025.",
    "CLLS-2025-12-07": "That day an ASH 2025 poster described a Phase 1 trial still under way.",
    "EQ-2025-04-24": "That day the company reported FDA meeting feedback that declined a Breakthrough Therapy designation, which is not a decision on an application.",
    "JANX-2025-12-01": "That day the company reported Phase 1 trial data.",
    "LYEL-2025-06-17": "That day the company announced trial data for a medical meeting.",
    "NRIX-2025-06-12": "That day the company reported trial data at the EHA 2025 congress.",
    "PHIO-2025-03-10": "The drug was in a Phase 1b trial, and no company news for that day was found.",
    "ANIK-2025-07-30": "That day the company reported that its pivotal trial missed its main goals.",
    "BMY-2025-06-12": "That day the company reported trial data at the EHA 2025 congress.",
    "CLDI-2025-04-28": "That day the company reported animal study data from a medical meeting.",
    "CRSP-2025-12-22": "That day the company gave a clinical data update.",
    "IMMX-2025-06-03": "That day the company filed a prospectus to sell shares.",
    "JNJ-2025-04-24": "That week the company presented trial data at a urology meeting.",
    "NRIX-2025-12-08": "That day the company reported trial data at ASH 2025.",
    "PHIO-2025-05-07": "That day the company reported Phase 1b trial results.",
    "ADCT-2025-06-12": "That day the company reported Phase 1b combination trial data.",
    "CGON-2025-03-24": "That day updated trial data were presented at a European urology congress.",
    "CMPX-2025-04-01": "That day the company reported topline results from a randomized trial.",
    "GLPG-2025-06-19": "That week the company reported new trial data.",
    "IMMX-2025-12-07": "That day the company reported Phase 2 trial data at ASH 2025.",
    "JNJ-2025-06-13": "That day the company reported first Phase 1b trial data.",
    "OGEN-2025-05-13": "That day the company reported an Australian ethics committee approval to start a trial.",
    "RPRX-2025-11-07": "Cytokinetics' release of November 5, 2025 said the application was still under FDA review.",
}
DRUG_NAME = {"MRK-2025-12-17": "Padcev plus Keytruda", "PFE-2025-12-17": "Padcev plus Keytruda",
             "ALPMY-2025-12-17": "Padcev plus Keytruda", "ABBV-2025-06-30": "SKINVIVE by JUVÉDERM",
             "NRIX-2025-12-08": "bexobrutideg (NX-5948)", "CRSP-2025-12-22": "zugocabtagene geleucel (zugo-cel)",
             "JNJ-2025-04-24": "INLEXZO (TAR-200)", "CMPX-2025-04-01": "tovecimig (CTX-009)",
             "IBRX-2025-11-05": "t-haNK with ANKTIVA and rituximab", "APTO-2025-02-20": "tuspetinib",
             "ONCY-2025-10-28": "pelareorep", "INBX-2025-01-21": "ozekibart (INBRX-109)",
             "BMY-2025-05-23": "iberdomide", "BMY-2025-06-12": "iberdomide", "CING-2025-05-14": "CTx-1301",
             "ALXO-2025-04-25": "evorpacept (ALX148)", "ALXO-2025-12-08": "evorpacept (ALX148)",
             "GMAB-2025-06-15": "epcoritamab", "AVBP-2025-06-23": "firmonertinib",
             "CHRS-2025-01-22": "casdozokitug", "CLLS-2025-02-14": "ALLO-501A",
             "IBRX-2025-08-13": "CD19 CAR-NK cell therapy", "ADCT-2025-06-12": "ZYNLONTA",
             "AURA-2025-03-24": "belzupacap sarotalocan (AU-011)", "REGN-2025-05-23": "linvoseltamab",
             "IMMX-2025-06-03": "NXC-201", "IMMX-2025-12-07": "NXC-201", "RPRX-2025-11-07": "aficamten"}


def _long(d):
    y, m, dd = map(int, d.split("-"))
    return date(y, m, dd).strftime("%B %-d, %Y")


def _held():
    rows = json.load(io.open(os.path.join(HERE, "held_pages_2026_11_26.json"), encoding="utf-8"))
    out = {}
    for s, r in rows.items():
        tk, d = s.split("-", 1)
        drug = DRUG_NAME.get(s, r["drug"])
        guess = "approval" if r["claimed"] == "approval" else "Complete Response Letter"
        why = f"There was no FDA decision on {drug} within 14 days of {_long(d)}. {EVENT[s]}"
        was = (f"A held decision page for {tk} dated {d} that guessed an FDA {guess} from the share price "
               f"(marked outcome unverified).")
        out[s] = (f"/ticker/{tk}", why, r["src"], was)
    return out


def _wrong(action, appl, applicant, wrong, where):
    return f"The FDA's {action} went to {applicant}, the applicant{appl}, not {wrong}. {where}"


MISFILED = {
    "IONI-2025-08-21": ("/fda-decision/IONS-2025-08-21",
                        _wrong("approval of Dawnzera (donidalorsen) on August 21, 2025", " under NDA 219407",
                               "Ionis Pharmaceuticals (IONS)", "I-ON Digital (IONI)",
                               "The decision already has its page under IONS."),
                        "Drugs@FDA, NDA 219407 (applicant Ionis Pharms Inc, approved 2025-08-21) " + DAF + "219407",
                        "A decision page for IONI dated 2025-08-21 recording Ionis's Dawnzera approval under the ticker of I-ON Digital."),
    "INTE-2025-03-28": ("/fda-decision/SNY-2025-03-28",
                        _wrong("approval of Qfitlia (fitusiran) on March 28, 2025", " under NDA 219019",
                               "Genzyme, a Sanofi company", "INTE",
                               "The decision already has its page under Sanofi."),
                        "Drugs@FDA, NDA 219019 (applicant Genzyme Corp, approved 2025-03-28) " + DAF + "219019",
                        "A decision page for INTE dated 2025-03-28 recording Sanofi's Qfitlia approval under INTE."),
    "AMRN-2025-12-02": ("/ticker/AMRX",
                        _wrong("approval of a generic albuterol sulfate inhaler on December 1, 2025", " under ANDA 211600",
                               "Amneal Ireland", "Amarin",
                               "Amarin is not a party to that application."),
                        "Drugs@FDA, ANDA 211600 (applicant Amneal Ireland Ltd, approved 2025-12-01) " + DAF + "211600",
                        "A decision page for AMRN dated 2025-12-02 recording Amneal's generic albuterol approval as an Amarin approval."),
    "ZLAB-2025-07-30": ("/fda-decision/REGN-2025-07-30",
                        _wrong("Complete Response Letter for odronextamab on July 30, 2025", "", "Regeneron", "Zai Lab",
                               "The decision already has its page under Regeneron."),
                        "Regeneron 8-K exhibit 99.1, second-quarter 2025 results "
                        "https://www.sec.gov/Archives/edgar/data/872589/000087258925000017/exhibit991q22025.htm",
                        "A held decision page for ZLAB dated 2025-07-30 that guessed an FDA Complete Response Letter from the share price (marked outcome unverified)."),
    "ABEO-2025-07-11": ("/fda-decision/RARE-2025-07-11",
                        _wrong("Complete Response Letter for UX111 (formerly ABO-102), announced July 11, 2025,", "", "Ultragenyx",
                               "Abeona", "The decision already has its page under Ultragenyx."),
                        "Ultragenyx 8-K of July 11, 2025 "
                        "https://www.sec.gov/Archives/edgar/data/1515673/000095017025095334/rare-20250711.htm",
                        "A held decision page for ABEO dated 2025-07-11 that guessed an FDA Complete Response Letter from the share price (marked outcome unverified)."),
    "IONS-2025-09-23": ("/fda-decision/BIIB-2025-09-23",
                        _wrong("Complete Response Letter for a high-dose regimen of SPINRAZA (nusinersen), announced September 23, 2025,",
                               "", "Biogen", "Ionis",
                               "The decision already has its page under Biogen."),
                        "Biogen release, regulatory update on high-dose nusinersen "
                        "https://investors.biogen.com/news-releases/news-release-details/biogen-provides-regulatory-update-high-dose-regimen-nusinersen",
                        "A held decision page for IONS dated 2025-09-23 that guessed an FDA Complete Response Letter from the share price (marked outcome unverified)."),
    "RHHBY-2025-11-25": ("/ticker/SRPT",
                         "There was no FDA approval for Roche's ELEVIDYS program within 14 days of November 25, 2025. "
                         "The FDA action nearest that date was a label change for ELEVIDYS approved on November 14, 2025, "
                         "whose US license holder is Sarepta, not Roche.",
                         "FDA, ELEVIDYS supplement approval of November 14, 2025 https://www.fda.gov/media/189632/download",
                         "A held decision page for RHHBY dated 2025-11-25 that guessed an FDA approval from the share price (marked outcome unverified)."),
}

RETIRE = {}
RETIRE.update(_held())
RETIRE.update(MISFILED)


def main():
    dry = "--dry-run" in sys.argv
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
        kind = "wrong company" if s in MISFILED else "no FDA decision"
        e = {"reason": f"{kind}: " + why, "document": src,
             "finding": ("the tracked list filed the action under a ticker that is not the applicant's" if s in MISFILED
                         else "the page's outcome was guessed from the share price; no FDA decision near that date"),
             "checked": TODAY}
        if pages.get(s) != e:
            pages[s] = e
            n += 1
    if n:
        io.open(p, "w", encoding="utf-8").write(json.dumps(ex, indent=1, ensure_ascii=False))
    print(f"runup_study_exclusions.json: {n} entr(ies) added")


if __name__ == "__main__":
    main()
