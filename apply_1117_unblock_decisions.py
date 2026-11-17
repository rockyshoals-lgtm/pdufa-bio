# -*- coding: utf-8 -*-
"""apply_1117_unblock_decisions.py -- the three Nov 14 goals and the evERA approval, recorded from primary sources.

Urgent order 2026-11-17 (BLOCKED #83). Read 2026-11-16 Pacific evening:
  * SMMT ivonescimab: Summit 8-K filed 2026-11-16, EX-99.1, release dated "Miami, Florida, November 15, 2026": the FDA
    "has issued a Complete Response Letter (CRL)". The release states no letter date: announcement day, unsourced FDA
    day, no margin, not in the census.
  * RHHBY giredestrant + everolimus (evERA): FDA oncology notification "On November 16, 2026, the Food and Drug
    Administration approved giredestrant (Wilserdly, Genentech, Inc.) ... in combination with everolimus", and "The FDA
    approved this application 4 weeks ahead of the FDA goal date". Goal 2026-12-18 is day-sourced (Genentech 2026-02-19).
  * CYTK aficamten MAPLE-HCM sNDA: Cytokinetics release Nov 16, 2026 (GlobeNewswire 04:00 ET): the FDA "has approved a
    supplemental New Drug Application (sNDA) updating the U.S. Prescribing Information for MYQORZO". No FDA day stated.
  * TEVA IGALMI at-home sNDA: Teva release Nov 16, 2026 8:00 AM: "today announced the U.S. Food and Drug Administration
    (FDA) approval of IGALMI (dexmedetomidine) sublingual film for at-home use". No FDA day stated.
The lidERA row (pdufa_rhhby_2026-11-30) is a different application and stays pending. Facts only, not investment advice.
"""
import datetime as dt, io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
SMMT = "https://www.sec.gov/Archives/edgar/data/1599298/000159929826000092/ivonescimabcrlscenariopr.htm"
GIR = "https://www.fda.gov/drugs/cancer-approvals/fda-approves-giredestrant-combination-everolimus-er-positive-her2-negative-esr1-mutated-locally"
CYTK = ("https://www.globenewswire.com/news-release/2026/11/16/3403219/35409/en/cytokinetics-announces-prescribing-information-"
        "for-myqorzo-aficamten-expanded-to-include-data-from-phase-3-maple-hcm.html")
TEVA = ("https://ir.tevapharm.com/news-and-events/press-releases/press-release-details/2026/U-S--FDA-Approves-IGALMI-as-First-"
        "At-Home-Acute-Treatment-for-Agitation-Associated-with-Schizophrenia-Schizoaffective-Disorder-or-Bipolar-I-or-II-"
        "Disorder-in-Adults/default.aspx")

D = {
 "pdufa_smmt_2026-11-14": dict(oc="CRL", dcd="2026-11-15", url="/fda-decision/SMMT-2026-11-15", unsrc=True,
     src="Summit Therapeutics 8-K filed 2026-11-16 (EX-99.1, release dated November 15, 2026)", su=SMMT,
     quote=("Summit Therapeutics Inc. (NASDAQ: SMMT) today announced that the U.S. Food and Drug Administration (FDA) has "
            "issued a Complete Response Letter (CRL) regarding the Biologics License Application (BLA) for ivonescimab in "
            "combination with platinum-containing chemotherapy"),
     note=("Per Summit: the FDA determined that substantial evidence of effectiveness is not established in the absence of a "
           "statistically significant overall survival improvement. The release does not state the letter's own date; the "
           "date shown is Summit's announcement, so no early or late margin is stated."),
     page=dict(ticker="SMMT", date="2026-11-15", outcome="CRL", drug="Ivonescimab",
               indication="With platinum chemotherapy, EGFR-mutated locally advanced or metastatic non-squamous NSCLC after an EGFR TKI (HARMONi)",
               company="Summit Therapeutics Inc.", cap="Large",
               headline=("Summit announced on November 15, 2026 that the FDA issued a Complete Response Letter on the BLA for "
                         "ivonescimab with platinum-containing chemotherapy in EGFR-mutated NSCLC after EGFR TKI therapy."),
               pdufa_note=("The PDUFA goal date was November 14, 2026 (Summit 8-K, January 29, 2026). Summit's release does "
                           "not state the letter's own date, so no margin is stated. Per Summit, the FDA found that "
                           "substantial evidence of effectiveness is not established without a statistically significant "
                           "overall survival improvement; HARMONi met its progression-free survival endpoint. A Complete "
                           "Response Letter means the FDA will not approve the application in its present form; the sponsor "
                           "can resubmit."),
               source=SMMT, source_label="Summit Therapeutics 8-K (EX-99.1), November 15, 2026")),
 "pdufa_rhhby_2026-12-18": dict(oc="Approved", dcd="2026-11-16", url="/fda-decision/RHHBY-2026-11-16", unsrc=False, fad="2026-11-16",
     src="FDA oncology approval notification, November 16, 2026", su=GIR, brand="Wilserdly", inn="giredestrant",
     quote=("On November 16, 2026, the Food and Drug Administration approved giredestrant (Wilserdly, Genentech, Inc.), an oral "
            "estrogen receptor antagonist, in combination with everolimus"),
     note="The FDA states it approved this application 4 weeks ahead of the FDA goal date (December 18, 2026).",
     page=dict(ticker="RHHBY", date="2026-11-16", outcome="Approved", drug="Wilserdly (giredestrant) + everolimus",
               indication="ER-positive, HER2-negative, ESR1-mutated locally advanced or metastatic breast cancer after endocrine therapy (evERA)",
               company="Roche Holding AG (Genentech)", cap="Large",
               headline=("The FDA approved Wilserdly (giredestrant) with everolimus on November 16, 2026 for adults with "
                         "ER-positive, HER2-negative, ESR1-mutated locally advanced or metastatic breast cancer whose disease "
                         "recurred or progressed on endocrine therapy."),
               pdufa_note=("The PDUFA goal date was December 18, 2026 (Genentech, February 19, 2026); the FDA approved on "
                           "November 16, 32 days early, and its notice says 4 weeks ahead of the goal. Per the FDA: in evERA "
                           "(ESR1-mutated population) the progression-free survival hazard ratio was 0.38; median PFS 10 versus "
                           "5.5 months. This is the evERA application; the separate lidERA (adjuvant) application has its own "
                           "November 30, 2026 goal and is still pending."),
               source=GIR, source_label="FDA oncology approval notification, November 16, 2026")),
 "pdufa_cytk_2026-11-14": dict(oc="Approved", dcd="2026-11-16", url="/fda-decision/CYTK-2026-11-16", unsrc=True,
     src="Cytokinetics press release, November 16, 2026 (GlobeNewswire)", su=CYTK, brand="MYQORZO", inn="aficamten",
     quote=("Cytokinetics, Incorporated (Nasdaq: CYTK) today announced that the U.S. Food and Drug Administration (FDA) has "
            "approved a supplemental New Drug Application (sNDA) updating the U.S. Prescribing Information for MYQORZO"),
     note=("Label update adding MAPLE-HCM (versus metoprolol); the indication is unchanged. Cytokinetics announced it on "
           "Monday November 16; the release does not state the FDA's action day, so no margin is stated."),
     page=dict(ticker="CYTK", date="2026-11-16", outcome="Approved", drug="MYQORZO (aficamten) MAPLE-HCM sNDA",
               indication="Symptomatic obstructive hypertrophic cardiomyopathy: label adds MAPLE-HCM data versus metoprolol",
               company="Cytokinetics Inc", cap="Mid",
               headline=("Cytokinetics announced on November 16, 2026 that the FDA approved its sNDA adding Phase 3 MAPLE-HCM "
                         "data (aficamten versus metoprolol) to the MYQORZO prescribing information; the indication is unchanged."),
               pdufa_note=("The PDUFA goal date was November 14, 2026 (a Saturday). Cytokinetics' release, dated Monday "
                           "November 16, does not state the FDA's action day, so no early or late margin is stated."),
               source=CYTK, source_label="Cytokinetics press release, November 16, 2026")),
 "pdufa_btai_2026-11-14": dict(oc="Approved", dcd="2026-11-16", url="/fda-decision/TEVA-2026-11-16", unsrc=True,
     src="Teva press release, November 16, 2026", su=TEVA, brand="IGALMI", inn="dexmedetomidine",
     quote=("Teva Pharmaceuticals ... today announced the U.S. Food and Drug Administration (FDA) approval of IGALMI "
            "(dexmedetomidine) sublingual film for at-home use"),
     note=("At-home use sNDA (submitted January 14, 2026 by BioXcel; Teva acquired IGALMI in late October 2026). Teva's "
           "release does not state the FDA's action day, so no margin is stated."),
     page=dict(ticker="TEVA", date="2026-11-16", outcome="Approved", drug="IGALMI (dexmedetomidine) at-home sNDA",
               indication="Acute agitation with schizophrenia, schizoaffective disorder or bipolar I/II disorder: at-home use (adults)",
               company="Teva Pharmaceutical Industries", cap="Large",
               headline=("Teva announced on November 16, 2026 that the FDA approved IGALMI (dexmedetomidine) sublingual film "
                         "for at-home use, the first at-home treatment for agitation associated with schizophrenia, "
                         "schizoaffective disorder or bipolar I or II disorder in adults."),
               pdufa_note=("The PDUFA goal date was November 14, 2026 (a Saturday; BioXcel 8-K, May 15, 2026). Teva's release "
                           "does not state the FDA's action day, so no margin is stated."),
               source=TEVA, source_label="Teva press release, November 16, 2026")),
}

P = os.path.join(SITE, "api", "v1", "dataset.mjs")
s = io.open(P, encoding="utf-8").read(); i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
for r in rows:
    x = D.get(r["id"])
    if not x or r.get("st") == "Decided":
        continue
    r.update({"st": "Decided", "oc": x["oc"], "dcd": x["dcd"], "url": x["url"], "ua": NOW})
    d = r.setdefault("_d", {})
    d.update({"decision_source": x["src"], "decision_source_url": x["su"], "announcement": x["src"],
              "announcement_url": x["su"], "decision_quote": x["quote"], "decision_note": x["note"]})
    if x.get("brand"):
        d["brand"] = x["brand"]
    if x.get("inn"):
        d["inn"] = x["inn"]
    if x["unsrc"]:
        d["decision_date_unsourced"] = True
    else:
        d.update({"fda_action_date": x["fad"], "fda_action_source_url": x["su"], "fda_action_record": x["src"]})
    print("decided:", r["id"], x["oc"], x["dcd"])
io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])

import price_source as ps, build_decision_page as bdp  # noqa: E402
PX = os.path.join(HERE, "_chart_pxcache.json"); px = json.load(open(PX))
for x in D.values():
    t = x["page"]["ticker"]
    for dd, c, _ in ps.daily(t, "2026-03-01", "2026-11-16"):
        px.setdefault(t, {}).setdefault(dd, c)
json.dump(px, open(PX, "w"))
for x in D.values():
    bdp.build(x["page"], px)

# acks
def jl(p, d):
    p = os.path.join(HERE, p); return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else d
def js(p, o):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(o, indent=1, ensure_ascii=False) + "\n")
print("held state keys:", [k for k in jl("_held_state.json", {}).get("issued_keys", [])][-12:])
