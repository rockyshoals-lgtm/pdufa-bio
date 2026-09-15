# -*- coding: utf-8 -*-
"""Every row whose id embeds a date it no longer holds gets a date_history explaining why.

FOUND BY THE NEW GUARD (tests/test_row_fields_agree.py) on its first run: the auditor's CORT row
was one of THIRTY-NINE ids carrying a date the row no longer holds. And NO row in the dataset
carried a date_history field, so none of those moves was recorded anywhere on the row.

TWO KINDS, TWO TREATMENTS.

  A MOVE. The sponsor extended the goal date (CAPR, Aug 22 -> Nov 22), or the registry's
  primary-completion estimate slid (most of the 09-14 re-sync), or we withdrew an unsourced day
  to a coarser precision (NVO denecimig). The id is a PRIMARY KEY that API consumers may hold;
  rewriting it silently breaks their continuity and turns one row into two in their store. So the
  id stays, and `_d.date_history` records the date it was keyed on, the date it holds now, and
  why. The id's date becomes documented history rather than an undocumented stale value.

  A CORRECTION. The date in the key was never real -- a manufactured 15th on a PDUFA, a
  `readout_` prefix on a decision. Nothing legitimate was ever keyed on it. Re-key. (The CORT
  row was handled that way by apply_0915_order_1.py.)

The guard accepts an id whose date differs from `d` ONLY when date_history covers the id's
date. That is the auditor's intent -- no silent stale keys -- without making every legitimate
extension a breaking change.

    python record_date_history.py [--dry-run]
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
TODAY = dt.date.today().isoformat()

# rows whose move has a specific, known reason
SPECIFIC = {
    "pdufa_capr_2026-08-22": ("2026-08-24", "The FDA extended the goal date from August 22 to "
                              "November 22, 2026 after Capricor's BLA amendment; Capricor announced "
                              "the extension on August 24, 2026 and /pdufa-date-changes records it."),
    "pdufa_nvo_mim8_2026-09-30": ("2026-09-10", "The September 30 day was withdrawn as unsourced "
                                  "-- no Novo Nordisk filing states a day, month or quarter -- "
                                  "and the row moved to year precision on the year-end sentinel."),
    "pdufa_cort_2026-03-25": ("2026-03-25", "This id was keyed on the FDA ACTION date (March 25, "
                              "2026) rather than the goal date (July 11, 2026). The row is decided "
                              "and the key is stable; the discrepancy is naming, not a date move."),
    "readout_tyra_2026-08-31": ("2026-08-03", "Tyra's second-quarter 2026 release guides SURF303 "
                                "initial results in 2027; the row was keyed on an August 31 "
                                "sentinel and now sits at year precision on the 2027 sentinel."),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    n = 0
    for r in rows:
        rid, d = str(r.get("id") or ""), str(r.get("d") or "")
        m = re.search(r"(\d{4}-\d{2}-\d{2})$", rid)
        if not m or m.group(1) == d or r.get("type") not in ("PDUFA", "Readout"):
            continue
        dd = r.setdefault("_d", {})
        hist = dd.get("date_history") or []
        if any(h.get("date") == m.group(1) for h in hist):
            continue
        when, why = SPECIFIC.get(rid, (None, None))
        if why is None:
            when = str(r.get("ua") or TODAY)[:10]
            st = str(r.get("st"))
            if r.get("type") == "Readout" and st == "Estimated":
                why = ("ClinicalTrials.gov's primary-completion estimate for this trial moved; "
                       f"the row was re-synced to the registry on {when}. /readouts defines "
                       "an estimated date as that registry window, so the row follows it.")
            elif r.get("type") == "Readout" and st == "Reported":
                why = ("The row was keyed on the guided window's sentinel; the result was "
                       f"reported on {d}, and a reported row carries the day it was reported.")
            elif r.get("type") == "Readout" and st == "Guided":
                why = ("Company guidance moved the window; the row was keyed on the earlier "
                       "window's sentinel and now holds the sentinel of the window the company "
                       "guides.")
            else:
                why = "The date this row was keyed on is no longer the date it holds."
        hist.insert(0, {"date": m.group(1), "note": "date the row was keyed on when created"})
        hist.append({"date": d, "changed": when, "why": why})
        dd["date_history"] = hist
        n += 1
        print(f"  {rid:<32} {m.group(1)} -> {d}   ({why[:60]}...)")

    if not a.dry_run:
        io.open(DATASET, "w", encoding="utf-8").write(
            src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    print(f"\n{n} row(s) given a date_history" + ("   (--dry-run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
