# -*- coding: utf-8 -*-
"""apply_1128_slgl_day.py -- Sol-Gel's SGT-610 Phase 3 top-line tightened to the day, red-teamed 2026-11-28.

readout_slgl_2026-12-31 was "late November 2026" (month precision) from Sol-Gel's Nov 12, 2026 Q3 release. Sol-Gel's
Nov 27, 2026 release (GlobeNewswire): "Sol-Gel Technologies to Host Conference Call to Discuss Top-Line Results from
Pivotal Phase 3 Clinical Trial of SGT-610 in Gorlin Syndrome" ... "will host a conference call on Monday, November 30,
2026, at 8:00am Eastern Time to discuss top-line results from its pivotal Phase 3 clinical trial (SGT-610-01)". Same
trial (SGT-610, patidegib gel 2%, prevention of basal cell carcinoma in adult Gorlin syndrome patients). The row moves
to Nov 30, 2026, day precision. RULE 1: 8:00 am ET is 5:00 am PT. Nothing is inferred about the result.

Idempotent. Facts only, not investment advice.   python apply_1128_slgl_day.py [--dry-run]
"""
import argparse
import io
import json
import sys

DATASET = "pdufa_site_src/api/v1/dataset.mjs"
ID = "readout_slgl_2026-12-31"
URL = ("https://www.globenewswire.com/news-release/2026/11/27/3411473/0/en/sol-gel-technologies-to-host-conference-"
       "call-to-discuss-top-line-results-from-pivotal-phase-3-clinical-trial-of-sgt-610-in-gorlin-syndrome.html")
QUOTE = ("will host a conference call on Monday, November 30, 2026, at 8:00am Eastern Time to discuss top-line results "
         "from its pivotal Phase 3 clinical trial (SGT-610-01) evaluating SGT-610 (patidegib gel, 2%) for the prevention "
         "of basal cell carcinoma lesions in adult patients with Gorlin syndrome")
LABEL = "Monday, November 30, 2026, 8:00 am ET (conference call on top-line results)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8").read()
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    row = next((r for r in rows if r["id"] == ID), None)
    if not row:
        print(f"{ID}: not in dataset, skipped")
        return 0
    d = row["_d"]
    assert row["t"] == "SLGL" and row["st"] == "Guided" and "SGT-610" in d.get("program", ""), row
    if row.get("dp") == "day" and row.get("d") == "2026-11-30":
        print(f"{ID}: already Nov 30 (day)")
        return 0
    if (d.get("resolution") or {}).get("state"):
        print(f"{ID}: already resolved, left alone")
        return 0
    hist = d.get("date_history") or []
    hist.append({"date": "2026-11-30", "changed": "2026-11-28",
                 "why": "Sol-Gel's release of 2026-11-27 names the day: “" + QUOTE + "”. Was 2026-11-30 "
                        "(month, “late November 2026”, release 2026-11-12)."})
    d.update({"date_history": hist, "guided_precision": "day", "guided_window": "2026-11-30", "guided_label": LABEL,
              "guided_form": "press release", "guided_filed": "2026-11-27", "guidance_text": QUOTE,
              "source_url": URL, "accession": None,
              "red_team": "2026-11-28: Sol-Gel release 2026-11-27 headline and first paragraph read; same trial "
                          "(SGT-610-01, patidegib gel 2%, Gorlin syndrome, NCT06050122 per the earlier pass); the call "
                          "is to discuss top-line results. 8:00 am ET = 5:00 am PT."})
    d.pop("accession", None)
    row.update({"d": "2026-11-30", "dp": "day", "url": URL, "ua": "2026-11-28T02:10:00Z"})
    row.pop("dm", None)
    if a.dry_run:
        print(json.dumps(row, indent=1)[:1500])
        return 0
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=True) + src[j:])
    print(f"{ID} -> 2026-11-30 (day)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
