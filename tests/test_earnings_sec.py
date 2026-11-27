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

PLANT=1 loosens the builder's time check until a five-hour shift (a time-zone error) passes; the guard must fail.
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
     "six months ended June 30, 2026.", "2026-11-12 08:00", "no_period", None),
    # red team, 2026-11-27: wording that only mentions results, or results of another time, is never results
    ("On October 20, 2026, the Company issued a press release announcing that it will release financial results for "
     "the third quarter ended September 30, 2026 after the market close on November 12, 2026.", "2026-10-20 08:00",
     "not_results", None),
    ("On October 22, 2026, the Company issued a press release announcing the date of its third quarter 2026 financial "
     "results conference call.", "2026-10-22 08:00", "not_results", None),
    ("On January 12, 2026, the Company announced certain unaudited financial results for the fourth quarter and full "
     "year ended December 31, 2025.", "2026-01-12 07:00", "preliminary", "2025Q4+FY"),
    ("In connection with the proposed public offering, the Company is disclosing certain financial results for the "
     "quarter ended September 30, 2026.", "2026-10-25 07:00", "preliminary", "2026Q3"),
    ("On September 8, 2026, the Company posted an updated corporate presentation, which includes financial results "
     "for the quarter ended June 30, 2026.", "2026-09-08 08:00", "not_results", None),
    ("On November 10, 2026, the Company announced financial results for the quarter ended December 31, 2026.",
     "2026-11-10 16:05", "no_period", None),
    ("On November 10, 2026, the Company announced its financial results for the third quarter ended September 30, "
     "2025.", "2026-11-10 16:05", "no_period", None),
    ("On August 12, 2026, the Company issued a press release announcing its financial results for the quarter and "
     "year ended June 30, 2026.", "2026-08-12 16:05", "no_period", None),
    ("On November 5, 2026, the Company issued a press release announcing its financial results for the three months "
     "ended September 30, 2026 compared with the three months ended September 30, 2025. The information in this Item "
     "2.02 shall not be deemed filed or otherwise subject to the liabilities of that section.", "2026-11-05 16:05",
     "results", "2026Q3"),
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
    if plant:
        B.SEC_CHECK_MAX = 400           # the planted fault: a check loose enough to pass a five-hour shift
    wire = {"tickers": {
        "AAA": {"name": "Alpha Inc.", "releases": [
            R("schedule", "2026-10-10 08:00", "2026Q3", report_date="2026-10-28"),
            R("results", "2026-10-28 16:05", "2026Q3"),
            R("results", "2026-07-29 16:05", "2026Q2")]},
        "BBB": {"name": "Beta Inc.", "releases": [
            R("schedule", "2026-10-15 08:00", "2026Q3", report_date="2026-11-04"),
            R("schedule", "2026-11-10 08:00", "2026Q4", report_date="2027-02-20")]},
        "CCC": {"name": "Gamma Inc.", "releases": []},
        "DDD": {"name": "Delta Inc.", "releases": []},
        "FYC": {"name": "Fiscal Co.", "releases": [
            R("results", "2026-08-20 16:05", "FY2026Q4"), R("results", "2025-08-21 16:05", "FY2025Q4")]},
    }}
    good = {"n": 40, "median_min": 7.0, "dated": 200, "dated_bad": 0}
    sec = {"check": good, "tickers": {
        # filed 30 minutes AFTER the newswire release: the release is the record, and the 8-K is not used at all
        "AAA": {"filings": {**F("0000000001-26-000001", "results", "2026Q3", "2026-10-28 16:35"),
                            # two days from any release, for a period the newswire also has: kept, but the release wins
                            **F("0000000001-26-000002", "results", "2026Q2", "2026-07-31 08:00")}},
        "BBB": {"filings": {**F("0000000002-26-000001", "results", "2026Q3", "2026-11-04 16:10"),
                            **F("0000000002-26-000002", "preliminary", "2026Q2", "2026-07-08 07:00"),
                            # before the announced day of February 20: never used
                            **F("0000000002-26-000003", "results", "2026Q4", "2027-02-10 07:00")}},
        "CCC": {"filings": {**F("0000000003-26-000001", "results", "2026Q3", "2026-11-05 07:00"),
                            **F("0000000003-26-000002", "results", "2026Q2", "2026-08-06 07:00"),
                            **F("0000000003-26-000003", "no_period", None, "2026-05-07 07:00"),
                            **F("0000000003-26-000005", "results", "2025Q3", "2026-11-12 07:00"),   # stale period
                            "0000000003-26-000004": dict(F("x", "results", "2026Q1", "2026-05-01 07:00")["x"],
                                                         url="https://example.com/fake-8k")}},
        # two 8-Ks claim one period: neither is used
        "DDD": {"filings": {**F("0000000004-26-000001", "results", "2025Q4", "2026-01-12 07:00"),
                            **F("0000000004-26-000002", "results", "2025Q4", "2026-03-02 16:05")}},
        # a fiscal-year company: an 8-K's calendar key must not relabel its fiscal releases
        "FYC": {"filings": F("0000000005-26-000001", "results", "2026Q3", "2026-11-03 16:01")},
    }}
    d = tempfile.mkdtemp()
    wp, sp = os.path.join(d, "w.json"), os.path.join(d, "s.json")
    json.dump(wire, io.open(wp, "w", encoding="utf-8"))

    def load(chk):
        json.dump(dict(sec, check=chk), io.open(sp, "w", encoding="utf-8"))
        return B.load(wp, sp)
    c, T = load(good)
    today = B.d_of("2026-11-20")
    if c.get("_sec_note"):
        return [f"8-K rows dropped: {c['_sec_note']}"]
    for k in ("2026Q3", "2026Q2"):
        if B.is_8k(T["AAA"]["P"][k]["results"]):
            f.append(f"AAA {k}: an 8-K replaced or stood beside the newswire release")
    if any(r.get("accession") == "0000000001-26-000001" for r in T["AAA"]["rel"]):
        f.append("AAA: an 8-K within a day of a newswire results release was kept")
    b = T["BBB"]["P"]
    if B.status_of(b["2026Q3"], today)[1] != "reported" or not B.is_8k(b["2026Q3"]["results"]):
        f.append("BBB: the 8-K did not make the passed announced day reported")
    if "2026Q2" in b:
        f.append("BBB: a preliminary 8-K was used as results")
    if b["2026Q4"]["results"]:
        f.append("BBB: an 8-K dated before the announced report day was used")
    if set(T.get("CCC", {}).get("P", {})) != {"2026Q3", "2026Q2"}:
        f.append(f"CCC: 8-K-only periods {sorted(T.get('CCC', {}).get('P', {}))}, want 2026Q2 and 2026Q3 "
                 "(no-period, stale and non-EDGAR rows never used)")
    if "CCC" in T and not B.has_page(T["CCC"], today):
        f.append("CCC: two 8-K periods but no page")
    if any(p["results"] for p in T.get("DDD", {}).get("P", {}).values()):
        f.append("DDD: two 8-Ks for one period, and one was used")
    fy = T["FYC"]["P"]
    if "FY2026Q4" not in fy or any(k.endswith("+FY") for k in fy):
        f.append(f"FYC: a fiscal company's releases were relabeled calendar: {sorted(fy)}")
    by_q = B.gather(T, today)[3]
    if any(tk in ("BBB", "CCC") for v in by_q.values() for _, tk in v):
        f.append("8-K rows entered the cross-company quarter statistics")
    if "CCC" in T:
        r = T["CCC"]["P"]["2026Q3"]["results"]
        if "(8-K, accepted by EDGAR)" not in B.res_time(r) or B.days_after_end("2026Q3", r) is not None:
            f.append("an 8-K time is not marked, or it was given a day count")
    # the time checks fail closed: a five-hour median, too few pairs, or EDGAR's filing-date rule broken
    for chk, why in ((dict(good, median_min=300.0), "a five-hour median"), (dict(good, n=3), "three pairs"),
                     (dict(good, dated_bad=40), "40 of 200 filings off EDGAR's filing-date rule")):
        _, T2 = load(chk)
        if any(B.is_8k(p["results"]) for t in T2.values() for p in t["P"].values()):
            f.append(f"8-K rows used despite {why}")
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
            if x.get("status") == "results" and not S.fresh(x.get("period_key"), B.d_of(x.get("accepted_et"))):
                f.append(f"{tk} {acc}: results for {x.get('period_key')} not ended within {S.MAX_DAYS} days "
                         f"before {x.get('accepted_et')}")
    dn, db = S.filing_date_check(c)
    if dn >= 20 and db > 0.05 * dn:
        f.append(f"{db} of {dn} stored 8-K times break EDGAR's filing-date rule: the time zone is being misread")
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
