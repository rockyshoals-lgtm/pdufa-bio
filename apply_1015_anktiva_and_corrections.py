# -*- coding: utf-8 -*-
"""apply_1015_anktiva_and_corrections.py -- 2026-10-15 (Pacific) publish, every fact read from a primary source.

1. ANKTIVA (IBRX), resolves the held watcher lead [fda_drugs_feed] pdufa_ibrx_2027-01-06 (held since
   2026-10-14T23:36:17Z UTC). FDA approval notification "FDA approves an expanded indication for nogapendekin
   alfa inbakicept-pmln for BCG-unresponsive non-muscle invasive bladder cancer": "On October 14, 2026, the Food
   and Drug Administration (FDA) approved nogapendekin alfa inbakicept-pmln (Anktiva ...) with BCG for adults with
   BCG-unresponsive NMIBC. This revises the prior indication ... to include patients with high-grade papillary-only
   tumors." The tracked application is the same one: ImmunityBio 8-K EX-99.1 of 2026-08-04 says the FDA accepted
   the sBLA "for ANKTIVA plus BCG in patients with BCG-unresponsive NMIBC with papillary disease without CIS and
   assigned a PDUFA target action date of January 6, 2027". ImmunityBio 8-K EX-99.1 of 2026-10-14 announces it.
   Goal date and action date both come from documents that state them: 84 days early.
2. ENSPRYNG (RHHBY) for MOGAD, a sourced goal date missing from the calendar. Genentech release of 2026-09-09:
   "The FDA is expected to make a decision on approval in MOGAD by January 10, 2027."
3. Decision pages that stated something the sources do not (verified 2026-10-14 against FDA letters, the FDA's
   PMA database, CBER letters and sponsor releases; see the builder note of 2026-10-15):
     BMY-2026-06-01   Camzyos: June 1 was the FDA's ACCEPTANCE (PDUFA Sept 30); approved 2026-09-30, NDA 214998 S-013
     SPRY-2026-05-15  neffy: May 15 was ARS's Q1 earnings release; the label change was approved 2026-03-26 (S-002)
     NVCR-2026-02-12  Optune Pax: FDA PMA P250034 decision and Novocure release were both 2026-02-11
     EBS-2026-02-13   NARCAN: the February action was the multipack supplement S-011, FDA 02-11, announced 02-12
     JAGX-2026-04-29  Canalevia-CA1: an effectiveness-trial topline, not an approval (NADA filed June 2026)
     LGND/XOMA/ZVRA-2026-06-08  Miplyffa: an Orange Book patent listing, no FDA action (approved 2024-09-20)
     PGEN-2026-05-27  Papzimeos: no FDA action on or near that date (approved 2025-08-14)
   Each retired slug is 301'd (to the corrected page, or to the drug page where there was no approval), removed from
   the decisions listing by sync_decisions_listing.py, and removed from _chart2026_events.json. Facts only.
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
FDA = ("https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-expanded-indication-"
       "nogapendekin-alfa-inbakicept-pmln-bcg-unresponsive-non-muscle")
EX = "https://www.sec.gov/Archives/edgar/data/1326110/000119312526421820/d188887dex991.htm"
MOGAD = "https://www.gene.com/media/press-releases/15124/2026-09-09/us-fda-grants-priority-review-for-genent"


def jload(p):
    return json.load(io.open(os.path.join(HERE, p), encoding="utf-8"))


def jsave(p, d):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])

# ---- 1. Anktiva decided
r = next(x for x in rows if x["id"] == "pdufa_ibrx_2027-01-06")
if r.get("st") != "Decided":
    r.update({"st": "Decided", "oc": "Approved", "dcd": "2026-10-14", "url": "/fda-decision/IBRX-2026-10-14",
              "ua": NOW, "name": "ANKTIVA (N-803) + BCG - papillary-only BCG-unresponsive NMIBC", "ta": "Oncology"})
    d = r.setdefault("_d", {})
    d.update({
        "brand": "Anktiva", "inn": "nogapendekin alfa inbakicept-pmln",
        "indication": ("With BCG, adults with BCG-unresponsive non-muscle invasive bladder cancer; now includes "
                       "high-grade papillary-only tumors as well as CIS with or without papillary tumors"),
        "indication_short": "BCG-unresponsive non-muscle invasive bladder cancer with papillary-only tumors",
        "title_indication": "Papillary NMIBC",
        "seo_desc": ("Anktiva (nogapendekin alfa inbakicept-pmln) with BCG was approved by the FDA on October 14, 2026 "
                     "for BCG-unresponsive NMIBC with papillary-only tumors, 84 days before its January 6, 2027 goal date."),
        "decision_source": "FDA approval notification, October 14, 2026 (Oncology/Hematologic Malignancies)",
        "decision_source_url": FDA,
        "fda_notice_title": ("FDA approves an expanded indication for nogapendekin alfa inbakicept-pmln for "
                             "BCG-unresponsive non-muscle invasive bladder cancer"),
        "decision_quote": ("On October 14, 2026, the Food and Drug Administration (FDA) approved nogapendekin alfa "
                           "inbakicept-pmln (Anktiva, Altor BioScience, LLC, an indirect wholly-owned subsidiary of "
                           "ImmunityBio, Inc.) with Bacillus Calmette-Guerin (BCG) for adults with BCG-unresponsive "
                           "non-muscle invasive bladder cancer (NMIBC)."),
        "fda_action_date": "2026-10-14", "fda_action_source_url": FDA,
        "fda_action_record": "FDA approval notification (sBLA, BLA 761336; letter not yet on Drugs@FDA)",
        "decision_date_note": ("The FDA's notification is dated October 14, 2026 and states the approval was made that "
                               "day. The goal date, January 6, 2027, is from ImmunityBio's 8-K exhibit of August 4, 2026."),
        "review": ("sBLA expanding the 2024 indication to papillary-only disease. Per the FDA, based on the prior "
                   "efficacy in QUILT-3.032 Cohort A (NCT03022825; 77 patients with CIS; CR 62%, 95% CI 51 to 73) "
                   "extended to high-grade papillary-only tumors on review of available scientific information."),
        "announcement_url": EX, "announcement": "ImmunityBio 8-K exhibit 99.1, October 14, 2026",
    })
    print("  ~ pdufa_ibrx_2027-01-06: Decided / Approved 2026-10-14 (84 days before 2027-01-06)")

# ---- 2. Enspryng MOGAD goal date
if not any(x["id"] == "pdufa_rhhby_2027-01-10" for x in rows):
    rows.append({
        "id": "pdufa_rhhby_2027-01-10", "t": "RHHBY", "company": "Roche Holding AG", "d": "2027-01-10", "dp": "day",
        "name": "Enspryng (satralizumab) - MOGAD (METEOROID)", "type": "PDUFA", "ta": "Neurology", "cap": "Large",
        "st": "Upcoming", "ua": NOW,
        "_d": {"nct_id": None,
               "indication": "Myelin oligodendrocyte glycoprotein antibody-associated disease (MOGAD)",
               "source": "Genentech press release 2026-09-09", "source_url": MOGAD,
               "source_quote": "The FDA is expected to make a decision on approval in MOGAD by January 10, 2027.",
               "brand": "Enspryng", "inn": "satralizumab", "trial": "METEOROID",
               "event_slug": "RHHBY-enspryng-mogad",
               "source_note": "sBLA, Priority Review, per Genentech release of September 9, 2026."}})
    print("  + pdufa_rhhby_2027-01-10: Enspryng MOGAD goal date (Genentech 2026-09-09)")
rows.sort(key=lambda x: (str(x.get("d") or "9999"), str(x.get("t") or "")))
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])

# ---- side stores
c = jload("_drug_approvals_confirmed.json")
if not any(a.get("slug") == "anktiva" and a.get("date") == "2026-10-14" for a in c["approvals"]):
    c["approvals"].append({"slug": "anktiva", "date": "2026-10-14", "brand": "Anktiva", "source": FDA})
    jsave("_drug_approvals_confirmed.json", c)

faq = jload("_decision_extra_faq.json")
faq["IBRX-2026-10-14"] = [
    ["When did the FDA approve Anktiva for papillary-only bladder cancer?",
     "The FDA approved nogapendekin alfa inbakicept-pmln (Anktiva, ImmunityBio) with BCG on October 14, 2026 for "
     "adults with BCG-unresponsive non-muscle invasive bladder cancer, expanding the indication to include high-grade "
     "papillary-only tumors, per the FDA's approval notification of that date. ImmunityBio had given January 6, 2027 "
     "as the goal date, so the action came 84 days early."],
    ["What evidence supported the Anktiva papillary-only approval?",
     "Per the FDA, efficacy was previously shown in Cohort A of QUILT-3.032 (NCT03022825), 77 patients with "
     "BCG-unresponsive NMIBC with carcinoma in situ, with a complete response rate of 62% (95% CI 51 to 73). The FDA "
     "extended that result to high-grade papillary-only disease on review of the available scientific information, "
     "citing the overlapping clinical features of the two tumor types."]]
jsave("_decision_extra_faq.json", faq)

ack = jload("_fda_drugs_feed_ack.json")
k = "pdufa_ibrx_2027-01-06|" + FDA.replace("https://", "http://")
if k not in ack["acked"]:
    ack["acked"].append(k)
    ack["reasons"][k] = ("Verified 2026-10-15 and published: FDA approval notification of 2026-10-14 is the decision on the "
                         "tracked sBLA (papillary NMIBC without CIS, goal 2027-01-06, IBRX 8-K 2026-08-04). Row Decided / "
                         "Approved, /fda-decision/IBRX-2026-10-14.")
    jsave("_fda_drugs_feed_ack.json", ack)

# ---- 3. retired slugs
RETIRE = {
    "/fda-decision/BMY-2026-06-01": "/fda-decision/BMY-2026-09-30",
    "/fda-decision/SPRY-2026-05-15": "/fda-decision/SPRY-2026-03-27",
    "/fda-decision/NVCR-2026-02-12": "/fda-decision/NVCR-2026-02-11",
    "/fda-decision/EBS-2026-02-13": "/fda-decision/EBS-2026-02-12",
    "/fda-decision/JAGX-2026-04-29": "/drug/canalevia-ca1",
    "/fda-decision/LGND-2026-06-08": "/drug/miplyffa",
    "/fda-decision/XOMA-2026-06-08": "/drug/miplyffa",
    "/fda-decision/ZVRA-2026-06-08": "/drug/miplyffa",
    "/fda-decision/PGEN-2026-05-27": "/drug/papzimeos",
}
vp = os.path.join(SITE, "vercel.json")
v = json.load(io.open(vp, encoding="utf-8"))
have = {x["source"] for x in v.get("redirects", [])}
for s, dst in RETIRE.items():
    if s not in have:
        v["redirects"].append({"source": s, "destination": dst, "permanent": True})
io.open(vp, "w", encoding="utf-8").write(json.dumps(v, indent=1, ensure_ascii=False) + "\n")

ev = jload("_chart2026_events.json")
gone = {(s.split("/")[-1].rsplit("-", 3)[0], "-".join(s.split("/")[-1].rsplit("-", 3)[1:])) for s in RETIRE}
fix = {("BMY", "2026-06-01"): "2026-09-30", ("SPRY", "2026-05-15"): "2026-03-27", ("NVCR", "2026-02-12"): "2026-02-11",
       ("EBS", "2026-02-13"): "2026-02-12"}
out = []
for e in ev:
    key = (e.get("ticker"), e.get("date"))
    if key in fix:
        e["date"] = fix[key]
        out.append(e)
    elif key in gone:
        continue
    else:
        out.append(e)
io.open(os.path.join(HERE, "_chart2026_events.json"), "w", encoding="utf-8").write(json.dumps(out, indent=0, ensure_ascii=False))

arch = jload("_fda_action_archive.json")
for s in RETIRE:
    arch.pop(s.split("/")[-1], None)
jsave("_fda_action_archive.json", arch)
print(f"  redirects {len(RETIRE)}; chart events {len(ev)} -> {len(out)}; archive entries pruned")

# ---- 4. slate (api/data.js): the MOGAD goal date on the calendar's other source (test_calendar_two_sources)
DATAJS = os.path.join(SITE, "api", "data.js")
s_ = io.open(DATAJS, encoding="utf-8").read()
k = s_.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(s_[k:])
if not any(c.get("ticker") == "RHHBY" and c.get("date") == "2027-01-10" for c in slate["catalysts"]):
    ref = next((c for c in slate["catalysts"] if c.get("ticker") == "RHHBY"), {})
    t_minus = (dt.date(2027, 1, 10) - dt.date.today()).days
    slate["catalysts"].append({"ticker": "RHHBY", "name": "Roche/Genentech", "date": "2027-01-10", "t_minus": t_minus,
                               "drug": "Enspryng (satralizumab) - MOGAD (METEOROID)",
                               "indication": "Myelin oligodendrocyte glycoprotein antibody-associated disease (MOGAD)",
                               "price": ref.get("price"), "mcap": ref.get("mcap"), "cap": "Large", "adv": ref.get("adv"),
                               "cash_months": None})
    slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
    io.open(DATAJS, "w", encoding="utf-8").write(s_[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":")) + s_[k + end:])
    print("  + api/data.js SLATE: RHHBY 2027-01-10 Enspryng MOGAD")

# ---- 5. /decisions/approvals (a hand-maintained Feb to Jul 2026 list): repoint the three re-dated approvals that
# fall in its range, drop Camzyos (approved Sept 30, outside the page) and the five rows that were not approvals.
import re as _re
AP = os.path.join(SITE, "decisions", "approvals", "index.html")
doc = io.open(AP, encoding="utf-8", errors="replace").read()
o = doc
MOVE = {"SPRY-2026-05-15": "SPRY-2026-03-27", "NVCR-2026-02-12": "NVCR-2026-02-11", "EBS-2026-02-13": "EBS-2026-02-12"}
for old, new in MOVE.items():
    tk, od, nd = old.split("-", 1)[0], old.split("-", 1)[1], new.split("-", 1)[1]
    doc = doc.replace(f'href="/fda-decision/{old}"><div class="t">{tk} · {od} ',
                      f'href="/fda-decision/{new}"><div class="t">{tk} · {nd} ')
for gone in ("BMY-2026-06-01", "JAGX-2026-04-29", "LGND-2026-06-08", "XOMA-2026-06-08", "ZVRA-2026-06-08", "PGEN-2026-05-27"):
    doc = _re.sub(r'<a class="row" href="/fda-decision/' + gone + r'">.*?</a>', "", doc, count=1, flags=_re.S)
if doc != o:
    io.open(AP, "w", encoding="utf-8").write(doc)
left = [g for g in list(MOVE) + ["BMY-2026-06-01", "JAGX-2026-04-29", "LGND-2026-06-08", "XOMA-2026-06-08",
                                  "ZVRA-2026-06-08", "PGEN-2026-05-27"] if f"/fda-decision/{g}" in doc]
print(f"  /decisions/approvals: 3 rows repointed, 6 removed; retired slugs still linked: {left or 'none'}")
