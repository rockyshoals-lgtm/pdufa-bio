# -*- coding: utf-8 -*-
"""ingest_presenters_2026_09_05.py -- deep-mine haul: 31 company-announced presenters.

Four parallel research passes over all 41 upcoming conferences (2026-09-05). Every row
below is from the COMPANY'S OWN release (wire service or IR page) with the URL on the
row -- conference program listings and news writeups were excluded, as were non-US
listings (Antengene, Leads Biolabs, Vicore, Ascletis, Caliway, Infex) and private
companies (Insilico, Marengo, BlossomHill, Avalyn, Altesa, Kailera). Caris (CAI) was
excluded as diagnostics, not a drug catalyst. Preclinical rows are labelled PRECLINICAL
in the drug field per the SLS discipline: a preclinical poster is not a clinical
readout and the clinical-readout conference statistics must not be attached to it.

Structural finding for the re-scan calendar: ASH/SABCS/ESMO-IO/ESMO-Asia/ACR/AES/
ObesityWeek/WMS + the Oct US meetings (ASN, IDWeek, AHA, ACAAI, ACG, AAO, ASBMR) have
no company PRs yet -- their announcement waves are late Sep through mid Nov. Re-run
this sweep ~Sep 18 (ASTRO/AACR-PANC/WMS wave), ~Oct 1 (October meetings), and ~Nov 5
(ASH abstract drop + December meetings).

Idempotent by (ticker, conference).
"""
import csv
import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PF = os.path.join(HERE, "catalysts_out", "conference_presentations_history.csv")

# (ticker, company, conf, start_date, drug, indication, pres_type, src_date, url)
NEW = [
 ("CGEM", "Cullinan Therapeutics, Inc.", "WCLC", "2026-09-12",
  "Zipalertinib (with Taiho Oncology)",
  "1L EGFR exon 20 insertion NSCLC (Phase 3 REZILIENT3 interim)",
  "Presidential Symposium oral", "2026-08-19",
  "https://secure.businesswire.com/news/home/20260819883527/en/Zipalertinib-Plus-Chemotherapy-First-Line-Phase-3-REZILIENT3-Trial-Data-Selected-for-Presidential-Symposium-Presentation-at-the-IASLC-2026-World-Conference-on-Lung-Cancer"),
 ("BNTX", "BioNTech SE", "WCLC", "2026-09-12",
  "Pumitamig (BNT327) + elfetabart drozuntecan",
  "NSCLC / SCLC (first global combination data)",
  "late-breaking oral + pipeline presentations", "2026-08-20",
  "https://www.globenewswire.com/news-release/2026/08/20/3348151/0/en/biontech-highlights-late-stage-lung-cancer-pipeline-momentum-and-first-global-data-for-pumitamig-elfetabart-drozuntecan-novel-novel-combination-at-wclc-2026.html"),
 ("NUVB", "Nuvation Bio Inc.", "WCLC", "2026-09-12",
  "IBTROZI (taletrectinib)", "ROS1+ NSCLC (TRUST-I/II subgroup analyses)",
  "data presentations", "2026-08-04",
  "https://www.prnewswire.com/news-releases/nuvation-bio-to-present-new-subgroup-analyses-of-pivotal-data-for-ibtrozi-taletrectinib-in-advanced-ros1-positive-non-small-cell-lung-cancer-at-wclc-and-esmo-annual-congresses-302841746.html"),
 ("NUVB", "Nuvation Bio Inc.", "ESMO", "2026-10-23",
  "IBTROZI (taletrectinib)", "ROS1+ NSCLC (TRUST-I/II subgroup analyses)",
  "data presentations", "2026-08-04",
  "https://www.prnewswire.com/news-releases/nuvation-bio-to-present-new-subgroup-analyses-of-pivotal-data-for-ibtrozi-taletrectinib-in-advanced-ros1-positive-non-small-cell-lung-cancer-at-wclc-and-esmo-annual-congresses-302841746.html"),
 ("SMMT", "Summit Therapeutics Inc.", "WCLC", "2026-09-12",
  "Ivonescimab", "EGFR-TKI-progressed NSCLC (HARMONi updated OS analysis)",
  "oral (session OA14)", "2026-08-25",
  "https://smmttx.com/news/press-releases/news-details/2026/Ivonescimab-Plus-Chemotherapy-Global-Phase-III-HARMONi-Primary-Analysis-Results-Published-in-The-Lancet-Oncology/default.aspx"),
 ("ABBV", "AbbVie Inc.", "WCLC", "2026-09-12",
  "ABBV-1480, ABBV-706, telisotuzumab adizutecan",
  "NSCLC / SCLC (Ph1b ABBV-1480 data)", "multiple presentations", "2026-08-21",
  "https://news.abbvie.com/2026-08-21-AbbVie-to-Present-New-Data-at-WCLC-2026-Showcasing-Innovation-Across-Lung-Cancer-Pipeline"),
 ("CMPX", "Compass Therapeutics, Inc.", "ESMO", "2026-10-23",
  "Tovecimig", "Advanced biliary tract cancer (randomized, paclitaxel +/- tovecimig)",
  "oral (Proffered Paper)", "2026-07-17",
  "https://www.globenewswire.com/news-release/2026/07/17/3329171/0/en/Compass-Therapeutics-Announces-Tovecimig-Data-Accepted-for-an-Oral-Presentation-at-the-ESMO-Congress-2026.html"),
 ("IMTX", "Immatics N.V.", "ESMO", "2026-10-23",
  "Anzu-cel (IMA203), IMA203CD8, IMA402",
  "Advanced melanoma / PRAME+ solid tumors",
  "proffered paper oral + rapid oral + poster", "2026-07-17",
  "https://www.globenewswire.com/news-release/2026/07/17/3329151/0/en/Immatics-Announces-Upcoming-Presentations-Across-Its-PRAME-Franchise-at-ESMO-Congress-2026.html"),
 ("ZNTL", "Zentalis Pharmaceuticals, Inc.", "ESMO", "2026-10-23",
  "Azenosertib", "Cyclin E1+ platinum-resistant ovarian cancer (DENALI OS + ASPENOVA)",
  "rapid oral + trial-in-progress poster", "2026-07-17",
  "https://www.globenewswire.com/news-release/2026/07/17/3329282/0/en/zentalis-pharmaceuticals-to-present-at-the-european-society-for-medical-oncology-esmo-congress-2026.html"),
 ("XNCR", "Xencor, Inc.", "ESMO", "2026-10-23",
  "XmAb819", "Advanced clear cell renal cell carcinoma (Phase 1)",
  "oral (Proffered Paper)", "2026-07-16",
  "https://www.businesswire.com/news/home/20260716029119/en/Xencor-Announces-Proffered-Paper-Oral-Presentation-at-ESMO-2026-for-Phase-1-Clinical-Study-of-XmAb819-in-Advanced-Clear-Cell-Renal-Cell-Carcinoma"),
 ("IDYA", "IDEAYA Biosciences, Inc.", "ESMO", "2026-10-23",
  "Darovasertib, IDE849 (SHR-4849)",
  "Uveal melanoma; SCLC / neuroendocrine carcinoma", "presentations x3", "2026-07-17",
  "https://ir.ideayabio.com/2026-07-17-IDEAYA-Biosciences-Announces-ESMO-2026-Presentations-for-Darovasertib-and-IDE849-Clinical-Programs"),
 ("EIKN", "Eikon Therapeutics, Inc.", "ESMO", "2026-10-23",
  "EIK1001, EIK1003, EIK1004, EIK1005",
  "Multiple advanced solid tumors (Ph1/2 and Ph2/3)", "abstracts x7", "2026-07-20",
  "https://www.globenewswire.com/news-release/2026/07/20/3329652/0/en/eikon-therapeutics-announces-seven-abstracts-accepted-for-presentation-at-the-2026-european-society-of-medical-oncology-esmo-congress.html"),
 ("ORIC", "ORIC Pharmaceuticals, Inc.", "ESMO", "2026-10-23",
  "Enozertinib (ORIC-114), rinzimetostat (ORIC-944)",
  "1L EGFR-atypical NSCLC; mCRPC",
  "poster x3 (2 clinical, 1 PRECLINICAL ePoster)", "2026-07-20",
  "https://www.globenewswire.com/news-release/2026/07/20/3329711/0/en/oric-pharmaceuticals-announces-three-presentations-at-the-european-society-for-medical-oncology-esmo-congress-2026.html"),
 ("KTTA", "Pasithea Therapeutics Corp.", "ESMO", "2026-10-23",
  "PAS-004", "MAPK pathway-driven advanced solid tumors (Phase 1)",
  "poster (Abstract 1050P)", "2026-07-21",
  "https://www.globenewswire.com/news-release/2026/07/21/3330295/0/en/Pasithea-Therapeutics-Announces-Presentation-of-PAS-004-Data-to-European-Society-for-Medical-Oncology-ESMO-Congress-2026.html"),
 ("IMMP", "Immutep Limited", "ESMO", "2026-10-23",
  "Eftilagimod alfa", "Soft tissue sarcoma (EFTISARC-NEO Ph2 IIT, HRQoL)",
  "presentation", "2026-07-24",
  "https://www.globenewswire.com/news-release/2026/07/24/3332815/0/en/immutep-announces-abstract-accepted-for-presentation-at-the-european-society-for-medical-oncology-esmo-congress-2026.html"),
 ("BLRX", "BioLineRx Ltd.", "ESMO", "2026-10-23",
  "GLIX1 (with Hemispherian AS) - PRECLINICAL",
  "HR-proficient ovarian cancer (preclinical synergy with PARP inhibitors)",
  "e-Poster (preclinical)", "2026-07-20",
  "https://www.prnewswire.com/news-releases/biolinerx-and-hemispherian-as-to-present-data-demonstrating-strong-synergy-of-glix1-with-parp-inhibitors-in-hr-proficient-ovarian-cancers-at-esmo-2026-302829471.html"),
 ("CADL", "Candel Therapeutics, Inc.", "ASTRO", "2026-09-26",
  "Aglatimagene besadenovec (CAN-2409)",
  "Localized intermediate-to-high-risk prostate cancer (Ph3 biomarker analysis)",
  "poster", "2026-08-03",
  "https://ir.candeltx.com/news-releases/news-release-details/candel-therapeutics-present-extended-data-phase-3-results"),
 ("SANA", "Sana Biotechnology, Inc.", "EASD", "2026-09-28",
  "UP421 (hypoimmune allogeneic islet cell therapy)",
  "Type 1 diabetes (first-in-human IST clinical data)",
  "symposium presentation", "2026-07-01",
  "https://www.globenewswire.com/news-release/2026/07/01/3320655/0/en/Sana-Biotechnology-Announces-Symposium-Presentation-at-the-European-Association-for-the-Study-of-Diabetes-EASD-Annual-Meeting-2026.html"),
 ("IPSC", "Century Therapeutics, Inc.", "EASD", "2026-09-28",
  "CNTY-813 (iPSC-derived islet replacement) - PRECLINICAL",
  "Type 1 diabetes (preclinical)", "oral #225 (preclinical)", "2026-07-09",
  "https://www.globenewswire.com/news-release/2026/07/09/3324741/0/en/Century-Therapeutics-Selected-for-Oral-Presentations-of-CNTY-813-Preclinical-Data-at-EASD-2026-and-Breakthrough-T1D-Clinical-Research-Congress-2026.html"),
 ("IBIO", "iBio, Inc.", "EASD", "2026-09-28",
  "IBIO-610 (Activin E antibody) - PRECLINICAL",
  "Obesity (preclinical NHP study, alone + with semaglutide)",
  "presentation #759 (preclinical)", "2026-07-01",
  "https://www.globenewswire.com/news-release/2026/07/01/3320497/0/en/iBio-Reports-Single-Dose-of-IBIO-610-Achieved-Near-Complete-Active-Activin-E-Inhibition-Through-Eight-Weeks-in-Obese-NHP-Study.html"),
 ("TLSA", "Tiziana Life Sciences Ltd", "ECTRIMS", "2026-10-21",
  "Intranasal foralumab",
  "Non-active secondary progressive MS (Ph2a INFORM-MS topline)",
  "topline data planned for presentation (company statement)", "2026-06-25",
  "https://www.globenewswire.com/news-release/2026/06/25/3317416/0/en/Tiziana-Announces-Last-Patient-Successfully-Dosed-in-its-Phase-2-INFORM-MS-Trial.html"),
 ("MNPR", "Monopar Therapeutics Inc.", "AASLD", "2026-11-05",
  "ALXN1840 (tiomolibdate choline)", "Wilson disease (FoCus Phase 3 analyses)",
  "oral + poster", "2026-08-19",
  "https://www.globenewswire.com/news-release/2026/08/19/3347581/0/en/monopar-appoints-jeffrey-d-kent-m-d-as-executive-vice-president-head-of-medical-affairs-announces-two-alxn1840-presentations-at-aasld-the-liver-meeting-2026.html"),
 ("BEAM", "Beam Therapeutics Inc.", "ERS", "2026-09-05",
  "BEAM-302", "Alpha-1 antitrypsin deficiency (Ph1/2 updated data)",
  "late-breaking oral", "2026-07-23",
  "https://investors.beamtx.com/news-releases/news-release-details/beam-therapeutics-present-updated-data-phase-12-trial-beam-302/"),
 ("SVRA", "Savara Inc.", "ERS", "2026-09-05",
  "Molgramostim (MOLBREEVI)", "Autoimmune pulmonary alveolar proteinosis",
  "oral + poster x2 (IMPALA-2)", "2026-08-24",
  "https://www.businesswire.com/news/home/20260824428528/en"),
 ("GRI", "GRI Bio, Inc.", "ERS", "2026-09-05",
  "GRI-0621", "Idiopathic pulmonary fibrosis (Ph2a data)",
  "late-breaking presentation", "2026-08-24",
  "https://www.globenewswire.com/news-release/2026/08/24/3349779/0/en/gri-bio-to-present-late-breaking-phase-2a-gri-0621-data-highlighting-lung-function-anti-fibrotic-biomarkers-and-favorable-tolerability-in-ipf-at-ers-2026.html"),
 ("TRVI", "Trevi Therapeutics, Inc.", "ERS", "2026-09-05",
  "Haduvio (nalbuphine ER)", "Refractory chronic cough / IPF chronic cough (RIVER)",
  "poster + abstract", "2026-08-26",
  "https://www.globenewswire.com/news-release/2026/08/26/3351240/0/en/trevi-therapeutics-announces-upcoming-presentations-at-the-european-respiratory-society-ers-congress-2026.html"),
 ("UTHR", "United Therapeutics Corporation", "ERS", "2026-09-05",
  "Ralinepag, nebulized treprostinil (TETON), Tyvaso",
  "PAH / IPF / PH-ILD", "oral + poster incl. late-breaking", "2026-08-28",
  "https://ir.unither.com/~/media/Files/U/United-Therapeutics-IR/documents/press-releases/2026/esc-ers-2026-press-release.pdf"),
 ("KYMR", "Kymera Therapeutics, Inc.", "ERS", "2026-09-05",
  "KT-621 (oral STAT6 degrader)",
  "Atopic dermatitis with comorbid asthma / allergic rhinitis (Ph1b BroADen)",
  "poster x2", "2026-09-01",
  "https://www.globenewswire.com/news-release/2026/09/01/3353950/0/en/kymera-therapeutics-announces-presentations-on-kt-621-a-first-in-class-oral-stat6-degrader-at-the-european-respiratory-society-and-european-academy-of-dermatology-venereology-congr.html"),
 ("LQDA", "Liquidia Corporation", "ERS", "2026-09-05",
  "YUTREPIA (treprostinil DPI) + L606",
  "PH-ILD (ASCENT baseline; Re-Spire Phase 3 TiP)", "poster x2", "2026-09-02",
  "https://www.globenewswire.com/news-release/2026/09/02/3355134/0/en/liquidia-to-present-posters-at-the-european-respiratory-society-ers-2026-congress.html"),
 ("INSM", "Insmed Incorporated", "ERS", "2026-09-05",
  "ARIKAYCE, BRINSUPRI (brensocatib), TPIP",
  "MAC lung disease / bronchiectasis / PH",
  "5 abstracts incl. late-breaking Ph3b ENCORE oral", "2026-09-03",
  "https://www.prnewswire.com/news-releases/insmed-to-present-data-across-its-respiratory-portfolio-including-new-late-breaking-arikayce-amikacin-liposome-inhalation-suspension-results-from-phase-3b-encore-study-at-the-european-respiratory-society-congress-2026-302868119.html"),
 ("RNTX", "Rein Therapeutics, Inc.", "ERS", "2026-09-05",
  "LTI-03 (inhaled)", "Idiopathic pulmonary fibrosis (dose-escalation study)",
  "late-breaking poster", "2026-09-04",
  "https://www.globenewswire.com/news-release/2026/09/04/3356530/28652/en/rein-therapeutics-to-present-late-breaking-poster-at-the-european-respiratory-society-ers-2026-congress.html"),
]


def main():
    rows = list(csv.DictReader(io.open(PF, encoding="utf-8", errors="replace")))
    have = {(r["ticker"], r["conference"]) for r in rows
            if str(r.get("catalyst_date", "")) >= "2026-09-01"}
    added = 0
    for (tk, co, conf, d, drug, ind, pt, sd, url) in NEW:
        if (tk, conf) in have:
            print(f"  skip {tk}/{conf}: already present")
            continue
        rows.append({
            "ticker": tk, "cik": "", "company": co, "catalyst_type": "Conference",
            "catalyst_date": d, "date_precision": "day", "drug": drug,
            "indication": ind, "source": "company_release", "source_url": url,
            "snippet": f"Company release {sd}: {pt} at {conf} 2026. "
                       + ("PRECLINICAL data; the clinical-readout conference "
                          "statistics on this site do not apply."
                          if "PRECLINICAL" in (drug + pt).upper() else
                          "Clinical data presentation announced by the company."),
            "confidence": "verified", "redistribute": "", "retrieved_at": "2026-09-05",
            "conference": conf, "pres_type": pt, "date_basis": "organiser_dates",
            "extractor_version": "deep_mine_2026_09_05"})
        added += 1
    with io.open(PF, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"presenter ingest: {added} row(s) added ({len(NEW)} in haul)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
