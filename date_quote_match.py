# -*- coding: utf-8 -*-
"""date_quote_match.py -- does a quoted source sentence state the date a row publishes?

One rule, shared by the guard (tests/test_quote_states_date.py) and anyone applying a fix.

pdufa.bio publishes a date for every open PDUFA goal and every company-guided readout, and next to
it the sponsor's own words (`_d.source_quote` for PDUFA rows, `_d.guidance_text` for guided
readouts). If those words do not contain the date at the precision we print, the row is either
mis-keyed (the date moved and the quote did not) or the quote was pasted from a different sentence.
Both have happened; both look fine on the page.

What "states the date" means, by the row's precision (`dp`):
  day      the month and the day of `d` (any common spelling: "November 30, 2026", "Nov. 30",
           "30 November 2026", "11/30/2026", "2026-11-30").
  month    the month name of `d` (the year must agree if the quote gives one next to it).
  quarter  the quarter of `d` and its year ("fourth quarter of 2026", "Q4 2026", "4Q26", "4Q 2026").
  half     the half of `d` and its year ("first half of 2027", "1H 2027", "H1 2027", "1H27"),
           or "mid-<year>" for a half ending in June.
  year     the year of `d`, or "end of <year>" / "year-end <year>".
A window end is the LAST day of the window, so a quarter row keyed 2026-12-31 needs Q4 2026.

Quotes are compared after normalising whitespace, dashes and non-breaking spaces. Matching is
deliberately lenient about spelling and strict about the value: "fourth quarter" passes for a Q4
row; "third quarter" never does.
"""
import datetime as dt
import re

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
          "october", "november", "december"]
ABBR = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
ORD_Q = {1: "first", 2: "second", 3: "third", 4: "fourth"}
ORD_H = {1: "first", 2: "second"}


def norm(s):
    s = (s or "").replace(" ", " ").replace("‑", "-").replace("–", "-").replace("—", "-")
    s = s.replace("’", "'").replace("…", " ")
    s = re.sub(r"\s+", " ", s).strip().lower()
    # 2026-11-25: "CY2027" (calendar year 2027, Immutep's wording) states the year 2027.
    return re.sub(r"\bcy\s?(20\d\d)\b", r"calendar year \1", s)


def _month_pat(m):
    full, ab = MONTHS[m - 1], ABBR[m - 1]
    alts = {full, ab + r"\.?"}
    if m == 9:
        alts.add(r"sept\.?")
    return "(?:" + "|".join(sorted(alts, key=len, reverse=True)) + ")"


def _year_pats(y):
    return [str(y), "'" + str(y)[2:]]


def states_day(q, d):
    m, day, y = d.month, d.day, d.year
    mp = _month_pat(m)
    pats = [
        rf"\b{mp}\s+{day}(?:st|nd|rd|th)?\b",
        rf"\b{day}(?:st|nd|rd|th)?\s+(?:of\s+)?{mp}\b",
        rf"\b0?{m}/0?{day}/(?:{y}|{str(y)[2:]})\b",
        rf"\b{y}-{m:02d}-{day:02d}\b",
    ]
    return any(re.search(p, q) for p in pats)


def states_month(q, d):
    return re.search(rf"\b{_month_pat(d.month)}\b", q) is not None and _year_ok(q, d.year)


def _year_ok(q, y):
    # if the quote names years at all, the row's year must be among them (a month-only "December"
    # with no year is accepted: sponsors say "in December" in a release dated that year).
    years = set(re.findall(r"\b(20\d\d)\b", q))
    if not years:
        return True
    return str(y) in years


def states_quarter(q, d):
    n = (d.month - 1) // 3 + 1
    y, yy = d.year, str(d.year)[2:]
    pats = [
        rf"\b{ORD_Q[n]}[- ]quarter(?: of)?(?: (?:calendar|fiscal) year)?(?: of)?(?: the year)?,? (?:of )?{y}\b",
        rf"\b{ORD_Q[n]}[- ]quarter\b[^.;]{{0,40}}\b{y}\b",
        rf"\bq{n}[ -]?(?:of )?(?:{y}|'?{yy})\b",
        rf"\b{n}q[ -]?(?:{y}|'?{yy})\b",
        rf"\b{y}[ -]q{n}\b",
    ]
    return any(re.search(p, q) for p in pats)


def states_half(q, d):
    n = 1 if d.month <= 6 else 2
    y, yy = d.year, str(d.year)[2:]
    pats = [
        rf"\b{ORD_H[n]}[- ]half(?: of)?(?: (?:calendar|fiscal) year)?(?: of)?,? (?:of )?{y}\b",
        rf"\b{ORD_H[n]}[- ]half\b[^.;]{{0,40}}\b{y}\b",
        rf"\bh{n}[ -]?(?:of )?(?:{y}|'?{yy})\b",
        rf"\b{n}h[ -]?(?:{y}|'?{yy})\b",
    ]
    if n == 1:
        pats.append(rf"\bmid[- ]?(?:year[- ])?{y}\b|\bmid[- ]?year,? {y}\b")
    if n == 2:
        pats.append(rf"\b(?:end|close) of {y}\b|\byear[- ]end {y}\b|\bby the end of (?:the year|{y})\b")
    return any(re.search(p, q) for p in pats)


def states_year(q, d):
    return re.search(rf"\b{d.year}\b", q) is not None or re.search(rf"\b(?:fy|year[- ]end )?'{str(d.year)[2:]}\b", q) is not None


CHECK = {"day": states_day, "month": states_month, "quarter": states_quarter, "half": states_half,
         "year": states_year}


def resolve_relative_years(q, ref):
    """Rewrite "this year" / "next year" / "later this year" as the calendar year they mean, using
    the date the sponsor wrote the sentence (`ref`, a date). Without `ref` nothing is rewritten."""
    if not ref:
        return q
    q = re.sub(r"\b(?:this|the current) (?:calendar )?year\b", str(ref.year), q)
    q = re.sub(r"\bnext (?:calendar )?year\b", str(ref.year + 1), q)
    # "before/by the end of the year" written in a dated release means that release's calendar year.
    q = re.sub(r"\b(?:the )?end of the year\b", f"end of {ref.year}", q)
    q = re.sub(r"\b(first|second|third|fourth) quarter of (?:the )?year\b", rf"\1 quarter of {ref.year}", q)
    return q


def quote_states_date(quote, d_iso, dp, ref_iso=None):
    """True if `quote` states `d_iso` at precision `dp`. Unknown precision -> False.
    `ref_iso`: the date the quoted document was published, used only to read "this year" and
    "next year" as the years they meant when written."""
    q = norm(quote)
    ref = None
    if ref_iso:
        try:
            ref = dt.date.fromisoformat(str(ref_iso)[:10])
        except Exception:
            ref = None
    q = resolve_relative_years(q, ref)
    if not q:
        return False
    try:
        d = dt.date.fromisoformat(d_iso)
    except Exception:
        return False
    fn = CHECK.get((dp or "").lower())
    return bool(fn and fn(q, d))
