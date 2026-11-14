# -*- coding: utf-8 -*-
"""backfill_runup_blanks.py -- fill run-up study cells that were blank only because the closes did not exist yet.

extend_runup_study.py appends a decision's row on the first run after the decision, when post_2d / post_5d (and for
some rows the T-120 baseline) cannot be computed yet; rows are "appended, never rewritten", so those cells stayed blank
forever and every post-decision figure silently excluded the newest events. This fills ONLY empty cells, from FMP closes
via price_source, with the study's own conventions (eve = last session strictly before the decision; post_N = eve close
-> close N sessions later, percent; T-120_* fractions from 120 sessions before eve). A cell that already holds a value
is never touched. Facts only, not investment advice.

    python backfill_runup_blanks.py [--dry-run]
"""
import argparse
import csv
import datetime as dt
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
POST = {"post_1d": 1, "post_2d": 2, "post_5d": 5}


def blank(v):
    return str(v).strip() in ("", "nan", "None")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    import price_source as ps
    today = eastern_today()
    rows = list(csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")))
    cols = list(rows[0].keys())
    filled, touched, unavailable = 0, 0, []
    for r in rows:
        d = r["pdufa_date"][:10]
        try:
            pd = dt.date.fromisoformat(d)
        except ValueError:
            continue
        need_post = [k for k in POST if k in r and blank(r[k])]
        need_120 = [k for k in ("T-120_T-1", "T-120_T-7", "T-120_T-3", "T-120_peak") if k in r and blank(r[k])]
        if pd < dt.date(2025, 1, 1):
            need_120 = []          # pre-2025 baselines were measured once on the recorded series; not refetched
        if not (need_post or need_120) or (today - pd).days < 2:
            continue
        b = ps.daily(r["ticker"], (pd - dt.timedelta(days=260)).isoformat(), min(today, pd + dt.timedelta(days=20)).isoformat())
        dates = [x[0] for x in b]; closes = [x[1] for x in b]
        eve_i = max((i for i, x in enumerate(dates) if x < d), default=None)
        if eve_i is None or (r.get("eve_date") and dates[eve_i] != r["eve_date"][:10]):
            unavailable.append((r["ticker"], d, "eve mismatch or no closes")); continue
        eve_p = closes[eve_i]
        n0 = filled
        for k in need_post:
            j = eve_i + POST[k]
            if j < len(closes) and eve_p:
                r[k] = (closes[j] / eve_p - 1) * 100; filled += 1
        if need_120 and eve_i >= 120 and closes[eve_i - 120]:
            base = closes[eve_i - 120]
            vals = {"T-120_T-1": closes[eve_i - 1] / base - 1 if eve_i >= 1 else None,
                    "T-120_T-7": closes[eve_i - 7] / base - 1, "T-120_T-3": closes[eve_i - 3] / base - 1,
                    "T-120_peak": max(closes[eve_i - 120:eve_i]) / base - 1}
            for k in need_120:
                if vals.get(k) is not None:
                    r[k] = vals[k]; filled += 1
        if filled > n0:
            touched += 1
    print(f"run-up blanks: {filled} cell(s) filled on {touched} row(s); {len(unavailable)} row(s) skipped "
          f"({', '.join(f'{t} {d}' for t, d, _ in unavailable[:8])}) | {ps.summary()}")
    if a.dry_run or not filled:
        return 0
    shutil.copyfile(CSVF, CSVF + ".bak_blanks")
    with open(CSVF, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
