# -*- coding: utf-8 -*-
"""apply_1016_enspryng_ted.py -- Enspryng (satralizumab-mwge) approved for thyroid eye disease, announced 2026-10-15.

Audit 2026-10-16 P0. Verified 2026-10-16 07:30 UTC (03:30 Eastern), primary sources only:
  Genentech release on gene.com, dateline "South San Francisco, CA -- October 15, 2026":
    https://www.gene.com/media/press-releases/15137/2026-10-15/fda-approves-genentechs-enspryng-a-first
    "Genentech ... announced today that the U.S. Food and Drug Administration (FDA) has approved Enspryng
     (satralizumab-mwge) for the treatment of adults with thyroid eye disease (TED)". SatraGO-2: proptosis response
     52.9% vs 23.4% placebo, diplopia reduction 60.7% vs 25.8% (active TED); SatraGO-1 missed its primary endpoint at
     week 24. Priority review; second indication after NMOSD (2020).
  Goal date: Genentech release of 2026-06-29, "The FDA is expected to make a decision on approval by October 15, 2026."
  FDA action day: NOT on record. openFDA drugsfda (last_updated 2026-10-14) shows no new BLA 761149 supplement; the
    FDA press and drugs feeds carry no notice. The release says "announced today ... has approved", which does not
    state the day the FDA acted. So: dcd 2026-10-15 (announcement), decision_date_unsourced, no fda_action_date, no
    early/late margin, out of the timing statistic until Drugs@FDA posts the letter (sync_fda_action_dates.py
    swaps it in and re-admits the row).
  Watcher: the 01:55 UTC run (21:55 Eastern, Oct 15) read the gene.com listing and raised nothing; the same parser
    finds the release at the top of the listing at 07:25 UTC. It reached the listing after that run.
Facts only; not investment advice.
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
REL = "https://www.gene.com/media/press-releases/15137/2026-10-15/fda-approves-genentechs-enspryng-a-first"
GOAL = "https://www.gene.com/media/press-releases/15118/2026-06-29/fda-grants-priority-review-to-genentechs"


def jload(p):
    return json.load(io.open(os.path.join(HERE, p), encoding="utf-8"))


def jsave(p, d):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
r = next(x for x in rows if x["id"] == "pdufa_rhhby_2026-10-15")
if r.get("st") != "Decided":
    r.update({"st": "Decided", "oc": "Approved", "dcd": "2026-10-15", "url": "/fda-decision/RHHBY-2026-10-15",
              "ua": NOW, "name": "Enspryng (satralizumab) - thyroid eye disease", "ta": "Ophthalmology"})
    d = r.setdefault("_d", {})
    d.update({
        "brand": "Enspryng", "inn": "satralizumab-mwge", "event_slug": "RHHBY-enspryng",
        "trial": "SatraGO-1, SatraGO-2", "nct_id": "NCT06106828",
        "indication": "Adults with thyroid eye disease (TED)",
        "indication_short": "adults with thyroid eye disease (TED)",
        "title_indication": "Thyroid Eye Disease",
        "seo_desc": ("Genentech announced on October 15, 2026 that the FDA approved Enspryng (satralizumab-mwge) for "
                     "adults with thyroid eye disease, the first subcutaneous TED treatment, based on SatraGO-1 and -2."),
        "decision_source": "Genentech press release, October 15, 2026", "decision_source_url": REL,
        "announcement_url": REL, "announcement": "Genentech press release, October 15, 2026",
        "decision_quote": ("Genentech, a member of the Roche Group (SIX: RO, ROP; OTCQX: RHHBY), announced today that the "
                           "U.S. Food and Drug Administration (FDA) has approved Enspryng (satralizumab-mwge) for the "
                           "treatment of adults with thyroid eye disease (TED)"),
        "decision_date_unsourced": True,
        "decision_date_note": ("2026-10-15 is the date of Genentech's release, which \"announced today\" that the FDA "
                               "\"has approved\" Enspryng; it does not state the day the FDA acted, and Drugs@FDA had "
                               "not posted the supplement letter for BLA 761149 when this was published. No early or "
                               "late margin against the October 15 goal date is published until an FDA record states "
                               "the action day."),
        "review": ("Supplemental BLA 761149, priority review. SatraGO-1 (NCT05987423) and SatraGO-2 (NCT06106828), "
                   "identically designed Phase III placebo-controlled studies, 258 patients in 19 countries. Per "
                   "Genentech, SatraGO-1 did not meet its primary endpoint at week 24; SatraGO-2 showed a proptosis "
                   "response of 52.9% vs 23.4% on placebo and diplopia reduction of 60.7% vs 25.8% in active TED."),
    })
    print("  ~ pdufa_rhhby_2026-10-15: Decided / Approved, announced 2026-10-15 (FDA action day not on record)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])

c = jload("_drug_approvals_confirmed.json")
if not any(a.get("slug") == "enspryng" and a.get("date") == "2026-10-15" for a in c["approvals"]):
    c["approvals"].append({"slug": "enspryng", "date": "2026-10-15", "brand": "Enspryng", "source": REL})
    jsave("_drug_approvals_confirmed.json", c)

faq = jload("_decision_extra_faq.json")
faq["RHHBY-2026-10-15"] = [
    ["Was Enspryng approved for thyroid eye disease?",
     "Yes. Genentech announced on October 15, 2026 that the FDA approved Enspryng (satralizumab-mwge) for adults with "
     "thyroid eye disease (TED), its goal date. Genentech describes it as the first and only at-home subcutaneous "
     "treatment for TED. pdufa.bio holds no FDA record of the action day yet; the FDA's letter had not been posted on "
     "Drugs@FDA when this page was published."],
    ["What trials supported the Enspryng TED approval?",
     "The Phase III SatraGO-1 and SatraGO-2 studies, 258 patients in total. Per Genentech, SatraGO-1 did not meet its "
     "primary endpoint at week 24, while SatraGO-2 showed a proptosis response of 52.9% with Enspryng versus 23.4% on "
     "placebo and diplopia reduction of 60.7% versus 25.8% in patients with active TED."],
    ["Does Enspryng have another FDA decision pending?",
     "Yes. Genentech says the FDA is expected to decide on Enspryng for MOGAD (myelin oligodendrocyte glycoprotein "
     "antibody-associated disease) by January 10, 2027, under priority review."]]
jsave("_decision_extra_faq.json", faq)

ack = jload("_newswire_ack.json")
for k, why in (("pdufa_rhhby_2026-10-15|" + REL,
                "REAL: published 2026-10-16 as /fda-decision/RHHBY-2026-10-15 (announced 2026-10-15; FDA action day not yet on Drugs@FDA)."),
               ("pdufa_rhhby_2027-01-10|" + REL,
                "Not this row: the release is the TED approval (pdufa_rhhby_2026-10-15); MOGAD goal 2027-01-10 still pending.")):
    if k not in ack["acked"]:
        ack["acked"].append(k)
        ack["reasons"][k] = why
jsave("_newswire_ack.json", ack)
print("  side stores: approvals_confirmed, extra FAQ (3), newswire ack (2)")
