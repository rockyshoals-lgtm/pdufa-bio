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
import re

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


# Design change 8 red team (2026-11-18). Every count of calendar rows "still ahead" uses these two, so the
# /calendar lede, its ItemList, the homepage tile and the month chips agree on which rows are ahead:
#   - a row with a day is ahead while that day is today or later;
#   - a row with only a month or a quarter ("Nov 2026", "Q1 2027") is ahead while its window has not ended;
#   - a "(est.)" row is an estimate with no source behind it and is never counted as a goal date.
_MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def row_is_estimate(text):
    return re.search(r"\(est\.?\)", text, re.I) is not None


def window_end(text):
    """The last ISO day of the window a dateless row names ("Nov 2026", "Q4 2026", "H1 2027"), or None."""
    m = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})\b", text)
    if m:
        y, mo = int(m.group(2)), _MON.index(m.group(1).lower()) + 1
    else:
        q = re.search(r"\bQ([1-4])\s+(\d{4})\b", text)
        h = re.search(r"\bH([12])\s+(\d{4})\b", text)
        if q:
            y, mo = int(q.group(2)), int(q.group(1)) * 3
        elif h:
            y, mo = int(h.group(2)), int(h.group(1)) * 6
        else:
            return None
    nxt = dt.date(y + (mo == 12), mo % 12 + 1, 1)
    return (nxt - dt.timedelta(days=1)).isoformat()


def row_ahead(text, iso, today):
    """True when a pending (undecided) calendar row is still ahead of `today` (ISO), by the rules above."""
    if row_is_estimate(text):
        return False
    if iso:
        return iso >= today
    end = window_end(text)
    return end is None or end >= today
