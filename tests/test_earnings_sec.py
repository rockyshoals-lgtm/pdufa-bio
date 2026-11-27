# -*- coding: utf-8 -*-
"""CI guard: results dates from the companies' own Form 8-K (Item 2.02) stand in only where the newswire feed carried
no results release, and only for what the filing itself says.

  * parse checks on 8-K Item 2.02 wording as filers print it: the quarter named by its last day, three-months-ended,
    quarter and year, fiscal quarters (no key: the year is the company's own), a preliminary January update (never
    results), an Item 2.02 that names no results; EDGAR acceptance times read as printed (Eastern)
  * builder checks on constructed caches: a newswire release beats the 8-K for the same period whatever the order;
    an 8-K makes a passed announced day reported; a ticker with only 8-K rows gets a page; 8-K rows never enter the
    cross-company quarter statistics; a failed time self-check drops every 8-K row; a non-results, preliminary or
    non-EDGAR row is never used
  * against _earnings_sec.json when present: every stored filing is an 8-K with Item 2.02 and an EDGAR link

PLANT=1 makes the self-check pass at a five-hour shift (a time-zone error) and the guard must fail.
"""
import io
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_earnings_pages as B  # noqa: E402
import fetch_earnings_sec as S  # noqa: E402

PARSE = [
    # (Item 2.02 text, accepted, status, key)
    ("On October 28, 2026, Biogen Inc. issued a press release announcing its financial results for the third quarter "
     "ended September 30, 2026. A copy of the press release is furnished as Exhibit 99.1.", "2026-10-28 06:07",
     "results", "2026Q3"),
    ("On November 5, 2026, the Company announced its financial results for the quarter ended September 30, 2026 and "
     "provided a business update.", "2026-11-05 16:01", "results", "2026Q3"),
    ("On February 26, 2026, AbCellera Biologics Inc. issued a press release reporting its financial results for the "
     "fourth quarter and full year ended December 31, 2025.", "2026-02-26 16:03", "results", "2025Q4+FY"),
    ("On March 3, 2026, the Registrant reported its results of operations for the three months and year ended "
     "December 31, 2025.", "2026-03-03 07:00", "results", "2025Q4+FY"),
    ("On August 7, 2025, the Company issued a press release announcing financial results for the three months ended "
     "June 30, 2025.", "2025-08-07 16:05", "results", "2025Q2"),
    ("On November 12, 2026, the Company announced its financial results for the year ended December 31, 2025 and the "
     "six months ended June 30, 2026.", "2026-11-12 08:00", "results", "2025FY"),
    ("On February 4, 2026, the Company issued a press release announcing its financial results for its first quarter "
     "of fiscal 2026 ended December 31, 2025.", "2026-02-04 16:10", "results", "FY2026Q1"),
    ("On November 3, 2026, Roivant Sciences Ltd. issued a press release announcing its financial results for the "
     "second fiscal quarter ended September 30, 2026.", "2026-11-03 07:30", "no_period", None),
    ("On January 12, 2026, the Company announced certain preliminary unaudited financial information for the fourth "
     "quarter and full year ended December 31, 2025, including net product revenue.", "2026-01-12 07:00",
     "preliminary", "2025Q4+FY"),
    ("The Company expects to report cash, cash equivalents and marketable securities of approximately $400 million "
     "as of December 31, 2025.", "2026-01-09 08:00", "preliminary", None),
    ("On May 1, 2026, the Company made available an investor presentation, which includes its cash position. The "
     "presentation is furnished as Exhibit 99.1.", "2026-05-01 08:00", "not_results", None),
]

BODY = ("UNITED STATES SECURITIES AND EXCHANGE COMMISSION FORM 8-K ... Item 2.02 Results of Operations and Financial "
        "Condition. On October 28, 2026, Biogen Inc. issued a press release announcing its financial results for the "
        "third quarter ended September 30, 2026. The information in this Item 2.02 is furnished. Item 9.01 Financial "
        "Statements and Exhibits. (d) Exhibits 99.1 Press release.")


def parse_checks():
    f = []
    for text, acc, st, k in PARSE:
        got = S.classify(text, acc)
        if (got[0], got[2]) != (st, k):
            f.append(f"parse {text[:70]!r}: got {got[0]} {got[2]}, want {st} {k}")
    seg = S.item_202(S.text_of(f"<html><body><p>{BODY}</p></body></html>"))
    if "third quarter ended September 30, 2026" not in seg or "Exhibits 99.1" in seg:
        f.append(f"item_202 did not cut the Item 2.02 paragraph: {seg[:120]!r}")
    if S.accepted_et("2026-10-28T06:07:33.000Z") != "2026-10-28 06:07":
        f.append("acceptance time not read as printed")
    if S.accepted_et("garbage"):
        f.append("a bad acceptance time gave a value")
    if not S.covered("2026-10-29 07:00", [("2026-10-28 16:05", "2026Q3")]) or \
            S.covered("2026-10-31 07:00", [("2026-10-28 16:05", "2026Q3")]):
        f.append("covered(): a newswire release within a day is the test")
    return f


def R(kind, pub, k, **kw):
    r = {"kind": kind, "published_et": pub, "period_key": k, "period": k, "url": "https://example.com/" + pub,
         "title": "t", "site": "businesswire.com"}
    r.update(kw)
    return r


def F(acc, st, k, a="2026-10-28 06:07"):
    return {acc: {"form": "8-K", "items": "2.02,9.01", "accepted_et": a, "filing_date": a[:10], "status": st,
                  "period": k, "period_key": k, "url": f"https://www.sec.gov/Archives/edgar/data/1/{acc}-index.htm"}}


def build_checks(plant=False):
    f = []
    wire = {"tickers": {
        "AAA": {"name": "Alpha Inc.", "releases": [
            R("schedule", "2026-10-10 08:00", "2026Q3", report_date="2026-10-28"),
            R("results", "2026-10-28 16:05", "2026Q3")]},
        "BBB": {"name": "Beta Inc.", "releases": [
            R("schedule", "2026-10-15 08:00", "2026Q3", report_date="2026-11-04")]},
        "CCC": {"name": "Gamma Inc.", "releases": []},
    }}
    sec = {"check": {"n": 40, "median_min": 300.0 if plant else 7.0}, "tickers": {
        "AAA": {"filings": F("0000000001-26-000001", "results", "2026Q3", "2026-10-28 16:01")},
        "BBB": {"filings": {**F("0000000002-26-000001", "results", "2026Q3", "2026-11-04 16:10"),
                            **F("0000000002-26-000002", "preliminary", "2026Q2", "2026-07-08 07:00")}},
        "CCC": {"filings": {**F("0000000003-26-000001", "results", "2026Q3", "2026-11-05 07:00"),
                            **F("0000000003-26-000002", "results", "2026Q2", "2026-08-06 07:00"),
                            **F("0000000003-26-000003", "no_period", None, "2026-05-07 07:00"),
                            "0000000003-26-000004": dict(F("x", "results", "2026Q1", "2026-05-01 07:00")["x"],
                                                         url="https://example.com/fake-8k")}},
    }}
    d = tempfile.mkdtemp()
    wp, sp = os.path.join(d, "w.json"), os.path.join(d, "s.json")
    json.dump(wire, io.open(wp, "w", encoding="utf-8"))
    json.dump(sec, io.open(sp, "w", encoding="utf-8"))
    c, T = B.load(wp, sp)
    today = B.d_of("2026-11-20")
    if c.get("_sec_note"):
        return [f"8-K rows dropped: {c['_sec_note']}"]
    a = T["AAA"]["P"]["2026Q3"]["results"]
    if B.is_8k(a) or a["published_et"] != "2026-10-28 16:05":
        f.append("AAA: the 8-K (filed earlier) replaced the newswire release")
    b = T["BBB"]["P"]
    if B.status_of(b["2026Q3"], today)[1] != "reported" or not B.is_8k(b["2026Q3"]["results"]):
        f.append("BBB: the 8-K did not make the passed announced day reported")
    if "2026Q2" in b:
        f.append("BBB: a preliminary 8-K was used as results")
    if set(T.get("CCC", {}).get("P", {})) != {"2026Q3", "2026Q2"}:
        f.append(f"CCC: 8-K-only periods {sorted(T.get('CCC', {}).get('P', {}))}, want 2026Q2 and 2026Q3 "
                 "(no-period and non-EDGAR rows never used)")
    if "CCC" in T and not B.has_page(T["CCC"], today):
        f.append("CCC: two 8-K periods but no page")
    by_q = B.gather(T, today)[3]
    if any(tk != "AAA" for v in by_q.values() for _, tk in v):
        f.append("8-K rows entered the cross-company quarter statistics")
    if "CCC" in T and "(8-K filed)" not in B.res_time(T["CCC"]["P"]["2026Q3"]["results"]):
        f.append("an 8-K time is not marked as the filing time")
    # the self-check: a five-hour median is a time-zone error and drops every 8-K row
    bad = dict(sec, check={"n": 40, "median_min": 300.0})
    json.dump(bad, io.open(sp, "w", encoding="utf-8"))
    c2, T2 = B.load(wp, sp)
    if plant:
        T2 = T                          # the planted run pretends the guard let the shifted rows through
    if "BBB" in T2 and any(B.is_8k(p["results"]) for p in T2["BBB"]["P"].values()):
        f.append("a failed time self-check (median 300 min) still let 8-K rows through")
    return f


def cache_checks():
    f = []
    if not os.path.isfile(S.CACHE):
        return f, "no _earnings_sec.json yet (written by the rebuild)"
    c = json.load(io.open(S.CACHE, encoding="utf-8"))
    n = 0
    for tk, ent in (c.get("tickers") or {}).items():
        for acc, x in (ent.get("filings") or {}).items():
            n += 1
            if x.get("form") != "8-K" or "2.02" not in str(x.get("items")) or not S.ACC.match(acc):
                f.append(f"{tk} {acc}: not an 8-K with Item 2.02")
            if not str(x.get("url", "")).startswith("https://www.sec.gov/Archives/edgar/data/"):
                f.append(f"{tk} {acc}: link is not an EDGAR filing")
            if x.get("status") == "results" and not x.get("period_key"):
                f.append(f"{tk} {acc}: results with no period")
    return f, f"{n} stored filings, check {c.get('check')}"


def main():
    plant = os.environ.get("PLANT") == "1"
    fails = parse_checks() + build_checks(plant)
    cf, note = cache_checks()
    fails += cf
    if fails:
        print("FAIL test_earnings_sec:\n  " + "\n  ".join(fails[:40]))
        return 1
    print(f"ok test_earnings_sec: {len(PARSE)} Item 2.02 wordings read as filed; 8-K rows stand in only for missing "
          f"newswire results; {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
