# -*- coding: utf-8 -*-
"""apply_1113_gazyva_pmn.py -- Gazyva (obinutuzumab) approved for primary membranous nephropathy; three leads triaged.

Read 2026-11-13 (Pacific evening) from the FDA's own page, "FDA Approves First Drug to Treat Adults with Primary
Membranous Nephropathy" (published Fri 11/13/2026 17:33): "The U.S. Food and Drug Administration has approved Gazyva
(obinutuzumab) injection to treat adults with primary membranous nephropathy at risk of disease progression, to induce
remission of proteinuria". The page is the FDA's notice; it states no action day of its own, so the row carries the
notice day and `decision_date_unsourced` until Drugs@FDA posts the supplement. The goal was guided to November 2026
(month precision): no early/late margin.
Acked: #82 (the same notice matched our Gazyva SLE row, goal Dec 2026: a different sBLA); #79 (the FDA republished its
April 13, 2021 Trodelvy urothelial notice, withdrawn Nov 22, 2024, with a Nov 12, 2026 pubDate; matched MRK's
sacituzumab tirumotecan row on "sacituzumab"). Facts only, not investment advice.
"""
import datetime as dt, io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
FDA = "https://www.fda.gov/drugs/news-events-human-drugs/fda-approves-first-drug-treat-adults-primary-membranous-nephropathy"
TRO = "http://www.fda.gov/drugs/cancer-approvals/fda-grants-accelerated-approval-sacituzumab-govitecan-advanced-urothelial-cancer"
FDAL = "http://www.fda.gov/drugs/news-events-human-drugs/fda-approves-first-drug-treat-adults-primary-membranous-nephropathy"
P = os.path.join(SITE, "api", "v1", "dataset.mjs")
s = io.open(P, encoding="utf-8").read(); i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
for r in rows:
    if r["id"] == "pdufa_rhhby_2026-11-30_pmn" and r.get("st") != "Decided":
        r.update({"st": "Decided", "oc": "Approved", "dcd": "2026-11-13", "url": "/fda-decision/RHHBY-2026-11-13", "ua": NOW})
        r["_d"].update({
            "decision_date_unsourced": True, "inn": "obinutuzumab", "trial": "MAJESTY",
            "indication_short": "primary membranous nephropathy", "title_indication": "Primary Membranous Nephropathy",
            "decision_source": "FDA notice, November 13, 2026", "decision_source_url": FDA,
            "announcement": "FDA notice, November 13, 2026", "announcement_url": FDA,
            "decision_quote": ("The U.S. Food and Drug Administration has approved Gazyva (obinutuzumab) injection to treat "
                               "adults with primary membranous nephropathy at risk of disease progression, to induce "
                               "remission of proteinuria"),
            "decision_note": ("The FDA's notice is dated November 13, 2026 and does not state the action day; the day will "
                              "be taken from Drugs@FDA when the supplement posts. The goal was guided only to November 2026, "
                              "so no early or late margin is stated."),
            "seo_desc": ("Gazyva (obinutuzumab) was approved by the FDA for adults with primary membranous nephropathy, "
                         "per the FDA's notice of November 13, 2026, the first drug for the disease.")})
io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])

import price_source as ps, build_decision_page as bdp  # noqa: E402
PX = os.path.join(HERE, "_chart_pxcache.json"); px = json.load(open(PX))
for d, c, _ in ps.daily("RHHBY", "2026-03-01", "2026-11-13"):
    px.setdefault("RHHBY", {}).setdefault(d, c)
json.dump(px, open(PX, "w"))
bdp.build({"ticker": "RHHBY", "date": "2026-11-13", "outcome": "Approved", "drug": "Gazyva (obinutuzumab)",
           "indication": "Primary membranous nephropathy at risk of disease progression, to induce remission of proteinuria (adults)",
           "company": "Roche Holding AG (Genentech)", "cap": "Large",
           "headline": ("The FDA approved Gazyva (obinutuzumab) for adults with primary membranous nephropathy at risk of "
                        "disease progression, to induce remission of proteinuria, per its notice of November 13, 2026: the "
                        "first drug approved specifically for the disease."),
           "pdufa_note": ("Genentech guided the decision to November 2026 (Priority Review, July 14, 2026), so no early or late "
                          "margin is stated. Per the FDA: in MAJESTY (142 adults, Gazyva versus tacrolimus), complete "
                          "remission at week 104 was 36% versus 6%. Gazyva carries a boxed warning for hepatitis B "
                          "reactivation and PML."),
           "source": FDA, "source_label": "FDA notice, November 13, 2026"}, px)

def jl(p, d):
    p = os.path.join(HERE, p); return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else d
ff = jl("_fda_drugs_feed_ack.json", {"acked": [], "reasons": {}})
for k, why in ((f"pdufa_rhhby_2026-11-30_pmn|{FDAL}", "Published 2026-11-13: /fda-decision/RHHBY-2026-11-13."),
               (f"pdufa_rhhby_2026-12-31_sle|{FDAL}", "The pMN approval notice; our SLE row is a different sBLA (goal Dec 2026)."),
               (f"pdufa_mrk_2027-06-15|{TRO}", "Republished April 13, 2021 Trodelvy urothelial notice (withdrawn Nov 22, 2024) "
                                               "with a Nov 12, 2026 pubDate; not MRK's sacituzumab tirumotecan.")):
    if k not in ff["acked"]:
        ff["acked"].append(k)
    ff.setdefault("reasons", {})[k] = why
io.open(os.path.join(HERE, "_fda_drugs_feed_ack.json"), "w", encoding="utf-8").write(json.dumps(ff, indent=1, ensure_ascii=False) + "\n")
print("Gazyva pMN published; 3 feed leads acked")
