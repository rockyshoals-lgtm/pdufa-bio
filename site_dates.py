# -*- coding: utf-8 -*-
"""site_dates.py -- the ONE calendar date a build stamps on its pages.

Audit 2026-09-05 (0800 slot) P2-7: a build at 00:21Z on Sept 6 stamped "as of September 6,
2026" on /calendar and "Updated September 6, 2026" on drug pages while it was 20:21 ET /
17:21 PT on Sept 5 and the API said as_of 2026-09-05. The stamps came from
datetime.date.today() on a UTC runner. The market, FMP and company releases are Eastern
(CLAUDE.md rule 1), so the site's calendar date is the EASTERN date of the build, from
here, everywhere a page prints one.
"""
import datetime as dt

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:            # no tz database: fall back to a fixed -4/-5 guess is worse than UTC-4
    _ET = dt.timezone(dt.timedelta(hours=-4))

MONTHS = ["", "January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def eastern_today():
    """The Eastern calendar date right now (what a reader in New York calls 'today')."""
    return dt.datetime.now(dt.timezone.utc).astimezone(_ET).date()


def eastern_stamp():
    """'September 6, 2026' for the Eastern date of this build."""
    d = eastern_today()
    return f"{MONTHS[d.month]} {d.day}, {d.year}"
