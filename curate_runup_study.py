# -*- coding: utf-8 -*-
"""curate_runup_study.py -- keep the run-up study to real, correctly labelled, once-counted FDA decisions.

Runs after extend_runup_study.py and before runup_study_stats.py, every rebuild. Idempotent.

  1. Labels and outcomes come from the published decision page (runup_study_events.decision_facts), for every
     row that has one. Fixes the extender's first-row-per-ticker labels (2026-11-18: GSK Nov 17 neladalkib was
     "tebipenem"; AZN Apr-May 2026 rows all "Truqap").
  2. A row whose decision page is not a primary-sourced approval or CRL leaves the study: "outcome unverified"
     pages (price-inferred; many are trial readouts, not PDUFA events) and the pages listed in
     runup_study_exclusions.json (cited source re-checked and found not to announce the FDA action).
  3. One FDA action, one row: two pages of one ticker whose Drugs@FDA validation names the same application and
     action date are one decision; the page dated on or soonest after the action stays.
  4. One price event, one row. Two rows with the same ticker and the same eve-of-decision close are the same
     price path counted twice (a Sunday and a Monday page for one CRL, or two applications decided the same
     day). If they agree on the outcome the first row is kept; if one is an approval and one a CRL, the move
     answers both and both leave the study, so the approval/CRL split never depends on sort order.

Removed rows are never deleted: they move to runup_study_excluded.csv with the reason and the row they
duplicate, so every change to the study's size can be traced, and extend_runup_study.py does not re-add them.

    python curate_runup_study.py [--dry-run]
"""
import argparse
import csv
import datetime as dt
import os
import sys
from collections import OrderedDict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from runup_study_events import EXCLUDED_CSV, decision_facts, eligibility, load_exclusions  # noqa: E402

CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
EXCL_COLS = ["cache_key", "ticker", "pdufa_date", "eve_date", "asset", "outcome", "reason", "kept_row"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")))
    cols = list(rows[0].keys())
    excl = load_exclusions()
    n0 = len(rows)

    relabelled, outcome_fixed, removed = [], [], []
    keep = []
    facts = {}
    for r in rows:
        tk, d = r["ticker"].strip().upper(), r["pdufa_date"][:10]
        r["_orig_asset"] = r.get("asset", "")   # the audit trail records what the row said before relabelling
        f = decision_facts(tk, d)
        facts[id(r)] = f
        ok, why = eligibility(tk, d, f, excl)
        if not ok:
            removed.append((r, why, ""))
            continue
        if f:
            if f["drug"] and r.get("asset", "") != f["drug"]:
                relabelled.append((tk, d, r.get("asset", ""), f["drug"]))
                r["asset"] = f["drug"]
            if f["indication"] and r.get("indication", "") != f["indication"]:
                r["indication"] = f["indication"]
            if r.get("outcome") != f["outcome"]:
                outcome_fixed.append((tk, d, r.get("outcome"), f["outcome"]))
                r["outcome"] = f["outcome"]
                r["outcome_bin"] = "1" if f["outcome"] == "APPROVAL" else "0"
        keep.append(r)

    # one FDA action, one row: two pages of one ticker whose Drugs@FDA validation names the same application and
    # action date (ASND Feb 27/28 2026). Keep the page dated on or soonest after the action (the market's first
    # look at it); a page dated before the action measures the wrong days.
    def gap(r, act):
        g = (dt.date.fromisoformat(r["pdufa_date"][:10]) - dt.date.fromisoformat(act)).days
        return (0, g) if g >= 0 else (1, -g)
    by_action = OrderedDict()
    for r in keep:
        fa = (facts.get(id(r)) or {}).get("fda_action")
        if fa:
            by_action.setdefault((r["ticker"].strip().upper(),) + fa, []).append(r)
    drop = set()
    for (tk, app, act), group in by_action.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda r: gap(r, act))
        for r in group[1:]:
            drop.add(id(r))
            removed.append((r, f"same FDA action as another page ({app}, action date {act})",
                            f"{group[0]['ticker']} {group[0]['pdufa_date'][:10]} {group[0].get('asset', '')[:60]}"))
    keep = [r for r in keep if id(r) not in drop]

    # one price event, one row: same ticker + same eve close
    events = OrderedDict()
    for r in sorted(keep, key=lambda x: (x["pdufa_date"][:10], x["ticker"], x.get("cache_key", ""))):
        k = (r["ticker"].strip().upper(), (r.get("eve_date") or "")[:10])
        events.setdefault(k if k[1] else (id(r),), []).append(r)
    final = []
    for k, group in events.items():
        if len(group) == 1:
            final.append(group[0])
            continue
        if len({g.get("outcome") for g in group}) > 1:
            # one price move answering an approval AND a CRL (BIIB Aug 4 2023: zuranolone approved for PPD, not
            # for MDD) cannot be filed under either outcome; keeping one would let sort order pick the answer
            for r in group:
                removed.append((r, "same price event, mixed outcomes (an approval and a CRL share one eve close)",
                                "; ".join(f"{g['pdufa_date'][:10]} {g.get('outcome')}" for g in group)))
            continue
        first = group[0]
        final.append(first)
        for r in group[1:]:
            removed.append((r, "same price event as an earlier row (same ticker, same eve-of-decision close)",
                            f"{first['ticker']} {first['pdufa_date'][:10]} {first.get('asset', '')[:60]}"))

    print(f"study rows: {n0} -> {len(final)}  (removed {len(removed)}, relabelled {len(relabelled)}, "
          f"outcome corrected {len(outcome_fixed)})")
    by = {}
    for _, why, _k in removed:
        key = why.split(":")[0].split("(")[0].strip()
        by[key] = by.get(key, 0) + 1
    for k, v in sorted(by.items(), key=lambda x: -x[1]):
        print(f"   removed {v:4d}  {k}")
    for x in relabelled[:8]:
        print(f"   relabel {x[0]:6s} {x[1]}  '{x[2][:40]}' -> '{x[3][:40]}'")
    for x in outcome_fixed[:8]:
        print(f"   outcome {x[0]:6s} {x[1]}  {x[2]} -> {x[3]}")

    if a.dry_run:
        print("DRY RUN -- not written.")
        return
    if not (removed or relabelled or outcome_fixed):
        print("nothing to change.")
        return

    with open(CSVF, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(final, key=lambda x: str(x.get("pdufa_date") or "")))

    have = set()
    old = []
    if os.path.exists(EXCLUDED_CSV):
        old = list(csv.DictReader(open(EXCLUDED_CSV, encoding="utf-8")))
        have = {o["cache_key"] for o in old}
    for r, why, kept in removed:
        ck = r.get("cache_key") or f"{r['ticker']}_{r['pdufa_date'][:10].replace('-', '')}"
        if ck in have:
            ck = f"{ck}#{(r.get('_orig_asset') or r.get('asset') or '')[:20]}"
            if ck in have:
                continue
        have.add(ck)
        old.append({"cache_key": ck, "ticker": r["ticker"], "pdufa_date": r["pdufa_date"][:10],
                    "eve_date": (r.get("eve_date") or "")[:10], "asset": r.get("_orig_asset", r.get("asset", "")),
                    "outcome": r.get("outcome", ""), "reason": why, "kept_row": kept})
    with open(EXCLUDED_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=EXCL_COLS)
        w.writeheader()
        w.writerows(sorted(old, key=lambda o: (o["pdufa_date"], o["ticker"])))
    print(f"wrote {CSVF} ({len(final)} rows) and {EXCLUDED_CSV} ({len(old)} removed rows on record)")


if __name__ == "__main__":
    main()
