# -*- coding: utf-8 -*-
"""apply_1010_neladalkib_month.py -- audit 2026-10-10 item 5 ruling: neladalkib to month precision.

The row's day, 2026-11-27, came from a Royalty Pharma 8-K quoting Nuvalent's May 2026 NDA-acceptance
announcement. Nuvalent was acquired by GSK (merger completed 2026-07-15; Form 15 filed 2026-07-27) and the
sponsor's own current statement is the GSK Q2 2026 results 6-K (2026-07-28), read 2026-10-10:
  "Neladalkib is an investigational ALK tyrosine kinase inhibitor (TKI) currently under review with the US
   FDA for use by patients with TKI pre-treated ALK-positive NSCLC, with PDUFA date anticipated in November
   2026."
No primary source read by the sponsor of record states the 27th. Ruling (auditor, 10-10): a day we cannot
source is a day we do not publish. The row moves to month precision with the 6-K as source; the former day
and its origin are kept in date_history. Facts only; not investment advice.
"""
import io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
SIXK = "https://www.sec.gov/Archives/edgar/data/1131399/000165495426006949/a1493o.htm"
s = io.open(P, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
r = next(x for x in rows if x["id"] == "pdufa_nuvl_2026-11-27")
d = r["_d"]
if r.get("dp") != "month":
    hist = d.setdefault("date_history", [])
    hist.append({"date": "2026-11-27", "precision": "day",
                 "source": d.get("source"), "source_url": d.get("source_url"),
                 "note": "day the row carried when created, from a Royalty Pharma 8-K quoting Nuvalent's May 2026 announcement"})
    hist.append({"date": "2026-11", "precision": "month", "changed": "2026-10-10",
                 "why": ("Nuvalent was acquired by GSK (July 2026). GSK's Q2 2026 results 6-K, the sponsor's own current "
                         "statement, gives only 'PDUFA date anticipated in November 2026'; no primary source states the 27th. "
                         "Audit 2026-10-10 ruling: month precision, GSK 6-K as source.")})
    r["d"], r["dp"], r["dm"] = "2026-11-30", "month", "2026-11"
    d["source"] = "GSK plc 6-K 2026-07-28 (Q2 2026 results)"
    d["source_url"] = SIXK
    d["source_quote"] = ("Neladalkib is an investigational ALK tyrosine kinase inhibitor (TKI) currently under review with the "
                         "US FDA for use by patients with TKI pre-treated ALK-positive NSCLC, with PDUFA date anticipated in "
                         "November 2026.")
    d["source_note"] = ("Former day 2026-11-27 (Royalty Pharma 8-K quoting Nuvalent) retired 2026-10-10; see date_history.")
    d["date_note"] = ("Day 2026-11-27 withdrawn 2026-10-10: no primary source of the sponsor of record (GSK) states it; "
                      "GSK's 6-K gives November 2026.")
    d.pop("days_to_decision", None)
    r["ua"] = "2026-10-10T17:00:00Z"
    print("  pdufa_nuvl_2026-11-27: dp month, dm 2026-11, source GSK 6-K 2026-07-28; former day in date_history")
else:
    print("  already month precision")
io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])

# The calendar follows the ledger of withdrawn days (fix_calendar_windowed_rows.py relabels "GSK 2026-11-27" to
# "GSK Nov 2026" from it); the homepage slate carries the month-end sentinel like every month row (REGN).
import re
LED = os.path.join(HERE, "_unsourced_day_dates.json")
led = json.load(io.open(LED, encoding="utf-8"))
if not any(e.get("ticker") == "GSK" and e.get("was_date") == "2026-11-27" for e in led["rows"]):
    led["rows"].append({"ticker": "GSK", "was_date": "2026-11-27", "month_kept": "2026-11", "new_precision": "month",
                        "why": ("GSK plc 6-K 2026-07-28 (Q2 2026 results) states the neladalkib PDUFA date as 'anticipated "
                                "in November 2026', a month. The November 27 day came from a Royalty Pharma 8-K quoting "
                                "Nuvalent's May 2026 announcement; Nuvalent was acquired by GSK in July 2026 and no primary "
                                "source of the sponsor of record states the day. Day withdrawn 2026-10-10 (audit ruling); "
                                "month sourced.")})
    io.open(LED, "w", encoding="utf-8", newline="\n").write(json.dumps(led, indent=1, ensure_ascii=False) + "\n")
    print("  _unsourced_day_dates.json: GSK 2026-11-27 -> month 2026-11")
SL = os.path.join(HERE, "pdufa_site_src", "api", "data.js")
t = io.open(SL, encoding="utf-8").read()
k = t.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(t[k:])
ch = 0
for c in slate["catalysts"]:
    if c.get("ticker") == "GSK" and str(c.get("date")) == "2026-11-27":
        c["date"] = "2026-11-30"; ch += 1
if ch:
    io.open(SL, "w", encoding="utf-8").write(t[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":")) + t[k + end:])
    print(f"  api/data.js SLATE: GSK neladalkib date -> 2026-11-30 (month-end sentinel, like every month row)")
# a pre-acquisition NUVL row for the same event still sat on the November page; one event, one row
for cp in (os.path.join(HERE, "pdufa_site_src", "calendar", "index.html"),
           os.path.join(HERE, "pdufa_site_src", "calendar", "2026", "november", "index.html")):
    doc = io.open(cp, encoding="utf-8", errors="replace").read()
    new = re.sub(r'<a class="row"[^>]*>\s*<div class="t">NUVL (?:&middot;|·) 2026-11-27</div>.*?</a>', "", doc, flags=re.S)
    if new != doc:
        io.open(cp, "w", encoding="utf-8", newline="").write(new)
        print(f"  removed the stale NUVL 2026-11-27 row from {os.path.relpath(cp, HERE)}")
