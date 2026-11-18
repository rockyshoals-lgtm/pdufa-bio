# -*- coding: utf-8 -*-
"""apply_1118b_decision_sources.py -- 27 decision pages that record a real FDA action, re-sourced and re-dated.

2026-11-18 (David, 2026-11-17 Eastern: "Red team the readout and pdufa dates again, let's build our moat here too
as the most accurate"). These pages were labelled "verified" by verify_decisions.py (2026-08-12) from an SEC filing
that merely contained "approval of", "FDA approval" or "complete response letter" (an underwriting agreement, an
earnings release weeks later, a slide deck). Each was re-checked on 2026-11-18 against a primary source: the FDA's
approval letter or Complete Response Letter file, an FDA page, or the company's own release or 8-K. The FDA action
is real on all 27; what was wrong is the cited source and, on most, the date in key facts:

  * the source row now links the primary source, with the sentence it was checked against kept in
    _decision_verification.json (evidence.quote, quote_checked);
  * key facts give the FDA's own action day ("FDA decision date") and the public day ("Announced") when they
    differ; where no public FDA record states the day, key facts say so, as label_announcement_only_dates.py does;
  * an FDA record of the day goes into _fda_action_archive.json, so inject_fda_action_record.py and
    build_decision_faq.py state it on the page and in its FAQ;
  * the drug row names the drug the FDA acted on (several old pages had none, or a truncated one);
  * LGND-2026-04-13: FILSPARI is Travere's application; Ligand holds a royalty, so the row says "Applicant".

Three pages dated to a day nothing happened (SNY-2025-06-02, REGN-2025-06-02, SNY-2025-12-28) were rebuilt on the
announcement day and retired by apply_1118_retire_decisions.py; 17 pages that record no FDA action were retired there
too. Times read from the releases are Eastern (RULE 1). Idempotent. Facts only, not investment advice.

    python apply_1118b_decision_sources.py [--dry-run]
"""
import argparse
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
TODAY = "2026-11-18"
NOT_ON_RECORD = "not found in a public FDA record"

L = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/"
C = "https://download.open.fda.gov/crl/"

# slug: fda = FDA action day (None: no public FDA record states it); ann = the public day, when key facts should
# show it; rec = the FDA record for _fda_action_archive.json (only when url is that record); label = link text.
FIX = {
    "ABBV-2026-02-20": dict(oc="Approved", fda="2026-02-19", ann="2026-02-20", rec="NDA 208573 S-031",
                            url=L + "2026/208573Orig1s031ltr.pdf",
                            label="FDA approval letter, NDA 208573 S-031, February 19, 2026",
                            quote="provides for the use of Venclexta in combination with acalabrutinib",
                            drug="VENCLEXTA (venetoclax) with acalabrutinib"),
    "AZN-2026-02-20": dict(oc="Approved", fda=None, ann="2026-02-20",
                           url="https://www.astrazeneca.com/media-centre/press-releases/2026/fixed-duration-calquence-combo-approved-in-us.html",
                           label="AstraZeneca release, February 20, 2026",
                           quote="AstraZeneca's Calquence (acalabrutinib) in combination with venetoclax has been approved in the US",
                           drug="CALQUENCE (acalabrutinib) with venetoclax"),
    "TAK-2025-06-30": dict(oc="Approved", fda=None, ann="2025-06-30",
                           url="https://www.takeda.com/newsroom/newsreleases/2025/gammagard-immunoglobulin/",
                           label="Takeda release, June 30, 2025",
                           quote="today announced that the U.S. Food and Drug Administration (FDA) has approved GAMMAGARD LIQUID ERC",
                           drug="GAMMAGARD LIQUID ERC (immune globulin infusion, human)"),
    "AMPH-2026-02-24": dict(oc="Approved", fda=None, ann="2026-02-24",
                            url="https://www.biospace.com/press-releases/amphastar-announces-fda-approval-for-ipratropium-bromide-hfa",
                            label="Amphastar release, February 24, 2026",
                            quote="the U.S. Food and Drug Administration (\"FDA\") has approved the Company's Abbreviated New Drug Application (\"ANDA\")",
                            drug="Ipratropium Bromide HFA Inhalation Aerosol"),
    "BIIB-2026-03-30": dict(oc="Approved", fda="2026-03-27", ann="2026-03-30", rec="NDA 209531 S-016",
                            url=L + "2026/209531Orig1s016ltr.pdf",
                            label="FDA approval letter, NDA 209531 S-016, March 27, 2026",
                            quote="This Prior Approval sNDA provides for revisions throughout the Prescribing Information (PI) regarding a completed clinical study [Study 4 (NCT04089566)], which provides an additional higher dosing regimen.",
                            drug="SPINRAZA (nusinersen)"),
    "LGND-2026-04-13": dict(oc="Approved", fda="2026-04-13", ann=None,
                            url="https://www.businesswire.com/news/home/20260413839195/en/",
                            label="Travere Therapeutics release, April 13, 2026",
                            quote="today announced that the U.S. Food and Drug Administration (FDA) has approved FILSPARI® (sparsentan) to reduce proteinuria",
                            drug="FILSPARI (sparsentan)",
                            applicant="Travere Therapeutics (Ligand Pharmaceuticals holds a royalty on FILSPARI sales)"),
    "MNKD-2026-05-29": dict(oc="Approved", fda="2026-05-29", ann=None,
                            url="https://www.sec.gov/Archives/edgar/data/0000899460/000119312526252544/mnkd-20260529.htm",
                            label="MannKind 8-K, May 29, 2026",
                            quote="On May 29, 2026, we announced that the U.S. Food and Drug Administration (FDA) approved Afrezza®(insulin human) Inhalation Powder for use in children and adolescents aged 6 and older.",
                            drug="AFREZZA (insulin human)"),
    "NVO-2026-03-26": dict(oc="Approved", fda="2026-03-26", ann="2026-03-26, after the close",
                           url="https://www.fda.gov/drugs/novel-drug-approvals-fda/novel-drug-approvals-2026",
                           label="FDA, Novel Drug Approvals for 2026 (Awiqli, March 26, 2026)",
                           quote="Awiqli | insulin icodec-abae | 3/26/2026",
                           drug="AWIQLI (insulin icodec-abae)"),
    "SNY-2026-04-22": dict(oc="Approved", fda="2026-04-22", ann=None, rec="BLA 761055 S-074",
                           url=L + "2026/761055Orig1s074ltr.pdf",
                           label="FDA approval letter, BLA 761055 S-074, April 22, 2026",
                           quote="This Prior Approval sBLA provides for expanding the indication for chronic spontaneous urticaria (CSU) to include pediatric patients aged 2 years to less than 12 years.",
                           drug="DUPIXENT (dupilumab)"),
    "REGN-2026-04-22": dict(oc="Approved", fda="2026-04-22", ann=None, rec="BLA 761055 S-074",
                            url=L + "2026/761055Orig1s074ltr.pdf",
                            label="FDA approval letter, BLA 761055 S-074, April 22, 2026",
                            quote="This Prior Approval sBLA provides for expanding the indication for chronic spontaneous urticaria (CSU) to include pediatric patients aged 2 years to less than 12 years.",
                            drug="DUPIXENT (dupilumab)"),
    "NVO-2025-01-28": dict(oc="Approved", fda="2025-01-28", ann=None, rec="NDA 209637 S-025",
                           url=L + "2025/209637Orig1s025ltr.pdf",
                           label="FDA approval letter, NDA 209637 S-025, January 28, 2025",
                           quote="provides for a new indication to reduce the risk of sustained estimated glomerular filtration rate (eGFR) decline",
                           drug="OZEMPIC (semaglutide)"),
    "PGEN-2025-08-15": dict(oc="Approved", fda="2025-08-14", ann="2025-08-15", rec="FDA announcement",
                            url="https://www.fda.gov/news-events/press-announcements/fda-approves-first-immunotherapy-recurrent-respiratory-papillomatosis",
                            label="FDA announcement, August 14, 2025",
                            quote="Today, the U.S. Food and Drug Administration approved Papzimeos (zopapogene imadenovec-drba),",
                            drug="PAPZIMEOS (zopapogene imadenovec-drba)"),
    "AZN-2026-04-27": dict(oc="Approved", fda="2026-04-24", ann="2026-04-27", rec="BLA 761451",
                           url=L + "2026/761451Orig1s000ltr.pdf",
                           label="FDA approval letter, BLA 761451, April 24, 2026",
                           quote="We have approved your BLA for Saphnelo (anifrolumab-fnia) accessorized pre-filled syringe and autoinjector",
                           drug="SAPHNELO (anifrolumab-fnia)"),
    "AZN-2026-05-15": dict(oc="Approved", fda=None, ann="2026-05-15",
                           url="https://www.astrazeneca.com/media-centre/press-releases/2026/enhertu-approved-in-two-her2-early-bc-settings.html",
                           label="AstraZeneca release, May 15, 2026",
                           quote="Enhertu approved in the US for two new indications for patients with HER2-positive early breast cancer",
                           drug="ENHERTU (fam-trastuzumab deruxtecan-nxki)"),
    "AZN-2026-05-18": dict(oc="Approved", fda="2026-05-15", ann="2026-05-18", rec="NDA 219878",
                           url=L + "2026/219878Orig1s000ltr.pdf",
                           label="FDA approval letter, NDA 219878, May 15, 2026",
                           quote="It is approved, effective on the date of this letter, for use as recommended in the enclosed agreed-upon labeling.",
                           drug="BAXFENDY (baxdrostat)"),
    "GSK-2026-03-13": dict(oc="Approved", fda="2026-03-12", ann="2026-03-13", rec="FDA product page",
                           url="https://www.fda.gov/vaccines-blood-biologics/arexvy",
                           label="FDA, Arexvy product page (approval of March 12, 2026)",
                           quote="March 12, 2026 Approval Letter - AREXVY",
                           drug="AREXVY (RSV vaccine, adjuvanted)",
                           company="GSK plc"),
    "HRMY-2026-02-17": dict(oc="Approved", fda="2026-02-13", ann="2026-02-17", rec="NDA 211150 S-006",
                            url=L + "2026/211150Orig1s006ltr.pdf",
                            label="FDA approval letter, NDA 211150 S-006, February 13, 2026",
                            quote="provides for the new indication of treatment of cataplexy in patients 6 years of age and older with narcolepsy.",
                            drug="WAKIX (pitolisant)"),
    "MRK-2026-04-21": dict(oc="Approved", fda="2026-04-20", ann="2026-04-21", rec="NDA 216964",
                           url=L + "2026/216964Orig1s000ltr.pdf",
                           label="FDA approval letter, NDA 216964, April 20, 2026",
                           quote="It is approved, effective on the date of this letter, for use as recommended in the enclosed agreed-upon labeling.",
                           drug="IDVYNSO (doravirine and islatravir)"),
    "REGN-2026-04-23": dict(oc="Approved", fda=None, ann="2026-04-23",
                            url="https://investor.regeneron.com/news-releases/news-release-details/otarmenitm-lunsotogene-parvec-cwha-approved-fda-first-and-only",
                            label="Regeneron release, April 23, 2026",
                            quote="today announced the U.S. Food and Drug Administration (FDA) has granted accelerated approval for Otarmeni™ (lunsotogene parvec-cwha)",
                            drug="OTARMENI (lunsotogene parvec-cwha)"),
    "NVAX-2025-05-19": dict(oc="Approved", fda=None, ann="2025-05-16 per the Novavax 8-K; press release 2025-05-19",
                            url="https://www.sec.gov/Archives/edgar/data/1000694/000110465925050226/tm2515521d1_8k.htm",
                            label="Novavax 8-K, May 2025 (approval announced May 16, 2025)",
                            quote="On May 16, 2025, Novavax, Inc. (\"Novavax\" or the \"Company\") announced that the U.S. Food and Drug Administration (\"FDA\") has approved the Company's Biologics License Application (\"BLA\") for Nuvaxovid",
                            drug="NUVAXOVID (COVID-19 Vaccine, Adjuvanted)"),
    "AXGN-2025-12-04": dict(oc="Approved", fda=None, ann="2025-12-03, after the close",
                            url="https://www.sec.gov/Archives/edgar/data/805928/000080592825000140/axgn-20251203.htm",
                            label="Axogen 8-K, December 3, 2025",
                            quote="On December 3, 2025, the Company announced it received FDA approval of its Biologics License Application for Avance ® (acellular nerve allograft-arwx).",
                            drug="AVANCE (acellular nerve allograft-arwx)"),
    "RYTM-2026-03-20": dict(oc="Approved", fda="2026-03-19", ann="2026-03-19, after the close", rec="NDA 213793 S-009",
                            url=L + "2026/213793Orig1s009ltr.pdf",
                            label="FDA approval letter, NDA 213793 S-009, March 19, 2026",
                            quote="addition of an indication to reduce excess body weight and maintain weight reduction long term",
                            drug="IMCIVREE (setmelanotide)"),
    "RGNX-2026-02-09": dict(oc="CRL", fda="2026-02-07", ann="2026-02-09", rec="BLA 125840 CRL",
                            url=C + "CRL_BLA125840_20260207.pdf",
                            label="FDA Complete Response Letter, BLA 125840, February 7, 2026",
                            quote="February 7, 2026",
                            drug="clemidsogene lanparvovec (RGX-121)"),
    "IRON-2026-02-13": dict(oc="CRL", fda="2026-02-13", ann=None, rec="NDA 220707 CRL",
                            url=C + "CRL_NDA220707_20260213.pdf",
                            label="FDA Complete Response Letter, NDA 220707, February 13, 2026",
                            quote="02/13/2026 12:35:22 PM",
                            drug="bitopertin"),
    "AQST-2026-02-02": dict(oc="CRL", fda=None, ann="2026-02-02",
                            url="https://www.biospace.com/press-releases/aquestive-therapeutics-announces-fda-issuance-of-complete-response-letter-for-anaphylm",
                            label="Aquestive release, February 2, 2026 (letter received January 30)",
                            quote="received a Complete Response Letter (CRL) from the U.S. Food and Drug Administration (FDA) on January 30, 2026",
                            drug="Anaphylm (dibutepinephrine) sublingual film"),
    "ABBV-2026-04-23": dict(oc="CRL", fda="2026-04-22", ann="2026-04-23", rec="BLA 761459 CRL",
                            url=C + "CRL_BLA761459_20260422.pdf",
                            label="FDA Complete Response Letter, BLA 761459, April 22, 2026",
                            quote="04/22/2026 01:23:25 PM",
                            drug="trenibotulinumtoxinE (AGN-151586)"),
    "FBIO-2025-10-01": dict(oc="CRL", fda="2025-09-30", ann="2025-10-01", rec="NDA 211241 CRL",
                            url=L + "2026/211241Orig1s000ltr.pdf",
                            label="FDA approval letter for NDA 211241 (January 2026), citing the CRL of September 30, 2025",
                            quote="which constituted a complete response to our September 30, 2025, action letter.",
                            drug="CUTX-101 (copper histidinate)"),
}
# The AQST letter date is the company's own statement (no FDA file); key facts show it as the day the letter was received.
RECEIVED = {"AQST-2026-02-02": "2026-01-30"}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def link(s):
    return f'<a href="{esc(s["url"])}" rel="nofollow noopener">{esc(s["label"])}</a>'


def kv(k, v):
    return f'<div class="kv"><span>{k}</span><b>{v}</b></div>'


def patch(doc, slug, s):
    d = slug.split("-", 1)[1]
    # 1. source rows
    has_primary = '<span>Primary source</span>' in doc
    doc = re.sub(r'(<div class="kv"><span>Primary source</span><b>).*?(</b></div>)',
                 lambda m: m.group(1) + link(s) + m.group(2), doc, count=1, flags=re.S)
    if has_primary:      # one source row is enough; the old Validation row repeated an unfinished check
        doc = re.sub(r'<div class="kv"><span>Validation</span><b>.*?</b></div>', "", doc, count=1, flags=re.S)
    else:
        doc = re.sub(r'(<div class="kv"><span>Validation</span><b>)(?:Verified \d{4}-\d{2}-\d{2}: <a [^>]*>.*?</a>)(</b></div>)',
                     lambda m: m.group(1) + f"Verified {TODAY}: " + link(s) + m.group(2), doc, count=1, flags=re.S)
    # 2. key-fact dates
    fda = s["fda"] or RECEIVED.get(slug)
    first = kv("FDA decision date", fda) if fda else kv("FDA decision date", NOT_ON_RECORD)
    if slug in RECEIVED:
        first = kv("CRL received (company)", RECEIVED[slug])
    rows = first + (kv("Announced", esc(s["ann"])) if s.get("ann") else "")
    doc = re.sub(r'<div class="kv"><span>(?:FDA decision date|CRL received \(company\))</span><b>[^<]*</b></div>'
                 r'(?:<div class="kv"><span>Announced</span><b>[^<]*</b></div>)?', lambda m: rows, doc, count=1)
    # 3. drug row
    dr = esc(s["drug"])
    if re.search(r'<span>Drug(?: / candidate)?</span>', doc):
        doc = re.sub(r'(<div class="kv"><span>Drug(?: / candidate)?</span><b>)[^<]*(</b></div>)',
                     lambda m: m.group(1) + dr + m.group(2), doc, count=1)
    else:
        doc = doc.replace(rows, rows + kv("Drug", dr), 1)
    # 4. applicant / company
    if s.get("company"):
        doc = re.sub(r'(<div class="kv"><span>Company</span><b>)[^<]*(</b></div>)',
                     lambda m: m.group(1) + esc(s["company"]) + m.group(2), doc, count=1)
    if s.get("applicant"):
        doc = re.sub(r'<div class="kv"><span>(?:Company|Applicant)</span><b>[^<]*</b></div>',
                     lambda m: kv("Applicant", esc(s["applicant"])), doc, count=1)
    return doc


def jload(p):
    return json.load(io.open(os.path.join(HERE, p), encoding="utf-8"))


def jsave(p, d, indent=1):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8", newline="").write(
        json.dumps(d, indent=indent, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.dry_run:
        write_ledgers()
        # pages still carrying the price-only banner (AZN-2026-02-20, NVO-2025-01-28) are upgraded by the
        # pipeline's own step from the ledger just written; the source row is then set below like the rest
        import subprocess
        subprocess.run([sys.executable, os.path.join(HERE, "upgrade_verified_decisions.py")], check=True)
    n = 0
    for slug, s in FIX.items():
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        doc = io.open(p, encoding="utf-8").read()
        new = patch(doc, slug, s)
        if s["url"] not in new and not a.dry_run:
            raise SystemExit(f"{slug}: source row not patched (template not recognised)")
        if new != doc:
            n += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"decision pages re-sourced: {n} of {len(FIX)}")


def write_ledgers():
    # ledger: the evidence is the primary source and the sentence checked in it
    ver = jload("_decision_verification.json")
    for slug, s in FIX.items():
        e = ver["results"].setdefault(slug, {"ticker": slug.split("-")[0], "date": slug.split("-", 1)[1],
                                             "asset": "", "claimed": "approval" if s["oc"] == "Approved" else "crl"})
        ev = e.get("evidence") or {}
        want = {"kind": "primary", "source_url": s["url"], "source_label": s["label"],
                "quote": s["quote"], "quote_checked": TODAY,
                "fda_action_date": s["fda"], "announced": s.get("ann")}
        if ev == want:
            continue
        if ev and ev.get("kind") != "primary" and "evidence_before_recheck" not in e:
            e["evidence_before_recheck"] = ev
            e["status_before_recheck"] = e.get("status")
        e["status"] = "verified_approved" if s["oc"] == "Approved" else "verified_crl"
        e["evidence"] = want
    jsave("_decision_verification.json", ver)
    # FDA record of the day (only where the cited source IS that record)
    arch = jload("_fda_action_archive.json")
    k = 0
    for slug, s in FIX.items():
        if not (s.get("rec") and s["fda"]):
            continue
        cur = arch.get(slug) or {}
        if cur.get("date") == s["fda"] and cur.get("source_url"):
            continue
        arch[slug] = {"checked": TODAY, "date": s["fda"], "record": s["rec"], "source_url": s["url"],
                      "name": s["drug"], "oc": s["oc"], "basis": "red team 2026-11-18: FDA record read directly"}
        k += 1
    jsave("_fda_action_archive.json", dict(sorted(arch.items())))
    print(f"_fda_action_archive.json: {k} FDA action day(s) recorded")

if __name__ == "__main__":
    main()
