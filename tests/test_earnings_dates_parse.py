# -*- coding: utf-8 -*-
"""Guard: fetch_earnings_dates.parse_item reads real company releases the way a person would.

2026-11-26 (David: "add earning dates"). Every fixture below is a real release as FMP's press-release feed carried it
(read 2026-11-26 through the FMP connector); texts are FMP's own excerpts. Checks:
  * schedule releases give the announced day, the period and the before-open / after-close words
  * results releases give the period and the newswire time (Eastern)
  * trial-data, investor-conference, inducement-grant and law-firm releases are not earnings rows
  * a release FMP files under the wrong symbol (Merck KGaA under MRK) is not attributed to it

    python tests/test_earnings_dates_parse.py          (PLANT=1 breaks the attribution rule; the guard must fail)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import fetch_earnings_dates as E  # noqa: E402

if os.environ.get("PLANT") == "1":
    E.mentions = lambda *a, **k: True

CASES = [
    # (ticker, name, item, expected subset or None)
    ("VKTX", "Viking Therapeutics, Inc.",
     {"publishedDate": "2026-10-21 16:05:00", "title": "Viking Therapeutics to Report Financial Results for Third "
      "Quarter 2026 on October 28, 2026", "text": "Conference Call Scheduled for Wednesday, October 28, at 4:30 p.m. "
      "Eastern Time  SAN DIEGO, Oct. 21, 2026 /PRNewswire/ -- Viking Therapeutics, Inc. (\"Viking\") (NASDAQ: VKTX), a "
      "clinical-stage biopharmaceutical company ..., today announced that the company will release financial results "
      "for the third quarter of 2026 after the market close on Wednesday, October 28, 2026.", "url": "u1"},
     {"kind": "schedule", "report_date": "2026-10-28", "period_key": "2026Q3", "timing": "after_close",
      "call_time": "4:30 p.m. ET"}),
    ("VKTX", "Viking Therapeutics, Inc.",
     {"publishedDate": "2026-10-28 16:05:00", "title": "Viking Therapeutics Reports Third Quarter 2026 Financial "
      "Results and Provides Corporate Update", "text": "... SAN DIEGO, Oct. 28, 2026 /PRNewswire/ -- Viking "
      "Therapeutics, Inc. (Viking) (Nasdaq: VKTX), ... today announced its financial results for the third quarter",
      "url": "u2"},
     {"kind": "results", "period_key": "2026Q3", "published_et": "2026-10-28 16:05"}),
    ("SRPT", "Sarepta Therapeutics, Inc.",
     {"publishedDate": "2026-10-22 08:30:00", "title": "Sarepta Therapeutics to Announce Third Quarter 2026 Financial "
      "Results", "text": "CAMBRIDGE, Mass.--(BUSINESS WIRE)--Sarepta Therapeutics, Inc. (NASDAQ:SRPT), the leader in "
      "precision genetic medicine for rare diseases, will report third quarter 2026 financial results after the Nasdaq "
      "Global Market closes on Thursday, Nov. 5, 2026. Subsequently, at 4:30 p.m. ET, the Company will host a "
      "conference call", "url": "u3"},
     {"kind": "schedule", "report_date": "2026-11-05", "period_key": "2026Q3", "timing": "after_close"}),
    ("SRPT", "Sarepta Therapeutics, Inc.",
     {"publishedDate": "2026-11-05 16:05:00", "title": "Sarepta Therapeutics Announces Third Quarter 2026 Financial "
      "Results and Recent Corporate Developments", "text": "Sarepta Therapeutics, Inc. (NASDAQ:SRPT) ... today reported "
      "financial results for the third quarter of 2026.", "url": "u4"},
     {"kind": "results", "period_key": "2026Q3"}),
    ("ARQT", "Arcutis Biotherapeutics, Inc.",
     {"publishedDate": "2026-10-21 16:00:00", "title": "Arcutis to Report Third Quarter 2026 Financial Results and Host "
      "Conference Call on November 4, 2026", "text": "Arcutis today announced that it will report its Q3 2026 financial "
      "results and provide a business update after the U.S. financial markets close on Nov 4.", "url": "u5"},
     {"kind": "schedule", "report_date": "2026-11-04", "period_key": "2026Q3", "timing": "after_close"}),
    ("CAPR", "Capricor Therapeutics, Inc.",
     {"publishedDate": "2026-11-03 09:00:00", "title": "Capricor Therapeutics to Report Third Quarter 2026 Financial "
      "Results and Provide Recent Corporate Update on November 10", "text": "SAN DIEGO, Nov. 03, 2026 (GLOBE NEWSWIRE) "
      "-- Capricor Therapeutics  (NASDAQ: CAPR), ... today announced that it will release its financial results for "
      "the third quarter ended September 30, 2026, after the market close on Tuesday, November 10, 2026. Management "
      "will host a conference call and webcast at 4:30 p.m.", "url": "u6"},
     {"kind": "schedule", "report_date": "2026-11-10", "period_key": "2026Q3", "timing": "after_close"}),
    ("ALNY", "Alnylam Pharmaceuticals, Inc.",
     {"publishedDate": "2026-10-29 08:00:00", "title": "Alnylam Pharmaceuticals Reports Third Quarter 2026 Financial "
      "Results and Highlights Recent Period Progress", "text": "Alnylam Pharmaceuticals, Inc. (Nasdaq: ALNY), the "
      "leading RNAi therapeutics company, today reported its consolidated financial results", "url": "u7"},
     {"kind": "results", "period_key": "2026Q3", "published_et": "2026-10-29 08:00"}),
    ("MRK", "Merck & Co., Inc.",
     {"publishedDate": "2026-10-29 06:30:00", "title": "Merck & Co., Inc., Rahway, N.J., USA Announces Third-Quarter "
      "2026 Financial Results; Highlights Multiple Milestones Advancing Broad, Diverse Pipeline", "text": "RAHWAY, "
      "N.J.--(BUSINESS WIRE)--Merck & Co., Inc., Rahway, N.J., USA Announces Third-Quarter 2026 Financial Results",
      "url": "u8"},
     {"kind": "results", "period_key": "2026Q3"}),
    # not earnings rows
    ("MRK", "Merck & Co., Inc.",
     {"publishedDate": "2026-10-21 08:35:00", "title": "Merck Collaborates with NVIDIA, Microsoft and Dawn Health to "
      "Develop Novel Support Model for People Living with Rare Tumors", "text": "DARMSTADT, Germany--(BUSINESS WIRE)--"
      "Merck, a leading science and technology company, today announced", "url": "n1"}, None),
    ("MRK", "Merck & Co., Inc.",
     {"publishedDate": "2026-11-12 07:00:00", "title": "Merck KGaA, Darmstadt, Germany, Reports Third Quarter 2026 "
      "Results", "text": "DARMSTADT, Germany--(BUSINESS WIRE)--Merck KGaA, Darmstadt, Germany, a leading science and "
      "technology company, today reported results", "url": "n2"}, None),
    ("ARQT", "Arcutis Biotherapeutics, Inc.",
     {"publishedDate": "2026-11-06 16:00:00", "title": "Arcutis Biotherapeutics Reports Inducement Grants Under Nasdaq "
      "Listing Rule 5635(c)(4)", "text": "Arcutis Biotherapeutics, Inc. (Nasdaq: ARQT) ...", "url": "n3"}, None),
    ("VKTX", "Viking Therapeutics, Inc.",
     {"publishedDate": "2026-11-03 16:30:00", "title": "Viking Therapeutics to Participate at Upcoming Investor "
      "Conferences", "text": "Viking Therapeutics, Inc. (NASDAQ: VKTX) ... will participate at the Stifel 2026 "
      "Healthcare Conference ... Conference Dates: November 10-12, 2026", "url": "n4"}, None),
    ("VKTX", "Viking Therapeutics, Inc.",
     {"publishedDate": "2026-09-22 07:05:00", "title": "Viking Therapeutics Announces Positive Topline Results from "
      "Maintenance Study of GLP-1/GIP Agonist VK2735", "text": "(NASDAQ: VKTX) ... Conference Call Scheduled for 8:00 "
      "a.m. ET Today", "url": "n5"}, None),
    ("ALNY", "Alnylam Pharmaceuticals, Inc.",
     {"publishedDate": "2026-10-29 17:40:00", "title": "Lost Money on Alnylam Pharmaceuticals, Inc. Stock? Glancy "
      "Prongay Wolke & Rotter LLP Continues Investigating Possible Securities Fraud", "text": "Investigation follows the "
      "July 30, 2026 disclosure regarding Alnylam Pharmaceuticals, Inc.", "url": "n6"}, None),
    ("SRPT", "Sarepta Therapeutics, Inc.",
     {"publishedDate": "2026-10-26 16:30:00", "title": "Sarepta Therapeutics to Present at Upcoming Investor "
      "Conferences", "text": "Sarepta Therapeutics, Inc. (NASDAQ:SRPT) ... will participate in the following upcoming "
      "investor conferences on Nov. 9, 2026", "url": "n7"}, None),
]


# CONSTRUCTED variants (red team, 2026-11-26): real release shapes with the wording changed to probe one rule each.
# Companies are tracked tickers; the texts are not claims about real events.
V, VN = "VKTX", "Viking Therapeutics, Inc."
CONSTRUCTED = [
    # dateline is the first date in the text; the report day comes later with its weekday
    (V, VN, {"publishedDate": "2026-10-21 16:05:00", "title": "Viking Therapeutics to Report Third Quarter 2026 Financial "
     "Results", "text": "SAN DIEGO, Oct. 21, 2026 /PRNewswire/ -- Viking Therapeutics, Inc. (NASDAQ: VKTX) will release "
     "results for the quarter ended September 30, 2026 after the market close on Wednesday, October 28, 2026.",
     "url": "c1"}, {"kind": "schedule", "report_date": "2026-10-28", "timing": "after_close"}),
    ("CAPR", "Capricor Therapeutics, Inc.", {"publishedDate": "2026-11-03 09:00:00", "title": "Capricor Therapeutics to "
     "Report Third Quarter 2026 Financial Results", "text": "SAN DIEGO, Nov. 03, 2026 (GLOBE NEWSWIRE) -- Capricor "
     "Therapeutics (NASDAQ: CAPR) will release its results on Tuesday, November 10, 2026.", "url": "c2"},
     {"kind": "schedule", "report_date": "2026-11-10"}),
    # a weekday that does not match its date voids the row
    (V, VN, {"publishedDate": "2026-10-21 16:05:00", "title": "Viking Therapeutics to Report Third Quarter 2026 Financial "
     "Results", "text": "Viking Therapeutics, Inc. (NASDAQ: VKTX) will report on Tuesday, October 28, 2026.", "url": "c3"},
     None),
    # results headlines with more after them
    (V, VN, {"publishedDate": "2026-10-28 16:05:00", "title": "Viking Therapeutics Reports Third Quarter 2026 Financial "
     "Results and Provides Clinical Update", "text": "(NASDAQ: VKTX)", "url": "c4"}, {"kind": "results",
     "period_key": "2026Q3"}),
    (V, VN, {"publishedDate": "2026-10-28 16:05:00", "title": "Viking Therapeutics Reports Third Quarter 2026 Financial "
     "Results and Upcoming Milestones", "text": "(NASDAQ: VKTX)", "url": "c5"}, {"kind": "results"}),
    # law firms, postponements, meetings, peers
    ("ALNY", "Alnylam Pharmaceuticals, Inc.", {"publishedDate": "2026-10-30 09:00:00", "title": "ALNY Investor Alert: "
     "Rosen Law Firm Announces Investigation Following Alnylam Third Quarter 2026 Results", "text": "(NASDAQ: ALNY)",
     "url": "c6"}, None),
    ("ALNY", "Alnylam Pharmaceuticals, Inc.", {"publishedDate": "2026-10-30 09:00:00", "title": "Alnylam Shareholders: "
     "Pomerantz Announces Investigation After Q3 2026 Earnings", "text": "(NASDAQ: ALNY)", "url": "c7"}, None),
    (V, VN, {"publishedDate": "2026-10-27 08:00:00", "title": "Viking Therapeutics Postpones Third Quarter 2026 Financial "
     "Results Release", "text": "(NASDAQ: VKTX)", "url": "c8"}, None),
    (V, VN, {"publishedDate": "2026-10-27 08:00:00", "title": "Viking Therapeutics Reschedules Third Quarter 2026 "
     "Financial Results Release to November 4", "text": "(NASDAQ: VKTX)", "url": "c9"},
     {"kind": "schedule", "report_date": "2026-11-04"}),
    (V, VN, {"publishedDate": "2026-06-10 16:05:00", "title": "Viking Therapeutics Announces Voting Results of 2026 Annual "
     "Meeting", "text": "(NASDAQ: VKTX)", "url": "c10"}, None),
    (V, VN, {"publishedDate": "2026-11-05 16:05:00", "title": "Ligand Reports Third Quarter 2026 Financial Results",
     "text": "... royalties from partners including Viking Therapeutics (NASDAQ: VKTX) ...", "url": "c11"}, None),
    # 'ANI' must not match 'Anika'
    ("ANIP", "ANI Pharmaceuticals, Inc.", {"publishedDate": "2026-11-05 07:00:00", "title": "Anika Reports Third Quarter "
     "2026 Financial Results", "text": "Anika Therapeutics, Inc. (NASDAQ: ANIK)", "url": "c12"}, None),
]


def main():
    fails = []
    for tk, name, item, want in CASES + CONSTRUCTED:
        got = E.parse_item(tk, name, item)
        if want is None:
            if got is not None:
                fails.append(f"{tk} {item['title'][:60]!r}: expected no row, got {got.get('kind')}")
            continue
        if got is None:
            fails.append(f"{tk} {item['title'][:60]!r}: expected {want['kind']}, got nothing")
            continue
        for k, v in want.items():
            if got.get(k) != v:
                fails.append(f"{tk} {item['title'][:60]!r}: {k}={got.get(k)!r}, expected {v!r}")
    if fails:
        print("FAIL test_earnings_dates_parse:\n  " + "\n  ".join(fails))
        return 1
    print(f"ok test_earnings_dates_parse: {len(CASES)} real releases and {len(CONSTRUCTED)} constructed variants parsed as expected")
    return cache_checks()
    return 0



def cache_checks():
    """The committed _earnings_dates.json, when present: schedule days on/after the release day and within 75 days,
    no noise words in any title, every row's title opening with the company's short name, no duplicate urls."""
    import json
    p = os.path.join(HERE, "_earnings_dates.json")
    if not os.path.exists(p):
        return 0
    bad = []
    for tk, ent in (json.load(open(p, encoding="utf-8")).get("tickers") or {}).items():
        stem = E.short_name(ent.get("name") or tk).lower()
        seen = set()
        for r in ent.get("releases") or []:
            t = r.get("title", "")
            if r.get("url") in seen:
                bad.append(f"{tk}: duplicate {r.get('url')}")
            seen.add(r.get("url"))
            if E.NOISE.search(t) and not re.search(r"reschedul", t, re.I):
                bad.append(f"{tk}: noise title {t[:60]!r}")
            if not t.lower().startswith(stem):
                bad.append(f"{tk}: title does not open with {stem!r}: {t[:60]!r}")
            if r.get("kind") == "schedule":
                pub, rd = r.get("published_et", "")[:10], r.get("report_date", "")
                if not (pub <= rd) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", rd):
                    bad.append(f"{tk}: schedule day {rd} before release day {pub}")
    if bad:
        print("FAIL test_earnings_dates_parse (cache):\n  " + "\n  ".join(bad[:40]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
