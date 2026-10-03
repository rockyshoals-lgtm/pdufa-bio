# -*- coding: utf-8 -*-
"""CI guard: the watcher matcher rules of audit 2026-10-03 (Tier 1.3), replayed on the real leads.

Between 2026-09-28 and 2026-10-03 three FALSE leads and one real one blocked 17 consecutive CI runs:

  AGIO     PYRUKYND SUPPL-7 approved 2026-09-28, class "MANUF (CMC)"   -> false (rule b)
  RHHBY    ANDA 220597, Novitium generic everolimus, 2026-09-21          -> false (rules a + c)
  RHHBY    FDA "FDA Approves First Treatment for MCT8 Deficiency" (Emcitate/tiratricol) matched
           Enspryng's thyroid eye disease filing on the lone word "thyroid" -> false (rule d)
  ABBV     "U.S. FDA Approves AbbVie's JUVMO(TM) (tavapadon) for Parkinson's Disease" -> REAL

Rules: (a) an ANDA never matches an NDA/BLA event; (b) MANUF/CMC/labeling-class supplements never
match; (c) on a combination row only the investigational drug is a match term; (d) a disease match
needs the indication phrase or two specific tokens, never a lone organ word.
Acceptance: the three false leads produce 0 leads; JUVMO still produces 1 (both feeds).

    python tests/test_matcher_rules_replay.py
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import watch_fda_approvals as A      # noqa: E402
import watch_sponsor_newswire as W   # noqa: E402
import watch_fda_drugs_feed as F     # noqa: E402

# rows as they stood when the leads fired (names verbatim from the dataset)
ENSPRYNG = {"id": "pdufa_rhhby_2026-10-15", "t": "RHHBY", "type": "PDUFA", "st": "Upcoming", "d": "2026-10-15",
            "name": "Enspryng (satralizumab) - (thyroid eye disease)", "_d": {"indication": "Thyroid eye disease (TED)"}}
GIRED = {"id": "pdufa_rhhby_2026-12-18", "t": "RHHBY", "type": "PDUFA", "st": "Upcoming", "d": "2026-12-18",
         "name": "Giredestrant (+ everolimus)", "_d": {"indication": "ER+/HER2-, ESR1-mutated metastatic breast cancer"}}
AGIO = {"id": "pdufa_agio_2026-11-01", "t": "AGIO", "type": "PDUFA", "st": "Upcoming", "d": "2026-11-01",
        "name": "Mitapivat (PYRUKYND) - (RISE UP)", "_d": {"indication": "Sickle cell disease (sNDA)"}}
ABBV = {"id": "pdufa_abbv_2026-12-31", "t": "ABBV", "type": "PDUFA", "st": "Upcoming", "d": "2026-12-31",
        "name": "Tavapadon (TEMPO)", "_d": {"indication": "Early Parkinson's disease"}}
ROWS = [ENSPRYNG, GIRED, AGIO, ABBV]

MCT8 = """<rss><channel><item><title>FDA Approves First Treatment for MCT8 Deficiency</title>
<link>http://www.fda.gov/news-events/press-announcements/fda-approves-first-treatment-mct8-deficiency</link>
<description>The U.S. Food and Drug Administration today approved Emcitate (tiratricol) tablets for oral suspension to
treat peripheral thyrotoxicosis (excess thyroid hormone levels in the blood that causes symptoms, such as rapid heart
rate, increased blood pressure and adverse effects on metabolism) in patients with MCT8 deficiency</description>
<pubDate>Mon, 28 Sep 2026 17:43:00 EDT</pubDate></item></channel></rss>"""
JUVMO_HEAD = "U.S. FDA Approves AbbVie's JUVMO™ (tavapadon) for Parkinson's Disease"
JUVMO_BODY = ("AbbVie today announced that the U.S. Food and Drug Administration (FDA) has approved JUVMO "
              "(tavapadon) tablets as the first and only selective D1/D5 receptor agonist for the treatment of "
              "adults with Parkinson's disease")


def main():
    fails = []
    # rule (b): the AGIO CMC supplement
    if A.is_decision_submission("NDA216196", {"submission_status": "AP", "submission_class_code": "MANUF (CMC)",
                                              "submission_type": "SUPPL", "submission_number": "7"}):
        fails.append("AGIO PYRUKYND SUPPL-7 MANUF (CMC) still counts as a decision (rule b)")
    for cls in ("LABELING", "REMS", "MANUF (CMC)"):
        if A.is_decision_submission("NDA1", {"submission_status": "AP", "submission_class_code": cls}):
            fails.append(f"class {cls} counts as a decision (rule b)")
    # rule (a): the Novitium generic
    if A.is_decision_submission("ANDA220597", {"submission_status": "AP", "submission_class_code": "UNKNOWN",
                                               "submission_type": "ORIG", "submission_number": "1"}):
        fails.append("ANDA 220597 (generic everolimus) counts as a decision on an NDA event (rule a)")
    # rule (c): the combination partner is not queried or matched
    if any(t.lower() == "everolimus" for t in A.search_terms(GIRED["name"])):
        fails.append(f"Drugs@FDA pass queries the combination partner: {A.search_terms(GIRED['name'])} (rule c)")
    if any(t.lower() == "everolimus" for t in W.terms_for(GIRED)):
        fails.append(f"feed matcher matches the combination partner: {W.terms_for(GIRED)} (rule c)")
    # rule (d): the MCT8 notice
    leads, _ = F.leads_from(MCT8, ROWS)
    if leads:
        fails.append("MCT8-deficiency notice still raises " + ", ".join(f"{r['id']} [{t}]" for r, t, _, _ in leads)
                     + " (rule d)")
    for r in ROWS:
        bad = [t for t in W.terms_for(r) if t.lower() in W.ORGAN_WORDS]
        if bad:
            fails.append(f"{r['id']} carries lone organ-word terms {bad} (rule d)")
    # the real one still fires: Drugs@FDA record and the sponsor headline
    if not A.is_decision_submission("NDA220415", {"submission_status": "AP", "submission_class_code": "TYPE 1",
                                                  "submission_type": "ORIG", "submission_number": "1"}):
        fails.append("JUVMO NDA 220415 ORIG-1 (TYPE 1) no longer counts as a decision")
    hits = W.match(JUVMO_HEAD + "\n" + JUVMO_BODY, [ABBV])
    if len(hits) != 1:
        fails.append(f"JUVMO sponsor headline produced {len(hits)} lead(s), expected 1")
    if fails:
        print(f"FAIL: {len(fails)} matcher-rule violation(s):")
        for f in fails:
            print("   " + f)
        return 1
    print("OK -- 3 false leads replay to 0 (CMC supplement, generic ANDA, lone 'thyroid'); JUVMO still 1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
