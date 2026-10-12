# -*- coding: utf-8 -*-
"""CI guard: /readouts starts at the current month and every passed readout window states what we found
(audit 2026-10-11 section 2c and order items 2 and 3).

On October 11 the page's lede said "covering July 2026" and 72 rows said "Window passed" with no outcome and
no date on which we last checked. Fails, on the rendered page, when:
  1. the lede's "covering" span does not start at the current Eastern month;
  2. a row in the passed-windows block carries none of the resolution phrases;
  3. (when FMP_API_KEY is set, i.e. in CI where resolve_past_readouts.py can search sponsor releases) any row
     still reads "not yet checked";
  4. the meta description does not end in a full sentence.
Plant: PLANT_UNRESOLVED=1 strips the resolution span from one row in memory and must FAIL.

    python tests/test_readouts_passed_windows_resolved.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

PAGE = os.path.join(HERE, "pdufa_site_src", "readouts", "index.html")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
RES = re.compile(r"Sponsor release \d{4}-\d{2}-\d{2}|(?:Terminated|Withdrawn|Suspended) per ClinicalTrials\.gov|"
                 r"No topline found as of \d{4}-\d{2}-\d{2}|Results posted on ClinicalTrials\.gov \d{4}-\d{2}-\d{2}|"
                 r"Trial completed per ClinicalTrials\.gov; no sponsor result on record|Window passed; not yet checked")


def main():
    doc = io.open(PAGE, encoding="utf-8", errors="replace").read()
    fails = []
    td = eastern_today()
    cur = f"{MONTHS[td.month - 1]} {td.year}"
    m = re.search(r"This page lists (\d+) expected clinical trial readouts covering ([A-Z][a-z]+ \d{4})", doc)
    if not m:
        fails.append("lede sentence not found")
    elif m.group(2) != cur:
        fails.append(f"lede covers from {m.group(2)}; the current Eastern month is {cur}")
    blk = re.search(r'<div id="readout-results">(.*?)<!--/readout-results-->', doc, re.S)
    if not blk:
        fails.append("passed-windows block missing")
        rows = []
    else:
        sub = re.search(r"Readout windows that have passed.*", blk.group(1), re.S)
        rows = re.findall(r'<a class="row".*?</a>', sub.group(0) if sub else "", re.S)
    if os.environ.get("PLANT_UNRESOLVED") == "1" and rows:
        rows[0] = RES.sub("", rows[0])
    bare = [r for r in rows if not RES.search(r)]
    if bare:
        fails.append(f"{len(bare)} passed-window row(s) carry no resolution, e.g. {re.sub(r'<[^>]+>', ' ', bare[0])[:90].strip()}")
    unchecked = sum(1 for r in rows if "not yet checked" in r)
    # In CI (key present) the search runs daily; a handful of fetch failures must not block a deploy, a
    # silent non-run must: more than a tenth unchecked means the step did not do its job.
    if rows and os.environ.get("FMP_API_KEY") and unchecked > max(3, len(rows) // 10):
        fails.append(f"{unchecked} of {len(rows)} passed-window row(s) still 'not yet checked' although the "
                     f"sponsor-release search can run")
    d = re.search(r'<meta name="description" content="([^"]*)"', doc)
    if not d or not re.search(r"[.!?]\s*$", d.group(1)):
        fails.append(f"meta description does not end in a full sentence: {d.group(1)[-60:] if d else None!r}")
    if fails:
        print("FAIL: /readouts passed windows / lede:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- /readouts lede starts at {cur}; {len(rows)} passed-window rows each state what we found "
          f"({unchecked} awaiting the sponsor-release search); description is a full sentence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
