# -*- coding: utf-8 -*-
"""apply_1120_venglustat_approval.py -- Infilbray (venglustat) approved by the FDA on November 18, 2026.
Resolves the two drug-page watcher leads that have held rows since Nov 18 (issue 117 escalation, issues 141 and 116).

1. venglustat (issue 141): REAL. Verified 2026-11-20 ~08:20 UTC (00:20 PT, 03:20 ET; RULE 1), primary source read itself:
   FDA News Release, "FDA Approves First Drug to Treat Neurological Symptoms of Type 3 Gaucher Disease", For Immediate
   Release November 18, 2026: "The U.S. Food and Drug Administration today approved Infilbray (venglustat) tablets, the
   first treatment for the neurological symptoms of Type 3 Gaucher disease (GD3) in adults and pediatric patients
   weighing at least 15 kg". Randomized, double-blind, multicenter study of 43 patients aged 12+ with GD3 previously
   stabilized on enzyme replacement therapy (ERT); once-daily oral Infilbray vs IV ERT every two weeks for 52 weeks; at
   Week 52 improvement on a measure combining ataxia and cognitive assessments vs ERT. Orphan Drug designation and
   Priority Review. "The approval of Infilbray was granted to Genzyme Corporation, a Sanofi Company."
   We never held a PDUFA row for venglustat (only an estimated SNY readout row; no goal date on our calendar), so, as for
   daraxonrasib (RVMD, Aug 26), the decision is a hand row in _drug_pages_manual.json plus a decision page. The FDA
   names the day ("today", release dated Nov 18), so the action day is FDA-sourced. No goal date, no margin claimed.

2. vidofludimus-calcium (issue 116): FALSE POSITIVE. openFDA Drugs@FDA, AP 2026-10-19 ORIG-1 TYPE 2 is NDA219456
   CALREZDY (calcium chloride), Fresenius Medical Care, read on api.fda.gov 2026-11-20. It matched only on the salt word
   CALCIUM in our slug. Acked; salt words join the watcher's STOP list (watch_drug_approvals.py) so it cannot recur.

Facts only; not investment advice.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TODAY = "2026-11-18"
FDA = ("https://www.fda.gov/news-events/press-announcements/"
       "fda-approves-first-drug-treat-neurological-symptoms-type-3-gaucher-disease")
PAGE = "/fda-decision/SNY-2026-11-18"
# SNY ADR closes, FMP historical-price-eod-light, read 2026-11-20 ~08:25 UTC; Eastern trading days.
# 2026-10-16 (40.61) matches the close already cached, so the series joins cleanly.
SNY_CLOSES = {"2026-10-19": 39.57, "2026-10-20": 41.4, "2026-10-21": 40.97, "2026-10-22": 41.96, "2026-10-23": 41.6,
              "2026-10-26": 41.79, "2026-10-27": 41.89, "2026-10-28": 42.24, "2026-10-29": 43.13, "2026-10-30": 44.34,
              "2026-11-02": 45.55, "2026-11-03": 45.33, "2026-11-04": 47.47, "2026-11-05": 46.91, "2026-11-06": 47.04,
              "2026-11-09": 48.12, "2026-11-10": 48.23, "2026-11-11": 48.43, "2026-11-12": 48.46, "2026-11-13": 48.37,
              "2026-11-16": 48.39, "2026-11-17": 47.53, "2026-11-18": 47.12, "2026-11-19": 46.06}
INDICATION = ("Neurological manifestations of Type 3 Gaucher disease (GD3) in adults and pediatric patients weighing "
              "at least 15 kg")
REVIEW = ("Per the FDA, Infilbray (venglustat) tablets were approved on November 18, 2026 with Orphan Drug designation "
          "and Priority Review; the approval was granted to Genzyme Corporation, a Sanofi company. The study: 43 "
          "patients aged 12 and older with GD3, previously stabilized on enzyme replacement therapy, randomized to "
          "once-daily oral Infilbray or intravenous enzyme replacement therapy every two weeks for 52 weeks; at Week 52 "
          "Infilbray patients improved on a measure combining ataxia and cognitive assessments. No PDUFA goal date was "
          "publicly disclosed, so this application was never a dated event on our calendar.")


def jload(p, default=None):
    p = os.path.join(HERE, p)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else default


def jsave(p, d):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


# 1. hand row (the drug page merges it with dataset rows)
m = jload("_drug_pages_manual.json")
if not any(r.get("url") == PAGE for r in m["rows"]):
    m["rows"].append({
        "t": "SNY", "company": "Sanofi", "d": TODAY, "dp": "day", "type": "PDUFA", "st": "Decided",
        "name": "Venglustat", "url": PAGE,
        "_d": {"indication": INDICATION, "review": REVIEW, "brand": "Infilbray", "inn": "venglustat",
               "decision_source": "FDA News Release, November 18, 2026", "decision_source_url": FDA},
    })
    jsave("_drug_pages_manual.json", m)

# 2. render ledger: /drug/venglustat may never show "no FDA decision" again
c = jload("_drug_approvals_confirmed.json")
if not any(a.get("slug") == "venglustat" and a.get("date") == TODAY for a in c["approvals"]):
    c["approvals"].append({"slug": "venglustat", "date": TODAY, "brand": "Infilbray", "source": FDA})
    jsave("_drug_approvals_confirmed.json", c)

# 3. FAQ on the decision page
faq = jload("_decision_extra_faq.json", {})
faq["SNY-2026-11-18"] = [
    ["Was venglustat approved by the FDA?",
     "Yes. On November 18, 2026 the FDA approved Infilbray (venglustat) tablets for the neurological symptoms of Type 3 "
     "Gaucher disease in adults and pediatric patients weighing at least 15 kg, per the FDA's own news release. The "
     "FDA calls it the first treatment for the neurological symptoms of Type 3 Gaucher disease. The approval was "
     "granted to Genzyme Corporation, a Sanofi company."],
    ["What study supported the Infilbray approval?",
     "Per the FDA, a randomized, double-blind study of 43 patients aged 12 and older with Type 3 Gaucher disease who had "
     "been stabilized on enzyme replacement therapy. Patients took Infilbray once daily by mouth or continued "
     "intravenous enzyme replacement therapy every two weeks for 52 weeks; at Week 52 the Infilbray group improved on a "
     "measure combining ataxia and cognitive assessments."],
    ["Did venglustat have a PDUFA date?",
     "No goal date was publicly disclosed, so it was not a dated event on our calendar. The FDA's release says the "
     "application had Priority Review and Orphan Drug designation."]]
jsave("_decision_extra_faq.json", faq)

# 4. decision page spec (built by build_decision_page.py)
A = 'rel="noopener" style="color:#e3ba5e"'
spec = [{
    "ticker": "SNY", "date": TODAY, "fda_action_date": TODAY, "outcome": "Approved",
    "drug": "Infilbray (venglustat)",
    "indication": INDICATION,
    "company": "Sanofi", "cap": "Large",
    "headline": ("The FDA approved Infilbray (venglustat) tablets on November 18, 2026, the first treatment for the "
                 "neurological symptoms of Type 3 Gaucher disease, in adults and children weighing at least 15 kg."),
    "pdufa_note": (f'The FDA\'s news release states that on November 18, 2026 it approved Infilbray (venglustat) '
                   f'tablets for the neurological symptoms of Type 3 Gaucher disease (GD3) in adults and pediatric '
                   f'patients weighing at least 15 kg, and that the approval was granted to Genzyme Corporation, a '
                   f'Sanofi company (<a href="{FDA}" {A}>FDA, November 18, 2026</a>). Per the FDA, a randomized, '
                   f'double-blind, multicenter study enrolled 43 patients aged 12 and older with GD3 who had been '
                   f'stabilized on enzyme replacement therapy; patients took Infilbray once daily by mouth or '
                   f'intravenous enzyme replacement therapy every two weeks for 52 weeks, and at Week 52 the Infilbray '
                   f'group improved on a measure combining ataxia and cognitive assessments. The FDA lists '
                   f'gastrointestinal symptoms and mood effects as the most frequent side effects and reports serious '
                   f'psychiatric risks including suicidal ideation and behavior. The application had Orphan Drug '
                   f'designation and Priority Review. No PDUFA goal date was publicly disclosed, so this application '
                   f'was never a dated event on our calendar.'),
    "source": FDA, "source_label": "FDA News Release, November 18, 2026",
    "h1": ('Infilbray (venglustat) <span class="g">FDA approval for Type 3 Gaucher disease</span>: Nov 18, 2026'),
}]
jsave("decision_pages_2026_11_18_sny.json", spec)

# 5. prices (real FMP closes, never overwritten) and the page
PX = os.path.join(HERE, "_chart_pxcache.json")
px = json.load(open(PX))
for dd, cl in SNY_CLOSES.items():
    px.setdefault("SNY", {}).setdefault(dd, cl)
json.dump(px, open(PX, "w"))
import build_decision_page as bdp  # noqa: E402
for e in spec:
    bdp.build(e, px)
print(f"  built {PAGE}")

# 6. watcher acks
dw = jload("_drug_watch_ack.json", {"acks": []})
ACKS = [
    ("venglustat", "fda-press:fda-approves-first-drug-treat-neurological-symptoms-type-3-g",
     "REAL: Infilbray (venglustat) approved Nov 18, 2026 per the FDA news release (read 2026-11-20); published as "
     "/fda-decision/SNY-2026-11-18 and recorded in _drug_approvals_confirmed.json."),
    ("vidofludimus-calcium", "openfda:20261019",
     "Not this drug: openFDA AP 2026-10-19 ORIG-1 is NDA219456 CALREZDY (calcium chloride), Fresenius Medical Care; "
     "matched only on the salt word CALCIUM. Vidofludimus calcium (IMUX) has no FDA action. Salt words now in STOP."),
]
for slug, src, why in ACKS:
    if not any(a.get("slug") == slug and a.get("source") == src for a in dw["acks"]):
        dw["acks"].append({"slug": slug, "source": src, "acked": "2026-11-20", "reason": why})
jsave("_drug_watch_ack.json", dw)
print("  acks: drug_watch (2); manual row, ledger, FAQ, page spec written")
