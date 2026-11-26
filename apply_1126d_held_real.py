# -*- coding: utf-8 -*-
"""apply_1126d_held_real.py -- the last 27 decision pages whose outcome was guessed from the share price.

David, 2026-11-26 06:51 ("keep building our databases ... most accurate facts, most accurate dates"), under his standing
hand-off for site fixes ("just do it, red team everything"). After apply_1126c_held_pages.py retired 69 held pages that
recorded no FDA decision, 27 pages were still titled "outcome unverified" and listed on /decisions as price-only. Each
was checked on 2026-11-26 against a primary source (an FDA letter, an FDA page or list, Drugs@FDA, or the company's own
release or SEC filing), and every source was opened again in a red-team pass before this script was written.

  * 18 record a real FDA action on the page's date. They are re-sourced the way apply_1118b_decision_sources.py does it:
    the verification ledger gets the primary source and the sentence checked, upgrade_verified_decisions.py lifts the
    price-only banner, and key facts give the FDA's own day and the public day where they differ. Where a partner's
    page already cites the FDA's letter for the same action (SNY-2026-02-24 for Dupixent), the same record is cited.
  * GSK-2025-02-17 records a real approval on a day the US market was closed (Presidents' Day). The FDA approved
    Penmenvy on Friday, February 14, 2025 and GSK announced it on Saturday, February 15, so the page is rebuilt on
    February 18, the first day GSK's NYSE shares traded on the news (build_decision_page.py,
    decision_pages_2026_11_26_penmenvy.json), and the old address redirects there. The first-trading-day key follows
    AXGN-2025-12-04 and RHHBY-2025-10-20 (announced on a Sunday).
  * 8 record something that was not an FDA approval or Complete Response Letter on that date: two Refusal to File
    letters, a license suspension, the removal of a REMS, a safety labeling change eleven days earlier, a tentative
    approval, a response the company itself sent to a clinical hold, and one with no FDA action at all. They are retired
    the way apply_1118_retire_decisions.py retires a page, with a /corrections entry naming what did happen.

Run-up study exclusions are added for the retired rows. RETIRE joins RETRACTED in tests/test_no_retracted_claims.py.
Idempotent. Facts only, not investment advice.

    python build_decision_page.py --events decision_pages_2026_11_26_penmenvy.json   (first)
    python apply_1126d_held_real.py [--dry-run]
"""
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
TODAY = "2026-11-26"

L = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/"
DAF = "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo="
CBER25 = ("https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/"
          "2025-biological-license-application-supplement-noteworthy-approvals")

# slug: oc, fda (FDA action day; None where no public FDA record states it), ann (public day, when it differs or is
# all we have), rec (FDA record id, only where url IS that record), url, label, quote (checked 2026-11-26), drug.
FIX = {
    "REGN-2026-02-24": dict(oc="Approved", fda="2026-02-23", ann="2026-02-24", rec="BLA 761055 S-075",
                            url=L + "2026/761055Orig1s075ltr.pdf",
                            label="FDA approval letter, BLA 761055 S-075, February 23, 2026",
                            quote="This Prior Approval sBLA provides for a new indication of treatment of adult and "
                                  "pediatric patients aged 6 years and older",
                            drug="DUPIXENT (dupilumab), allergic fungal rhinosinusitis"),
    "JNJ-2026-02-17": dict(oc="Approved", fda=None, ann="2026-02-17",
                           url="https://www.jnj.com/media-center/press-releases/fda-approves-rybrevant-faspro-amivantamab-"
                               "and-hyaluronidase-lpuj-as-the-only-egfr-targeted-therapy-that-can-be-administered-once-a-month",
                           label="Johnson & Johnson release, February 17, 2026",
                           quote="the U.S. Food and Drug Administration (FDA) has approved a new, simplified monthly "
                                 "dosing schedule",
                           drug="RYBREVANT FASPRO (amivantamab and hyaluronidase-lpuj), once-monthly dosing"),
    "BMY-2025-12-04": dict(oc="Approved", fda="2025-12-04",
                           url="https://www.fda.gov/news-events/press-announcements/fda-approves-first-car-t-cell-"
                               "therapy-marginal-zone-lymphoma-us",
                           rec="BLA 125714 (FDA press announcement)", label="FDA press announcement, December 4, 2025",
                           quote="The U.S. Food and Drug Administration today approved a new indication for Breyanzi",
                           drug="Breyanzi (lisocabtagene maraleucel), marginal zone lymphoma"),
    "AMRX-2025-12-01": dict(oc="Approved", fda=None, ann="2025-12-01",
                            url="https://www.globenewswire.com/news-release/2025/12/01/3197418/0/en/Amneal-Announces-U-S-"
                                "FDA-Approval-of-Cyclosporine-Ophthalmic-Emulsion-0-05.html",
                            label="Amneal release, December 1, 2025",
                            quote="the U.S. Food and Drug Administration (FDA) has approved the Company's cyclosporine "
                                  "ophthalmic emulsion 0.05%",
                            drug="Cyclosporine ophthalmic emulsion 0.05% (generic of RESTASIS)"),
    "RHHBY-2025-10-20": dict(oc="Approved", fda=None, ann="2025-10-19, a Sunday",
                             url="https://www.gene.com/media/press-releases/15085/2025-10-19/fda-approves-genentechs-gazyva-for-the-t",
                             label="Genentech release, October 19, 2025",
                             quote="has approved Gazyva (obinutuzumab) for the treatment of adult patients with active "
                                   "lupus nephritis",
                             drug="Gazyva (obinutuzumab), lupus nephritis"),
    "KRYS-2025-09-15": dict(oc="Approved", fda="2025-09-12", ann="2025-09-15",
                            url="https://www.fda.gov/vaccines-blood-biologics/vyjuvek",
                            rec="BLA STN 125774 (approval letter of September 12, 2025)",
                            label="FDA product page for VYJUVEK (approval letter of September 12, 2025)",
                            quote="September 12, 2025 Approval Letter",
                            drug="VYJUVEK (beremagene geperpavec-svdt), label update"),
    "TAK-2025-09-05": dict(oc="Approved", fda="2025-09-05", url=CBER25, rec="STN 125577/691",
                           label="FDA list of 2025 biologics supplement approvals, STN 125577/691, September 5, 2025",
                           quote="To expand the current approved adult prophylaxis indication for type 3 von "
                                 "Willebrand disease (VWD)",
                           drug="VONVENDI [von Willebrand factor (Recombinant)], expanded indication"),
    "TEVA-2025-08-28": dict(oc="Approved", fda="2025-08-27", ann="2025-08-28", rec="ANDA 214568",
                            url="https://www.fda.gov/drugs/drug-and-biologic-approval-and-ind-activity-reports/"
                                "2025-first-generic-drug-approvals",
                            label="FDA list of 2025 first generic approvals, ANDA 214568, August 27, 2025",
                            quote="ANDA 214568, Liraglutide Injection, Teva Pharmaceuticals Development, Inc., "
                                  "Saxenda Injection, 8/27/2025",
                            drug="Liraglutide injection (first generic of Saxenda)"),
    "MRNA-2025-08-27": dict(oc="Approved", fda="2025-08-27", url=CBER25, rec="STN 125752/305 and 125835/6",
                            label="FDA list of 2025 biologics supplement approvals, STN 125752/305 and 125835/6, "
                                  "August 27, 2025",
                            quote="To include the 2025-2026 Formula and associated labeling revisions.",
                            drug="Spikevax and mNEXSPIKE, 2025-2026 Formula"),
    "PFE-2025-08-27": dict(oc="Approved", fda="2025-08-27", url=CBER25, rec="STN 125742/656",
                           label="FDA list of 2025 biologics supplement approvals, STN 125742/656, August 27, 2025",
                           quote="10 mcg drug product (2025-2026 Formula) in the single-dose vial presentation",
                           drug="COMIRNATY, 2025-2026 Formula",
                           applicant="BioNTech Manufacturing GmbH (Pfizer co-commercializes)"),
    "DSNKY-2025-06-23": dict(oc="Approved", fda="2025-06-23", rec="BLA 761464",
                             url=DAF + "761464",
                             label="Drugs@FDA, BLA 761464, action date June 23, 2025",
                             quote="On June 23, 2025, the Food and Drug Administration granted accelerated approval to "
                                   "datopotamab deruxtecan-dlnk",
                             drug="Datroway (datopotamab deruxtecan-dlnk), EGFR-mutated NSCLC (accelerated approval)"),
    "RHHBY-2025-07-18": dict(oc="CRL", fda=None, ann="2025-07-18",
                             url="https://www.gene.com/media/press-releases/15070/2025-07-18/genentech-provides-update-on-supplementa",
                             label="Genentech release, July 18, 2025",
                             quote="the U.S. Food and Drug Administration (FDA) issued a Complete Response Letter (CRL)",
                             drug="Columvi (glofitamab-gxbm) with gemcitabine and oxaliplatin (GemOx)"),
    "AMRX-2025-06-12": dict(oc="Approved", fda="2025-06-11", ann="2025-06-12", rec="ANDA 218256",
                            url=DAF + "218256",
                            label="Drugs@FDA, ANDA 218256, approval June 11, 2025",
                            quote="06/11/2025 ORIG-1 Approval",
                            drug="Prednisolone acetate ophthalmic suspension 1% (generic of Pred Forte)"),
    "MRNA-2025-06-12": dict(oc="Approved", fda="2025-06-12", rec="BLA STN 125796/37",
                            url="https://www.fda.gov/media/187046/download",
                            label="FDA approval letter, BLA STN 125796/37, June 12, 2025",
                            quote="in individuals 18 through 59 years of age who are at increased risk for LRTD caused "
                                  "by RSV",
                            drug="mRESVIA (mRNA-1345), adults 18 to 59 at increased risk"),
    "MRK-2025-06-09": dict(oc="Approved", fda="2025-06-09", rec="BLA 761432",
                           url=L + "2025/761432Orig1s000Correctedltr.pdf",
                           label="FDA approval letter (corrected), BLA 761432, action date June 9, 2025",
                           quote="The effective action date will remain June 9, 2025, the date of the original approval "
                                 "letter.",
                           drug="ENFLONSIA (clesrovimab-cfor)"),
    "MRNA-2025-05-31": dict(oc="Approved", fda="2025-05-30", ann="2025-05-31", rec="BLA STN 125835/0",
                            url="https://www.fda.gov/media/186740/download",
                            label="FDA approval letter, BLA STN 125835/0, May 30, 2025",
                            quote="COVID-19 Vaccine, mRNA (MNEXSPIKE) is indicated for active immunization to prevent "
                                  "coronavirus disease 2019 (COVID-19)",
                            drug="MNEXSPIKE (mRNA-1283)"),
    "INCY-2025-01-16": dict(oc="Approved", fda=None, ann="2025-01-15, after the close",
                            url="https://investor.incyte.com/news-releases/news-release-details/incyte-and-syndax-"
                                "announce-us-food-and-drug-administration-fda",
                            label="Incyte and Syndax release, January 15, 2025, 5:34 p.m. ET",
                            quote="the U.S. Food and Drug Administration (FDA) has approved Niktimvo (axatilimab-csfr) "
                                  "in 9 mg and 22 mg vial sizes",
                            drug="Niktimvo (axatilimab-csfr), 9 mg and 22 mg vials"),
    "SNDX-2025-01-16": dict(oc="Approved", fda=None, ann="2025-01-15, after the close",
                            url="https://investor.incyte.com/news-releases/news-release-details/incyte-and-syndax-"
                                "announce-us-food-and-drug-administration-fda",
                            label="Incyte and Syndax release, January 15, 2025, 5:34 p.m. ET",
                            quote="the U.S. Food and Drug Administration (FDA) has approved Niktimvo (axatilimab-csfr) "
                                  "in 9 mg and 22 mg vial sizes",
                            drug="Niktimvo (axatilimab-csfr), 9 mg and 22 mg vials"),
}

NEW = "GSK-2025-02-18"
NEW_ANN = "2025-02-15 (a Saturday, London); February 17 was a US market holiday"
PENMENVY_LETTER = ("https://www.fda.gov/files/vaccines%2C%20blood%20%26%20biologics/published/"
                   "february_14_2025_approval_letter_-_penmenvy.pdf")

SEC_AXSM = "https://www.sec.gov/Archives/edgar/data/1579428/000095017025083441/axsm-ex99_1.htm"
# (dest, why, src, was) as apply_1118_retire_decisions.py takes them
RETIRE = {
    "GSK-2025-02-17": (f"/fda-decision/{NEW}",
                       "The FDA approved Penmenvy on February 14, 2025 and GSK announced it on February 15; February 17 "
                       "was a US market holiday. The decision now has its page on February 18, the first day GSK's US "
                       "shares traded on the news.",
                       PENMENVY_LETTER,
                       "A decision page for GSK dated February 17, 2025, a day the US market was closed, that guessed "
                       "an approval from the share price (marked outcome unverified)."),
    "SRPT-2025-11-25": ("/ticker/SRPT",
                        "There was no FDA approval for Elevidys on or near November 25, 2025. On November 14 the FDA "
                        "approved a boxed warning and narrowed the indication to ambulatory patients, a safety labeling "
                        "change, not an approval.",
                        "https://www.fda.gov/news-events/press-announcements/fda-approves-new-safety-warning-and-revised-"
                        "indication-limits-use-elevidys-following-reports-fatal",
                        "A held decision page for SRPT dated 2025-11-25 that guessed an FDA approval from the share "
                        "price (marked outcome unverified)."),
    "AMRX-2025-10-29": ("/ticker/AMRX",
                        "The FDA's letter of October 28, 2025 tentatively approved Amneal's beclomethasone dipropionate "
                        "HFA inhaler (ANDA 213811) and said it could not grant final approval yet; a tentative approval "
                        "is not an approval.",
                        L + "2025/213811Orig1s000TAltr.pdf",
                        "A held decision page for AMRX dated 2025-10-29 that guessed an FDA approval from the share "
                        "price (marked outcome unverified)."),
    "GMAB-2025-09-12": ("/ticker/GMAB",
                        "There was no FDA decision on epcoritamab within 14 days of September 12, 2025. Genmab's report "
                        "for the nine months to September 30, 2025 lists no Complete Response Letter; the pending "
                        "application then had a target date of November 30, 2025.",
                        "https://www.sec.gov/Archives/edgar/data/1434265/000143426525000092/genmabinterimreportq32025.htm",
                        "A held decision page for GMAB dated 2025-09-12 that guessed an FDA Complete Response Letter "
                        "from the share price (marked outcome unverified)."),
    "VALN-2025-08-25": ("/ticker/VALN",
                        "The FDA did not approve IXCHIQ in August 2025. On August 22, 2025 it suspended the vaccine's "
                        "biologics license; Valneva announced it on August 25.",
                        "https://www.fda.gov/safety/medical-product-safety-information/fda-update-safety-ixchiq-"
                        "chikungunya-vaccine-live-fda-suspends-biologics-license-fda-safety",
                        "A held decision page for VALN dated 2025-08-25 that guessed an FDA approval from the share "
                        "price (marked outcome unverified)."),
    "BMY-2025-06-27": ("/ticker/BMY",
                       "There was no FDA approval for Breyanzi on or near June 27, 2025. That day the FDA removed the "
                       "REMS for six CAR-T therapies, Breyanzi among them, with label updates; no new indication was "
                       "approved.",
                       "https://www.fda.gov/news-events/press-announcements/fda-eliminates-risk-evaluation-and-"
                       "mitigation-strategies-rems-autologous-chimeric-antigen-receptor",
                       "A held decision page for BMY dated 2025-06-27 that guessed an FDA approval from the share price "
                       "(marked outcome unverified)."),
    "GHRS-2025-06-20": ("/ticker/GHRS",
                        "There was no FDA decision on GH001 in June 2025. No marketing application had been filed; on "
                        "June 20 GH Research said it had sent the FDA its response to a clinical hold on its IND.",
                        "https://www.sec.gov/Archives/edgar/data/0001855129/000114036125023162/ef20050847_ex99-1.htm",
                        "A held decision page for GHRS dated 2025-06-20 that guessed an FDA Complete Response Letter "
                        "from the share price (marked outcome unverified)."),
    "AXSM-2025-06-09": ("/ticker/AXSM",
                        "The FDA did not issue a Complete Response Letter for AXS-14 (esreboxetine). On June 9, 2025 "
                        "Axsome said it had received a Refusal to File letter: the FDA found the application not "
                        "complete enough to review.",
                        SEC_AXSM,
                        "A held decision page for AXSM dated 2025-06-09 that guessed an FDA Complete Response Letter "
                        "from the share price (marked outcome unverified)."),
    "HRMY-2025-02-19": ("/ticker/HRMY",
                        "The FDA did not issue a Complete Response Letter for pitolisant in idiopathic hypersomnia. On "
                        "February 19, 2025 Harmony said it had received a Refusal to File letter for the supplemental "
                        "application.",
                        "https://ir.harmonybiosciences.com/news-releases/news-release-details/harmony-biosciences-"
                        "provides-update-status-supplemental-new-drug",
                        "A held decision page for HRMY dated 2025-02-19 that guessed an FDA Complete Response Letter "
                        "from the share price (marked outcome unverified)."),
}


def jload(p):
    return json.load(io.open(os.path.join(HERE, p), encoding="utf-8"))


def jsave(p, d, indent=1):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8", newline="").write(
        json.dumps(d, indent=indent, ensure_ascii=False) + "\n")


def write_ledgers(dry):
    ver = jload("_decision_verification.json")
    arch = jload("_fda_action_archive.json")
    pub = jload("_decision_published.json")
    items = dict(FIX)
    items[NEW] = dict(oc="Approved", fda="2025-02-14", ann="2025-02-15", rec="BLA STN 125819/0", url=PENMENVY_LETTER,
                      label="FDA approval letter, BLA STN 125819/0, February 14, 2025",
                      quote="February 14, 2025 ... in individuals 10 through 25 years of age.",
                      drug="Penmenvy (MenABCWY vaccine)")
    nv = na = 0
    for slug, s in items.items():
        e = ver["results"].setdefault(slug, {"ticker": slug.split("-")[0], "date": slug.split("-", 1)[1],
                                             "asset": s["drug"], "claimed": "approval" if s["oc"] == "Approved" else "crl"})
        want = {"kind": "primary", "source_url": s["url"], "source_label": s["label"], "quote": s["quote"],
                "quote_checked": TODAY, "fda_action_date": s["fda"], "announced": s.get("ann")}
        status = "verified_approved" if s["oc"] == "Approved" else "verified_crl"
        if not (e.get("evidence") == want and e.get("status") == status):
            nv += 1
        if e.get("evidence") and e.get("evidence") != want and e["evidence"].get("kind") != "primary" and "evidence_before_recheck" not in e:
            e["evidence_before_recheck"] = e["evidence"]
        if "status_before_recheck" not in e and e.get("status") != status:
            e["status_before_recheck"] = e.get("status")
        e["status"], e["evidence"] = status, want
        if s.get("rec") and s["fda"]:
            cur = arch.get(slug) or {}
            if not (cur.get("date") == s["fda"] and cur.get("source_url")):
                arch[slug] = {"checked": TODAY, "date": s["fda"], "record": s["rec"], "source_url": s["url"],
                              "name": s["drug"], "oc": s["oc"],
                              "basis": "held-page audit 2026-11-26: FDA record read directly"}
                na += 1
    if NEW not in pub:
        pub[NEW] = TODAY
    if not dry:
        jsave("_decision_verification.json", ver)
        jsave("_fda_action_archive.json", dict(sorted(arch.items())))
        jsave("_decision_published.json", pub, indent=0)
    print(f"_decision_verification.json: {nv} record(s) set to a primary source; _fda_action_archive.json: {na} day(s)")


def patch_pages(dry):
    import apply_1118b_decision_sources as B
    B.TODAY = TODAY
    n = 0
    for slug, s in FIX.items():
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        doc = io.open(p, encoding="utf-8").read()
        new = B.patch(doc, slug, s)
        if not dry and s["url"].replace("&", "&amp;") not in new and s["url"] not in new:
            raise SystemExit(f"{slug}: source row not patched (template not recognised)")
        if new != doc:
            n += 1
            if not dry:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    # the rebuilt Penmenvy page: build_decision_page.py labels its key day "Announced"; GSK announced on the 15th
    p = os.path.join(SITE, "fda-decision", NEW, "index.html")
    doc = io.open(p, encoding="utf-8").read()
    new = doc.replace('<div class="kv"><span>Announced</span><b>2025-02-18</b></div>',
                      '<div class="kv"><span>Announced</span><b>' + NEW_ANN + '</b></div>'
                      '<div class="kv"><span>First US trading day</span><b>2025-02-18</b></div>')
    if new != doc:
        n += 1
        if not dry:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"decision pages re-sourced: {n} of {len(FIX) + 1}")


def listing_rows(dry):
    """/decisions rows of the re-sourced pages said 'Approved: price-only'. upgrade_verified_decisions.py renames such
    a row only when the text ends the row, and badge_decision_provenance.py had put its badge after it. Name the drug."""
    lp = os.path.join(SITE, "decisions", "index.html")
    doc = io.open(lp, encoding="utf-8").read()
    new, n = doc, 0
    names = {slug: re.split(r"\s*[(\[,]", s["drug"])[0].strip()[:48] for slug, s in FIX.items()}
    names["EBS-2026-01-14"] = "OTC NARCAN Nasal Spray"   # a sourced page whose row had the same leftover tag
    for slug, name in names.items():
        new, k = re.subn(r'(<a class="row" href="/fda-decision/' + re.escape(slug) + r'">.{0,200}?class="d"><span class="[a-z]+">'
                         r'(?:Approved|CRL)</span>): price-only', lambda m: m.group(1) + ": " + name, new, count=1, flags=re.S)
        n += k
    if new != doc and not dry:
        io.open(lp, "w", encoding="utf-8", newline="").write(new)
    print(f"/decisions rows named: {n}")


def main():
    dry = "--dry-run" in sys.argv
    if not os.path.isdir(os.path.join(SITE, "fda-decision", NEW)):
        raise SystemExit(f"build {NEW} first: python build_decision_page.py --events decision_pages_2026_11_26_penmenvy.json")
    write_ledgers(dry)
    if not dry:
        subprocess.run([sys.executable, os.path.join(HERE, "upgrade_verified_decisions.py")], check=True)
    patch_pages(dry)
    listing_rows(dry)
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
        kind = "wrong date" if s == "GSK-2025-02-17" else "no FDA approval or CRL"
        e = {"reason": f"{kind}: " + why, "document": src,
             "finding": ("the page sat on a day the US market was closed; the decision is re-keyed to the first "
                         "trading day after the announcement" if s == "GSK-2025-02-17"
                         else "the page's outcome was guessed from the share price; the FDA action that date was "
                              "something else, or there was none"),
             "checked": TODAY}
        if pages.get(s) != e:
            pages[s] = e
            n += 1
    if n:
        io.open(p, "w", encoding="utf-8").write(json.dumps(ex, indent=1, ensure_ascii=False))
    print(f"runup_study_exclusions.json: {n} entr(ies) added")


if __name__ == "__main__":
    main()
