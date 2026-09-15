# -*- coding: utf-8 -*-
"""ONE OWNER for how a non-day PDUFA date is written, everywhere on the site.

Audit 2026-09-14 item 5: "Every value that appears on more than one surface needs a single owner
and a cross-surface equality check in CI." This is that owner for the goal-date window.

WHY IT WAS NEEDED. On 09-10 twelve year-end rows lost a manufactured day. The calendar learned;
the event pages did not, and kept "Dec 31 2026" in their <title>, meta description, FAQ answer
and Event schema. Worse, the calendar disagreed with ITSELF: the same four events rendered as
"Dec 2026" on /calendar/2026/december and "Q4 2026 (est.)" on /calendar. One event, two labels,
both live, because two renderers each formatted the date their own way.

THE RULE. A window label is a function of the dataset row and nothing else:
    month   -> "Dec 2026"          (we know the month; say the month)
    quarter -> "Q3 2026"
    year    -> "2026"
    day     -> the ISO day, unchanged
An UNBACKED page -- one with no dataset row behind it at all -- has no window to derive, and
that absence is the finding, not something to paper over with a prettier string. Those get
UNSOURCED_LABEL and are expected to say so in words.

Every renderer imports from here. A renderer that formats its own is the defect.
"""
import datetime as dt

MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MON_FULL = ["", "January", "February", "March", "April", "May", "June", "July",
            "August", "September", "October", "November", "December"]

#: what a page says when NO dataset row backs it and no source states a date
UNSOURCED_LABEL = "Date not sourced"


def _ym(row):
    dm = str(row.get("dm") or "")
    if len(dm) >= 7:
        return int(dm[:4]), int(dm[5:7])
    d = str(row.get("d") or "")
    if len(d) >= 7:
        return int(d[:4]), int(d[5:7])
    return None, None


def window_label(row):
    """Short label, e.g. 'Dec 2026' / 'Q4 2026' / '2026' / '2026-11-30'."""
    dp = str(row.get("dp") or "day")
    y, m = _ym(row)
    if dp == "day":
        return str(row.get("d") or "")
    if y is None:
        return UNSOURCED_LABEL
    if dp == "quarter":
        return f"Q{(m - 1) // 3 + 1} {y}"
    if dp == "year":
        return str(y)
    return f"{MON[m]} {y}"


def window_label_long(row):
    """Prose form for body copy, e.g. 'December 2026' / 'the fourth quarter of 2026'."""
    dp = str(row.get("dp") or "day")
    y, m = _ym(row)
    if dp == "day":
        d = str(row.get("d") or "")
        if len(d) == 10:
            return f"{MON_FULL[int(d[5:7])]} {int(d[8:10])}, {y}"
        return d
    if y is None:
        return UNSOURCED_LABEL.lower()
    if dp == "quarter":
        nth = {1: "first", 2: "second", 3: "third", 4: "fourth"}[(m - 1) // 3 + 1]
        return f"the {nth} quarter of {y}"
    if dp == "year":
        return str(y)
    return f"{MON_FULL[m]} {y}"


def window_span(row):
    """(startDate, endDate) for Event schema. A window is a span, not a point."""
    dp = str(row.get("dp") or "day")
    y, m = _ym(row)
    if dp == "day":
        d = str(row.get("d") or "")
        return d, d
    if y is None:
        return None, None
    if dp == "year":
        return f"{y}-01-01", f"{y}-12-31"
    if dp == "quarter":
        q = (m - 1) // 3 + 1
        s = (q - 1) * 3 + 1
        e = s + 2
    else:
        s = e = m
    last = (dt.date(y + (e == 12), (e % 12) + 1, 1) - dt.timedelta(days=1)).day
    return f"{y}-{s:02d}-01", f"{y}-{e:02d}-{last:02d}"


def is_day(row):
    return str(row.get("dp") or "day") == "day"


def earliness_allowed(row):
    """May a page say "N days early" for this row?

    Audit 2026-09-14 P0-C. We published "82 Days Early" in the <title> of
    /fda-decision/BAYRY-2026-09-09, measured against a November 30 goal date that the SAME PAGE
    said was never sourced. The page contradicted itself, and 82 days would have been the
    second-largest early margin on the site.

    The rule already governs the timing statistic (build_early_decisions gates on dp == "day"
    after the 09-10 pass). It has to govern the renderers too, or the number simply reappears one
    layer up -- which is precisely what happened. An unsourced goal rounded to a late day
    produces, by construction, the largest possible earliness in the most flattering direction.

    THE TEST IS PRECISION, AND ONLY PRECISION. My first version also demanded `_d.source_url`,
    which sounds stricter and better and is neither: 25 of the 30 day-precision decided rows have
    no source_url merely because that field has not been back-filled, so the rule would have
    stripped the earliness figure from almost the whole archive -- REGN, RARE, BMY, MRK and the
    rest -- while /research/fda-decision-timing went on counting all 30. That is a NEW
    cross-surface contradiction introduced while fixing one, which is the opposite of the job.

    Precision already carries the meaning. The 09-10 pass did not annotate unsourceable days, it
    DOWNGRADED them: a goal we cannot trace to a filing stops being `dp: "day"` and becomes a
    month, quarter or year. So `dp == "day"` is exactly the statement "we stand behind this day",
    and it is the same gate build_early_decisions.collect() uses. One rule, one meaning.
    """
    return is_day(row)


def earliness_refusal(row):
    """The sentence a page uses instead of a number, saying why."""
    if not is_day(row):
        return ("We do not state how early this decision was: the goal date we hold for it is "
                "a window, not a day, so there is no day to measure against.")
    return ("We do not state how early this decision was: the goal date we had carried for it "
            "was never sourced to a filing or company release, and an unsourced goal cannot "
            "measure earliness.")
