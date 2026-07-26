"""CI guard (P0-0): the conference dataset can be CORRECTED, never silently REDUCED.

A data "fix" once truncated conference_presentations_history.csv from 715 rows / 39 conferences
to 224 / 11 -- and nothing caught it. The mechanism: an unescaped newline in a press-release
snippet split one row across two physical lines; the next crawl re-read the file, pandas hit an
unterminated field, and everything past the break was lost on the concat+dedup+rewrite.

safe_to_csv() now writes QUOTE_ALL + strips newlines, and the crawler's conference merge refuses
to shrink. This test is the backstop: run it before any publish. A crawl that returns fewer rows,
fewer conferences, or fewer tickers than the previous run FAILS the build.

    python tests/test_crawler_no_regression.py

Baseline: conference_presentations_history.prev.csv, snapshotted by the crawler on each GOOD write.
If .prev is absent (first run) the test passes with a note -- there is nothing to regress against.
"""
import os, sys
import pandas as pd

CANON = "catalysts_out/conference_presentations_history.csv"
PREV  = "catalysts_out/conference_presentations_history.prev.csv"

def fail(msg):
    print(f"  FAIL {msg}")
    return 1

def main():
    if not os.path.exists(CANON):
        print(f"  FAIL {CANON} does not exist"); return 1
    try:
        new = pd.read_csv(CANON, low_memory=False)
    except Exception as e:
        print(f"  FAIL {CANON} is UNREADABLE ({e}) -- a file that cannot be parsed is not a file"); return 1

    if not os.path.exists(PREV):
        print(f"OK -- {len(new)} rows, {new.conference.nunique()} conferences. "
              f"No {PREV} baseline yet; nothing to regress against.")
        return 0

    prev = pd.read_csv(PREV, low_memory=False)
    bad = 0
    if len(new) < len(prev) * 0.95:
        bad += fail(f"row count collapsed {len(prev)} -> {len(new)} (>5% drop)")
    lost = set(prev["conference"]) - set(new["conference"])
    if lost:
        bad += fail(f"lost {len(lost)} conferences: {sorted(lost)[:12]}")
    if new["ticker"].nunique() < prev["ticker"].nunique() * 0.95:
        bad += fail(f"ticker coverage collapsed {prev.ticker.nunique()} -> {new.ticker.nunique()}")

    if bad:
        print(f"\n{bad} regression failure(s). Data can be corrected, never silently reduced. DO NOT PUBLISH.")
        return 1
    print(f"OK -- {len(new)} rows, {new.conference.nunique()} conferences, "
          f"{new.ticker.nunique()} tickers; no regression vs {len(prev)}-row baseline.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
