# -*- coding: utf-8 -*-
"""Conference rows in the rendered dataset carry a status that agrees with the Eastern date.

  * end < today            -> "Ended"
  * start <= today <= end  -> "In progress"
  * start > today          -> "Scheduled"

Audit 2026-09-08 N1: ERS (2026-09-05..09-09) read "Scheduled" on Sept 8 because the writer knew
only Ended/Scheduled and judged them on the UTC day. Asserts the dataset the API and pages are
built from (pdufa_site_src/api/v1/dataset.mjs), not the script.

Proved 0 -> 1 -> 0 on 2026-09-08 by planting "Scheduled" on the ERS row.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")


def expected(start, end, today):
    if end < today:
        return "Ended"
    if start <= today:
        return "In progress"
    return "Scheduled"


def main():
    src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    today = eastern_today().isoformat()
    confs = [r for r in rows if r.get("type") == "Conference"]
    bad = []
    for r in confs:
        start = str(r.get("d", ""))
        end = str((r.get("_d") or {}).get("end") or start)
        want = expected(start, end, today)
        if r.get("st") != want:
            bad.append(f"{r.get('t')} {start}..{end} st={r.get('st')!r} want {want!r}")
    print(f"conference rows: {len(confs)}; status disagreeing with Eastern date {today}: {len(bad)}")
    for b in bad:
        print("  " + b)
    if not confs:
        print("FAIL: no Conference rows in dataset")
        return 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
