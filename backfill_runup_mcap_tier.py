# -*- coding: utf-8 -*-
"""backfill_runup_mcap_tier.py -- give every run-up study row its market-cap tier at the eve of the decision.

2026-11-03: 97 of 1,883 study rows (every decision added by extend_runup_study.py since Feb 2025) had no mcap_tier,
because the extender read a dataset field (_d.market_cap_usd) that almost no row carries. Untiered rows count in the
study's overall figures but in NO size tier, so every "by market cap" number (cohort medians, /research/pdufa-stock-
run-up-by-market-cap, the decision pages' cohort line) silently excluded nearly all of 2026.

Tier = FMP historical market cap on the eve date (last trading day strictly before the decision; the row's eve_date),
the same thresholds as the existing rows. Rows FMP cannot price stay blank and are listed. Idempotent.

    python backfill_runup_mcap_tier.py [--dry-run]
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fmp_mcap import mcap_on, tier_label  # noqa: E402

CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")))
    cols = list(rows[0].keys())
    todo = [r for r in rows if not (r.get("mcap_tier") or "").strip()]
    print(f"study rows {len(rows)}; without a tier {len(todo)}")
    done, miss = 0, []
    for r in todo:
        eve = (r.get("eve_date") or r["pdufa_date"])[:10]
        m = mcap_on(r["ticker"], eve)
        if not m:
            miss.append(f"{r['ticker']} {r['pdufa_date'][:10]}"); continue
        r["mcap"] = r.get("mcap") or str(int(m))
        r["mcap_tier"] = tier_label(m)
        done += 1
        print(f"  {r['ticker']:6s} {r['pdufa_date'][:10]}  eve {eve}  ${m/1e6:,.0f}M  {r['mcap_tier']}", flush=True)
    print(f"tiered {done}; FMP had no market cap for {len(miss)}: {', '.join(miss)}")
    if done and not a.dry_run:
        with open(CSVF, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print("written")


if __name__ == "__main__":
    main()
