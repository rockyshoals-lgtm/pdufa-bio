# -*- coding: utf-8 -*-
"""add_nvo_mim8.py -- restore the NVO Mim8 (denecimig) PDUFA row, goal 2026-09-30.

Found while actioning the 2026-09-01b re-audit: /pdufa/NVO-mim8 is the single
best-converting page on the site (60% CTR at position 3 on Bing) and the calendar's
September section lists the event -- but BOTH data stores (api/data.js slate and
api/v1/dataset.mjs) had no row for it. An API consumer asking about our top event got
nothing, and no decided-sweep would ever watch it.

Verified 2026-09-01: Novo Nordisk submitted the denecimig BLA in September 2025
(PR: prnewswire 302568838) and the application is still under FDA review -- July 2026
FRONTIER-extension data at ISTH was presented for an INVESTIGATIONAL drug, and no
approval news exists. The 2026-09-30 goal date is the one this site already publishes on
/calendar and /pdufa/NVO-mim8; this script restores dataset parity with those pages, it
does not assert a new date.

Idempotent, same pattern as add_repl_pdufa.py.
"""
import json, os, sys
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATA = os.path.join(SITE, "api", "data.js")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
BLA_PR = ("https://www.prnewswire.com/news-releases/novo-nordisk-submits-biologics-"
          "license-application-bla-to-fda-for-mim8-an-investigational-prophylaxis-"
          "treatment-for-people-living-with-hemophilia-a-with-or-without-inhibitors-"
          "302568838.html")

DATE = "2026-09-30"
DRUG = "Mim8 (denecimig)"
IND = "Hemophilia A prophylaxis, with or without inhibitors"

# ---- data.js slate ----------------------------------------------------------------------
src = open(DATA, encoding="utf-8").read()
i = src.find("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(src[i + len("const SLATE="):])
if any(c.get("ticker") == "NVO" and str(c.get("date"))[:10] == DATE
       for c in slate.get("catalysts", [])):
    print("data.js: NVO Mim8 PDUFA already present")
else:
    today = dt.date.today()
    slate["catalysts"].append({
        "ticker": "NVO", "name": "Novo Nordisk A/S", "date": DATE,
        "t_minus": (dt.date.fromisoformat(DATE) - today).days,
        "drug": DRUG, "indication": IND,
        "price": None, "mcap": None, "cap": "", "adv": None, "cash_months": None,
    })
    slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
    open(DATA, "w", encoding="utf-8").write(
        src[:i + len("const SLATE=")] + json.dumps(slate, separators=(",", ":"))
        + src[i + len("const SLATE=") + end:])
    print("data.js: added NVO Mim8 PDUFA 2026-09-30")

# ---- dataset.mjs (the machine-readable API) --------------------------------------------
ds = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
j = ds.find("[")
arr, dend = json.JSONDecoder().raw_decode(ds[j:])
if any(r.get("t") == "NVO" and r.get("type") == "PDUFA" and str(r.get("d"))[:10] == DATE
       for r in arr):
    print("dataset.mjs: NVO Mim8 PDUFA already present")
else:
    arr.append({
        "id": f"pdufa_nvo_mim8_{DATE}", "t": "NVO", "company": "Novo Nordisk A/S",
        "d": DATE, "dp": "day", "name": DRUG, "type": "PDUFA", "ta": "Hematology",
        "cap": "Large", "st": "Upcoming", "url": "/pdufa/NVO-mim8", "ua": NOW,
        "_d": {"indication": IND, "bla_submitted": "2025-09",
               "bla_source": BLA_PR,
               "date_provenance": "goal date as published on /calendar and "
                                  "/pdufa/NVO-mim8 since 2026-08-07; dataset row "
                                  "restored 2026-09-01 after it was found missing"},
    })
    arr.sort(key=lambda r: (str(r.get("d") or "9999"), str(r.get("t") or "")))
    open(DATASET, "w", encoding="utf-8").write(
        ds[:j] + json.dumps(arr, separators=(",", ":"), ensure_ascii=False) + ds[j + dend:])
    print("dataset.mjs: added NVO Mim8 PDUFA 2026-09-30")
