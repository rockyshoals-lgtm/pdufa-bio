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

Rebuild 45940203634 (2026-11-27, built 00:01 ET after the midnight guard waited) failed this guard on a
TRUE page: /fda-this-month said "Page updated November 26" because nothing on it had changed since the
Nov 26 build (November had 0 decisions left, December's preview unchanged). "Page updated" is the
content-change date (build_freshness_stamp.py; tests/test_datemodified_honest.py checks it), so stamping
Nov 27 there would have been the false claim. A daily page now passes when its one stamp is today OR its
own content-change date from _sitemap_lastmod.json, and never later than today Eastern -- a UTC clock
after 7 PM ET still lands on tomorrow and still fails.
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


# Audit 2026-10-11 order 5: the freshness strip's "Data as of {Eastern rebuild time}" is baked into the
# static text (it was a placeholder). It names a DIFFERENT fact from "Page updated {content date}": when
# the dataset was rebuilt, not when this page's content changed. Two named facts are not two dates for
# one thing, so that span is excluded here; every other stamp on a page must still agree.
BUILT_SPAN = re.compile(r'<span data-fresh-built[^>]*>.*?</span>', re.S)


def stamps(doc):
    out = set()
    doc = BUILT_SPAN.sub("", doc)
    for m in STAMP.finditer(doc):
        d = to_date(m.group(1))
        if d:
            out.add(d)
    return out


LASTMOD = os.path.join(HERE, "_sitemap_lastmod.json")


def content_date(page_path):
    """The content-change date the sitemap state holds for this page, or None."""
    try:
        import json
        st = json.load(io.open(LASTMOD, encoding="utf-8"))
    except Exception:
        return None
    rel = os.path.relpath(page_path, HERE).replace("\\", "/")
    d = (st.get(rel) or {}).get("date")
    try:
        return dt.date.fromisoformat(d) if d else None
    except ValueError:
        return None


def daily_ok(found, today, changed):
    """A daily page's one stamp is today, or its own content-change date; never after today Eastern."""
    (d,) = found
    if d > today:
        return False
    return d == today or (changed is not None and d == changed)


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
                and not daily_ok(found, today, content_date(p)):
            bad.append(f"{rel}: stamped {next(iter(found))}, Eastern build date is {today}")
    assert not bad, "page(s) stamped with more than one date, or the wrong clock:\n  " \
        + "\n  ".join(bad)


def test_daily_ok_self_check():
    t = dt.date(2026, 11, 27)
    y = dt.date(2026, 11, 26)
    assert daily_ok({t}, t, None)
    assert daily_ok({y}, t, y)                        # unchanged since yesterday: the honest stamp
    assert not daily_ok({y}, t, None)                 # stale with no content date behind it
    assert not daily_ok({y}, t, dt.date(2026, 11, 20))  # stamp disagrees with its content date
    assert not daily_ok({dt.date(2026, 11, 28)}, t, dt.date(2026, 11, 28))  # UTC clock ahead of Eastern


if __name__ == "__main__":
    test_daily_ok_self_check()
    test_one_date_per_page()
    print("OK")
