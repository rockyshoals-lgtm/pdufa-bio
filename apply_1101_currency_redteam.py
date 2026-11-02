# -*- coding: utf-8 -*-
"""apply_1101_currency_redteam.py -- currency pass and red-team fixes of 2026-11-01 (David: "ensure everything is up
to date and current, fix any issues, red team everything"). Every fact below was read from a primary source on
2026-11-01 (17:00-19:00 Pacific); see odin_cowork_dropbox/2026-11-01_BUILDER_currency_redteam.md.

Decisions
  INO   VOCERYQ (INO-3107) accelerated approval, RRP. FDA press announcement "For Immediate Release: October 30,
        2026 ... today granted accelerated approval" (CBER product, so no Drugs@FDA record). Goal Oct 30 (Inovio 8-K
        2026-05-13, already the row's source): on the goal date.
  AZN   Ultomiris (ravulizumab) IgAN accelerated approval: Drugs@FDA BLA 761108 S-046 AP 2026-10-21; AstraZeneca 6-K
        2026-10-22. Row was "Dec 2026" with no source: no goal day, so out of the timing census.
  LLY   Mounjaro (tirzepatide) SURPASS-CVOT MACE indication: FDA letter NDA 215866 S-044/S-045 dated 2026-08-27.
        The calendar carried it as an unsourced "Q4 2026 (est.)" pending row.
  NVS   Pluvicto mAPMN/S (PSMAddition): Drugs@FDA NDA 215833 S-037 AP 2026-07-31 (letter + label). Same.
  GILD/MRK Trodelvy + Keytruda: BLA 761115 S-063/S-064 AP 2026-06-24, already published as GILD-2026-06-24;
        /pdufa/MRK-trodelvy still read "under FDA review" (handled in canonicalise_duplicate_event_pages.py).
Dates moved
  AGIO  mitapivat SCD sNDA: Agios release 2026-10-30, major amendment, "The PDUFA goal date ... is now February 1,
        2027" (was Nov 1, 2026).
  EXEL  zanzalintinib + atezolizumab: Exelixis 8-K EX-99.1 2026-10-29, "The updated PDUFA target action date is
        March 3, 2027" (three-month extension announced September 2026; was Dec 3, 2026).
  RHHBY Lunsumio VELO + Polivy (SUNMO): Roche release 2026-06-18, "The FDA is expected to make a decision on approval
        by 9 February 2027". The calendar showed an unsourced "Q4 2026 (est.)" row.
  NVO   Mim8 (denecimig): Novo 6-K 2026-10-02, review extended for facility remediation, "The FDA has not
        communicated a new timeline". Year precision kept, now sourced and explained.
Sponsor change
  BTAI -> TEVA  IGALMI at-home sNDA: BioXcel 8-K 2026-10-30 Item 2.01, sale of substantially all assets incl. "the
        pending supplemental n[DA]" to Teva completed 2026-10-26 (BioXcel in Chapter 11 since Aug 27, trading as
        BTAIQ). Teva release 2026-10-27: BXCL501 "under FDA review". Goal Nov 14 stays on BioXcel's 8-K 2026-05-15.
Census integrity (red team: "36 decisions with a sourced goal" while 14 CSV rows had an empty goal_source)
  13 rows get the sponsor document that states their goal day (all matched the day held). REGN garetosmab: every
  Regeneron source says "August 2026" only, so the held Aug 31 was never sourced: month precision now, out of the
  census, and the decision page's "12 days early" goes.
Facts only; not investment advice.
"""
import datetime as dt
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
TODAY = "2026-11-01"

FDA_INO = ("https://www.fda.gov/news-events/press-announcements/"
           "fda-approves-first-plasmid-dna-based-immunotherapy-adults-recurrent-respiratory-papillomatosis")
INO_REL = ("https://www.prnewswire.com/news-releases/inovio-announces-fda-accelerated-approval-of-voceryq-an-"
           "immunotherapy-to-reduce-the-frequency-of-surgery-in-adults-with-recurrent-respiratory-papillomatosis-rrp-302925406.html")
AZN_6K = "https://www.sec.gov/Archives/edgar/data/901832/000165495426009093/a9580z.htm"
AZN_DAF = "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo=761108"
AGIO_REL = ("https://www.globenewswire.com/news-release/2026/10/30/3392151/31990/en/agios-announces-new-pdufa-goal-date-of-"
            "february-1-2027-for-mitapivat-sickle-cell-disease-snda-company-is-launch-ready-and-in-labeling-discussions-with-fda.html")
EXEL_8K = "https://www.sec.gov/Archives/edgar/data/939767/000093976726000114/exel20260930exhibit991.htm"
ROCHE_LP = "https://www.roche.com/media/releases/med-cor-2026-06-18"
NVO_6K = "https://www.sec.gov/Archives/edgar/data/353278/000117184326006374/f6k_100226.htm"
BTAI_8K = "https://www.sec.gov/Archives/edgar/data/1720893/000110465926120737/tm2624733d2_8k.htm"
TEVA_REL = ("https://www.globenewswire.com/news-release/2026/10/27/3388911/0/en/teva-acquires-worldwide-rights-to-bxcl501-"
            "further-expanding-innovative-neuroscience-pipeline.html")
REGN_REL = ("https://investor.regeneron.com/news-releases/news-release-details/"
            "garetosmab-biologics-license-application-accepted-fda-priority")

src = io.open(DATASET, encoding="utf-8", errors="replace").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
by = {r["id"]: r for r in rows}
log = []


def move(rid, new_d, dp, why, src_name, url, quote):
    r = by[rid]
    d = r.setdefault("_d", {})
    if r.get("d") == new_d:
        return
    h = d.setdefault("date_history", [])
    if not h:
        h.append({"date": r["d"], "note": "date the row held before this change"})
    h.append({"date": new_d, "changed": TODAY, "why": why})
    r["d"], r["dp"], r["ua"] = new_d, dp, NOW
    if dp != "day":
        r["dm"] = new_d[:7]
    d.update({"source": src_name, "source_url": url, "source_quote": quote})
    d.pop("goal_unsourced", None)
    log.append(f"~ {rid}: goal -> {new_d} ({dp})")


# ---- decisions
r = by["pdufa_ino_2026-10-30"]
if r.get("st") != "Decided":
    r.update({"st": "Decided", "oc": "Approved", "dcd": "2026-10-30", "url": "/fda-decision/INO-2026-10-30", "ua": NOW,
              "name": "VOCERYQ (INO-3107) - recurrent respiratory papillomatosis"})
    r["_d"].update({
        "brand": "Voceryq", "inn": "doruxapapogene ralaplasmid and lalikinogene sifuplasmid-gxfd",
        "indication_short": "recurrent respiratory papillomatosis (adults)", "title_indication": "Recurrent Respiratory Papillomatosis",
        "seo_desc": ("Voceryq (INO-3107) was approved by the FDA on October 30, 2026 (accelerated approval) for adults with "
                     "recurrent respiratory papillomatosis, on its goal date."),
        "decision_source": "FDA press announcement, October 30, 2026", "decision_source_url": FDA_INO,
        "fda_action_date": "2026-10-30", "fda_action_source_url": FDA_INO,
        "fda_action_record": "FDA press announcement, October 30, 2026 (CBER product; not in Drugs@FDA)",
        "announcement": "INOVIO press release, October 30, 2026", "announcement_url": INO_REL,
        "decision_quote": ("The U.S. Food and Drug Administration today granted accelerated approval for Voceryq "
                           "(doruxapapogene ralaplasmid and lalikinogene sifuplasmid-gxfd) for treatment of adults with "
                           "recurrent respiratory papillomatosis (RRP)"),
        "decision_date_note": "The FDA's announcement is dated October 30, 2026 and states the approval was granted that day, the goal date.",
    })
    log.append("~ pdufa_ino_2026-10-30: Decided / Approved 2026-10-30 (on goal date)")

r = by["pdufa_azn_2026-12-31"]
if r.get("st") != "Decided":
    r.update({"st": "Decided", "oc": "Approved", "dcd": "2026-10-21", "url": "/fda-decision/AZN-2026-10-21", "ua": NOW,
              "name": "Ultomiris (ravulizumab) - IgA nephropathy"})
    r["_d"].update({
        "brand": "Ultomiris", "inn": "ravulizumab-cwvz", "indication": "Primary IgA nephropathy at risk of disease progression (reduce proteinuria; accelerated approval)",
        "indication_short": "IgA nephropathy (reduce proteinuria)", "title_indication": "IgA Nephropathy",
        "seo_desc": ("Ultomiris (ravulizumab) was approved by the FDA on October 21, 2026 (accelerated approval) to reduce "
                     "proteinuria in adults with primary IgA nephropathy, per Drugs@FDA."),
        "decision_source": "Drugs@FDA, BLA 761108 supplement 46, approved October 21, 2026", "decision_source_url": AZN_DAF,
        "fda_action_date": "2026-10-21", "fda_action_source_url": AZN_DAF, "fda_action_record": "BLA 761108 S-046",
        "announcement": "AstraZeneca 6-K, October 22, 2026", "announcement_url": AZN_6K,
        "census_note": "Not in the decision-timing census (checked 2026-11-01): AstraZeneca stated no goal date for this sBLA.",
        "decision_quote": ("Ultomiris (ravulizumab) has been approved in the US to reduce proteinuria in adults with primary "
                           "immunoglobulin A nephropathy (IgAN) at risk for disease progression."),
    })
    log.append("~ pdufa_azn_2026-12-31: Decided / Approved 2026-10-21 (Drugs@FDA S-046)")

# ---- dates moved
move("pdufa_agio_2026-11-01", "2027-02-01", "day",
     "Major amendment: the FDA extended the goal by three months after Agios's October 19 response on a possible REMS (Agios release 2026-10-30).",
     "Agios press release 2026-10-30 (GlobeNewswire)", AGIO_REL,
     "The PDUFA goal date for this sNDA, which was submitted under the FDA's accelerated approval pathway and granted Priority Review, is now February 1, 2027.")
move("pdufa_exel_2026-12-03", "2027-03-03", "day",
     "Three-month extension after Exelixis submitted updated safety and efficacy data in response to an FDA information request (announced September 2026; Exelixis 8-K 2026-10-29).",
     "Exelixis 8-K 2026-10-29 (EX-99.1, Q3 2026 results)", EXEL_8K,
     "The updated PDUFA target action date is March 3, 2027.")

if "pdufa_rhhby_2027-02-09_sunmo" not in by:
    rows.append({"id": "pdufa_rhhby_2027-02-09_sunmo", "t": "RHHBY", "company": "Roche Holding AG", "d": "2027-02-09", "dp": "day",
                 "name": "Lunsumio VELO (mosunetuzumab) + Polivy - relapsed/refractory LBCL (SUNMO)", "type": "PDUFA",
                 "ta": "Oncology", "cap": "Large", "st": "Upcoming", "ua": NOW, "url": "/pdufa/RHHBY-lunsumio-polivy",
                 "_d": {"indication": "Relapsed or refractory large B-cell lymphoma after at least one prior line of systemic therapy",
                        "brand": "Lunsumio VELO", "inn": "mosunetuzumab", "trial": "SUNMO", "event_slug": "RHHBY-lunsumio-polivy",
                        "source": "Roche press release 2026-06-18 (sBLA accepted)", "source_url": ROCHE_LP,
                        "source_quote": "The FDA is expected to make a decision on approval by 9 February 2027."}})
    log.append("+ pdufa_rhhby_2027-02-09_sunmo: Lunsumio VELO + Polivy, goal Feb 9, 2027 (Roche 2026-06-18)")

r = by["pdufa_nvo_mim8_2026-09-30"]
d = r["_d"]
if d.get("source_url") != NVO_6K:
    d.update({"source": "Novo Nordisk 6-K 2026-10-02 (denecimig BLA update)", "source_url": NVO_6K,
              "source_quote": "The FDA has not communicated a new timeline for regulatory action on the BLA",
              "date_note": ("Novo Nordisk's 6-K of October 2, 2026: the FDA's review of the denecimig BLA is still ongoing, "
                            "extended because of facility remediation; the FDA has not communicated a new timeline and has not "
                            "identified deficiencies in the clinical efficacy or safety data. No goal day, month or quarter is "
                            "published, so the row carries the year only.")})
    r["ua"] = NOW
    log.append("~ pdufa_nvo_mim8_2026-09-30: sourced to Novo 6-K 2026-10-02 (review extended, no new timeline)")

# ---- sponsor change: BioXcel -> Teva
r = by["pdufa_btai_2026-11-14"]
if r.get("t") != "TEVA":
    d = r["_d"]
    d.setdefault("ticker_history", []).append({"ticker": "BTAI", "until": "2026-10-26",
                                               "why": "BioXcel sold IGALMI, BXCL501 and the pending sNDA to Teva (8-K 2026-10-30, Item 2.01)."})
    r.update({"t": "TEVA", "company": "Teva Pharmaceutical Industries (acquired from BioXcel Therapeutics, Oct 26, 2026)",
              "cap": "Large", "ua": NOW})
    d["event_slug"] = "BTAI-igalmi"
    d["sponsor_note"] = ("BioXcel Therapeutics filed for Chapter 11 on August 27, 2026 and completed the sale of IGALMI, "
                         "BXCL501 and the pending supplemental NDA to Teva on October 26, 2026 (BioXcel 8-K, October 30, 2026). "
                         "Teva's October 27 release describes BXCL501 as under FDA review. The goal date of November 14, 2026 "
                         "is BioXcel's (8-K, May 15, 2026); Teva has not restated it.")
    d["sponsor_sources"] = [BTAI_8K, TEVA_REL]
    log.append("~ pdufa_btai_2026-11-14: sponsor BioXcel (BTAI) -> Teva (TEVA), goal Nov 14 kept on BioXcel's 8-K")

# ---- census integrity: goal sources (red-team research 2026-11-01)
GOAL_SRC = {
    "pdufa_cort_2026-03-25": ("Corcept 8-K 2026-02-24 (EX-99.1)", "https://www.sec.gov/Archives/edgar/data/1088856/000162828026011080/cort022426ex991pressrelease.htm", "has a Prescription Drug User Fee Act (PDUFA) date of July 11, 2026."),
    "pdufa_gsk_2026-06-18": ("Spero 8-K 2026-05-13 (EX-99.1, reporting GSK's announcement)", "https://www.sec.gov/Archives/edgar/data/1701108/000119312526221567/d147628dex991.htm", "the U.S. Food and Drug Association (FDA) set the Prescription Drug User Fee Act (PDUFA) date ... as June 18, 2026."),
    "pdufa_spro_2026-06-18": ("Spero 8-K 2026-05-13 (EX-99.1)", "https://www.sec.gov/Archives/edgar/data/1701108/000119312526221567/d147628dex991.htm", "the U.S. Food and Drug Association (FDA) set the Prescription Drug User Fee Act (PDUFA) date ... as June 18, 2026."),
    "pdufa_achv_2026-06-20": ("Achieve 10-Q 2026-05-12", "https://www.sec.gov/Archives/edgar/data/949858/000119312526218177/achv-20260331.htm", "assigned a Prescription Drug User Fee Act, or PDUFA, targeted action date of June 20, 2026."),
    "pdufa_uncy_2026-06-29": ("Unicycive 8-K 2026-05-12 (EX-99.1)", "https://www.sec.gov/Archives/edgar/data/1766140/000121390026054736/ea029027701ex99-1.htm", "with a Prescription Drug User Fee Act (PDUFA) target action date of June 29, 2026"),
    "pdufa_celc_2026-07-17": ("Celcuity 8-K 2026-06-02", "https://www.sec.gov/Archives/edgar/data/1603454/000149315226026761/form8-k.htm", "assigned a Prescription Drug User Fee Act (\"PDUFA\") goal date of July 17, 2026."),
    "pdufa_nuvl_2026-09-18": ("Nuvalent 8-K 2026-05-07 (EX-99.1)", "https://www.sec.gov/Archives/edgar/data/1861560/000186156026000020/nuvl-ex99_1.htm", "under FDA review with PDUFA target action date of September 18, 2026"),
    "pdufa_mnkd_2026-07-26": ("MannKind 8-K 2026-05-06 (EX-99.1)", "https://www.sec.gov/Archives/edgar/data/899460/000119312526208910/mnkd-ex99_1.htm", "Furoscix ReadyFlow Autoinjector PDUFA target action date of July 26, 2026"),
    "pdufa_otlk_2026-07-29": ("Outlook Therapeutics 8-K 2026-06-16 (EX-99.1)", "https://www.sec.gov/Archives/edgar/data/1649989/000110465926074346/tm2618010d1_ex99-1.htm", "The FDA set a Prescription Drug User Fee Act (PDUFA) goal date of July 29, 2026."),
    "pdufa_vtrs_2026-07-30": ("Viatris 8-K 2026-02-26 (EX-99.1)", "https://www.sec.gov/Archives/edgar/data/1792044/000179204426000010/exhibit991-4q25earningsrel.htm", "the FDA has assigned a PDUFA goal date of July 30, 2026."),
    "pdufa_repl_2026-08-02": ("Replimune 8-K 2026-07-31 (EX-99.1)", "https://www.sec.gov/Archives/edgar/data/1737953/000110465926088857/tm2621708d1_ex99-1.htm", "The FDA's target action date under the Class 1 resubmission is August 2, 2026."),
    "pdufa_bmy_2026-08-17": ("Bristol Myers Squibb 10-Q 2026-07-30", "https://www.sec.gov/Archives/edgar/data/14272/000001427226000020/bmy-20260630.htm", "FDA acceptance of our NDA for iberdomide in RRMM with a PDUFA date of August 17, 2026"),
    "pdufa_rare_2026-08-23": ("Ultragenyx 8-K 2026-08-04 (EX-99.1)", "https://www.sec.gov/Archives/edgar/data/1515673/000119312526332802/rare-ex99_1.htm", "assigned a Prescription Drug User Fee Act (PDUFA) action date of August 23, 2026."),
    "pdufa_ions_2026-09-22": ("Ionis 8-K 2026-07-29 (EX-99.1)", "https://www.sec.gov/Archives/edgar/data/874015/000114036126029960/ef20078953_ex99-1.htm", "New Drug Application (NDA) under FDA Priority Review with PDUFA target action date of September 22, 2026"),
}
n_src = 0
for rid, (name, url, quote) in GOAL_SRC.items():
    d = by[rid].setdefault("_d", {})
    if d.get("source_url") != url:
        d.update({"source": name, "source_url": url, "source_quote": quote})
        d.pop("goal_unsourced", None)
        n_src += 1
log.append(f"~ census goal sources recorded on {n_src} row(s)")

r = by["pdufa_regn_2026-08-31"]
if r.get("dp") != "month":
    d = r["_d"]
    d.setdefault("date_history", []).append({"date": "2026-08-31", "changed": TODAY, "why": (
        "The day was never sourced: Regeneron's acceptance release (2026-02-19), Q1 8-K and Q2 10-Q all say only "
        "'August 2026'. Month precision; the 'days early' margin is withdrawn.")})
    r.update({"dp": "month", "dm": "2026-08", "ua": NOW})
    d.update({"source": "Regeneron press release 2026-02-19 (BLA accepted, priority review)", "source_url": REGN_REL,
              "source_quote": "The target action date for the FDA decision is August 2026.",
              "census_note": "Not in the decision-timing census (checked 2026-11-01): Regeneron stated the goal only as August 2026 (month)."})
    log.append("~ pdufa_regn_2026-08-31: goal -> August 2026 (month); out of the timing census")

rows.sort(key=lambda x: (str(x.get("d") or "9999"), str(x.get("t") or "")))
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print("\n".join("  " + x for x in log))
