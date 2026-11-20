# -*- coding: utf-8 -*-
"""apply_1120b_untracked_approvals.py -- three FDA approvals on drugs we have pages for, which the site never recorded.

Found 2026-11-20 by checking openFDA Drugs@FDA (AP submissions, ORIG or EFFICACY class, Nov 1-20, read in Chrome
before 08:45 UTC = 03:45 ET; RULE 1) against /fda-decision. None had a PDUFA row, so no watcher armed, and each drug page
still showed an older decision as the latest:

1. JNJ RYBREVANT FASPRO, HNSCC (issue 135 item). FDA letter BLA 761433/S-002 "ACCELERATED APPROVAL", read in full:
   single agent for adults with recurrent or metastatic head and neck squamous cell carcinoma whose disease has progressed
   on or after platinum-based chemotherapy and an anti-PD-(L)1 antibody; not indicated for HPV-associated oropharyngeal
   SCC. sBLA received May 20, 2026. Signed electronically 11/05/2026 04:17 PM. J&J release (PR Newswire, 9:03 PM ET
   Nov 5): 42 percent overall response rate (95% CI 32-52 percent). /drug/rybrevant-faspro said "most recent FDA
   decision: Dec 18, 2025".
2. AZN IMFINZI, muscle-invasive bladder cancer. Drugs@FDA BLA 761069 S-059 (efficacy) AP 2026-11-13. AstraZeneca
   release (Business Wire, 6:39 PM ET Nov 13): Imfinzi with enfortumab vedotin-ejfv before radical cystectomy, then
   Imfinzi alone after it, for adults with MIBC ineligible for or refusing cisplatin-based chemotherapy. /drug/imfinzi
   said "most recent: May 28, 2026".
3. NVS COSENTYX, polymyalgia rheumatica. FDA letter BLA 125504/S-101 (with 761349/S-016), read in full: new indication
   for adults with PMR; sBLA received January 16, 2026; signed electronically 11/16/2026 05:45 PM. Novartis release
   (dateline Basel, November 17; GlobeNewswire 9:43 PM ET Nov 16): Cosentyx 150 mg for adults with PMR who have had an
   inadequate response to corticosteroids or cannot tolerate a corticosteroid taper. openFDA lists the status date as
   2026-11-17; the letter's own signature says Nov 16, and the announcement came that evening, so Nov 16 is used.
   /drug/cosentyx said "most recent: Mar 13, 2026".

We hold no disclosed goal date for any of these, so no margin is claimed. Not tracked, not added (no primary source
read): KLYGEFA (gefurulimab, AZN/Alexion) BLA 761488 AP 11-13; ZURZUVAE efficacy supplement 11-13.
Facts only; not investment advice.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
A = 'rel="noopener" style="color:#e3ba5e"'
JNJ_L = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/761433Orig1s002ltr.pdf"
JNJ_R = ("https://www.prnewswire.com/news-releases/johnson--johnson-announces-us-fda-approval-of-rybrevant-faspro-"
         "amivantamab-and-hyaluronidase-lpuj-as-first-and-only-dual-targeted-therapy-for-advanced-head-and-neck-cancer-"
         "302931583.html")
AZN_D = "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo=761069"
AZN_R = ("https://www.businesswire.com/news/home/20261113582858/en/Perioperative-IMFINZI%C2%AE-durvalumab-approved-in-"
         "the-US-in-novel-regimen-with-neoadjuvant-enfortumab-vedotin-ejfv-for-patients-with-muscle-invasive-bladder-cancer/")
NVS_L = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/125504Orig1s101,761349Orig1s016ltr.pdf"
NVS_R = ("https://www.globenewswire.com/news-release/2026/11/17/3404251/0/en/novartis-cosentyx-becomes-first-and-only-"
         "fda-approved-anti-il-17-biologic-for-people-with-polymyalgia-rheumatica-pmr.html")

# closes, FMP historical-price-eod-light, read 2026-11-20 before 08:45 UTC; Eastern trading days; Oct 16 matches the cache.
DAYS = ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28",
        "2026-10-29", "2026-10-30", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-09",
        "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13", "2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19"]
CLOSES = {
    "JNJ": [253.79, 259.36, 257.78, 267.61, 263.81, 266.3, 268.73, 271.04, 275.2, 273.2, 270.56, 266.17, 276.32, 272.32,
            276.22, 282.11, 280.78, 280.41, 283.52, 285.75, 282.55, 278.7, 272.7, 267.14],
    "AZN": [163.95, 168.82, 168.45, 172.57, 171.49, 172.06, 170.08, 169.51, 174.4, 186.65, 186.58, 183.88, 189.01, 186.85,
            186.43, 189.39, 186.76, 185.48, 184.38, 184.45, 184.02, 182.27, 178.76, 175.41],
    "NVS": [150.2, 153.64, 153.93, 156.27, 151.12, 153.81, 156.86, 156.08, 161.1, 160.79, 161.52, 159.26, 164.98, 161.93,
            162.55, 163.69, 163.26, 160.32, 160.25, 160.5, 160.2, 159.13, 155.21, 151.22],
}

SPECS = [
    {
        "ticker": "JNJ", "date": "2026-11-05", "fda_action_date": "2026-11-05", "outcome": "Approved",
        "drug": "RYBREVANT FASPRO (amivantamab and hyaluronidase-lpuj)",
        "indication": ("Adults with recurrent or metastatic head and neck squamous cell carcinoma that progressed on or "
                       "after platinum-based chemotherapy and an anti-PD-(L)1 antibody (accelerated approval)"),
        "company": "Johnson & Johnson", "cap": "Large",
        "headline": ("The FDA granted accelerated approval to RYBREVANT FASPRO on November 5, 2026 as a single agent for "
                     "adults with recurrent or metastatic head and neck squamous cell carcinoma after platinum-based "
                     "chemotherapy and an anti-PD-(L)1 antibody."),
        "pdufa_note": (f'The FDA\'s accelerated approval letter for BLA 761433 supplement 2, signed November 5, 2026 '
                       f'(<a href="{JNJ_L}" {A}>FDA letter</a>), covers RYBREVANT FASPRO as a single agent for adults '
                       f'with recurrent or metastatic head and neck squamous cell carcinoma (HNSCC) whose disease has '
                       f'progressed on or after platinum-based chemotherapy and an anti-PD-(L)1 antibody. The letter '
                       f'states that it is not indicated for HPV-associated oropharyngeal squamous cell carcinoma, and '
                       f'that the supplemental application was received on May 20, 2026. Johnson &amp; Johnson announced '
                       f'the approval the same evening and reported a 42 percent overall response rate (95 percent '
                       f'confidence interval, 32 to 52 percent) (<a href="{JNJ_R}" {A}>Johnson &amp; Johnson, '
                       f'November 5, 2026</a>). We hold no publicly disclosed PDUFA goal date for this supplement, so '
                       f'no early or late margin is given.'),
        "source": JNJ_L, "source_label": "FDA approval letter, BLA 761433 S-002",
        "h1": ('RYBREVANT FASPRO <span class="g">FDA approval for head and neck cancer</span>: Nov 5, 2026'),
    },
    {
        "ticker": "AZN", "date": "2026-11-13", "fda_action_date": "2026-11-13", "outcome": "Approved",
        "drug": "Imfinzi (durvalumab)",
        "indication": ("Adults with muscle-invasive bladder cancer ineligible for or refusing cisplatin-based "
                       "chemotherapy, with enfortumab vedotin-ejfv before cystectomy, then alone after it"),
        "company": "AstraZeneca", "cap": "Large",
        "headline": ("Imfinzi (durvalumab) was approved in the US on November 13, 2026 with neoadjuvant enfortumab "
                     "vedotin-ejfv, then as adjuvant monotherapy after radical cystectomy, for cisplatin-ineligible "
                     "muscle-invasive bladder cancer."),
        "pdufa_note": (f'Drugs@FDA records BLA 761069 supplement 59 (efficacy) for Imfinzi as approved on November 13, '
                       f'2026 (<a href="{AZN_D}" {A}>Drugs@FDA</a>). AstraZeneca announced that evening that Imfinzi in '
                       f'combination with enfortumab vedotin-ejfv as neoadjuvant treatment, followed by Imfinzi '
                       f'monotherapy as adjuvant treatment after radical cystectomy, was approved for adults with '
                       f'muscle-invasive bladder cancer who are ineligible for or have refused cisplatin-based '
                       f'chemotherapy (<a href="{AZN_R}" {A}>AstraZeneca, November 13, 2026</a>). We hold no publicly '
                       f'disclosed PDUFA goal date for this supplement, so no early or late margin is given.'),
        "source": AZN_D, "source_label": "Drugs@FDA, BLA 761069 S-059",
        "h1": ('Imfinzi (durvalumab) <span class="g">FDA approval for muscle-invasive bladder cancer</span>: '
               'Nov 13, 2026'),
    },
    {
        "ticker": "NVS", "date": "2026-11-16", "fda_action_date": "2026-11-16", "outcome": "Approved",
        "drug": "COSENTYX (secukinumab)",
        "indication": ("Adults with polymyalgia rheumatica with an inadequate response to corticosteroids or who "
                       "cannot tolerate a corticosteroid taper"),
        "company": "Novartis", "cap": "Large",
        "headline": ("The FDA approved COSENTYX (secukinumab) on November 16, 2026 for adults with polymyalgia "
                     "rheumatica, a new indication."),
        "pdufa_note": (f'The FDA\'s supplement approval letter for BLA 125504 supplement 101, signed November 16, 2026 '
                       f'(<a href="{NVS_L}" {A}>FDA letter</a>), adds a new indication for the treatment of adult '
                       f'patients with polymyalgia rheumatica (PMR); the letter states that the supplemental application '
                       f'was received on January 16, 2026. openFDA\'s Drugs@FDA data lists the approval under November 17; the date '
                       f'here is the letter\'s own signature date. Novartis announced the approval that evening (US '
                       f'Eastern time; its release is datelined Basel, November 17) for Cosentyx 150 mg in adults with '
                       f'PMR who have had an inadequate response to corticosteroids or who cannot tolerate a '
                       f'corticosteroid taper (<a href="{NVS_R}" {A}>Novartis, November 17, 2026</a>). We hold no publicly '
                       f'disclosed PDUFA goal date for this supplement, so no early or late margin is given.'),
        "source": NVS_L, "source_label": "FDA approval letter, BLA 125504 S-101",
        "h1": ('COSENTYX (secukinumab) <span class="g">FDA approval for polymyalgia rheumatica</span>: Nov 16, 2026'),
    },
]
LEDGER = [("rybrevant-faspro", "2026-11-05", "RYBREVANT FASPRO", JNJ_L),
          ("imfinzi", "2026-11-13", "Imfinzi", AZN_D),
          ("cosentyx", "2026-11-16", "Cosentyx", NVS_L)]
FAQ = {
    "JNJ-2026-11-05": [
        ["Was RYBREVANT FASPRO approved for head and neck cancer?",
         "Yes. The FDA granted accelerated approval on November 5, 2026, per its own approval letter, for adults with "
         "recurrent or metastatic head and neck squamous cell carcinoma whose disease progressed on or after "
         "platinum-based chemotherapy and an anti-PD-(L)1 antibody. It is not indicated for HPV-associated "
         "oropharyngeal squamous cell carcinoma."]],
    "AZN-2026-11-13": [
        ["What did the FDA approve for Imfinzi on November 13, 2026?",
         "Per Drugs@FDA and AstraZeneca, Imfinzi (durvalumab) with enfortumab vedotin-ejfv before radical cystectomy, "
         "followed by Imfinzi alone after surgery, for adults with muscle-invasive bladder cancer who are ineligible for "
         "or have refused cisplatin-based chemotherapy."]],
    "NVS-2026-11-16": [
        ["Is Cosentyx approved for polymyalgia rheumatica?",
         "Yes. The FDA's approval letter, signed November 16, 2026, adds polymyalgia rheumatica in adults as a new "
         "indication for Cosentyx (secukinumab). Novartis says the approval covers 150 mg for patients who had an "
         "inadequate response to corticosteroids or cannot tolerate a corticosteroid taper."]],
}


def jload(p, default=None):
    p = os.path.join(HERE, p)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else default


def jsave(p, d):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


c = jload("_drug_approvals_confirmed.json")
for slug, day, brand, src in LEDGER:
    if not any(a.get("slug") == slug and a.get("date") == day for a in c["approvals"]):
        c["approvals"].append({"slug": slug, "date": day, "brand": brand, "source": src})
jsave("_drug_approvals_confirmed.json", c)

faq = jload("_decision_extra_faq.json", {})
faq.update(FAQ)
jsave("_decision_extra_faq.json", faq)

jsave("decision_pages_2026_11_20_untracked.json", SPECS)

# FDA action days, from the FDA's own record, for the fact-first lede (build_decision_lede.py reads this file; entries
# with a date are never re-checked by sync_archive_fda_dates.py). Cosentyx: the letter's signature (Nov 16), not the
# openFDA status date (Nov 17), which sync_archive_fda_dates would reject as after the announcement anyway.
ARCH = {
    "JNJ-2026-11-05": {"checked": "2026-11-20", "class": "EFFICACY", "date": "2026-11-05", "letter": JNJ_L,
                       "name": "RYBREVANT FASPRO (amivantamab and hyaluronidase-lpuj)", "record": "BLA 761433 SUPPL-2",
                       "source_url": JNJ_L, "terms": ["RYBREVANT FASPRO", "amivantamab"]},
    "AZN-2026-11-13": {"checked": "2026-11-20", "class": "EFFICACY", "date": "2026-11-13", "letter": None,
                       "name": "Imfinzi (durvalumab)", "record": "BLA 761069 SUPPL-59", "source_url": AZN_D,
                       "terms": ["Imfinzi", "durvalumab"]},
    "NVS-2026-11-16": {"checked": "2026-11-20", "class": "EFFICACY", "date": "2026-11-16", "letter": NVS_L,
                       "name": "COSENTYX (secukinumab)", "record": "BLA 125504 SUPPL-101", "source_url": NVS_L,
                       "terms": ["COSENTYX", "secukinumab"]},
}
fa = jload("_fda_action_archive.json", {})
for k, v in ARCH.items():
    if not (fa.get(k) or {}).get("date"):
        fa[k] = v
jsave("_fda_action_archive.json", fa)

PX = os.path.join(HERE, "_chart_pxcache.json")
px = json.load(open(PX))
for tk, closes in CLOSES.items():
    assert len(closes) == len(DAYS), tk
    for dd, cl in zip(DAYS, closes):
        px.setdefault(tk, {}).setdefault(dd, cl)
json.dump(px, open(PX, "w"))
import build_decision_page as bdp  # noqa: E402
for e in SPECS:
    bdp.build(e, px)
    print(f"  built /fda-decision/{e['ticker']}-{e['date']}")
