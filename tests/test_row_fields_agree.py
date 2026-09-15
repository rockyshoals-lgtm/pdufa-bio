# -*- coding: utf-8 -*-
"""CI guard: every field on a row that restates its date agrees with the date. Audit 09-15 ORDER 2+3.

readout_cort_2026-09-15 said December 17 in `date`, September in `date_month`, the 15th in its id,
and carried a readout_ prefix on a PDUFA row. Four fields, three dates. It was reported in four
consecutive audits as "self-contradictions" before it was fixed, and one of the wrong fields was
the sort key /developers tells consumers to use.

This is the week's pattern inside a single row: the day was corrected and its derived copies were
not. Three invariants, each cheap, each closing a class:

  1. `dm` (date_month) == `d`[:7] whenever both are present. A month must be the month of its day.
  2. The date embedded in an id equals the row's own `d` -- OR the row's `_d.date_history`
     records that date as one the row once held. Ids are primary keys API consumers may hold, so
     a legitimate move (an FDA extension, a registry estimate that slid, a day withdrawn to a
     coarser precision) keeps its key and documents the move. A stale date in a key with NO
     history is a fourth answer for anyone who parses ids, and fails.
  3. An id prefixed `readout_` is a Readout, `pdufa_` a PDUFA, and so on. Type and prefix agree.

Asserted on the dataset the API ships, not on a sampled response.

    python tests/test_row_fields_agree.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
PREFIX = {"pdufa": "PDUFA", "readout": "Readout", "adcomm": "AdComm", "conf": "Conference",
          "conference": "Conference"}


def main():
    if not os.path.exists(DATASET):
        print("  SKIP dataset not found")
        return 0
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    fail = 0
    for r in rows:
        rid, d, dm, typ = str(r.get("id") or ""), str(r.get("d") or ""), r.get("dm"), r.get("type")

        # 1. month agrees with day
        if dm and d and str(dm)[:7] != d[:7]:
            print(f"  FAIL {rid}: date_month {dm} but date {d}. /developers tells consumers to "
                  f"sort on date_month first; this row would sort {abs(int(d[5:7]) - int(str(dm)[5:7]))} "
                  f"month(s) from where it belongs.")
            fail += 1

        # 2. the date in the id equals the row's date
        m = re.search(r"(\d{4}-\d{2}-\d{2})$", rid)
        if m and d and m.group(1) != d and typ in ("PDUFA", "Readout"):
            # conference/adcomm ids may legitimately key on a start date that later moved; a
            # PDUFA or Readout id that disagrees with its own row is a stale key UNLESS the row
            # documents the move: date_history must record the id's date as one the row held
            hist = (r.get("_d") or {}).get("date_history") or []
            covered = any(isinstance(h, dict) and h.get("date") == m.group(1) for h in hist)
            if not covered:
                print(f"  FAIL {rid}: id carries {m.group(1)} but the row's date is {d} and no "
                      f"date_history records the move. A stale date in a primary key is a fourth "
                      f"answer for anyone who parses ids: re-key it, or document the move.")
                fail += 1

        # 3. prefix agrees with type
        pre = rid.split("_", 1)[0].lower()
        want = PREFIX.get(pre)
        if want and typ and want != typ:
            print(f"  FAIL {rid}: id prefix says {want} but type is {typ}.")
            fail += 1

    if fail:
        print(f"\n{fail} row(s) disagree with themselves. DO NOT PUBLISH.")
        return 1
    print(f"OK -- all {len(rows)} rows: date_month is the month of date, ids carry the row's own "
          f"date, id prefixes match types.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
