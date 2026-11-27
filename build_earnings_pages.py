# -*- coding: utf-8 -*-
"""build_earnings_pages.py -- /earnings and /earnings/<TICKER>: the quarterly-results dates companies announce, from
their own press releases.

David, 2026-11-26 21:07 UTC: "Concurrently continue our moat increase add earning dates ...".

Reads _earnings_dates.json (fetch_earnings_dates.py: the companies' own releases on the newswires, timestamps Eastern,
CLAUDE.md RULE 1). Nothing here is estimated: a report day appears only when the company's own release names it, and a
results date is the newswire timestamp of the company's results release.

  * /earnings: report days companies have announced that are still ahead; results released in the last 30 days; the
    days from each calendar quarter's end to the results release, across companies; every ticker with a page; a CSV of
    every row (CC BY 4.0)
  * /earnings/<TICKER>: one page per ticker with at least two results releases or an announced day still ahead: every
    period with the day the company announced, when the results went out, and the days after the period ended

A report day counts as ahead when its date is today or later (Eastern), no results release for the same period has
been read, and the company has not put out a postponement for that period after announcing it. When a company
announced a period twice, the later announcement is used and the earlier day is named.

FACTS ONLY: dates as the companies' releases print them. No estimates, no forecasts, no view on any company.

    python build_earnings_pages.py [--cache PATH] [--site DIR] [--today YYYY-MM-DD]
"""
import argparse
import collections
import csv
import datetime as dt
import io
import json
import os
import re
import shutil
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_crl_companies import BASE, page  # noqa: E402
from build_crl_facts import esc, pretty  # noqa: E402
from fetch_earnings_dates import period_end  # noqa: E402
from site_dates import eastern_today  # noqa: E402

CACHE = os.path.join(HERE, "_earnings_dates.json")
SEC_CACHE = os.path.join(HERE, "_earnings_sec.json")
SEC_SITE = "SEC EDGAR (Form 8-K, Item 2.02)"
# fetch_earnings_sec.py stores the median minutes from the newswire release to the 8-K accepted the same day; a few
# minutes to a few hours is normal (filers furnish the release after it goes out). Outside this range the 8-K times
# are being read in the wrong time zone, and no 8-K row is used.
SEC_CHECK_MIN, SEC_CHECK_MAX = -30, 240
SITE = os.path.join(HERE, "pdufa_site_src")
RECENT_DAYS = 30
MIN_PERIODS = 2          # a ticker page needs this many periods read, or an announced day ahead or passed
TICKER_OK = re.compile(r"^[A-Z][A-Z0-9.]{0,6}$")
COLUMNS = ["ticker", "company", "kind", "period", "period_key", "published_et", "report_date", "timing_words",
           "call_time", "release_title", "release_url", "newswire_site", "ticker_page"]


def d_of(s):
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def fmt_et(s):
    """'2026-10-28 16:05' -> 'October 28, 2026, 4:05 p.m. ET' (the cache's times are Eastern already)."""
    try:
        t = dt.datetime.strptime(str(s)[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        d = d_of(s)
        return pretty(d) if d else str(s or "")
    h = t.hour % 12 or 12
    return f"{pretty(t.date())}, {h}:{t.minute:02d} {'a.m.' if t.hour < 12 else 'p.m.'} ET"


def fetched_et(s):
    """The cache's UTC 'fetched' stamp as an Eastern calendar date ('November 26, 2026'), or ''."""
    try:
        t = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return ""
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        t = t.astimezone(ZoneInfo("America/New_York"))
    except Exception:  # noqa: BLE001
        t = t - dt.timedelta(hours=5)
    return pretty(t.date())


def ok_url(u):
    return isinstance(u, str) and u.startswith("https://")


def is_8k(r):
    return (r or {}).get("site") == SEC_SITE


def sec_rows(path):
    """ticker -> results rows from the companies' own 8-K filings under Item 2.02 (fetch_earnings_sec.py), only those
    whose Item 2.02 text names the period and calls them results, and only while the cache's time self-check holds.
    Returns ({}, reason) when the 8-K rows are not used."""
    try:
        c = json.load(io.open(path, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}, "no 8-K cache"
    chk = c.get("check") or {}
    med = chk.get("median_min")
    if chk.get("n", 0) >= 10 and (med is None or not SEC_CHECK_MIN <= med <= SEC_CHECK_MAX):
        return {}, f"8-K times fail the self-check (median {med} min from the newswire release over {chk.get('n')})"
    out = {}
    for tk, ent in (c.get("tickers") or {}).items():
        if not TICKER_OK.match(tk or "") or not isinstance(ent, dict):
            continue
        for acc, f in sorted((ent.get("filings") or {}).items()):
            if not isinstance(f, dict) or f.get("status") != "results" or not f.get("period_key"):
                continue
            a = str(f.get("accepted_et") or "")
            if not re.fullmatch(r"20\d\d-\d\d-\d\d \d\d:\d\d", a) or not ok_url(f.get("url")) or \
                    not str(f["url"]).startswith("https://www.sec.gov/Archives/edgar/data/"):
                continue
            out.setdefault(tk, []).append({
                "kind": "results", "published_et": a, "period": f.get("period") or "", "period_key": f["period_key"],
                "title": f"Form 8-K, Item 2.02 (Results of Operations and Financial Condition), filed "
                         f"{pretty(d_of(a))}", "url": f["url"], "site": SEC_SITE, "accession": acc})
    return out, ""


def norm_key(k):
    """One key per reporting period, however the releases print it: a calendar company's 'Fourth Quarter 2025',
    'Fourth Quarter and Year-End 2025' and 'Full Year 2025' releases are all about the period ending December 31, 2025
    (2025Q4); a fiscal year's results release is its fourth fiscal quarter's."""
    k = k or ""
    m = re.fullmatch(r"(20\d\d)(?:Q4\+FY|FY)", k)
    if m:
        return f"{m.group(1)}Q4"
    m = re.fullmatch(r"FY(20\d\d)", k)
    if m:
        return f"FY{m.group(1)}Q4"
    return k


def same_period(a, b):
    """Two period keys for one quarter: the same year and quarter with and without the 'FY' prefix, or two calendar
    keys that end on the same day (a first half and its second quarter)."""
    qa, qb = re.fullmatch(r"(?:FY)?(20\d\dQ[1-4])", a or ""), re.fullmatch(r"(?:FY)?(20\d\dQ[1-4])", b or "")
    if qa and qb:
        return qa.group(1) == qb.group(1)
    ea, eb = period_end(a), period_end(b)
    return bool(ea and ea == eb)


def periods(rel):
    """period -> {"schedules": [...] oldest first, "results": earliest results row, "postponed": [...], "keys": set of
    the period keys as parsed}. A postponement that names no period voids the pending announcement it follows: one
    published after the latest announcement of a period and no later than its report day."""
    out = collections.defaultdict(lambda: {"schedules": [], "results": None, "postponed": [], "keys": set()})
    loose = []
    ks = {r.get("period_key") or "" for r in rel}
    # a company that prints its quarters as calendar quarters ('Third Quarter 2026') and never as fiscal ones uses
    # 'fiscal year' for the calendar year ('Fourth Quarter and Fiscal Year 2025'): read those keys as calendar
    calendar_co = any(re.fullmatch(r"20\d\dQ[1-3]", k) for k in ks) and \
        not any(re.fullmatch(r"FY20\d\dQ[1-3]", k) for k in ks)
    for r in sorted(rel, key=lambda r: r.get("published_et") or ""):
        if not d_of(r.get("published_et")):
            continue
        if calendar_co:
            m = re.fullmatch(r"FY(20\d\d)(Q4)?", r.get("period_key") or "")
            if m:
                r = dict(r, period_key=f"{m.group(1)}Q4+FY" if m.group(2) else f"{m.group(1)}FY")
        kind, k0 = r.get("kind"), r.get("period_key")
        if kind == "postponed" and not k0:
            loose.append(r)
            continue
        if not k0:
            continue
        k = norm_key(k0)
        if kind == "schedule" and d_of(r.get("report_date")):
            out[k]["schedules"].append(r)
            out[k]["keys"].add(k0)
        elif kind == "results" and (out[k]["results"] is None or (is_8k(out[k]["results"]) and not is_8k(r))):
            # the company's newswire release is the record; its 8-K stands in only when no release was read
            out[k]["results"] = r
            out[k]["keys"].add(k0)
        elif kind == "postponed":
            out[k]["postponed"].append(r)
    # one period, two wordings: a schedule read as '2024Q3' and its results read as 'FY2024Q3' (a company whose fiscal
    # quarters are calendar ones), or as '2026H1' and '2026Q2'. When the results release came out on the announced day
    # or the next one and names the same quarter, it is that announcement's results: file it under the schedule's key
    for k in [k for k, p in out.items() if p["results"] and not p["schedules"]]:
        r, rd = out[k]["results"], d_of(out[k]["results"].get("published_et"))
        hits = [k2 for k2, p2 in out.items() if k2 != k and p2["schedules"] and not p2["results"]
                and same_period(k, k2) and 0 <= (rd - d_of(p2["schedules"][-1]["report_date"])).days <= 1]
        if len(hits) == 1:
            out[hits[0]]["results"] = r
            out[hits[0]]["keys"] |= out[k]["keys"]
            out[hits[0]]["postponed"] += out[k]["postponed"]
            del out[k]
    for p in out.values():
        if p["schedules"] and not p["results"]:
            s = p["schedules"][-1]
            p["postponed"] += [x for x in loose if x["published_et"] > s["published_et"]
                               and d_of(x["published_et"]) <= d_of(s["report_date"])]
    return out


def status_of(p, today):
    """For one period: (latest schedule or None, 'ahead' | 'reported' | 'postponed' | 'passed' | '')."""
    s = p["schedules"][-1] if p["schedules"] else None
    if p["results"]:
        return s, "reported"
    if s and any((x["published_et"] or "") > (s["published_et"] or "") for x in p["postponed"]):
        return s, "postponed"
    if s:
        return s, ("ahead" if d_of(s["report_date"]) >= today else "passed")
    return None, ("postponed" if p["postponed"] else "")


def days_after_end(k, r):
    """Calendar days from the end of the period the results release names to the release; None for fiscal periods."""
    end = period_end((r or {}).get("period_key") or k)
    d = d_of(r.get("published_et")) if r else None
    return (d - end).days if end and d else None


LEGAL_CASE = {"INC": "Inc", "CORP": "Corp", "CORPORATION": "Corporation", "LTD": "Ltd", "LIMITED": "Limited",
              "CO": "Co", "COMPANY": "Company", "HOLDINGS": "Holdings"}


def display_name(n):
    """A name filed in capitals ('ADMA BIOLOGICS, INC.') reads as 'ADMA Biologics, Inc.': words of four letters or
    fewer stay as filed (they are often the brand's own capitals), longer ones and legal forms take capitals only at
    the start. Any other name is left exactly as filed."""
    if not n.isupper() or len(n) <= 6:
        return n

    def one(w):
        core = w.strip(".,")
        if core in LEGAL_CASE:
            return w.replace(core, LEGAL_CASE[core])
        return w if len(core) <= 4 else w.replace(core, core.capitalize())
    return " ".join(one(w) for w in n.split(" "))


def load(path, sec_path=SEC_CACHE):
    c = json.load(io.open(path, encoding="utf-8"))
    sec, why = sec_rows(sec_path) if sec_path else ({}, "")
    c["_sec_note"] = why
    T = {}
    for tk, v in (c.get("tickers") or {}).items():
        if not TICKER_OK.match(tk or "") or not isinstance(v, dict):
            continue
        rel, seen = list(sec.get(tk, [])), set()
        for r in (v.get("releases") or []):
            # the feed sometimes carries one release twice (same time, same headline): count it once
            key = (r.get("published_et"), (r.get("title") or "").strip().lower()) if isinstance(r, dict) else None
            if key and ok_url(r.get("url")) and key not in seen:
                seen.add(key)
                rel.append(r)
        if rel:
            T[tk] = {"name": display_name(v.get("name") or tk), "rel": rel, "P": periods(rel)}
    return c, T


ORDN = {"1": "first", "2": "second", "3": "third", "4": "fourth"}


def label(k, p=None):
    """The period in one wording, from its key: 'Q3 2026', 'Q4 and full year 2025', 'Fiscal 2027 Q1', 'First half
    2026'."""
    keys = (p or {}).get("keys") or set()
    m = re.fullmatch(r"(20\d\d)Q([1-4])", k)
    if m:
        y, q = m.group(1), m.group(2)
        if q == "4" and keys and keys <= {f"{y}FY"}:
            return f"Full year {y}"            # every release names only the year, never a fourth quarter
        full = q == "4" and any(re.fullmatch(r"20\d\d(Q4\+FY|FY)", x) for x in keys)
        return f"Q{q} {'and full year ' if full else ''}{y}"
    m = re.fullmatch(r"FY(20\d\d)Q([1-4])", k)
    if m:
        y, q = m.group(1), m.group(2)
        if q == "4" and keys and keys <= {f"FY{y}"}:
            return f"Fiscal year {y}"
        full = q == "4" and f"FY{y}" in keys
        return f"Fiscal {y} Q{q}" + (" and fiscal year" if full else "")
    m = re.fullmatch(r"(20\d\d)H([12])", k)
    if m:
        return f"{'First' if m.group(2) == '1' else 'Second'} half {m.group(1)}"
    return k


def rel_link(r, text=None):
    if is_8k(r) and text in (None, "release", "results"):
        text = "8-K"
    return f'<a href="{esc(r["url"])}" rel="noopener nofollow">{esc(text or "release")}</a>'


def res_time(r):
    """When the results went out, as the source shows it: the newswire time, or the 8-K's acceptance time marked."""
    return esc(fmt_et(r["published_et"])) + (" (8-K filed)" if is_8k(r) else "")


def when(s):
    w = (s.get("timing_words") or "").strip()
    ct = (s.get("call_time") or "").strip()
    bits = []
    if w:
        bits.append(f'&ldquo;{esc(w)}&rdquo;')
    if ct:
        bits.append(f'call {esc(ct)}')
    return "; ".join(bits) or "not stated"


def gather(T, today):
    ahead, recent, passed, by_q = [], [], [], collections.defaultdict(list)
    for tk, t in T.items():
        for k, p in t["P"].items():
            s, st = status_of(p, today)
            if st == "ahead":
                ahead.append((d_of(s["report_date"]), tk, k, s, p))
            elif st == "passed":
                passed.append((d_of(s["report_date"]), tk, k, s))
            r = p["results"]
            if r:
                rd = d_of(r["published_et"])
                if 0 <= (today - rd).days < RECENT_DAYS:
                    recent.append((r["published_et"], tk, k, r))
                n = days_after_end(k, r)
                m = re.fullmatch(r"(20\d\d)Q([1-4])(\+FY)?", k)
                # quarter stats count a release only when its own headline names the quarter: a full-year-only or
                # half-year release (annual and semiannual filers) is not a quarterly report
                # and the newswire time only: an 8-K's filing time is not the release time
                if n is not None and m and not is_8k(r) and re.fullmatch(r"20\d\dQ[1-4](\+FY)?", r.get("period_key") or ""):
                    by_q[(int(m.group(1)), int(m.group(2)))].append((n, tk))
    ahead.sort(key=lambda x: (x[0], x[1]))
    recent.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return ahead, recent, passed, by_q


def has_page(t, today):
    """A company page needs two periods read (any mix of announced days and results), or an announced day ahead or
    passed, so every row the hub lists in short has a page that shows it in full."""
    return len(t["P"]) >= MIN_PERIODS or any(status_of(p, today)[1] in ("ahead", "passed") for p in t["P"].values())


def write_csv(T, path, pages):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = []
    for tk, t in T.items():
        for r in t["rel"]:
            if r.get("kind") not in ("schedule", "results", "postponed"):
                continue
            rows.append([tk, t["name"], "results_8k" if is_8k(r) else r.get("kind"), r.get("period") or "", r.get("period_key") or "",
                         r.get("published_et") or "", r.get("report_date") or "", r.get("timing_words") or "",
                         r.get("call_time") or "", r.get("title") or "", r.get("url"), r.get("site") or "",
                         f"{BASE}/earnings/{tk}" if tk in pages else ""])
    rows.sort(key=lambda x: (x[0], x[5], x[2]))
    with io.open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        w.writerows(rows)
    return len(rows)


def co(tk, T, pages):
    nm = esc(T[tk]["name"])
    return (f'<a href="/earnings/{esc(tk)}">{nm} ({esc(tk)})</a>' if tk in pages else f'{nm} ({esc(tk)})')


SOURCE = ('Every date on this page comes from the company\'s own press release as the newswires carried it (read '
          'through Financial Modeling Prep\'s press-release feed; times are US Eastern). A report day appears only when '
          'the company\'s release names it, such as &ldquo;will release financial results for the third quarter of '
          '2026 after the market close on Wednesday, October 28, 2026&rdquo;; a results date is the newswire time of '
          'the company\'s results release. No date here is estimated, and a vendor\'s projected earnings date is never '
          'used: where a company has not announced its next report day, this page shows none. A release is matched to '
          'a ticker only when it prints the ticker\'s exchange tag or its headline opens with the company\'s name; '
          'law-firm and shareholder-alert releases are left out. Where no newswire results release was read for a '
          'period, the company\'s own Form 8-K under Item 2.02 (Results of Operations and Financial Condition) stands '
          'in, marked &ldquo;8-K&rdquo;: its time is when the SEC\'s EDGAR system accepted the filing, which can be '
          'minutes or hours after the release itself went out, and only an 8-K whose Item 2.02 text names the period '
          'and calls the figures results is used (a preliminary update is not). Facts only, not investment advice.')


def hub(T, pages, today, fetched, n_csv):
    ahead, recent, passed, by_q = gather(T, today)
    n_tk = len(T)
    title = "Biotech Earnings Dates Companies Have Announced | pdufa.bio"
    desc = ("Biotech and pharma earnings dates as the companies announce them in their own press releases: report days "
            "ahead and recent results. No estimated dates.")
    B = ['<h1>Earnings dates, <span class="g">as the companies announce them</span></h1>',
         f'<p class="sub" data-earn="lede">Companies\' own press releases name {len(ahead)} report '
         f'day{"s" if len(ahead) != 1 else ""} still ahead as of {esc(pretty(today))}, and {len(recent)} results '
         f'release{"s" if len(recent) != 1 else ""} went out in the last {RECENT_DAYS} days, across the {n_tk} '
         f'companies with at least one earnings release read so far'
         + (f' (releases read through {esc(fetched_et(fetched))})' if fetched_et(fetched) else '') + '.</p>',
         f'<p class="sub">{SOURCE}</p>',
         f'<h2>Announced report days still ahead ({len(ahead)})</h2>']
    if ahead:
        B.append('<table><tr><th>Report day</th><th>Company</th><th>Period</th><th>When, as the release words it</th>'
                 '<th>Announced</th></tr>')
        for d, tk, k, s, p in ahead:
            moved = [x for x in p["schedules"][:-1] if x.get("report_date") != s.get("report_date")]
            note = (f' (earlier announced for {esc(pretty(d_of(moved[-1]["report_date"])))})' if moved else "")
            note += " (today)" if d == today else ""
            B.append(f'<tr data-earn-ahead="{esc(tk)}|{esc(k)}"><td>{esc(pretty(d))}{note}</td><td>{co(tk, T, pages)}</td>'
                     f'<td>{esc(label(k, p))}</td><td>{when(s)}</td>'
                     f'<td>{rel_link(s, pretty(d_of(s["published_et"])))}</td></tr>')
        B.append('</table>')
    else:
        B.append('<p class="sub">No company this site tracks has announced a report day that is still ahead in a '
                 'release read so far.</p>')
    B.append(f'<h2>Results released in the last {RECENT_DAYS} days ({len(recent)})</h2>')
    if recent:
        B.append('<table><tr><th>Released</th><th>Company</th><th>Period</th><th>Days after the period ended</th>'
                 '<th>Release</th></tr>')
        for pub, tk, k, r in recent:
            n = days_after_end(k, r)
            B.append(f'<tr data-earn-recent="{esc(tk)}|{esc(k)}"><td>{res_time(r)}</td><td>{co(tk, T, pages)}</td>'
                     f'<td>{esc(label(k, T[tk]["P"][k]))}</td><td>{"" if n is None else n}</td><td>{rel_link(r)}</td></tr>')
        B.append('</table>')
    else:
        B.append(f'<p class="sub">No results release in the last {RECENT_DAYS} days among the releases read.</p>')
    qs = sorted((q for q, v in by_q.items() if len(v) >= 5), reverse=True)[:6]
    if qs:
        B += ['<h2>Days from quarter end to results, across companies</h2>',
              '<p class="sub">For each calendar quarter, the calendar days from the quarter\'s last day to the date of '
              'each company\'s results release for it (a fourth-quarter release that also reports the full year counted '
              'once). Releases that report only a full year or a half year are left out, and so are periods a company '
              'prints as fiscal, since a fiscal period need not end with the calendar quarter. Quarters with fewer '
              'than five companies are not shown.</p>',
              '<table><tr><th>Quarter</th><th>Companies</th><th>Median days</th><th>Middle half (25th to 75th '
              'percentile)</th><th>Shortest</th><th>Longest</th></tr>']
        for y, q in qs:
            xs = sorted(n for n, _ in by_q[(y, q)])
            qq = statistics.quantiles(xs, n=4, method="inclusive")
            B.append(f'<tr data-earn-q="{y}Q{q}"><td>Q{q} {y}</td><td>{len(xs)}</td><td>{statistics.median(xs):g}</td>'
                     f'<td>{qq[0]:g} to {qq[2]:g}</td><td>{xs[0]}</td><td>{xs[-1]}</td></tr>')
        B.append('</table>')
    if passed:
        passed.sort(key=lambda x: (x[0], x[1]), reverse=True)
        B += [f'<h2>Announced days that passed with no results release read ({len(passed)})</h2>',
              '<p class="sub">The company announced a report day, the day has passed, and neither a results release '
              'nor an 8-K under Item 2.02 for that period is among the releases and filings read. That can mean the release was not carried under the company\'s '
              'ticker, or its headline names the period in words this page does not read; it does not show that the '
              'company did not report.</p>',
              '<table><tr><th>Announced day</th><th>Company</th><th>Period</th><th>Announcement</th></tr>']
        for d, tk, k, s in passed[:60]:
            B.append(f'<tr data-earn-passed="{esc(tk)}|{esc(k)}"><td>{esc(pretty(d))}</td><td>{co(tk, T, pages)}</td>'
                     f'<td>{esc(label(k, T[tk]["P"][k]))}</td><td>{rel_link(s, pretty(d_of(s["published_et"])))}</td></tr>')
        B.append('</table>' + (f'<p class="sub">The {len(passed) - 60} older ones show on each company\'s page.</p>'
                                if len(passed) > 60 else ''))
    lst = sorted(pages)
    B += [f'<h2>Every company with an earnings page ({len(lst)})</h2>',
          '<p class="sub">A company has a page here once its releases cover at least two periods (an announced report '
          'day or a results release for each), or show an announced report day still ahead or passed.</p>',
          '<p class="sub" data-earn="index">' + " &middot; ".join(
              f'<a href="/earnings/{esc(tk)}">{esc(tk)}</a>' for tk in lst) + '</p>',
          f'<p class="sub">Every row read ({n_csv}): <a href="/earnings/data/earnings-dates.csv">earnings-dates.csv</a> '
          '(CC BY 4.0, please credit pdufa.bio), with each release\'s headline and link. The release is the record: '
          'where a company corrects a date, the newer release is used.</p>',
          '<p class="sub"><a href="/calendar">FDA calendar</a> &middot; <a href="/conferences">Medical conferences</a>'
          ' &middot; <a href="/readouts">Trial readouts</a> &middot; <a href="/crl">CRL database</a></p>',
          '<script type="application/ld+json">' + json.dumps({
              "@context": "https://schema.org", "@type": "Dataset",
              "name": "Biotech earnings dates announced by the companies",
              "description": desc, "url": f"{BASE}/earnings", "license": "https://creativecommons.org/licenses/by/4.0/",
              "creator": {"@type": "Organization", "name": "pdufa.bio", "url": BASE},
              "dateModified": str(fetched)[:10],
              "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                                "contentUrl": f"{BASE}/earnings/data/earnings-dates.csv"}]},
              ensure_ascii=False).replace("</", "<\\/") + '</script>']
    return page(title, desc, "/earnings", B)


def ticker_page(tk, T, pages, today, fetched, site):
    t = T[tk]
    nm = t["name"]
    rows = []
    for k, p in t["P"].items():
        s, st = status_of(p, today)
        r = p["results"]
        sort = (r or {}).get("published_et") or (s or {}).get("report_date") or (p["postponed"][-1]["published_et"]
                                                                                 if p["postponed"] else "")
        rows.append((sort, k, p, s, st, r))
    rows.sort(key=lambda x: x[0], reverse=True)
    nxt = [x for x in rows if x[4] == "ahead"]
    nxt.sort(key=lambda x: x[3]["report_date"])
    if nxt:
        _, k, p, s, _, _ = nxt[0]
        lede = (f'{esc(nm)} has announced that it will report {esc(label(k, p))} results on '
                f'{esc(pretty(d_of(s["report_date"])))}'
                + (f', {esc(s["timing_words"])}' if s.get("timing_words") else "")
                + f' (its release of {esc(pretty(d_of(s["published_et"])))}).')
    elif any(x[4] == "postponed" and x[3] and (today - d_of(x[3]["report_date"])).days <= 90 for x in rows):
        _, k, p, s, _, _ = max((x for x in rows if x[4] == "postponed" and x[3]), key=lambda x: x[3]["published_et"])
        pp = max(p["postponed"], key=lambda x: x["published_et"])
        lede = (f'{esc(nm)} announced {esc(pretty(d_of(s["report_date"])))} for its {esc(label(k, p))} results, then '
                f'put out a postponement on {esc(pretty(d_of(pp["published_et"])))}; no new report day has been read '
                f'since.')
    else:
        lede = (f'{esc(nm)} has not announced its next report day in a release read through '
                f'{esc(fetched_et(fetched) or pretty(today))}.')
    done = [x for x in rows if x[5]]
    if done:
        _, k, _, _, _, r = done[0]
        if is_8k(r):
            lede += (f' Its latest results, for {esc(label(k, t["P"][k]))}, were filed with the SEC on Form 8-K on '
                     f'{esc(fmt_et(r["published_et"]))}.')
        else:
            lede += f' Its latest results release, for {esc(label(k, t["P"][k]))}, went out on {esc(fmt_et(r["published_et"]))}.'
    title = f"{nm} ({tk}) Earnings Dates | pdufa.bio"
    desc = (f"{nm} ({tk}) earnings dates: the report days it announced and when each results release went out, "
            f"from its own press releases.")
    if len(desc) > 155:                     # search engines cut longer descriptions mid-word
        desc = (f"{tk} earnings dates: the report days the company announced and when each results release went out, "
                f"from its own press releases.")
    B = [f'<h1>{esc(nm)} ({esc(tk)}) <span class="g">earnings dates</span></h1>',
         f'<p class="sub" data-earn="lede">{lede}</p>',
         '<table><tr><th>Period</th><th>Report day announced</th><th>Results released</th>'
         '<th>Days after the period ended</th><th>Releases</th></tr>']
    for _, k, p, s, st, r in rows:
        if s:
            ann = esc(pretty(d_of(s["report_date"])))
            moved = [x for x in p["schedules"][:-1] if x.get("report_date") != s.get("report_date")]
            if moved:
                ann += f' (earlier announced for {esc(pretty(d_of(moved[-1]["report_date"])))})'
            if s.get("timing_words"):
                ann += f', &ldquo;{esc(s["timing_words"])}&rdquo;'
        else:
            ann = "no announcement read"
        if r:
            res = res_time(r)
        elif st == "postponed":
            res = "postponed by the company"
        elif st == "ahead":
            res = "ahead"
        else:
            res = "no results release read for this period"
        n = days_after_end(k, r)
        links = [rel_link(x, "announcement") for x in ([s] if s else [])]
        links += [rel_link(x, "postponement") for x in p["postponed"]]
        links += [rel_link(r, "results")] if r else []
        B.append(f'<tr data-earn-row="{esc(k)}"><td>{esc(label(k, p))}</td>'
                 f'<td>{ann}</td><td>{res}</td><td>{"" if n is None else n}</td><td>{" &middot; ".join(links)}</td></tr>')
    B.append('</table>')
    B.append('<p class="sub">Days after the period ended are calendar days from the last day of the calendar quarter, '
             'half or year to the date of the results release; they are left blank for a period the company prints as '
             'fiscal, since a fiscal period need not end with the calendar quarter.'
             + (f' Releases read through {esc(fetched_et(fetched))}.' if fetched_et(fetched) else '') + '</p>')
    B.append(f'<p class="sub">{SOURCE}</p>')
    more = []
    if os.path.isfile(os.path.join(site, "ticker", tk, "index.html")):
        more.append(f'<a href="/ticker/{esc(tk)}">{esc(tk)} FDA dates and decisions</a>')
    more.append('<a href="/earnings">All announced earnings dates</a>')
    lst = sorted(pages)
    i = lst.index(tk)
    near = [x for x in lst[max(0, i - 3):i] + lst[i + 1:i + 4]]
    B.append('<p class="sub">' + " &middot; ".join(more) + '</p>')
    if near:
        B.append('<p class="sub" data-earn="near">Other earnings pages: ' + " &middot; ".join(
            f'<a href="/earnings/{esc(x)}">{esc(T[x]["name"])} ({esc(x)})</a>' for x in near) + '</p>')
    return page(title, desc, f"/earnings/{tk}", B)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=CACHE)
    ap.add_argument("--sec-cache", default=SEC_CACHE)
    ap.add_argument("--site", default=SITE)
    ap.add_argument("--today", default="")
    a = ap.parse_args(argv)
    if not os.path.isfile(a.cache):
        print(f"earnings pages: {os.path.basename(a.cache)} not found; nothing written")
        return 0
    c, T = load(a.cache, a.sec_cache)
    if c.get("_sec_note"):
        print(f"earnings pages: 8-K rows not used: {c['_sec_note']}")
    today = d_of(a.today) or eastern_today()
    if not T:
        print("earnings pages: no ticker has a release with a link; nothing written")
        return 0
    pages = {tk for tk, t in T.items() if has_page(t, today)}
    root = os.path.join(a.site, "earnings")
    # pages of tickers that no longer qualify are removed, so the site never keeps a page the data no longer backs
    if os.path.isdir(root):
        for d in os.listdir(root):
            if TICKER_OK.match(d) and d not in pages and os.path.isfile(os.path.join(root, d, "index.html")):
                shutil.rmtree(os.path.join(root, d))
    n_csv = write_csv(T, os.path.join(root, "data", "earnings-dates.csv"), pages)
    io.open(os.path.join(root, "index.html"), "w", encoding="utf-8").write(hub(T, pages, today, c.get("fetched") or "", n_csv))
    for tk in sorted(pages):
        os.makedirs(os.path.join(root, tk), exist_ok=True)
        io.open(os.path.join(root, tk, "index.html"), "w", encoding="utf-8").write(
            ticker_page(tk, T, pages, today, c.get("fetched") or "", a.site))
    ahead = gather(T, today)[0]
    n8 = sum(1 for t in T.values() for p in t["P"].values() if is_8k(p["results"]))
    print(f"/earnings: {len(T)} tickers with releases, {len(pages)} pages, {len(ahead)} announced days ahead, "
          f"{len(gather(T, today)[2])} passed with no results read, {n8} periods from 8-K only, {n_csv} CSV rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
