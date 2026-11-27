# -*- coding: utf-8 -*-
"""Guard: backfill_conference_runup re-dates older conference leads by the additions' rule only, from organiser-dated
meetings, and keeps nothing that does not re-check from what is stored.

2026-11-27 (coordinator, from the Yo research check: 439 leads 2022-2026 "matched to an SEC filing"). The red team
found the lead file's anchors were one calendar date per meeting edition (conf_registry.json), not the filing's: all
439 matched that file, AACR 2022 sat a month before the meeting, ASCO 2024 on the abstract day. So the leads are only
pointers, and this guard holds the backfill to the additions' rule:
  1. conf_study/meetings_past.json: every edition has an https organiser source whose quote states its start and end
     day and month; no edition repeats or contradicts conferences.json / meetings_extra.json; 0-7 days long.
  2. find_row on SYNTHETIC releases (names invented): the earliest own data release in the window anchors; a "to
     present" notice, a partner's release, a release outside the window, and the lead file's own date do not.
  3. The committed cache, when present: every row re-checks from what is stored (X.passes), anchors before the
     published study's cut-off, comes from a lead, is not in the published study, and complete rows carry every
     window in range.

    python tests/test_conference_runup_backfill.py   (PLANT=1 plants a bad row; the guard must fail)
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
import backfill_conference_runup as B  # noqa: E402
import extend_conference_runup as X  # noqa: E402

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


MON = "jan feb mar apr may jun jul aug sep oct nov dec".split()

# 1. past meetings ----------------------------------------------------------------------------------------
past = json.load(io.open(B.PAST, encoding="utf-8"))["meetings"]
check(len(past) >= 60, f"meetings_past.json: only {len(past)} editions")
seen = set()
others = json.load(io.open(os.path.join(HERE, "conferences.json"), encoding="utf-8"))["conferences"]
others += json.load(io.open(X.EXTRA, encoding="utf-8"))["meetings"]
other_by = {(c["code"], c["start"][:4]): c for c in others if c.get("start")}
for m in past:
    tag = f"{m.get('code')} {m.get('start', '')[:4]}"
    check(set(m) == {"code", "name", "start", "end", "city", "source", "source_quote"}, f"{tag}: fields {sorted(m)}")
    check(str(m.get("source", "")).startswith("https://"), f"{tag}: source not https")
    try:
        s, e = dt.date.fromisoformat(m["start"]), dt.date.fromisoformat(m["end"])
    except Exception:  # noqa: BLE001
        check(False, f"{tag}: bad dates")
        continue
    check(0 <= (e - s).days <= 7, f"{tag}: {(e - s).days} days long")
    check("2021-06-01" <= m["start"] < B.CUTOFF, f"{tag}: start {m['start']} outside the backfill range")
    q = m.get("source_quote", "").lower()
    nums = set(re.findall(r"\b0?(\d{1,2})\b", q))
    check(str(s.day) in nums and str(e.day) in nums and MON[s.month - 1] in q,
          f"{tag}: quote does not state {m['start']}..{m['end']}: {q[:80]!r}")
    k = (m["code"], m["start"][:4])
    check(k not in seen, f"{tag}: edition listed twice")
    seen.add(k)
    o = other_by.get(k)
    check(o is None or (o["start"], o["end"]) == (m["start"], m["end"]), f"{tag}: contradicts the calendar")

# 2. find_row on synthetic releases ---------------------------------------------------------------------------
m = {"code": "AACR", "name": "AACR Annual Meeting", "start": "2022-04-08", "end": "2022-04-13",
     "source": "https://example.org/aacr"}
ms = [m]
nm, tk = "Zorvexa Therapeutics, Inc.", "ZZQA"
body = "CITY, April 9, 2022 -- Zorvexa Therapeutics, Inc. (Nasdaq: ZZQA), a clinical company, today presented data."


def item(day, title, text=body, url="https://example.org/r"):
    return {"publishedDate": f"{day} 08:00:00", "title": title, "text": text, "url": url}


notice = item("2022-03-10", "Zorvexa Therapeutics to Present Data at AACR 2022")
partner = item("2022-04-08", "Partnerco Presents Data at AACR 2022",
               "Partnerco (NYSE: PRTN) and its partner Zorvexa Therapeutics, Inc. (Nasdaq: ZZQA) presented data.")
early = item("2022-02-01", "Zorvexa Therapeutics Presents Data at AACR 2022")          # before the window
lead_day = item("2022-03-08", "Zorvexa Therapeutics Reports Fourth Quarter 2021 Financial Results")
good = item("2022-04-09", "Zorvexa Therapeutics Presents Preclinical Data at AACR 2022", url="https://example.org/g")
later = item("2022-04-12", "Zorvexa Therapeutics Presents More Data at AACR 2022", url="https://example.org/l")
row, why = B.find_row(tk, nm, m, ms, [later, partner, notice, early, lead_day, good], "https://example.org/lead",
                      "2026-11-27")
check(row is not None and row["anchor"] == "2022-04-09" and row["release_url"] == "https://example.org/g",
      f"find_row: wanted the 2022-04-09 own data release, got {row and row['anchor']} ({why})")
check(row is not None and row.get("lead_source") == "https://example.org/lead", "find_row: lead source not kept")
row, why = B.find_row(tk, nm, m, ms, [partner, notice, early, lead_day], "", "2026-11-27")
check(row is None, f"find_row: a notice, partner release, out-of-window release or results release anchored ({why})")

# 3. committed cache ----------------------------------------------------------------------------------------
cache = json.load(io.open(B.CACHE, encoding="utf-8")) if os.path.exists(B.CACHE) else {"rows": []}
rows = list(cache.get("rows", []))
if os.environ.get("PLANT"):
    rows.append({"key": "ZZQA|AACR|2022", "ticker": "ZZQA", "company": nm, "conf": "AACR", "meeting_code": "AACR",
                 "year": 2022, "meeting_start": "2022-03-08", "meeting_end": "2022-03-08",
                 "meeting_source": "", "anchor": "2022-03-08", "release_title": "Zorvexa Highlights AACR",
                 "release_url": "https://example.org/x", "status": "complete"})
allm = B.all_meetings()
lead_keys = {B.lead_key(r) for r in B.leads()}
pub = X.published_keys()
keys = set()
for r in rows:
    k = r.get("key", "")
    check(k not in keys, f"cache: duplicate key {k}")
    keys.add(k)
    check(str(r.get("release_url", "")).startswith("https://"), f"cache {k}: release link not https")
    check(r.get("anchor", "9999") < B.CUTOFF, f"cache {k}: anchor {r.get('anchor')} after the published study")
    check(k in lead_keys, f"cache {k}: not from a lead")
    check((r.get("ticker"), r.get("conf"), str(r.get("year"))) not in pub, f"cache {k}: already in the published study")
    check(X.passes(r, allm, r.get("company") or r.get("ticker")), f"cache {k}: does not re-check from what is stored")
    if r.get("status") == "complete":
        vals = [r.get(f) for f in B.FIELDS]
        check(all(isinstance(v, (int, float)) and X.RANGE[0] < v < X.RANGE[1] for v in vals),
              f"cache {k}: complete row with a missing or out-of-range window")

if fails:
    print(f"FAIL: {len(fails)} conference backfill problem(s)")
    for f in fails[:12]:
        print("  ", f)
    sys.exit(1)
print(f"  PASS: {len(past)} organiser-dated past editions; backfill rule holds on synthetic releases; "
      f"{len(rows)} cached row(s) re-check from what is stored")
