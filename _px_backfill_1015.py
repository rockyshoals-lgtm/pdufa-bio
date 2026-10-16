# -*- coding: utf-8 -*-
"""One-off (2026-10-15): add FMP daily closes from 2025-07-01 for the tickers whose decision pages are being
corrected or published, so build_decision_page.py has the T-120 window. Same source and function as
refresh_pxcache.py (FMP EOD adjusted closes). Adds dates; never overwrites an existing close."""
import json
import os
import sys

_ARGS = sys.argv[1:]
sys.argv = [sys.argv[0]]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import refresh_pxcache as R  # noqa: E402  (loads the env and the FMP key; main() is not run)

TICKERS = _ARGS or ["IBRX", "TEVA", "PFE", "AMGN", "BMY", "SPRY", "NVCR", "EBS", "GILD"]
cache = json.load(open(R.CACHE))
for tk in TICKERS:
    rows = R.eod(tk, "2025-07-01")
    have = cache.setdefault(tk, {})
    added = 0
    for d, c in rows:
        if d not in have:
            have[d] = c
            added += 1
    ds = sorted(have)
    print(f"{tk}: fetched {len(rows)}, added {added}, range {ds[0] if ds else '-'} .. {ds[-1] if ds else '-'}")
json.dump(cache, open(R.CACHE, "w"))
