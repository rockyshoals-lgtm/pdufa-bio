# -*- coding: utf-8 -*-
"""CI guard: /earnings and /earnings/<TICKER> show only what the companies' own releases in _earnings_dates.json say.

  * rule checks on constructed periods: a results release makes a period reported; a postponement published after
    the announcement voids the day; a second announcement replaces the first; a day is ahead only from today on;
    days after the period end are calendar days from the quarter's last day
  * against the built pages (when they exist): every report day shown as ahead is a schedule row of that ticker and
    period in the cache, dated on or after the page's own "as of" day, with no results row for the period; every
    recent results row and every ticker-page row is a cache row; a ticker page exists only for a ticker in the cache;
    the CSV holds exactly the cache's schedule, results and postponement rows, each with an https link

PLANT=1 adds a report day for a ticker the cache does not have to the hub as read, and the guard must fail.
"""
import csv
import datetime as dt
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_earnings_pages as B  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src", "earnings")
MON = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                       "September", "October", "November", "December"])}


def R(kind, pub, k, **kw):
    r = {"kind": kind, "published_et": pub, "period_key": k, "period": k, "url": "https://example.com/" + pub[:10],
         "title": "t"}
    r.update(kw)
    return r


def rule_checks():
    f = []
    today = dt.date(2026, 11, 26)
    P = B.periods([R("schedule", "2026-10-21 16:05", "2026Q3", report_date="2026-10-28"),
                   R("results", "2026-10-28 16:05", "2026Q3")])
    if B.status_of(P["2026Q3"], today)[1] != "reported":
        f.append("a period with a results release is not 'reported'")
    if B.days_after_end("2026Q3", P["2026Q3"]["results"]) != 28:
        f.append("days after the end of Q3 2026 to Oct 28 should be 28")
    if B.days_after_end("2025Q4+FY", R("results", "2026-02-11 16:16", "2025Q4+FY")) != 42:
        f.append("days after the end of 2025 to Feb 11 2026 should be 42")
    if B.days_after_end("FY2027Q1", R("results", "2026-08-10 16:05", "FY2027Q1")) is not None:
        f.append("a fiscal period must have no days-after-end figure")
    P = B.periods([R("schedule", "2026-11-20 08:00", "2026Q3", report_date="2026-12-03"),
                   R("postponed", "2026-11-25 08:00", "2026Q3")])
    if B.status_of(P["2026Q3"], today)[1] != "postponed":
        f.append("a postponement after the announcement does not void the day")
    P = B.periods([R("postponed", "2026-11-01 08:00", "2026Q3"),
                   R("schedule", "2026-11-20 08:00", "2026Q3", report_date="2026-12-03")])
    if B.status_of(P["2026Q3"], today)[1] != "ahead":
        f.append("a new announcement after a postponement is not 'ahead'")
    P = B.periods([R("schedule", "2026-11-10 08:00", "2026Q3", report_date="2026-12-01"),
                   R("schedule", "2026-11-20 08:00", "2026Q3", report_date="2026-12-08")])
    s, st = B.status_of(P["2026Q3"], today)
    if st != "ahead" or s["report_date"] != "2026-12-08":
        f.append("the later of two announcements is not the one used")
    P = B.periods([R("schedule", "2026-11-10 08:00", "2026Q3", report_date="2026-11-26")])
    if B.status_of(P["2026Q3"], today)[1] != "ahead":
        f.append("a report day of today is not 'ahead'")
    if B.status_of(P["2026Q3"], dt.date(2026, 11, 27))[1] != "passed":
        f.append("a report day before today is not 'passed'")
    if B.fmt_et("2026-10-28 16:05") != "October 28, 2026, 4:05 p.m. ET" or B.fmt_et("2026-10-28 00:30") != \
            "October 28, 2026, 12:30 a.m. ET":
        f.append("fmt_et misformats Eastern times")
    return f


def page_checks(plant=False):
    f = []
    hub = os.path.join(SITE, "index.html")
    if not os.path.isfile(B.CACHE) or not os.path.isfile(hub):
        return f, "no cache or no built /earnings (skipped page checks)"
    c, T = B.load(B.CACHE)
    doc = io.open(hub, encoding="utf-8").read()
    if plant:
        doc = doc.replace("</table>", '<tr data-earn-ahead="ZZZZ|2026Q3"><td>x</td></tr></table>', 1)
    m = re.search(r'still ahead as of (\w+) (\d{1,2}), (\d{4})', doc)
    if not m:
        return [f"/earnings: no 'as of' day in the lede"], ""
    asof = dt.date(int(m.group(3)), MON[m.group(1)], int(m.group(2)))
    for tk, k in re.findall(r'data-earn-ahead="([^"|]+)\|([^"]+)"', doc):
        p = (T.get(tk) or {}).get("P", {}).get(k)
        if not p:
            f.append(f"/earnings ahead row {tk} {k}: no such ticker and period in the cache")
            continue
        s = p["schedules"][-1] if p["schedules"] else None
        if not s or B.d_of(s["report_date"]) < asof:
            f.append(f"/earnings ahead row {tk} {k}: no announced day on or after {asof}")
        if p["results"]:
            f.append(f"/earnings ahead row {tk} {k}: the cache has its results release")
    for tk, k in re.findall(r'data-earn-recent="([^"|]+)\|([^"]+)"', doc):
        p = (T.get(tk) or {}).get("P", {}).get(k)
        if not p or not p["results"]:
            f.append(f"/earnings recent row {tk} {k}: no results row in the cache")
    for d in sorted(os.listdir(SITE)):
        pg = os.path.join(SITE, d, "index.html")
        if not B.TICKER_OK.match(d) or not os.path.isfile(pg):
            continue
        if d not in T:
            f.append(f"/earnings/{d}: ticker not in the cache")
            continue
        P = T[d]["P"]
        tdoc = io.open(pg, encoding="utf-8").read()
        for k, cells in re.findall(r'<tr data-earn-row="([^"]+)">(.*?)</tr>', tdoc):
            if k not in P:
                f.append(f"/earnings/{d} row {k}: period not in the cache")
            elif P[k]["results"] and B.esc(B.fmt_et(P[k]["results"]["published_et"])) not in cells:
                f.append(f"/earnings/{d} row {k}: results time differs from the cache")
    path = os.path.join(SITE, "data", "earnings-dates.csv")
    if not os.path.isfile(path):
        f.append("/earnings/data/earnings-dates.csv missing")
    else:
        rows = list(csv.DictReader(io.open(path, encoding="utf-8-sig")))
        want = sum(1 for t in T.values() for r in t["rel"] if r.get("kind") in ("schedule", "results", "postponed"))
        if len(rows) != want:
            f.append(f"CSV has {len(rows)} rows, the cache {want}")
        keys = {(tk, r.get("published_et"), r.get("url")) for tk, t in T.items() for r in t["rel"]}
        for x in rows:
            if not x["release_url"].startswith("https://"):
                f.append(f"CSV {x['ticker']} {x['published_et']}: link is not https")
            if (x["ticker"], x["published_et"], x["release_url"]) not in keys:
                f.append(f"CSV {x['ticker']} {x['published_et']}: not a cache row")
    n = len(re.findall(r"data-earn-ahead=", doc))
    return f, f"{n} ahead rows, {len(T)} tickers checked against the cache"


def main():
    plant = os.environ.get("PLANT") == "1"
    fails = rule_checks()
    pf, note = page_checks(plant)
    fails += pf
    if fails:
        print("FAIL test_earnings_pages:\n  " + "\n  ".join(fails[:40]))
        return 1
    print(f"ok test_earnings_pages: rules hold; {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
