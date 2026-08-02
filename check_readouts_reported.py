# -*- coding: utf-8 -*-
"""check_readouts_reported.py -- the hybrid "flag for exact date" step.

The window-move for every elapsed readout is auto-logged by build_readout_results.py. This sweep
surfaces the readouts whose estimated window closed LAST MONTH (a small rolling set) so a human can
confirm the actual readout date + outcome, upgrading that entry from a coarse window move to a precise
day-of reaction. Advisory only (feeds the daily review issue); it never publishes anything.

    python check_readouts_reported.py
"""
import json, os, re
import datetime as dt

SITE = "pdufa_site_src"
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
TODAY = dt.date.today()
PREV_YM = (dt.date(TODAY.year, TODAY.month, 1) - dt.timedelta(days=1)).strftime("%Y-%m")


def main():
    src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    arr, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    flagged = []
    for r in arr:
        if r.get("type") != "Readout" or not r.get("t"):
            continue
        ym = (r.get("dm") or str(r.get("d") or "")[:7])
        if ym == PREV_YM:
            flagged.append((r["t"], r.get("name") or "", ym))
    if flagged:
        print(f"*** {len(flagged)} readout(s) whose window closed {PREV_YM} -- confirm the actual "
              f"readout date + outcome to upgrade the auto-logged window move to a precise reaction: ***")
        for t, name, ym in flagged:
            print(f"  READOUT NEEDS VERIFICATION  {t}  ({ym})  {name[:50]}")
    else:
        print(f"No readouts closed in {PREV_YM}.")


if __name__ == "__main__":
    main()
