# -*- coding: utf-8 -*-
"""apply_1119_livsayis_approval.py -- Livsayis (cemdisiran), generalized myasthenia gravis, approval announced by
Regeneron on November 18, 2026. Row pdufa_regn_2026-11-30 (goal date stated as a MONTH, November 2026).

Verified 2026-11-19 ~01:20 UTC (2026-11-18 20:20 Eastern, 17:20 Pacific; RULE 1), each page read itself:
  Regeneron release on GlobeNewswire, dateline "TARRYTOWN, N.Y., Nov. 18, 2026": Regeneron "today announced that the
    U.S. Food and Drug Administration (FDA) has approved Livsayis (cemdisiran)" for generalized myasthenia gravis in
    adults who are anti-acetylcholine receptor (AChR) antibody-positive; subcutaneous, four times a year (every three
    months). Phase 3 NIMBLE (randomized, double-blind, placebo-controlled): MG-ADL change at week 24 -4.5 vs -2.2
    placebo (placebo-adjusted 2.3, p=0.0005); MG-ADL responders 76.6% vs 44.1% (p<0.001); QMG 4.2 vs 1.5 (placebo-
    adjusted 2.8, p=0.0015). Boxed warning for serious meningococcal infections; available only through a REMS.
    The release approves cemdisiran alone; the combination arm of NIMBLE is not part of this approval.
  FDA record: NOT yet posted. The FDA's Novel Drug Approvals 2026 page (content current as of 11/16/2026) does not list
    Livsayis; Drugs@FDA was not reachable from the build host. So this row carries NO fda_action_date: the page states
    the announcement day as the announcement day (label_announcement_only_dates.py), and sync_fda_action_dates.py writes
    the FDA's own day when Drugs@FDA posts it.
  Goal date: Regeneron 8-K of 2026-07-30 (already on the row): "target action date in November 2026". Month precision,
    so NO early or late margin is published (a margin needs a day-precision goal and an FDA action day).
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
ANN = "2026-11-18"
RID = "pdufa_regn_2026-11-30"
PAGE_URL = "/fda-decision/REGN-2026-11-18"
REL = ("https://www.globenewswire.com/news-release/2026/11/18/3406224/0/en/livsayis-cemdisiran-approved-by-the-fda-as-"
       "first-and-only-sirna-therapy-in-generalized-myasthenia-gravis-and-only-treatment-with-four-times-a-year-"
       "subcutaneous-dosing.html")
GOAL = "https://www.sec.gov/Archives/edgar/data/872589/000087258926000023/exhibit991q22026.htm"
QUOTE = ("Regeneron Pharmaceuticals, Inc. (NASDAQ: REGN) today announced that the U.S. Food and Drug Administration (FDA) "
         "has approved Livsayis (cemdisiran) for the treatment of generalized myasthenia gravis (gMG) in adult patients "
         "who are anti-acetylcholine receptor (AChR) antibody-positive.")
REGN_CLOSES = {"2026-10-19": 782.04, "2026-10-20": 807.48, "2026-10-21": 805.67, "2026-10-22": 819.09,
               "2026-10-23": 805.02, "2026-10-26": 807.67, "2026-10-27": 816.1, "2026-10-28": 813.27,
               "2026-10-29": 818.77, "2026-10-30": 927.89, "2026-11-02": 961.26, "2026-11-03": 973.36,
               "2026-11-04": 930.67, "2026-11-05": 902.9, "2026-11-06": 904.35, "2026-11-09": 919.96,
               "2026-11-10": 916.06, "2026-11-11": 959.41, "2026-11-12": 951.19, "2026-11-13": 955.47,
               "2026-11-16": 952.4, "2026-11-17": 957.76, "2026-11-18": 945.53}


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
assert r.get("dp") == "month" and r.get("dm") == "2026-11", "goal precision changed; re-verify before publishing"
if r.get("st") != "Decided":
    r.update({"st": "Decided", "oc": "Approved", "dcd": ANN, "url": PAGE_URL, "ua": NOW})
    d = r.setdefault("_d", {})
    d.update({
        "brand": "Livsayis", "inn": "cemdisiran", "trial": "NIMBLE",
        "indication": "Generalized myasthenia gravis (gMG) in adults who are anti-AChR antibody-positive",
        "decision_source": "Regeneron press release, November 18, 2026 (GlobeNewswire)",
        "decision_source_url": REL, "decision_date_unsourced": True,
        "decision_quote": QUOTE,
        "decision_note": ("Regeneron announced the approval on November 18, 2026. The FDA's own record of the action "
                          "day was not yet posted when this row was updated. The goal date is stated as a month "
                          "(November 2026, Regeneron 8-K of July 30, 2026), so no early or late margin is published."),
        "announcement": "Regeneron press release, November 18, 2026 (GlobeNewswire)",
        "announcement_url": REL,
        "review": ("NDA under Priority Review following use of a Priority Review Voucher (Regeneron 8-K, July 30, 2026). "
                   "Per Regeneron, the Phase 3 NIMBLE trial (randomized, double-blind, placebo-controlled): on the "
                   "primary endpoint, MG-ADL total score improved 4.5 points with Livsayis versus 2.2 with placebo at "
                   "week 24 (placebo-adjusted 2.3, p=0.0005); 76.6% versus 44.1% were MG-ADL responders (p<0.001); QMG "
                   "improved 4.2 versus 1.5 points (placebo-adjusted 2.8, p=0.0015). Subcutaneous dosing four times a "
                   "year. Boxed warning for serious meningococcal infections; available only through a REMS."),
    })
    print(f"  {RID}: Decided / Approved, announced {ANN} -> {PAGE_URL} (FDA day not yet posted; goal month only, no margin)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=asc) + src[j:])

c = jload("_drug_approvals_confirmed.json")
if not any(a.get("slug") == "cemdisiran" and a.get("date") == ANN for a in c["approvals"]):
    c["approvals"].append({"slug": "cemdisiran", "date": ANN, "brand": "Livsayis", "source": REL})
    jsave("_drug_approvals_confirmed.json", c)

faq = jload("_decision_extra_faq.json", {})
faq["REGN-2026-11-18"] = [
    ["Was cemdisiran approved by the FDA?",
     "Yes. Regeneron announced on November 18, 2026 that the FDA approved Livsayis (cemdisiran) for adults with "
     "generalized myasthenia gravis who are anti-acetylcholine receptor antibody-positive. The FDA's own record of the "
     "action day had not been posted when this page was published."],
    ["Was the Livsayis decision early?",
     "pdufa.bio does not publish a margin for this decision. Regeneron stated the target action date as November 2026, "
     "a month rather than a day, after using a Priority Review Voucher, and the approval was announced on November 18, "
     "2026, within that month."],
    ["What did the NIMBLE trial show?",
     "Per Regeneron, at week 24 the MG-ADL score improved 4.5 points with Livsayis versus 2.2 with placebo, and 76.6% of "
     "patients versus 44.1% on placebo had at least a 3-point improvement. Livsayis is given under the skin four times a "
     "year and carries a boxed warning for serious meningococcal infections."]]
jsave("_decision_extra_faq.json", faq)

A = 'rel="noopener" style="color:#e3ba5e"'
spec = [{
    "ticker": "REGN", "date": ANN, "outcome": "Approved",
    "drug": "Livsayis (cemdisiran)",
    "indication": "Generalized myasthenia gravis in adults who are anti-AChR antibody-positive",
    "company": "Regeneron Pharmaceuticals", "cap": "Large",
    "headline": ("Regeneron announced on November 18, 2026 that the FDA approved Livsayis (cemdisiran) for adults with "
                 "anti-AChR antibody-positive generalized myasthenia gravis, on the Phase 3 NIMBLE trial."),
    "pdufa_note": (f'Regeneron announced on November 18, 2026 that the FDA approved Livsayis (cemdisiran), given under '
                   f'the skin four times a year, for adults with generalized myasthenia gravis who are anti-acetylcholine '
                   f'receptor antibody-positive (<a href="{REL}" {A}>Regeneron\'s announcement</a>). The FDA\'s own record '
                   f'of the action day had not been posted when this page was published. Regeneron stated the target '
                   f'action date as November 2026 after using a Priority Review Voucher (<a href="{GOAL}" {A}>Regeneron '
                   f'8-K, July 30, 2026</a>); because that is a month, not a day, no early or late margin is given. Per '
                   f'Regeneron, in the Phase 3 NIMBLE trial the MG-ADL score improved 4.5 points with Livsayis versus 2.2 '
                   f'with placebo at week 24 (p=0.0005), and 76.6% versus 44.1% of patients improved by at least 3 points. '
                   f'Livsayis carries a boxed warning for serious meningococcal infections and is available only through '
                   f'a REMS.'),
    "source": REL, "source_label": "Regeneron press release, November 18, 2026",
}]
jsave("decision_pages_2026_11_18_regn.json", spec)

PX = os.path.join(HERE, "_chart_pxcache.json")
px = json.load(open(PX))
for dd, cl in REGN_CLOSES.items():
    px.setdefault("REGN", {}).setdefault(dd, cl)
json.dump(px, open(PX, "w"))
import build_decision_page as bdp  # noqa: E402
for e in spec:
    bdp.build(e, px)
print(f"  built {PAGE_URL}; ledger + FAQ + page spec written")
