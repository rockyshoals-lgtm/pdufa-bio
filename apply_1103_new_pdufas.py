# -*- coding: utf-8 -*-
"""apply_1103_new_pdufas.py -- 21 announced PDUFA goal dates that were on no surface of the site (2026-11-03).

Found by a full-text sweep of EDGAR 8-K/6-K exhibits May 1 - Nov 3, 2026 for "PDUFA" + "target action date" /
"PDUFA date", diffed against api/v1/dataset.mjs. Every row below quotes the sponsor's own SEC exhibit, which states a
DAY. Rows the sweep found but this script does NOT add, with reasons, are in the builder note (partner restatements
by RPRX/LGND/ZLAB, the ARGX slide whose program-to-date mapping is ambiguous, and dates already on the site).
Market-cap tier from Polygon reference data at write time (same thresholds the site uses). Facts only.
"""
import datetime as dt
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
DATAJS = os.path.join(SITE, "api", "data.js")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
sys.path.insert(0, HERE)
from extend_runup_study import load_key  # noqa: E402

E = "https://www.sec.gov/Archives/edgar/data/"
# id-suffix, ticker, company (None = reuse dataset spelling), goal, name, ta, indication, source label, url, quote, slug
NEW = [
 ("qure_2027-05-01", "QURE", "uniQure N.V.", "2027-05-01", "Ifezuntirgene inilparvovec (AMT-130) - Huntington's disease",
  "Neurology", "Huntington's disease (Accelerated Approval pathway; FDA tentatively plans an advisory committee)",
  "uniQure 8-K 2026-11-02 (EX-99.1, BLA accepted, priority review)", E + "1590560/000110465926120915/tm2628699d1_ex99-1.htm",
  "The application has been granted Priority Review with a Prescription Drug User Fee Act (PDUFA) target action date of May 1, 2027.", "QURE-amt-130"),
 ("pvla_2027-02-28", "PVLA", "Palvella Therapeutics, Inc.", "2027-02-28", "QTORIN rapamycin - microcystic lymphatic malformations (SELVA)",
  "Rare Disease", "Microcystic lymphatic malformations", "Palvella 8-K 2026-10-28 (EX-99.1, NDA accepted, priority review)",
  E + "1583648/000119312526435113/pvla-ex99_1.htm",
  "The FDA has assigned a Prescription Drug User Fee Act (PDUFA) target action date of February 28, 2027.", "PVLA-qtorin-rapamycin"),
 ("bmrn_2027-02-28", "BMRN", None, "2027-02-28", "VOXZOGO (vosoritide) - full approval, children with achondroplasia",
  "Rare Disease", "Children with achondroplasia (application for full approval)", "BioMarin 8-K 2026-11-02 (EX-99.1, Q3 2026 results)",
  E + "1048477/000104847726000021/earningsrelease-2nov26ex991.htm",
  "BioMarin's application for full approval of VOXZOGO in children with achondroplasia is under review by the FDA, with a PDUFA target action date of February 28, 2027.", "BMRN-voxzogo-achondroplasia"),
 ("bmrn_2027-05-30", "BMRN", None, "2027-05-30", "VOXZOGO (vosoritide) - hypochondroplasia (sNDA)",
  "Rare Disease", "Hypochondroplasia", "BioMarin 8-K 2026-11-02 (EX-99.1, Q3 2026 results)",
  E + "1048477/000104847726000021/earningsrelease-2nov26ex991.htm",
  "Food and Drug Administration (FDA) has set a PDUFA target action date of May 30, 2027 for its supplemental NDA to expand the use of VOXZOGO for the treatment of HCH", "BMRN-voxzogo-hypochondroplasia"),
 ("insm_2027-01-28", "INSM", None, "2027-01-28", "ARIKAYCE (amikacin liposome inhalation suspension) - MAC lung disease (sNDA)",
  "Infectious Disease", "MAC lung disease, as part of a combination antibacterial drug regimen", "Insmed 10-Q 2026-10-29",
  E + "1104506/000110450626000047/insm-20260930.htm",
  "In September 2026, our US supplemental new drug application (sNDA) for ARIKAYCE in patients with MAC lung disease was accepted and granted priority review by the FDA as part of a combination antibacterial drug regimen, with a target action date of January 28, 2027.", "INSM-arikayce"),
 ("jazz_2027-04-16", "JAZZ", None, "2027-04-16", "Cannabidiol oral capsule formulation (NDA)",
  "CNS/Neurology", "Oral cannabidiol capsule formulation", "Jazz 8-K 2026-11-02 (EX-99.1, Q3 2026 results)",
  E + "1232524/000123252426000056/a3q26earningsrelease.htm",
  "The PDUFA target action date for our New Drug Application (NDA) for the oral cannabidiol capsule formulation is April 16, 2027.", "JAZZ-cannabidiol-capsule"),
 ("dyn_2027-01-21", "DYN", None, "2027-01-21", "Z-rostudirsen - Duchenne muscular dystrophy, exon 51",
  "Rare Disease", "Duchenne muscular dystrophy amenable to exon 51 skipping", "Dyne 8-K 2026-07-29 (EX-99.1, BLA accepted, priority review)",
  E + "1818794/000119312526323940/dyn-ex99_1.htm",
  "Biologics License Application (BLA) for z-rostudirsen in exon 51 DMD accepted for review by FDA; Priority Review granted; PDUFA target action date set for January 21, 2027", "DYN-z-rostudirsen"),
 ("pypd_2026-11-28", "PYPD", "PolyPid Ltd.", "2026-11-28", "D-PLEX100 - prevention of surgical site infections",
  "Infectious Disease", "Prevention of surgical site infections in patients undergoing abdominal colorectal surgery",
  "PolyPid 6-K 2026-07-29 (EX-99.1, NDA accepted, priority review)", E + "1611842/000121390026082564/ea029964201ex99-1.htm",
  "The FDA did not identify any filing review issues and set a Prescription Drug User Fee Act (PDUFA) target action date of November 28, 2026", "PYPD-d-plex100"),
 ("bmy_2027-03-11", "BMY", None, "2027-03-11", "Reblozyl (luspatercept) with a JAK inhibitor - myelofibrosis-associated anemia (INDEPENDENCE)",
  "Hematology", "Adults with myelofibrosis-associated anemia receiving red blood cell transfusions, with concomitant JAK inhibitor therapy",
  "Bristol Myers Squibb 8-K 2026-07-30 (EX-99.1, Q2 2026 results)", E + "14272/000001427226000018/a2026q2ex991-filing.htm",
  "The FDA granted a Prescription Drug User Fee Act (PDUFA) date of March 11, 2027.", "BMY-reblozyl-mf"),
 ("bmy_2027-05-13", "BMY", None, "2027-05-13", "Mezigdomide + carfilzomib + dexamethasone - RRMM (SUCCESSOR-2)",
  "Hematology", "Relapsed or refractory multiple myeloma", "Bristol Myers Squibb 8-K 2026-07-30 (EX-99.1, Q2 2026 results)",
  E + "14272/000001427226000018/a2026q2ex991-filing.htm",
  "The FDA accepted a New Drug Application for mezigdomide in combination with carfilzomib and dexamethasone (MeziKd) in patients with relapsed or refractory multiple myeloma (RRMM), granting a PDUFA date of May 13, 2027.", "BMY-mezigdomide"),
 ("hrmy_2027-04-01", "HRMY", "Harmony Biosciences Holdings, Inc.", "2027-04-01", "Pitolisant GR (gastro-resistant formulation) - NDA",
  "CNS/Neurology", "Pitolisant gastro-resistant formulation (NDA accepted July 2026)", "Harmony 8-K 2026-08-04 (EX-99.1, Q2 2026 results)",
  E + "1802665/000110465926090086/hrmy-20260804xex99d1.htm", "Pitolisant GR NDA Accepted in July; Target PDUFA Date April 1, 2027", "HRMY-pitolisant-gr"),
 ("blte_2027-02-12", "BLTE", None, "2027-02-12", "Tinlarebant - Stargardt disease type 1",
  "Ophthalmology", "Stargardt disease type 1 (STGD1)", "Belite Bio 6-K 2026-08-11 (EX-99.1, NDA accepted, priority review)",
  E + "1889109/000110465926094040/tm2622827d1_ex99-1.htm",
  "The FDA has set a Prescription Drug User Fee Act (PDUFA) date of February 12, 2027.", "BLTE-tinlarebant"),
 ("imnm_2027-04-28", "IMNM", "Immunome, Inc.", "2027-04-28", "Varegacestat - desmoid tumors (RINGSIDE)",
  "Oncology", "Adults with desmoid tumors", "Immunome 8-K 2026-08-11 (EX-99.1, Q2 2026 results)",
  E + "1472012/000119312526344577/imnm-ex99_1.htm",
  "Varegacestat PDUFA target action date set for April 28, 2027, following U.S. FDA acceptance of New Drug Application (NDA) for adults with desmoid tumors", "IMNM-varegacestat"),
 ("zbio_2027-05-27", "ZBIO", None, "2027-05-27", "Obexelimab - IgG4-related disease",
  "Immunology", "IgG4-related disease", "Zenas BioPharma 8-K 2026-08-13 (EX-99.1, Q2 2026 results)",
  E + "1953926/000110465926095437/tm2622871d1_ex99-1.htm",
  "Obexelimab BLA submission for the treatment of IgG4-RD accepted by FDA; PDUFA target action date of May 27, 2027", "ZBIO-obexelimab"),
 ("apmd_2027-02-28", "APMD", "Apnimed, Inc.", "2027-02-28", "AD109 (Oxnimbi) - obstructive sleep apnea",
  "CNS/Neurology", "Obstructive sleep apnea", "Apnimed 8-K 2026-09-08 (EX-99.1, Q2 2026 results)",
  E + "1745648/000119312526385355/apmd-ex99_1.htm",
  "U.S. Food and Drug Administration (FDA) Accepted the NDA for AD109, with a proposed proprietary name Oxnimbi, and assigned a PDUFA target action date of February 28, 2027", "APMD-ad109"),
 ("ntla_2027-03-10", "NTLA", "Intellia Therapeutics, Inc.", "2027-03-10", "Lonvoguran ziclumeran (lonvo-z) - hereditary angioedema",
  "Rare Disease", "Hereditary angioedema", "Intellia 8-K 2026-09-08 (EX-99.1, BLA accepted, priority review)",
  E + "1652130/000119312526385194/ntla-ex99_1.htm",
  "FDA sets Prescription Drug User Fee Act (PDUFA) date of March 10, 2027", "NTLA-lonvo-z"),
 ("aqst_2027-03-16", "AQST", "Aquestive Therapeutics, Inc.", "2027-03-16", "Anaphylm (dibutepinephrine) sublingual film - NDA resubmission",
  "Immunology", "Anaphylaxis (Class 2 resubmission after the January 30, 2026 CRL)", "Aquestive 8-K 2026-10-15 (EX-99.1, resubmission accepted)",
  E + "1398733/000139873326000058/a2026-10x19aquestivepduf.htm",
  "Aquestive Therapeutics Announces FDA Acceptance of Anaphylm NDA Resubmission and PDUFA Goal Date of March 16, 2027", "AQST-anaphylm"),
 ("eton_2027-03-29", "ETON", "Eton Pharmaceuticals, Inc.", "2027-03-29", "LIBERVANT (diazepam) buccal film - ages 6 to 11 (Type 9 NDA)",
  "CNS/Neurology", "Seizure clusters, expansion to patients ages 6 to 11", "Eton 8-K 2026-10-14 (EX-99.1)",
  E + "1710340/000143774926032600/ex_1025429.htm",
  "The NDA has a Prescription Drug User Fee Act (PDUFA) target action date of March 29, 2027.", "ETON-libervant"),
 ("mrk_2027-03-22", "MRK", None, "2027-03-22", "ENFLONSIA (clesrovimab) - second RSV season (SMART)",
  "Infectious Disease", "RSV lower respiratory tract disease in children under 2 at increased risk, through their second RSV season",
  "Merck 8-K 2026-10-29 (EX-99.1, Q3 2026 results)", E + "310158/000110465926119825/tm2628203d1_ex99-1.htm",
  "U.S. FDA set PDUFA date of March 22, 2027.", "MRK-enflonsia"),
 ("mrk_2027-04-22", "MRK", None, "2027-04-22", "IDVYNSO - treatment-naive HIV-1 (P053) and 96-week data (sNDAs)",
  "Infectious Disease", "Adults with HIV-1 infection (treatment-naive; 96-week data in virologically suppressed adults)",
  "Merck 8-K 2026-10-29 (EX-99.1, Q3 2026 results)", E + "310158/000110465926119825/tm2628203d1_ex99-1.htm",
  "U.S. FDA set a PDUFA date for both sNDAs of April 22, 2027.", "MRK-idvynso"),
 ("mrk_2027-06-15", "MRK", None, "2027-06-15", "Sacituzumab tirumotecan (sac-TMT) - endometrial cancer (TroFuse-005)",
  "Oncology", "Adults with endometrial cancer previously treated with platinum chemotherapy and a PD-1/PD-L1 inhibitor",
  "Merck 8-K 2026-10-29 (EX-99.1, Q3 2026 results)", E + "310158/000110465926119825/tm2628203d1_ex99-1.htm",
  "U.S. FDA set Prescription Drug User Fee Act (PDUFA) date of June 15, 2027.", "MRK-sac-tmt"),
]


def tier(mcap):
    if not mcap:
        return ""
    return ("Nano" if mcap < 50e6 else "Micro" if mcap < 300e6 else "Small" if mcap < 2e9
            else "Mid" if mcap < 10e9 else "Large")


def polygon(tk, key):
    try:
        u = f"https://api.polygon.io/v3/reference/tickers/{tk}?apiKey={key}"
        r = json.load(urllib.request.urlopen(u, timeout=20)).get("results", {})
        return r.get("market_cap"), r.get("name")
    except Exception:  # noqa: BLE001
        return None, None


key = load_key()
src = io.open(DATASET, encoding="utf-8").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
ids = {r["id"] for r in rows}
s_ = io.open(DATAJS, encoding="utf-8").read()
k = s_.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(s_[k:])
today = dt.date.today()
added = 0
for sfx, tk, co, d, name, ta, ind, sname, url, quote, slug in NEW:
    rid = "pdufa_" + sfx
    if rid in ids:
        continue
    known = next((r for r in rows if r.get("t") == tk and r.get("company")), None)
    mcap, pname = polygon(tk, key)
    company = (known or {}).get("company") or co or pname or tk
    cap = tier(mcap) or (known or {}).get("cap") or ""
    rows.append({"id": rid, "t": tk, "company": company, "d": d, "dp": "day", "name": name, "type": "PDUFA", "ta": ta,
                 "cap": cap, "st": "Upcoming", "ua": NOW, "url": f"/pdufa/{slug}",
                 "_d": {"indication": ind, "event_slug": slug, "source": sname, "source_url": url, "source_quote": quote,
                        "source_note": "Found 2026-11-03 by an EDGAR full-text sweep; the date is the sponsor's own statement."}})
    ref = next((c for c in slate["catalysts"] if c.get("ticker") == tk), {})
    slate["catalysts"].append({"ticker": tk, "name": ref.get("name") or company, "date": d,
                               "t_minus": (dt.date.fromisoformat(d) - today).days, "drug": name, "indication": ind,
                               "price": ref.get("price"), "mcap": mcap or ref.get("mcap"), "cap": cap,
                               "adv": ref.get("adv"), "cash_months": ref.get("cash_months")})
    added += 1
    print(f"  + {rid}: {tk} {d} {cap or '?'}  {name}")
rows.sort(key=lambda x: (str(x.get("d") or "9999"), str(x.get("t") or "")))
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
io.open(DATAJS, "w", encoding="utf-8").write(s_[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":")) + s_[k + end:])
print(f"{added} PDUFA row(s) added (dataset + slate)")
