# -*- coding: utf-8 -*-
"""CI guard: the harvester's precision-provenance rule (audit 09-15 ORDER 6) holds on synthetic
records. Three rules, each with a case that would have caused a real incident:

  1. most recent day-precision statement wins            (CAPR Aug 22 -> Nov 22)
  2. a quarter is never rounded to a day                 (09-10 P0: PTGX/TAK/ROIV "Sep 30")
  3. a later quarter does not override an earlier day    (09-14 P0: Q3 overriding Sep 26);
     a coarse window that does NOT contain the day is a conflict, kept and flagged.

Also: merge_crawl_to_slate must not default a blank precision to "day".

    python tests/test_precision_provenance_rule.py
"""
import importlib.util
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_crawler():
    spec = importlib.util.spec_from_file_location("catalyst_crawler", os.path.join(HERE, "catalyst_crawler.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.argv = ["catalyst_crawler.py"]
    spec.loader.exec_module(mod)
    return mod


def main():
    fail = 0
    try:
        cc = load_crawler()
    except Exception as e:  # the crawler imports pandas etc.; CI has them
        print(f"  SKIP could not import catalyst_crawler ({e})")
        return 0
    import pandas as pd

    def row(tk, d, prec, drug, ret, conf=0.9):
        return {"ticker": tk, "catalyst_type": "PDUFA", "catalyst_date": d, "date_precision": prec,
                "drug": drug, "retrieved_at": ret, "confidence": conf, "source": "t", "source_url": "u"}

    # rule 1 + rule 3 (redundant): May 8-K says Sep 26; Aug 10-Q says Q3 -> one row, the day
    df = cc.resolve_date_precision(pd.DataFrame([
        row("MIRM", "2026-09-26", "day", "Zilurgisertib", "2026-05-06T00:00:00Z"),
        row("MIRM", "2026-Q3", "quarter", "Zilurgisertib", "2026-08-10T00:00:00Z")]))
    if not (len(df) == 1 and df.iloc[0]["catalyst_date"] == "2026-09-26" and df.iloc[0]["date_precision"] == "day"):
        print(f"  FAIL rule 3 (redundant coarse restatement should drop): {df[['catalyst_date','date_precision']].values.tolist()}")
        fail += 1

    # rule 1: two days, the later statement wins as the date (both kept as distinct keys; the
    # site's date_history records the move) -- the rule must not drop either day row
    df = cc.resolve_date_precision(pd.DataFrame([
        row("CAPR", "2026-08-22", "day", "Deramiocel", "2026-05-01T00:00:00Z"),
        row("CAPR", "2026-11-22", "day", "Deramiocel", "2026-08-24T00:00:00Z")]))
    if len(df) != 2:
        print(f"  FAIL rule 1 must keep both day statements for the change detector: {len(df)}")
        fail += 1

    # rule 2: a "day" whose value is a quarter label is demoted, never served as a day
    df = cc.resolve_date_precision(pd.DataFrame([row("PTGX", "2026-Q3", "day", "Rusfertide", "2026-07-24T00:00:00Z")]))
    if df.iloc[0]["date_precision"] != "quarter":
        print(f"  FAIL rule 2: quarter label served with precision {df.iloc[0]['date_precision']!r}")
        fail += 1

    # rule 3 (conflict): a later Q4 after a Sep 26 day -> both kept, Q4 flagged
    df = cc.resolve_date_precision(pd.DataFrame([
        row("XXXX", "2026-09-26", "day", "Drugone", "2026-05-06T00:00:00Z"),
        row("XXXX", "2026-Q4", "quarter", "Drugone", "2026-08-10T00:00:00Z")]))
    flagged = df[df["date_precision"].eq("quarter")]
    if not (len(df) == 2 and len(flagged) == 1 and "window-conflict" in str(flagged.iloc[0]["data_flags"])):
        print(f"  FAIL rule 3 (conflict): expected both rows kept and the quarter flagged; got "
              f"{df[['catalyst_date','date_precision','data_flags']].values.tolist()}")
        fail += 1

    # merge() must route through the rule
    src = io.open(os.path.join(HERE, "catalyst_crawler.py"), encoding="utf-8").read()
    if not re.search(r"return resolve_date_precision\(out\)", src):
        print("  FAIL catalyst_crawler.merge() no longer applies resolve_date_precision().")
        fail += 1

    # merge_crawl_to_slate must not default blank precision to day
    m = io.open(os.path.join(HERE, "merge_crawl_to_slate.py"), encoding="utf-8").read()
    if re.search(r'date_precision"\)\s*or\s*"day"', m):
        print("  FAIL merge_crawl_to_slate.py defaults a blank date_precision to \"day\" -- a "
              "coarse row with no stated precision would be published as a calendar day.")
        fail += 1

    if fail:
        print(f"\n{fail} precision-provenance rule failure(s). DO NOT PUBLISH.")
        return 1
    print("OK -- precision rule: latest day wins; quarter never a day; later quarter never overrides "
          "an earlier day (conflicts flagged); merge() applies it; slate merge has no day default.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
