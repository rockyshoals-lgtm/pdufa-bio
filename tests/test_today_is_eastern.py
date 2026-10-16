# -*- coding: utf-8 -*-
"""CI guard: every rendered "today" on the daily pages is the Eastern build date (audit 2026-10-13 P1, RULE 1).

/fda-decisions-today read "No FDA decision ... has been published today, October 14, 2026" at 22:20 Eastern on
October 13: build_today_page.py took dt.date.today() from the runner's UTC clock, and every nightly build lands
20:00 to 21:30 Eastern, after midnight UTC, so the page was a day ahead for four hours every night. This reads
the rendered pages and fails when any "today, {date}" / "as of {date}" / "Today is {date}" they print differs
from site_dates.eastern_today() (the same value build-info's `as_of_eastern` carries).

Plant: PLANT_UTC_TODAY=1 substitutes tomorrow's date for one page's "today" in memory and must FAIL.

    python tests/test_today_is_eastern.py
"""
import datetime as dt
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from site_dates import eastern_today, MONTHS  # noqa: E402

PAGES = ["fda-decisions-today/index.html", "fda-this-month/index.html", "fda-approval-decisions-this-week/index.html",
         "index.html", "calendar/index.html"]
TODAY_RX = re.compile(r"(?:\btoday,|\bas of|\bToday is|\bpublished today,?)\s*(?:<[^>]+>\s*)*"
                      r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
                      r" \d{1,2}, \d{4})")


def main():
    td = eastern_today()
    want = f"{MONTHS[td.month]} {td.day}, {td.year}"
    tomorrow = td + dt.timedelta(days=1)
    plant = f"{MONTHS[tomorrow.month]} {tomorrow.day}, {tomorrow.year}"
    fails, n = [], 0
    for rel in PAGES:
        p = os.path.join(SITE, rel.replace("/", os.sep))
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        found = sorted(set(m.group(1) for m in TODAY_RX.finditer(doc)))
        if os.environ.get("PLANT_UTC_TODAY") == "1" and rel.startswith("fda-decisions-today"):
            found = [plant]
        for f in found:
            n += 1
            if f != want:
                fails.append(f"/{rel.replace('/index.html', '')}: says today is {f}; the Eastern build date is {want}")
    # 2026-10-16: test_lede_matches_table counted /calendar with the runner's UTC date at 21:49 ET and blocked a
    # correct deploy. ~25 builders/guards still call dt.date.today(); the job must run them on Eastern time.
    wf = io.open(os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml"), encoding="utf-8").read()
    if os.environ.get("PLANT_NO_TZ") == "1":
        wf = wf.replace("TZ: America/New_York", "")
    if not re.search(r"(?m)^  rebuild:\n(?:    .*\n)*?    env:\n(?:      .*\n)*?      TZ: America/New_York\s*$", wf):
        fails.append(".github/workflows/pdufa-rebuild.yml: the rebuild job does not set env TZ: America/New_York, so "
                     "every dt.date.today() on the runner is the UTC date (a day ahead from 20:00 ET)")
    if fails:
        print("FAIL: a page calls the wrong calendar day 'today' (RULE 1: Eastern, not the runner's UTC clock):")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} 'today' stamp(s) across the daily pages all read {want} (Eastern).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
