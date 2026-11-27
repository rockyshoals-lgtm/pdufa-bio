# -*- coding: utf-8 -*-
"""Guard: extend_conference_runup anchors only on a company's own data release from the meeting, and prices
rows with the published study's exact arithmetic.

2026-11-26 (David: "mine for conferences ... put the run up red team"). Three parts:
  1. Headline rules, on SYNTHETIC headlines shaped like real ones (company names invented):
       * "Presents data at ESMO 2026" anchors; "to present", "abstracts accepted", "highlights" do not
       * "ESMO Asia 2026" is not ESMO; a headline naming another year is not this edition
  2. Window arithmetic on a synthetic price series, checked by hand-computed values.
  3. The committed cache (_conference_runup_additions.json), when present: every row has an https
     release link, an anchor inside its meeting's window, a meeting with an organiser source, no duplicate
     key, no overlap with the published study, and complete rows carry every window in a sane range.
  Also: conf_study/meetings_extra.json has an organiser source and quote for every meeting.

    python tests/test_conference_runup_additions.py   (PLANT=1 plants a bad row; the guard must fail)
"""
import csv
import datetime as dt
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import extend_conference_runup as X  # noqa: E402

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


# 1. headline rules ---------------------------------------------------------------------------------------
esmo = {"code": "ESMO", "name": "European Society for Medical Oncology Congress", "start": "2026-10-23",
        "end": "2026-10-27", "source": "https://example.org/esmo"}
esmo_asia = {"code": "ESMO Asia", "name": "ESMO Asia Congress", "start": "2026-12-04", "end": "2026-12-06",
             "source": "https://example.org/esmo-asia"}
acr = {"code": "ACR", "name": "ACR Convergence", "start": "2026-11-06", "end": "2026-11-11",
       "source": "https://example.org/acr"}
ash = {"code": "ASH", "name": "ASH Annual Meeting", "start": "2026-12-12", "end": "2026-12-15",
       "source": "https://example.org/ash"}
aha = {"code": "AHA", "name": "AHA Scientific Sessions", "start": "2026-11-06", "end": "2026-11-09",
       "source": "https://example.org/aha"}
asn = {"code": "ASN", "name": "ASN Kidney Week", "start": "2026-10-22", "end": "2026-10-25",
       "source": "https://example.org/asn"}
ena = {"code": "ENA", "name": "EORTC-NCI-AACR Symposium", "start": "2026-11-18", "end": "2026-11-20",
       "source": "https://example.org/ena"}
esc = {"code": "ESC", "name": "ESC Congress", "start": "2026-08-28", "end": "2026-08-31",
       "source": "https://example.org/esc"}
ada = {"code": "ADA", "name": "ADA Scientific Sessions", "start": "2026-06-05", "end": "2026-06-08",
       "source": "https://example.org/ada"}
ers = {"code": "ERS", "name": "ERS Congress", "start": "2026-09-05", "end": "2026-09-09",
       "source": "https://example.org/ers"}
ms = [esmo, esmo_asia, acr, ash, aha, asn, ena, esc, ada, ers]
CASES = [
    ("Zorvexa Therapeutics Announces Data From Three Clinical Trials at ESMO 2026", esmo, True),
    ("Quellbridge Bio Presents New Data at ESMO 2026 Showing Durable Responses", esmo, True),
    ("Quellbridge Bio Highlights Progress at the European Society for Medical Oncology (ESMO) Congress 2026",
     esmo, False),
    ("Zorvexa Therapeutics to Present Data at ESMO 2026", esmo, False),
    ("Zorvexa Therapeutics Announces Abstracts Accepted for Presentation at ESMO 2026", esmo, False),
    ("Zorvexa Therapeutics Presents Data at ESMO Asia 2026", esmo, False),
    ("Zorvexa Therapeutics Presents Data at ESMO Asia 2026", esmo_asia, True),
    ("Zorvexa Therapeutics Presents Data at ESMO 2025", esmo, False),
    ("Zorvexa Therapeutics Reports Third Quarter 2026 Financial Results and Highlights ESMO Data", esmo, False),
    ("Corvalith Bio Presents New Clinical Data at ACR Convergence 2026", acr, True),
    ("Corvalith Bio Presents Data at the 68th ASH Annual Meeting", ash, True),
    ("Corvalith Bio Presents Data Showing ASH Levels in Soil", ash, False),          # bare ASH never counts
    ("Corvalith Bio Presents New Data at ASH 2026", ash, True),                      # code + year counts
    # red team, Nov 26 2026: shapes of real headlines that announce a talk still to come (names invented)
    ("Zorvexa ORIGIN Final Efficacy Analysis Will be A Featured Late-breaking Oral Presentation at ASN Kidney "
     "Week 2026", asn, False),
    ("Zorvexa Phase 3 Results to Be Showcased in Presidential Symposium at ESMO 2026", esmo, False),
    ("Zorvexa Data Sets to Be Featured at ESMO 2026", esmo, False),
    ("Zorvexa Announces Presentation of New Data at AHA 2026", aha, False),
    ("Zorvexa Announces Late-Breaking Presentation of Phase 2 Data at AHA Scientific Sessions 2026", aha, False),
    ("Zorvexa Highlights Acceptance of Three Abstracts at ASH 2026", ash, False),
    ("Zorvexa Presents New Data at the AHA Hypertension Scientific Sessions 2026", aha, False),
    ("Zorvexa Presents Data at Hypertrophic Cardiomyopathy Scientific Sessions with AHA 2026", aha, False),
    ("Zorvexa Presents Positive Phase 3 Results at ESMO 2026; Company to Host Investor Webcast", esmo, True),
    ("Zorvexa Presents Phase 1 Data at the EORTC-NCI-AACR Symposium", ena, True),
    ("Zorvexa Presents Late-Breaking Data at AHA Scientific Sessions 2026", aha, True),
    # red team round 2: diseases are not meetings; edition numbers inside names; topline-then-meeting releases
    ("Zorvexa Presents New Late-Breaking Data in Hypertension at AHA Scientific Sessions 2026", aha, True),
    ("Zorvexa Presents Heart Failure Outcomes Data at ESC Congress 2026", esc, True),
    ("Zorvexa Presents Gene Therapy Data at ASH 2026", ash, True),
    ("Zorvexa Results Presented in Hot Line Session at the European Society of Cardiology (ESC) Congress 2026",
     esc, True),
    ("Zorvexa Presents Data at ESC Heart Failure 2026", esc, False),
    ("Zorvexa Presents New Data at the American Diabetes Association's 86th Scientific Sessions", ada, True),
    ("Zorvexa Presents Data at the ERS International Congress 2026", ers, True),
    ("Zorvexa Reports Positive Phase 3 Topline Results; Full Data to Be Presented at ESMO 2026", esmo, False),
    ("Zorvexa Reports Positive Topline Results - Data Will Be Presented at AHA 2026", aha, False),
    ("Zorvexa Presents Data at ESMO Virtual Plenary 2026", esmo, False),
    ("Zorvexa Announces Presentation of Phase 3 Data Demonstrating Durable Responses at ESMO 2026", esmo, True),
    ("Co - Late-Breaking Data Presented at AHA Scientific Sessions 2026", aha, True),
]
for title, m, want in CASES:
    got = X.anchors(title, m, ms)
    check(got == want, f"headline rule: {title!r} -> {got}, want {want}")

# red team 2026-11-27: the meeting a headline names, and what a release out before the meeting opens says
endo = {"code": "ENDO", "name": "ENDO", "start": "2026-06-13", "end": "2026-06-16", "source": "https://example.org/endo"}
check(not X.anchors("Zorvexa Presents New Data at the Pediatric Endocrine Society's 2026 Annual Meeting", endo, ms + [endo]),
      "headline rule: the Pediatric Endocrine Society was read as ENDO")
check(not X.anchors("Zorvexa Announces Multiple AlloNK\u00ae Data Presentations at ESMO 2026", esmo, ms),
      "headline rule: a notice of presentations with a trademark sign in it was read as data")
check(not X.early_ok("Zorvexa Highlights Pipeline at ESMO 2026", "Zorvexa announced that new data will be presented at "
                     "ESMO 2026.", "2026-09-22", esmo), "early release: a notice of talks to come anchored the meeting")
check(X.early_ok("Zorvexa Highlights Pipeline at ESMO 2026", "Data will be presented: ORR was 42% in 30 patients.",
                 "2026-10-13", esmo), "early release: an abstract-day release with a result in figures was dropped")
check(X.early_ok("Zorvexa Highlights Pipeline at ESMO 2026", "new data will be presented today", "2026-10-24", esmo),
      "early release: a release during the meeting was held to the before-the-meeting rule")
check(not X.early_ok("Zorvexa Showcases Data at AD/PD 2026 and ESMO 2026", "Zorvexa today showcased data.",
                     "2026-10-01", esmo), "early release: a release naming another meeting anchored this one")
# attribution: a partner's release that only cites the ticker is not the ticker's
check(not X.own("ZZQA", "Zorvexa Therapeutics Inc.", "Partnerco Presents Overall Survival Data at ESMO 2026",
                "Partnerco (HKEX: 9999.HK) and its partner Zorvexa Therapeutics Inc. (NASDAQ: ZZQA) today"),
      "attribution: partner's release landed on the ticker")
check(X.own("ZZQA", "Zorvexa Therapeutics Inc.", "Zorvexa Therapeutics Presents Overall Survival Data at ESMO 2026",
            "Zorvexa Therapeutics Inc. (NASDAQ: ZZQA) today"), "attribution: the company's own release rejected")
# attribution from what is stored: the tie to the ticker can sit past the stored excerpt (run 558: seven rows such
# as Lyell's EHA release, whose "(Nasdaq: LYEL)" sits 700 characters in, passed at fetch and failed this guard).
# The row keeps the tying words as release_evidence, so a row that passed at fetch passes here. Synthetic names.
_lead = ("Highlights: more than 100 patients treated, no Grade 3 events, translational data support durable "
         "responses and dual targeting; partner Partnerco (NYSE: PRTN) holds rights outside the US. ") * 4
for tag, body in [("tag", _lead + "CITY, Oct. 24, 2026 -- Zorvexa Therapeutics, Inc. (Nasdaq: ZZQA), a clinical company"),
                  ("name", _lead + "CITY, Oct. 24, 2026 -- Zorvexa Therapeutics, Inc., a clinical company, announced")]:
    nm, tt = "Zorvexa Therapeutics, Inc.", "Zorvexa Presents Updated Data at ESMO 2026"
    check(len(body) > X.EXCERPT + 20, f"evidence case {tag}: body not longer than the excerpt")
    check(X.own("ZZQA", nm, tt, body), f"evidence case {tag}: full release not attributed")
    check(not X.own("ZZQA", nm, tt, body[:X.EXCERPT]), f"evidence case {tag}: excerpt alone should not attribute")
    row = {"ticker": "ZZQA", "release_excerpt": body[:X.EXCERPT], "release_evidence": X.evidence("ZZQA", nm, body)}
    check(0 < len(row["release_evidence"]) <= 400, f"evidence case {tag}: evidence missing or too long")
    check(row["release_evidence"] in body, f"evidence case {tag}: evidence is not the release's own words")
    check(X.own("ZZQA", nm, tt, X.stored_text(row)), f"evidence case {tag}: stored row no longer attributed")
    row.update({"meeting_code": "ESMO", "conf": "ESMO", "meeting_start": esmo["start"], "meeting_end": esmo["end"],
                "meeting_source": esmo["source"], "anchor": "2026-10-24", "release_title": tt})
    check(X.passes(row, [esmo, esmo_asia], nm), f"evidence case {tag}: stored row fails passes()")
# the evidence is cut from the same string as the excerpt: FMP sends double-escaped entities ("&amp;amp;"), and
# a second clean() would shift a tag that straddles character 600 back inside it, so no evidence would be kept
_raw = ("Data from the partner&amp;amp;rsquo;s study &amp;amp; ours, " * 20)[:661] + \
    " CITY -- Zorvexa (Nasdaq: ZZQA), a clinical company, today announced data."
_once = X.FE.clean(_raw)
_nm, _tt = "Zorvexa Therapeutics, Inc.", "Zorvexa Presents Updated Data at ESMO 2026"
_at = _once.find("(Nasdaq")
check(_at < X.EXCERPT < _at + 14 and X.FE.clean(_once).find("(Nasdaq") < X.EXCERPT - 14,
      "double-escape case no longer puts the tag across the excerpt's end (and inside it after a second clean)")
check(X.own("ZZQA", _nm, _tt, _once) and not X.own("ZZQA", _nm, _tt, _once[:X.EXCERPT]),
      "double-escape case: attribution should need the words past the excerpt")
_row = {"ticker": "ZZQA", "release_excerpt": _once[:X.EXCERPT], "release_evidence": X.evidence("ZZQA", _nm, _once)}
check(X.own("ZZQA", _nm, _tt, X.stored_text(_row)), "evidence lost when the release carries double-escaped entities")
check(X.evidence("ZZQA", "Zorvexa Therapeutics, Inc.", "Zorvexa Therapeutics, Inc. (Nasdaq: ZZQA)" + " x" * 400) == "",
      "evidence kept although the tag is inside the excerpt")
check(X.evidence("ZZQA", "Zorvexa Therapeutics, Inc.", _lead + " (NYSE: PRTN) partner of Zorvexa") == "",
      "evidence kept from another company's tag")
check(X.study_code("IDWeek") == "IDWEEK" and X.study_code("ESMO") == "ESMO", "study codes do not match the study")

# every hand-verified presenter is read, ticker page or not (6 of 28 Aug-Nov 2026 presenters had none)
_uni = X.universe()
for _tk in ("TGTX", "NBP", "APRE", "ENTX"):
    check(_tk in _uni, f"universe: verified presenter {_tk} is never read")

# 2. window arithmetic ------------------------------------------------------------------------------------
day0 = dt.date(2026, 1, 5)
series, d = [], day0
while len(series) < 60:
    if d.weekday() < 5:
        series.append((d.isoformat(), 100.0 + len(series)))   # close = 100 + index
    d += dt.timedelta(days=1)
anchor = series[40][0]          # i = 40; d1 = close(i-1) = 139; close(i-30) = 110; close(i+1) = 141
w = X.window(series, anchor)
check(w is not None, "window: complete series gave no window")
if w:
    check(w["runup_30d"] == round((139 / 110 - 1) * 100, 2), f"runup_30d {w['runup_30d']}")
    check(w["runup_5d"] == round((139 / 135 - 1) * 100, 2), f"runup_5d {w['runup_5d']}")
    check(w["event_day"] == round((141 / 139 - 1) * 100, 2), f"event_day {w['event_day']}")
    check(w["post_10d"] == round((150 / 139 - 1) * 100, 2), f"post_10d {w['post_10d']}")
    check(w["d_minus_1"] == series[39][0] and w["d0"] == anchor, "window: wrong d-1 / d0")
check(X.window(series, series[30][0]) is None, "window: fewer than 35 days before still priced")
check(X.window(series, series[50][0]) is None, "window: fewer than 11 days after still priced")

# meetings_extra.json -------------------------------------------------------------------------------------
extra = json.load(io.open(X.EXTRA, encoding="utf-8"))["meetings"]
for m in extra:
    check(str(m.get("source", "")).startswith("https://"), f"meetings_extra {m.get('code')}: no https source")
    check(bool(m.get("source_quote")), f"meetings_extra {m.get('code')}: no organiser quote")
    check(m.get("start", "") <= m.get("end", "") and len(m.get("start", "")) == 10,
          f"meetings_extra {m.get('code')}: bad dates")

# 3. the committed cache ----------------------------------------------------------------------------------
cache = None
if os.path.exists(X.CACHE):
    cache = json.load(io.open(X.CACHE, encoding="utf-8"))
if os.environ.get("PLANT") == "1":
    cache = cache or {"rows": []}
    cache["rows"] = list(cache["rows"]) + [{
        "key": "ZZQA|ESMO|2026", "ticker": "ZZQA", "conf": "ESMO", "year": 2026, "meeting_start": "2026-10-23",
        "meeting_end": "2026-10-27", "meeting_source": "https://example.org", "anchor": "2026-07-01",
        "release_url": "http://example.org/pr", "release_title": "Partnerco to Present Data at ESMO 2026",
        "status": "complete", "runup_30d": 900.0},
        {"key": "ZZQB|ESMO|2026", "ticker": "ZZQB", "company": "Zorvexa Therapeutics Inc.", "conf": "ESMO",
         "meeting_code": "ESMO", "year": 2026, "meeting_start": "2026-10-23", "meeting_end": "2026-10-27",
         "meeting_source": "https://example.org/esmo", "anchor": "2026-10-24", "release_url": "https://example.org/pr",
         "release_title": "Partnerco Presents Overall Survival Data at ESMO 2026",
         "release_excerpt": "Partnerco (HKEX: 9999.HK) and partner Zorvexa Therapeutics Inc. (NASDAQ: ZZQB)",
         "status": "pending"}]
if cache is not None:
    pub = X.published_keys()
    seen = set()
    for r in cache.get("rows", []):
        k = r.get("key", "")
        check(k not in seen, f"cache {k}: duplicate key")
        seen.add(k)
        check(k == f"{r.get('ticker')}|{r.get('conf')}|{r.get('year')}", f"cache {k}: key does not match row")
        check((r.get("ticker"), r.get("conf"), str(r.get("year"))) not in pub, f"cache {k}: already in published study")
        check(str(r.get("release_url", "")).startswith("https://"), f"cache {k}: release link not https")
        check(str(r.get("meeting_source", "")).startswith("https://"), f"cache {k}: meeting has no source")
        check(bool(r.get("release_title")), f"cache {k}: no release headline")
        try:
            lo = (dt.date.fromisoformat(r["meeting_start"]) - dt.timedelta(days=X.EARLY_DAYS)).isoformat()
            hi = (dt.date.fromisoformat(r["meeting_end"]) + dt.timedelta(days=X.LATE_DAYS)).isoformat()
            check(lo <= r["anchor"] <= hi, f"cache {k}: anchor {r['anchor']} outside {lo}..{hi}")
        except (KeyError, ValueError):
            check(False, f"cache {k}: missing or bad dates")
        check(r.get("status") in ("pending", "complete", "check"), f"cache {k}: bad status")
        ev = r.get("release_evidence", "")
        check(len(ev) <= 400, f"cache {k}: release_evidence longer than 400 characters")
        check(X.passes(r, X.meetings(X.EARLY_DATE, "9999-12-31"), r.get("company", "")),
              f"cache {k}: no longer passes the headline, meeting or attribution rules ({r.get('release_title', '')[:80]})")
        check(str(r.get("year")) == str(r.get("meeting_start", ""))[:4], f"cache {k}: year is not the meeting's")
        if r.get("status") == "complete":
            for f in ("runup_30d", "runup_20d", "runup_10d", "runup_5d", "event_day", "post_5d", "post_10d"):
                v = r.get(f)
                check(isinstance(v, (int, float)) and X.RANGE[0] < v < X.RANGE[1],
                      f"cache {k}: {f}={v!r} missing or out of range")
            check(r.get("d0", "") >= r.get("anchor", "~") and r.get("d_minus_1", "~") < r.get("anchor", ""),
                  f"cache {k}: price days do not straddle the anchor")

if fails:
    print("FAIL test_conference_runup_additions:")
    for f in fails[:40]:
        print("  -", f)
    sys.exit(1)
print(f"OK test_conference_runup_additions ({len(CASES)} headline cases, window arithmetic, "
      f"{len(extra)} extra meetings, {len((cache or {}).get('rows', []))} cache rows)")
