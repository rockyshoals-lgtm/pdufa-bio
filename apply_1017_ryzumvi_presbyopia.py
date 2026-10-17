# -*- coding: utf-8 -*-
"""apply_1017_ryzumvi_presbyopia.py -- phentolamine ophthalmic solution 0.75% (RYZUMVI) approved for presbyopia.

Resolves the two held leads of 2026-10-16T16:13:56Z (UTC): [sponsor_feed] pdufa_ird_2026-10-17 and [drug_pages]
phentolamine-ophthalmic. Verified 2026-10-17 04:20 UTC (00:20 Eastern), primary sources only:
  Opus Genetics release on ir.opusgtx.com, "October 16, 2026 12:00pm EDT": Opus "today announced that the U.S. Food
    and Drug Administration (FDA) has approved the Company's supplemental New Drug Application (sNDA) for phentolamine
    ophthalmic solution 0.75% for the treatment of presbyopia in adults." Marketed as RYZUMVI (NDA 217064, approved
    2023 for pharmacologically induced mydriasis); Viatris holds exclusive U.S. commercial rights. VEGA-2 and VEGA-3.
  Goal date: Opus release of 2026-02-25, "The FDA has assigned a PDUFA goal date of October 17, 2026." (The IRD row
    cited a BioSpace copy; replaced by the sponsor's own page.) Viatris 8-K of 2026-02-26 states the same sNDA.
  FDA action day: NOT on record. openFDA (last_updated 2026-10-16) shows no new NDA 217064 supplement; no FDA feed item.
    So dcd 2026-10-16 (announcement), decision_date_unsourced, no early/late margin, out of the timing statistic until
    Drugs@FDA posts the letter (sync_fda_action_dates.py swaps it in).
Two partner rows, two decision pages (the INCY/MIRM Atebrioz convention). Facts only; not investment advice.
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
REL = ("https://ir.opusgtx.com/press-releases/detail/546/opus-genetics-announces-fda-approval-of-phentolamine-"
       "ophthalmic-solution-0-75-for-the-treatment-of-presbyopia")
GOAL = ("https://ir.opusgtx.com/press-releases/detail/519/opus-genetics-announces-fda-acceptance-of-supplemental-new-"
        "drug-application-for-phentolamine-ophthalmic-solution-0-75-for-the-treatment-of-presbyopia")
QUOTE = ("Opus Genetics ... today announced that the U.S. Food and Drug Administration (FDA) has approved the "
         "Company's supplemental New Drug Application (sNDA) for phentolamine ophthalmic solution 0.75% for the "
         "treatment of presbyopia in adults.")
NOTE = ("2026-10-16 is the date of Opus Genetics' release, which \"today announced\" that the FDA \"has approved\" the "
        "sNDA; it does not state the day the FDA acted, and Drugs@FDA had not posted the supplement letter for NDA "
        "217064 when this was published. No early or late margin against the October 17 goal date is published until "
        "an FDA record states the action day.")


def jload(p):
    return json.load(io.open(os.path.join(HERE, p), encoding="utf-8"))


def jsave(p, d):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
for rid, tk in (("pdufa_ird_2026-10-17", "IRD"), ("pdufa_vtrs_2026-10-17", "VTRS")):
    r = next(x for x in rows if x["id"] == rid)
    if r.get("st") == "Decided":
        continue
    r.update({"st": "Decided", "oc": "Approved", "dcd": "2026-10-16", "url": f"/fda-decision/{tk}-2026-10-16",
              "ua": NOW, "ta": "Ophthalmology"})
    d = r.setdefault("_d", {})
    d.update({
        "brand": "RYZUMVI", "inn": "phentolamine", "trial": "VEGA-2, VEGA-3",
        "indication": "Presbyopia in adults (sNDA; RYZUMVI was already approved for pharmacologically induced mydriasis)",
        "indication_short": "presbyopia in adults",
        "title_indication": "Presbyopia",
        "seo_desc": "Opus Genetics announced Oct 16, 2026 that the FDA approved RYZUMVI (phentolamine 0.75%) for presbyopia, based on VEGA-2 and -3; Viatris holds U.S. rights.",
        "decision_source": "Opus Genetics press release, October 16, 2026", "decision_source_url": REL,
        "announcement_url": REL, "announcement": "Opus Genetics press release, October 16, 2026",
        "decision_quote": QUOTE, "decision_date_unsourced": True, "decision_date_note": NOTE,
        "review": ("Supplemental NDA 217064 (RYZUMVI, approved 2023 for pharmacologically induced mydriasis), presbyopia "
                   "in adults, supported by the Phase 3 VEGA-2 and VEGA-3 trials, which per Opus met their primary and "
                   "all key secondary endpoints. Viatris holds exclusive U.S. commercial rights."),
    })
    if tk == "IRD":
        d.update({"source": "Opus Genetics press release 2026-02-25", "source_url": GOAL,
                  "source_quote": "The FDA has assigned a PDUFA goal date of October 17, 2026."})
    print(f"  ~ {rid}: Decided / Approved, announced 2026-10-16 (FDA action day not on record)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])

c = jload("_drug_approvals_confirmed.json")
if not any(a.get("slug") == "phentolamine-ophthalmic" and a.get("date") == "2026-10-16" for a in c["approvals"]):
    c["approvals"].append({"slug": "phentolamine-ophthalmic", "date": "2026-10-16", "brand": "RYZUMVI", "source": REL})
    jsave("_drug_approvals_confirmed.json", c)

faq = jload("_decision_extra_faq.json")
qa = [["Was phentolamine eye drop (RYZUMVI) approved for presbyopia?",
       "Yes. Opus Genetics announced on October 16, 2026 that the FDA approved its supplemental application for "
       "phentolamine ophthalmic solution 0.75%, marketed as RYZUMVI, for the treatment of presbyopia in adults. The "
       "goal date was October 17, 2026. pdufa.bio holds no FDA record of the action day yet; the FDA's letter had not "
       "been posted on Drugs@FDA when this page was published."],
      ["Who sells RYZUMVI for presbyopia in the U.S.?",
       "Per Opus Genetics, Viatris holds exclusive rights to commercialize phentolamine ophthalmic solution 0.75% in "
       "the United States under a global licensing agreement, and the approval triggers a milestone payment to Opus."],
      ["What trials supported the presbyopia approval?",
       "The Phase 3 VEGA-2 and VEGA-3 trials, both of which met their primary and all key secondary efficacy endpoints "
       "with no treatment-related serious adverse events reported, according to Opus Genetics."]]
faq["IRD-2026-10-16"] = qa
faq["VTRS-2026-10-16"] = qa
jsave("_decision_extra_faq.json", faq)

ack = jload("_newswire_ack.json")
k = "pdufa_ird_2026-10-17|" + REL
if k not in ack["acked"]:
    ack["acked"].append(k)
    ack["reasons"][k] = ("REAL: published 2026-10-17 as /fda-decision/IRD-2026-10-16 and /fda-decision/VTRS-2026-10-16 "
                         "(announced 2026-10-16; FDA action day not yet on Drugs@FDA).")
    jsave("_newswire_ack.json", ack)
da = jload("_drug_watch_ack.json")
if not any(x.get("slug") == "phentolamine-ophthalmic" and x.get("source") == "sponsor:IRD:2026-10-16" for x in da["acks"]):
    da["acks"].append({"slug": "phentolamine-ophthalmic", "source": "sponsor:IRD:2026-10-16",
                       "reason": ("REAL: presbyopia sNDA approved, announced by Opus Genetics 2026-10-16; published as "
                                  "/fda-decision/IRD-2026-10-16 and recorded in _drug_approvals_confirmed.json."),
                       "acked": "2026-10-17"})
    jsave("_drug_watch_ack.json", da)
print("  side stores: approvals_confirmed, FAQ x2, newswire ack, drug-watch ack")
