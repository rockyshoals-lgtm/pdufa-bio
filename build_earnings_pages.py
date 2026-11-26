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
SITE = os.path.join(HERE, "pdufa_site_src")
RECENT_DAYS = 30
MIN_RESULTS = 2          # a ticker page needs this many results releases, or an announced day still ahead
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


def periods(rel):
    """period -> {"schedules": [...] oldest first, "results": earliest results row, "postponed": [...], "keys": set of
    the period keys as parsed}. A postponement that names no period voids the pending announcement it follows: one
    published after the latest announcement of a period and no later than its report day."""
    out = collections.defaultdict(lambda: {"schedules": [], "results": None, "postponed": [], "keys": set()})
    loose = []
    for r in sorted(rel, key=lambda r: r.get("published_et") or ""):
        if not d_of(r.get("published_et")):
            continue
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
        elif kind == "results" and out[k]["results"] is None:
            out[k]["results"] = r
            out[k]["keys"].add(k0)
        elif kind == "postponed":
            out[k]["postponed"].append(r)
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


def load(path):
    c = json.load(io.open(path, encoding="utf-8"))
    T = {}
    for tk, v in (c.get("tickers") or {}).items():
        if not TICKER_OK.match(tk or "") or not isinstance(v, dict):
            continue
        rel = [r for r in (v.get("releases") or []) if isinstance(r, dict) and ok_url(r.get("url"))]
        if rel:
            T[tk] = {"name": v.get("name") or tk, "rel": rel, "P": periods(rel)}
    return c, T


ORDN = {"1": "first", "2": "second", "3": "third", "4": "fourth"}


def label(k, p=None):
    """The period in one wording, from its key: 'Q3 2026', 'Q4 and full year 2025', 'Fiscal 2027 Q1', 'First half
    2026'."""
    keys = (p or {}).get("keys") or set()
    m = re.fullmatch(r"(20\d\d)Q([1-4])", k)
    if m:
        full = m.group(2) == "4" and any(re.fullmatch(r"20\d\d(Q4\+FY|FY)", x) for x in keys)
        return f"Q{m.group(2)} {'and full year ' if full else ''}{m.group(1)}"
    m = re.fullmatch(r"FY(20\d\d)Q([1-4])", k)
    if m:
        full = m.group(2) == "4" and f"FY{m.group(1)}" in keys
        return f"Fiscal {m.group(1)} Q{m.group(2)}" + (" and fiscal year" if full else "")
    m = re.fullmatch(r"(20\d\d)H([12])", k)
    if m:
        return f"{'First' if m.group(2) == '1' else 'Second'} half {m.group(1)}"
    return k


def rel_link(r, text=None):
    return f'<a href="{esc(r["url"])}" rel="noopener nofollow">{esc(text or "release")}</a>'


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
                if 0 <= (today - rd).days <= RECENT_DAYS:
                    recent.append((r["published_et"], tk, k, r))
                n = days_after_end(k, r)
                m = re.fullmatch(r"(20\d\d)Q([1-4])(\+FY)?", k)
                if n is not None and m:
                    by_q[(int(m.group(1)), int(m.group(2)))].append((n, tk))
    ahead.sort(key=lambda x: (x[0], x[1]))
    recent.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return ahead, recent, passed, by_q


def has_page(t, today):
    n = sum(1 for p in t["P"].values() if p["results"])
    return n >= MIN_RESULTS or any(status_of(p, today)[1] == "ahead" for p in t["P"].values())


def write_csv(T, path, pages):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = []
    for tk, t in T.items():
        for r in t["rel"]:
            if r.get("kind") not in ("schedule", "results", "postponed"):
                continue
            rows.append([tk, t["name"], r.get("kind"), r.get("period") or "", r.get("period_key") or "",
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
          'law-firm and shareholder-alert releases are left out. Facts only, not investment advice.')


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
            B.append(f'<tr data-earn-recent="{esc(tk)}|{esc(k)}"><td>{esc(fmt_et(pub))}</td><td>{co(tk, T, pages)}</td>'
                     f'<td>{esc(label(k, T[tk]["P"][k]))}</td><td>{"" if n is None else n}</td><td>{rel_link(r)}</td></tr>')
        B.append('</table>')
    else:
        B.append(f'<p class="sub">No results release in the last {RECENT_DAYS} days among the releases read.</p>')
    qs = sorted((q for q, v in by_q.items() if len(v) >= 5), reverse=True)[:6]
    if qs:
        B += ['<h2>Days from quarter end to results, across companies</h2>',
              '<p class="sub">For each calendar quarter, the calendar days from the quarter\'s last day to the date of '
              'each company\'s results release for it (fourth-quarter releases that also report the full year '
              'and full-year releases counted once). Periods a company prints as fiscal (a fiscal quarter or a fiscal '
              'year) are left out, since a fiscal period need not end with the calendar quarter. Quarters with fewer '
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
              '<p class="sub">The company announced a report day, the day has passed, and no results release for that '
              'period is among the releases read. That can mean the release was not carried under the company\'s '
              'ticker, or its headline names the period in words this page does not read; it does not show that the '
              'company did not report.</p>',
              '<table><tr><th>Announced day</th><th>Company</th><th>Period</th><th>Announcement</th></tr>']
        for d, tk, k, s in passed[:60]:
            B.append(f'<tr data-earn-passed="{esc(tk)}|{esc(k)}"><td>{esc(pretty(d))}</td><td>{co(tk, T, pages)}</td>'
                     f'<td>{esc(label(k, T[tk]["P"][k]))}</td><td>{rel_link(s, pretty(d_of(s["published_et"])))}</td></tr>')
        B.append('</table>' + (f'<p class="sub">The {len(passed) - 60} older ones are in the CSV.</p>'
                                if len(passed) > 60 else ''))
    lst = sorted(pages)
    B += [f'<h2>Every company with an earnings page ({len(lst)})</h2>',
          '<p class="sub">A company has a page here once its releases show at least two results releases, or a report '
          'day still ahead.</p>',
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
        lede += f' Its latest results release, for {esc(label(k, t["P"][k]))}, went out on {esc(fmt_et(r["published_et"]))}.'
    title = f"{nm} ({tk}) Earnings Dates | pdufa.bio"
    desc = (f"When {nm} ({tk}) reports quarterly results: the report days it announced and when each results release "
            f"went out, from the company's own press releases.")
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
            res = esc(fmt_et(r["published_et"]))
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
    ap.add_argument("--site", default=SITE)
    ap.add_argument("--today", default="")
    a = ap.parse_args(argv)
    if not os.path.isfile(a.cache):
        print(f"earnings pages: {os.path.basename(a.cache)} not found; nothing written")
        return 0
    c, T = load(a.cache)
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
    print(f"/earnings: {len(T)} tickers with releases, {len(pages)} pages, {len(ahead)} announced days ahead, "
          f"{n_csv} CSV rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
