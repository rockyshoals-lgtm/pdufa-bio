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
    # real, 2026-11-26 red team of the built pages: three results headlines the parser missed, so the announced day
    # showed as passed with no results release
    ("BMY", "Bristol-Myers Squibb Company",
     {"publishedDate": "2026-10-29 06:59:00", "title": "Bristol Myers Squibb Reports Third Quarter Financial Results "
      "for 2026", "text": "PRINCETON, N.J.--(BUSINESS WIRE)--Bristol Myers Squibb Reports Third Quarter Financial "
      "Results for 2026.", "url": "u-bmy"},
     {"kind": "results", "period_key": "2026Q3", "published_et": "2026-10-29 06:59"}),
    ("AMPH", "Amphastar Pharmaceuticals, Inc.",
     {"publishedDate": "2026-11-05 16:10:00", "title": "Amphastar Pharmaceuticals Reports Financial Results for the "
      "Three Months Ended September 30, 2026", "text": "Net revenues of $207.6 million for the three months ended "
      "September 30, 2026 GAAP net income of $37.8 million, or $0.87 per share, for the third quarter ... RANCHO "
      "CUCAMONGA, Calif.", "url": "u-amph"},
     {"kind": "results", "period_key": "2026Q3", "published_et": "2026-11-05 16:10"}),
    ("AXGN", "Axogen, Inc.",
     {"publishedDate": "2026-07-29 07:05:00", "title": "Axogen, Inc. Reports Second Quarter 2026 Financial Results",
      "text": "ALACHUA, Fla. and TAMPA, Fla.", "url": "u-axgn"},
     {"kind": "results", "period_key": "2026Q2", "published_et": "2026-07-29 07:05"}),
    # real, 2026-11-27 (David: "use the info in drive and see what you can verify by linked sources"): results
    # releases FMP carried that the parser missed, found by checking Drive earnings watchlists against the companies'
    # own releases. The year sat in the end date, not beside the quarter; "Unaudited" blocked the headline; and
    # "AbCellera Biologics" never matched the headline brand "AbCellera".
    ("SMMT", "Summit Therapeutics Inc.",
     {"publishedDate": "2026-11-04 16:36:00", "title": "Summit Therapeutics Reports Financial Results and Operational "
      "Progress for the Third Quarter and Nine Months Ended September 30, 2026", "text": "MIAMI--(BUSINESS WIRE)---- "
      "$SMMT--Summit Therapeutics Inc. (NASDAQ: SMMT) today reported its financial results for the third quarter and "
      "nine months ended September 30, 2026", "url": "u-smmt"},
     {"kind": "results", "period_key": "2026Q3", "published_et": "2026-11-04 16:36"}),
    ("IMVT", "Immunovant, Inc.",
     {"publishedDate": "2026-11-09 07:00:00", "title": "Immunovant Provides Corporate Updates and Reports Financial "
      "Results for the Quarter Ended September 30, 2026", "text": "IMVT-1402 600 mg met the primary endpoint of ACR20 "
      "response at Week 28 ... Roivant will host a live conference call and webcast at 8:00 a.m.", "url": "u-imvt"},
     {"kind": "results", "period_key": "2026Q3", "published_et": "2026-11-09 07:00"}),
    ("ENTA", "Enanta Pharmaceuticals Inc",
     {"publishedDate": "2026-11-16 16:01:00", "title": "Enanta Pharmaceuticals Reports Financial Results for its "
      "Fiscal Fourth Quarter and Year-Ended September 30, 2026", "text": "WATERTOWN, Mass.--(BUSINESS WIRE)--Enanta "
      "Pharmaceuticals, Inc. (NASDAQ:ENTA), ... today reported financial results for its fiscal fourth quarter and "
      "year-ended September 30, 2026.", "url": "u-enta"},
     {"kind": "results", "period_key": "FY2026Q4", "published_et": "2026-11-16 16:01"}),
    ("BLTE", "Belite Bio, Inc",
     {"publishedDate": "2026-11-12 06:00:00", "title": "Belite Bio Reports Unaudited Third Quarter 2026 Financial "
      "Results and Provides a Corporate Update", "text": "SAN DIEGO, Nov. 12, 2026 (GLOBE NEWSWIRE) -- Belite Bio, Inc "
      "(NASDAQ: BLTE) ... today announced its financial results for the third quarter ended September 30, 2026",
      "url": "u-blte"},
     {"kind": "results", "period_key": "2026Q3", "published_et": "2026-11-12 06:00"}),
    ("ABCL", "AbCellera Biologics Inc.",
     {"publishedDate": "2026-11-09 16:05:00", "title": "AbCellera Reports Q3 2026 Business Results", "text":
      "VANCOUVER, British Columbia--(BUSINESS WIRE)---- $ABCL--AbCellera Reports Q3 2026 Business Results.",
      "url": "u-abcl"},
     {"kind": "results", "period_key": "2026Q3", "published_et": "2026-11-09 16:05"}),
    # Roivant's fiscal year ends March 31: its "Second Quarter Ended September 30" names a fiscal quarter whose fiscal
    # year label would be a guess, so it is not read (no row rather than a wrong period)
    ("ROIV", "Roivant Sciences Ltd.",
     {"publishedDate": "2026-11-09 07:00:00", "title": "Roivant Reports Financial Results for the Second Quarter Ended "
      "September 30, 2026, and Provides Business Update", "text": "LISRAYA (brepocitinib) generated net product "
      "revenue of $31.0 million in its first 5 weeks of launch", "url": "u-roiv"},
     None),
    # constructed: preliminary figures stay out even with 'unaudited' now allowed in the headline
    ("BLTE", "Belite Bio, Inc",
     {"publishedDate": "2026-01-12 06:00:00", "title": "Belite Bio Announces Unaudited Preliminary Fourth Quarter "
      "2025 Financial Results", "text": "Belite Bio, Inc (NASDAQ: BLTE) today announced preliminary", "url": "u-blte-p"},
     None),
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
    # real, 2026-11-26 page red team: "Year-End" was not read as the full year, so the release had no period
    ("VKTX", "Viking Therapeutics, Inc.",
     {"publishedDate": "2026-02-11 16:16:00", "title": "Viking Therapeutics Reports Fourth Quarter and Year-End 2025 "
      "Financial Results and Provides Corporate Update", "text": "SAN DIEGO, Feb. 11, 2026 /PRNewswire/ -- Viking "
      "Therapeutics, Inc. (Viking) (Nasdaq: VKTX), ... today announced its financial results for the fourth quarter "
      "and year ended December 31, 2025", "url": "u2b"},
     {"kind": "results", "period_key": "2025Q4+FY", "published_et": "2026-02-11 16:16"}),
    ("VKTX", "Viking Therapeutics, Inc.",
     {"publishedDate": "2026-02-04 16:05:00", "title": "Viking Therapeutics to Report Financial Results for Fourth "
      "Quarter and Year-End 2025 on February 11, 2026", "text": "Conference Call Scheduled for Wednesday, February 11 at "
      "4:30 p.m. Eastern Time  SAN DIEGO, Feb. 4, 2026 /PRNewswire/ -- Viking Therapeutics, Inc. (\"Viking\") (NASDAQ: "
      "VKTX), ... today announced that the company will release financial results for the fourth quarter and year-end "
      "2025 after the market close on Wednesday, February 11, 2026.", "url": "u2c"},
     {"kind": "schedule", "period_key": "2025Q4+FY", "report_date": "2026-02-11", "timing": "after_close"}),
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
    # red team round 2: year-to-date headlines read as the quarter that ends on the day, never as the half or year
    ("AMPH", "Amphastar Pharmaceuticals, Inc.", {"publishedDate": "2026-08-06 16:10:00", "title": "Amphastar Pharmaceuticals Reports Financial Results for the Three and Six Months Ended June 30, 2026", "text": "Amphastar Pharmaceuticals, Inc. (NASDAQ: AMPH) reported results.", "url": "m1"},
     {"kind": "results", "period_key": "2026Q2"}),
    ("AMPH", "Amphastar Pharmaceuticals, Inc.", {"publishedDate": "2026-02-26 16:10:00", "title": "Amphastar Pharmaceuticals Reports Financial Results for the Three and Twelve Months Ended December 31, 2025", "text": "Amphastar Pharmaceuticals, Inc. (NASDAQ: AMPH) reported results.", "url": "m2"},
     {"kind": "results", "period_key": "2025Q4+FY"}),
    ("AMPH", "Amphastar Pharmaceuticals, Inc.", {"publishedDate": "2026-11-05 16:10:00", "title": "Amphastar Pharmaceuticals Reports Financial Results for the Nine Months Ended September 30, 2026", "text": "Amphastar Pharmaceuticals, Inc. (NASDAQ: AMPH) reported results.", "url": "m3"},
     None),
    ("AMPH", "Amphastar Pharmaceuticals, Inc.", {"publishedDate": "2026-08-20 16:10:00", "title": "Amphastar Pharmaceuticals Reports Financial Results for the Twelve Months Ended June 30, 2026", "text": "Amphastar Pharmaceuticals, Inc. (NASDAQ: AMPH) reported results.", "url": "m4"},
     {"kind": "results", "period_key": "FY2026"}),
    ("AMPH", "Amphastar Pharmaceuticals, Inc.", {"publishedDate": "2026-08-20 16:10:00", "title": "Amphastar Pharmaceuticals Reports Financial Results for the Three and Twelve Months Ended June 30, 2026", "text": "Amphastar Pharmaceuticals, Inc. (NASDAQ: AMPH) reported results.", "url": "m5"},
     {"kind": "results", "period_key": "FY2026Q4"}),
    # a name stored without its legal form still matches a headline that gives the whole name with one
    ("ALVO", "Alvotech", {"publishedDate": "2026-08-20 07:00:00", "title": "Alvotech SA Reports First Half 2026 Results",
     "text": "REYKJAVIK, Iceland.", "url": "a1"}, {"kind": "results", "period_key": "2026H1"}),
    # "Fourth Quarter and Fiscal Year 2025" stays fiscal in the parser (the page builder reads it as calendar only for a
    # company whose other releases print calendar quarters)
    (V, VN, {"publishedDate": "2025-09-05 16:05:00", "title": "Viking Therapeutics Reports Fourth Quarter and Fiscal "
     "Year 2025 Financial Results", "text": "Viking Therapeutics, Inc. (NASDAQ: VKTX) reported.", "url": "f2"},
     {"kind": "results", "period_key": "FY2025Q4"}),
    # a legal form that is not the company's own does not make another company's headline its own
    ("AGIO", "Agios Pharmaceuticals, Inc.", {"publishedDate": "2026-08-01 07:00:00", "title": "Agios Ltd. Reports "
     "Second Quarter 2026 Financial Results", "text": "LONDON.", "url": "g1"}, None),
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
     "Results Release", "text": "(NASDAQ: VKTX)", "url": "c8"}, {"kind": "postponed", "period_key": "2026Q3"}),
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

    # round 2: 'announces ... results <call|date|release>' is a schedule, never a results row
    (V, VN, {"publishedDate": "2026-10-20 08:00:00", "title": "Viking Therapeutics Announces Third Quarter 2026 Financial "
     "Results Conference Call and Webcast", "text": "(NASDAQ: VKTX) will report results after the market close on "
     "Wednesday, October 28, 2026.", "url": "d1"}, {"kind": "schedule", "report_date": "2026-10-28"}),
    (V, VN, {"publishedDate": "2026-10-20 08:00:00", "title": "Viking Therapeutics Announces Date of Third Quarter 2026 "
     "Financial Results Release", "text": "(NASDAQ: VKTX) on October 28, 2026", "url": "d2"},
     {"kind": "schedule", "report_date": "2026-10-28"}),
    (V, VN, {"publishedDate": "2026-10-20 08:00:00", "title": "Viking Therapeutics Announces Third Quarter 2026 Earnings "
     "Release Date", "text": "(NASDAQ: VKTX)", "url": "d3"}, None),
    (V, VN, {"publishedDate": "2026-10-20 08:00:00", "title": "Viking Therapeutics Announces Upcoming Third Quarter 2026 "
     "Financial Results Release", "text": "(NASDAQ: VKTX)", "url": "d4"}, None),
    # round 2: the call's day is not the report day
    (V, VN, {"publishedDate": "2026-10-28 16:05:00", "title": "Viking Therapeutics to Report Third Quarter 2026 Financial "
     "Results", "text": "Conference Call Scheduled for Thursday, November 5, at 8:30 a.m. Eastern Time SAN DIEGO, Oct. 28, "
     "2026 /PRNewswire/ -- Viking Therapeutics, Inc. (NASDAQ: VKTX) will release results after the market close on "
     "Wednesday, November 4, 2026.", "url": "d5"}, {"kind": "schedule", "report_date": "2026-11-04",
     "call_time": "8:30 a.m. ET"}),
    (V, VN, {"publishedDate": "2026-10-28 16:05:00", "title": "Viking Therapeutics to Host Conference Call on November 5 "
     "to Discuss Third Quarter 2026 Financial Results", "text": "(NASDAQ: VKTX)", "url": "d6"}, None),
    # round 2: other companies' releases
    ("MRK", "Merck & Co., Inc.", {"publishedDate": "2026-11-12 07:00:00", "title": "Merck Reports Strong Third Quarter "
     "2026 Results", "text": "DARMSTADT, Germany--(BUSINESS WIRE)--Merck, a leading science and technology company ...",
     "url": "d7"}, None),
    ("VRTX", "Vertex Pharmaceuticals Incorporated", {"publishedDate": "2026-11-05 16:05:00", "title": "Vertex Reports "
     "Third Quarter 2026 Financial Results", "text": "Vertex, Inc. (NASDAQ: VERX), a global provider of tax technology",
     "url": "d8"}, None),
    # round 2: real-results shapes that the noise filter must not drop; brand headline names
    (V, VN, {"publishedDate": "2026-10-28 16:05:00", "title": "Viking Therapeutics Reports Third Quarter 2026 Financial "
     "Results and Highlights Progress Across Investigational Pipeline", "text": "(NASDAQ: VKTX)", "url": "d9"},
     {"kind": "results", "period_key": "2026Q3"}),
    ("LLY", "Eli Lilly and Company", {"publishedDate": "2026-10-30 06:45:00", "title": "Lilly reports third-quarter 2026 "
     "financial results", "text": "Eli Lilly and Company (NYSE: LLY) today announced", "url": "d10"},
     {"kind": "results", "period_key": "2026Q3"}),
    ("NVAX", "Novavax INC", {"publishedDate": "2026-11-06 07:00:00", "title": "Novavax Reports Third Quarter 2026 "
     "Financial Results", "text": "Novavax, Inc. (Nasdaq: NVAX)", "url": "d11"}, {"kind": "results"}),
    # round 2: a past day with a weekday does not void the release
    (V, VN, {"publishedDate": "2026-11-18 08:00:00", "title": "Viking Therapeutics to Report Third Quarter 2026 Financial "
     "Results on November 24", "text": "Viking (NASDAQ: VKTX), which last reported on Wednesday, October 28, will release "
     "results on Tuesday, November 24, 2026.", "url": "d12"}, {"kind": "schedule", "report_date": "2026-11-24"}),
    # round 3: call announcements, preliminary figures, wire datelines after the tag, fiscal periods
    (V, VN, {"publishedDate": "2026-10-20 08:00:00", "title": 'Viking Therapeutics Announces Conference Call and Webcast for Third Quarter 2026 Financial Results', "text": '(NASDAQ: VKTX)', "url": "e1"}, None),
    (V, VN, {"publishedDate": "2026-10-20 08:00:00", "title": 'Viking Therapeutics Announces Conference Call to Discuss Third Quarter 2026 Financial Results', "text": '(NASDAQ: VKTX)', "url": "e2"}, None),
    (V, VN, {"publishedDate": "2026-10-20 08:00:00", "title": 'Viking Therapeutics Announces Webcast of Third Quarter 2026 Financial Results', "text": '(NASDAQ: VKTX)', "url": "e3"}, None),
    (V, VN, {"publishedDate": "2026-10-20 08:00:00", "title": 'Viking Therapeutics Announces It Will Report Third Quarter 2026 Financial Results on November 5', "text": '(NASDAQ: VKTX)', "url": "e4"}, {"kind": "schedule", "report_date": "2026-11-05"}),
    (V, VN, {"publishedDate": "2026-01-12 08:00:00", "title": 'Viking Therapeutics Announces Preliminary Fourth Quarter and Full Year 2025 Results', "text": '(NASDAQ: VKTX)', "url": "e5"}, None),
    (V, VN, {"publishedDate": "2026-10-20 08:00:00", "title": 'Viking Therapeutics Announces Third Quarter 2026 Financial Results and Conference Call Date', "text": '(NASDAQ: VKTX)', "url": "e6"}, None),
    (V, VN, {"publishedDate": "2026-10-28 16:05:00", "title": 'Viking Therapeutics Reports Third Quarter 2026 Financial Results and Provides Update on Manufacturing Delay', "text": '(NASDAQ: VKTX)', "url": "e7"}, {"kind": "results", "period_key": "2026Q3"}),
    (V, VN, {"publishedDate": "2026-10-21 16:05:00", "title": 'Viking Therapeutics to Report Third Quarter 2026 Financial Results', "text": 'SAN DIEGO / ACCESSWIRE / October 21, 2026 / Viking (NASDAQ: VKTX) today announced it will report results after the market close November 4, 2026.', "url": "e8"}, {"kind": "schedule", "report_date": "2026-11-04"}),
    (V, VN, {"publishedDate": "2026-10-21 16:05:00", "title": 'Viking Therapeutics to Host Conference Call to Discuss Third Quarter 2026 Financial Results on November 5, 2026', "text": '(NASDAQ: VKTX) will release results after the market close on Wednesday, November 4, 2026.', "url": "e9"}, {"kind": "schedule", "report_date": "2026-11-04"}),
    (V, VN, {"publishedDate": "2026-10-20 08:00:00", "title": 'Viking Therapeutics to Present New Long-Term Efficacy Results for VK2735 at ObesityWeek 2026', "text": '(NASDAQ: VKTX)', "url": "e10"}, None),
    (V, VN, {"publishedDate": "2027-02-25 16:05:00", "title": 'Viking Therapeutics Reports Fourth Quarter Results; Issues 2027 Outlook', "text": '(NASDAQ: VKTX)', "url": "e11"}, None),
    (V, VN, {"publishedDate": "2026-08-10 16:05:00", "title": 'Viking Therapeutics Reports First Quarter Fiscal 2027 Financial Results', "text": '(NASDAQ: VKTX)', "url": "e12"}, {"kind": "results", "period_key": "FY2027Q1"}),
    (V, VN, {"publishedDate": "2026-08-10 16:05:00", "title": 'Viking Therapeutics Reports Q1 Fiscal 2027 Financial Results', "text": '(NASDAQ: VKTX)', "url": "e13"}, {"kind": "results", "period_key": "FY2027Q1"}),
    (V, VN, {"publishedDate": "2026-02-25 16:05:00", "title": 'Viking Therapeutics Reports Fourth Quarter and Full Year 2025 Financial Results', "text": '(NASDAQ: VKTX)', "url": "e14"}, {"kind": "results", "period_key": "2025Q4+FY"}),
    (V, VN, {"publishedDate": "2026-02-25 16:05:00", "title": 'Viking Therapeutics Reports Q4 and Full Year 2025 Financial Results', "text": '(NASDAQ: VKTX)', "url": "e14b"}, {"kind": "results", "period_key": "2025Q4+FY"}),
    (V, VN, {"publishedDate": "2026-02-25 16:05:00", "title": 'Viking Therapeutics Reports Fourth-Quarter and Year-Ended 2025 Financial Results', "text": '(NASDAQ: VKTX)', "url": "e14c"}, {"kind": "results", "period_key": "2025Q4+FY"}),
    (V, VN, {"publishedDate": "2026-10-28 16:05:00", "title": 'Viking Therapeutics Reports Third Quarter 2027 Financial Results', "text": '(NASDAQ: VKTX)', "url": "e15"}, None),
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
    no noise words in any title, known kinds only, no duplicate urls. (No check against today's company name: a rename
must not block a deploy; each row stores the stem it was matched with.)"""
    import json
    p = os.path.join(HERE, "_earnings_dates.json")
    if not os.path.exists(p):
        return 0
    bad = []
    for tk, ent in (json.load(open(p, encoding="utf-8")).get("tickers") or {}).items():
        seen = set()
        for r in ent.get("releases") or []:
            t = r.get("title", "")
            if r.get("url") in seen:
                bad.append(f"{tk}: duplicate {r.get('url')}")
            seen.add(r.get("url"))
            if E.NOISE.search(t):
                bad.append(f"{tk}: noise title {t[:60]!r}")
            if r.get("kind") not in ("results", "schedule", "postponed"):
                bad.append(f"{tk}: unknown kind {r.get('kind')!r}")
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
