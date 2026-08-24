# -*- coding: utf-8 -*-
"""add_amlx_avexitide.py -- give AMLX's positive Phase 3 an event row, so it gets pages.

Red team 2026-08-19 and again 08-24: /drug/avexitide and /ticker/AMLX are both 404 even though
AMLX posted a positive Phase 3 on 2026-08-18 which we published to /readouts (+63.8% day-of).
The cause is structural, not an oversight in the builders: AMLX had NO row in dataset.mjs at
all. build_drug_pages and build_ticker_hubs both build from the dataset, so a company whose only
appearance is in readout_reported_manual.json is invisible to them.

This adds the readout as a dated, sourced event. Facts from Amylyx's own release (2026-08-18):
LUCIDITY, a 78-participant randomised double-blind placebo-controlled Phase 3 in post-bariatric
hypoglycaemia after Roux-en-Y gastric bypass, met the FDA-agreed primary endpoint with a 55%
reduction in the composite rate of Level 2 and Level 3 hypoglycaemic events versus placebo
(p=0.000003), and met all secondary endpoints. Avexitide holds Breakthrough Therapy and Orphan
Drug designations; Amylyx has said it plans to submit an NDA by the end of 2026.

The row's id matches the entry already in readout_reported_manual.json, so the drug page renders
it as REPORTED with its measured day-of move rather than as an upcoming catalyst.

Idempotent.

    python add_amlx_avexitide.py [--dry-run]
"""
import argparse, datetime as dt, io, json, os, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
SRC = ("https://www.businesswire.com/news/home/20260817275387/en/Amylyx-Pharmaceuticals-"
       "Announces-Positive-Topline-Results-from-Phase-3-LUCIDITY-Clinical-Trial-of-Avexitide-"
       "in-Post-Bariatric-Hypoglycemia")

ROW = {
    "id": "readout_amlx_2026-08-18",
    "t": "AMLX",
    "company": "Amylyx Pharmaceuticals, Inc.",
    "d": "2026-08-18",
    "dp": "day",
    "name": "Avexitide",
    "type": "Readout",
    "ta": "Endocrinology / Metabolic",
    "cap": "",
    # A readout that has REPORTED is not an FDA "Decided" record: `oc` carries the decision
    # vocabulary (Approved / CRL / Withdrawn) and test_decided_consistency rightly rejects
    # anything else there. Widening that vocabulary to fit a readout would blur two different
    # event types in the API. Status is "Reported" and the clinical result lives in _d.
    "st": "Reported",
    "url": SRC,
    "_d": {
        "readout_outcome": "Positive",
        "reported_date": "2026-08-18",
        "indication": ("Post-bariatric hypoglycaemia (PBH) after Roux-en-Y gastric bypass "
                       "surgery"),
        "nct_id": "NCT06747468",
        "review": ("Phase 3 LUCIDITY (n=78) met the FDA-agreed primary endpoint: a 55% reduction "
                   "in the composite rate of Level 2 and Level 3 hypoglycaemic events versus "
                   "placebo (p=0.000003), with all secondary endpoints met and no treatment-"
                   "related serious adverse events. Avexitide holds Breakthrough Therapy and "
                   "Orphan Drug designations. Amylyx has said it plans to submit an NDA to the "
                   "FDA by the end of 2026; no action date exists yet, because no application "
                   "has been filed."),
        "market_cap_usd": None,
    },
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    j = src.find("[")
    arr, end = json.JSONDecoder().raw_decode(src[j:])
    if any(r.get("id") == ROW["id"] for r in arr):
        print("AMLX avexitide row already present")
        return 0
    row = dict(ROW)
    row["ua"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    arr.append(row)
    arr.sort(key=lambda r: (str(r.get("d") or "9999"), str(r.get("t") or "")))
    if not a.dry_run:
        io.open(DATASET, "w", encoding="utf-8").write(
            src[:j] + json.dumps(arr, separators=(",", ":"), ensure_ascii=False) + src[j + end:])
    print(f"{'DRY RUN: would add' if a.dry_run else 'added'} AMLX avexitide readout "
          f"({ROW['d']}, {ROW['oc']}) -> /drug/avexitide and /ticker/AMLX can now build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
