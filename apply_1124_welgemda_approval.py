# -*- coding: utf-8 -*-
"""apply_1124_welgemda_approval.py -- Welgemda (BBP-418, ribitol), LGMD2I/R9, approval announced by BridgeBio on
November 23, 2026. Row pdufa_bbio_2026-11-27 (goal date stated as a DAY, November 27, 2026).

Unblocks rebuild runs 45273798191 and 45289011118 (issue 190): tests/test_open_goal_not_in_fda_record.py matched the
open row to "FDA Novel Drug Approvals: Welgemda (ribitol) 2026-11-23", as the guard is meant to.

Verified 2026-11-24 ~01:25 UTC (2026-11-23 20:25 Eastern, 17:25 Pacific; RULE 1), primary source read itself:
  BridgeBio 8-K Exhibit 99.1 (SEC EDGAR), dateline "PALO ALTO, Calif., Nov. 23, 2026": BridgeBio "today announced that
    the FDA granted traditional (full) approval to Welgemda (BBP-418, ribitol)", indicated for limb-girdle muscular
    dystrophy type 2I/R9 (LGMD2I/R9) in adult and pediatric patients weighing at least 30 kg. Phase 3 FORTIFY: 100-meter
    timed test velocity benefit of 0.27 m/s vs placebo at 12 months (p<0.0001); FVC percent predicted benefit 4.89% at
    12 months (p=0.0071).
  FDA record: the FDA Novel Drug Approvals 2026 page read from this host showed content current as of 11/19/2026 with no
    Welgemda row; the rebuild's own read of that page (the guard output) lists Welgemda on 2026-11-23. Not read here by
    us, so this row carries NO fda_action_date: the page states the announcement day as the announcement day, and
    sync_fda_action_dates.py writes the FDA's own day when Drugs@FDA posts it. No early/late margin is published until
    then (a margin needs an FDA-sourced action day).
  Goal date: BridgeBio 8-K of 2026-08-10 (already on the row): BBP-418 "accepted with Priority Review (PDUFA November 27,
    2026)".
Facts only; not investment advice.
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
ANN = "2026-11-23"
RID = "pdufa_bbio_2026-11-27"
PAGE_URL = "/fda-decision/BBIO-2026-11-23"
REL = "https://www.sec.gov/Archives/edgar/data/1743881/000174388126000050/bbiowelgemdapdufa-ex991.htm"
GOAL = "https://www.sec.gov/Archives/edgar/data/1743881/000174388126000026/bbio-20260630xex991.htm"
QUOTE = ("BridgeBio Pharma, Inc. (Nasdaq: BBIO) today announced that the FDA granted traditional (full) approval to "
         "Welgemda (BBP-418, ribitol)")
# BBIO closes, FMP historical-price-eod-light, read 2026-11-24 ~01:25 UTC; Eastern trading days. 2026-10-16 (66.39)
# matches the close already cached. Nov 23 is left out: read during after-hours with a part-day volume.
BBIO_CLOSES = {"2026-10-19": 67.94, "2026-10-20": 67.55, "2026-10-21": 67.74, "2026-10-22": 68.12, "2026-10-23": 68.56,
               "2026-10-26": 68.15, "2026-10-27": 69.37, "2026-10-28": 70.82, "2026-10-29": 70.73, "2026-10-30": 74.95,
               "2026-11-02": 75.0, "2026-11-03": 74.03, "2026-11-04": 77.89, "2026-11-05": 74.27, "2026-11-06": 74.29,
               "2026-11-09": 77.93, "2026-11-10": 78.67, "2026-11-11": 79.54, "2026-11-12": 78.17, "2026-11-13": 78.3,
               "2026-11-16": 77.36, "2026-11-17": 76.8, "2026-11-18": 78.01, "2026-11-19": 78.18, "2026-11-20": 76.03}
INDICATION = "Limb-girdle muscular dystrophy type 2I/R9 (LGMD2I/R9) in adult and pediatric patients weighing at least 30 kg"


def jload(p, default=None):
    p = os.path.join(HERE, p)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else default


def jsave(p, d):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


src = io.open(DATASET, encoding="utf-8").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
asc = src[i:j] == json.dumps(rows, indent=1, ensure_ascii=True)
r = next(x for x in rows if x["id"] == RID)
assert r.get("dp") == "day" and r.get("d") == "2026-11-27", "goal date changed; re-verify before publishing"
if r.get("st") != "Decided":
    r.update({"st": "Decided", "oc": "Approved", "dcd": ANN, "url": PAGE_URL, "ua": NOW})
    d = r.setdefault("_d", {})
    d.update({
        "brand": "Welgemda", "inn": "ribitol", "trial": "FORTIFY",
        "indication": INDICATION,
        "decision_source": "BridgeBio 8-K Exhibit 99.1, November 23, 2026 (SEC EDGAR)",
        "decision_source_url": REL, "decision_date_unsourced": True,
        "decision_quote": QUOTE,
        "decision_note": ("BridgeBio announced the approval on November 23, 2026, four days before the November 27, "
                          "2026 goal date it disclosed. The FDA's own record of the action day was not read when this "
                          "row was updated, so no early or late margin is published yet."),
        "announcement": "BridgeBio 8-K Exhibit 99.1, November 23, 2026 (SEC EDGAR)",
        "announcement_url": REL,
        "review": ("NDA accepted with Priority Review, PDUFA goal date November 27, 2026 (BridgeBio 8-K, August 10, 2026). "
                   "BridgeBio states the FDA granted traditional (full) approval. Per BridgeBio, in the Phase 3 FORTIFY "
                   "trial the 100-meter timed test showed a 0.27 m/s velocity benefit relative to placebo at 12 months "
                   "(p<0.0001), and forced vital capacity (percent predicted) a 4.89% benefit at 12 months (p=0.0071)."),
    })
    print(f"  {RID}: Decided / Approved, announced {ANN} -> {PAGE_URL} (FDA day not read here; no margin yet)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=asc) + src[j:])

c = jload("_drug_approvals_confirmed.json")
for slug in ("bbp-418",):
    if not any(a.get("slug") == slug and a.get("date") == ANN for a in c["approvals"]):
        c["approvals"].append({"slug": slug, "date": ANN, "brand": "Welgemda", "source": REL})
jsave("_drug_approvals_confirmed.json", c)

faq = jload("_decision_extra_faq.json", {})
faq["BBIO-2026-11-23"] = [
    ["Was BBP-418 (ribitol) approved by the FDA?",
     "Yes. BridgeBio announced on November 23, 2026 that the FDA granted traditional (full) approval to Welgemda "
     "(BBP-418, ribitol) for limb-girdle muscular dystrophy type 2I/R9 in adult and pediatric patients weighing at "
     "least 30 kg."],
    ["Was the Welgemda decision early?",
     "BridgeBio announced the approval on November 23, 2026, four days before the November 27, 2026 PDUFA goal date it "
     "had disclosed. pdufa.bio publishes a margin only from the FDA's own record of the action day, which had not been "
     "read when this page was published."],
    ["What did the FORTIFY trial show?",
     "Per BridgeBio, at 12 months the 100-meter timed test showed a 0.27 m/s velocity benefit relative to placebo "
     "(p<0.0001), and forced vital capacity (percent predicted) a 4.89% benefit (p=0.0071)."]]
jsave("_decision_extra_faq.json", faq)

A = 'rel="noopener" style="color:#e3ba5e"'
spec = [{
    "ticker": "BBIO", "date": ANN, "outcome": "Approved",
    "drug": "Welgemda (BBP-418, ribitol)",
    "indication": "Limb-girdle muscular dystrophy type 2I/R9 (LGMD2I/R9), patients weighing at least 30 kg",
    "company": "BridgeBio Pharma", "cap": "Large",
    "headline": ("BridgeBio announced on November 23, 2026 that the FDA granted traditional approval to Welgemda "
                 "(BBP-418, ribitol) for LGMD2I/R9, on the Phase 3 FORTIFY trial."),
    "pdufa_note": (f'BridgeBio announced on November 23, 2026 that the FDA granted traditional (full) approval to '
                   f'Welgemda (BBP-418, ribitol), an oral treatment for limb-girdle muscular dystrophy type 2I/R9 in adult '
                   f'and pediatric patients weighing at least 30 kg (<a href="{REL}" {A}>BridgeBio 8-K, Exhibit 99.1</a>). '
                   f'BridgeBio had disclosed a PDUFA goal date of November 27, 2026 under Priority Review '
                   f'(<a href="{GOAL}" {A}>BridgeBio 8-K, August 10, 2026</a>), so the announcement came four days '
                   f'before it. The FDA\'s own record of the action day had not been read when this page was published, '
                   f'so no early or late margin is given yet. Per BridgeBio, in the Phase 3 FORTIFY trial the 100-meter '
                   f'timed test showed a 0.27 m/s velocity benefit relative to placebo at 12 months (p&lt;0.0001).'),
    "source": REL, "source_label": "BridgeBio 8-K Exhibit 99.1, November 23, 2026",
}]
jsave("decision_pages_2026_11_23_bbio.json", spec)

PX = os.path.join(HERE, "_chart_pxcache.json")
px = json.load(open(PX))
for dd, cl in BBIO_CLOSES.items():
    px.setdefault("BBIO", {}).setdefault(dd, cl)
json.dump(px, open(PX, "w"))
import build_decision_page as bdp  # noqa: E402
for e in spec:
    bdp.build(e, px)
print(f"  built {PAGE_URL}; ledger + FAQ + page spec written")
