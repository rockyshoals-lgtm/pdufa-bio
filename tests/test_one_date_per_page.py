# -*- coding: utf-8 -*-
"""One calendar date per page, and it is the Eastern date of the build.

Audit 2026-09-07 C2: the first build to straddle UTC midnight (03:47Z = 23:47 ET Sept 6)
printed "Updated September 7, 2026" in the freshness header (build_sitemap.py's UTC TODAY
feeding the content-change state) while the same tree's ledes and JSON-LD said September 6
(site_dates.eastern_stamp). Two dates for one build is the site contradicting itself about
the one thing it sells. Every stamper now draws from site_dates; this asserts the RENDER:

  * on every page checked, all "Updated / updated / as of / Last computed" dates agree;
  * on the pages rebuilt every day (/calendar, /fda-this-month, /runup-by-year) that date is
    the Eastern date the build ran on (site_dates.eastern_today()), not the UTC one.

Drug pages are checked for internal agreement only: an unchanged drug page keeps its
content-change date on purpose (build_freshness_stamp.py), so it need not equal today.

Proved 0 -> 1 -> 0 on 2026-09-07 by planting "Updated Sep 8, 2026" on /runup-by-year.
"""
import datetime as dt
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from site_dates import eastern_today, MONTHS  # noqa: E402

DAILY = ["calendar/index.html", "fda-this-month/index.html", "runup-by-year/index.html"]
LONG = {m: i for i, m in enumerate(MONTHS) if m}
SHORT = {m[:3]: i for i, m in enumerate(MONTHS) if m}
STAMP = re.compile(r"(?:Updated|updated|as of|Last computed)\s*(?:<[^>]+>\s*)*"
                   r"((?:[A-Z][a-z]+\.? \d{1,2}, \d{4})|(?:\d{4}-\d{2}-\d{2}))")


def to_date(s):
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return dt.date.fromisoformat(s)
    mon, day, year = re.match(r"^([A-Za-z]+)\.? (\d{1,2}), (\d{4})$", s).groups()
    mi = LONG.get(mon) or SHORT.get(mon[:3])
    return dt.date(int(year), mi, int(day)) if mi else None


def stamps(doc):
    out = set()
    for m in STAMP.finditer(doc):
        d = to_date(m.group(1))
        if d:
            out.add(d)
    return out


def test_one_date_per_page():
    today = eastern_today()
    bad = []
    pages = [os.path.join(SITE, p) for p in DAILY]
    pages += sorted(glob.glob(os.path.join(SITE, "drug", "*", "index.html")))
    for p in pages:
        if not os.path.isfile(p):
            continue
        rel = "/" + os.path.relpath(p, SITE).replace("\\", "/").replace("/index.html", "")
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        found = stamps(doc)
        if len(found) > 1:
            bad.append(f"{rel}: {len(found)} different stamp dates on one page: "
                       + ", ".join(sorted(d.isoformat() for d in found)))
        elif found and p.endswith(tuple(d.replace("/", os.sep) for d in DAILY)) \
                and found != {today}:
            bad.append(f"{rel}: stamped {next(iter(found))}, Eastern build date is {today}")
    assert not bad, "page(s) stamped with more than one date, or the wrong clock:\n  " \
        + "\n  ".join(bad)


if __name__ == "__main__":
    test_one_date_per_page()
    print("OK")
