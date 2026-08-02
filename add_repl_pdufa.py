# -*- coding: utf-8 -*-
"""add_repl_pdufa.py -- add the Replimune (REPL) RP1 PDUFA, FDA goal date 2026-08-02.

Why this was missing: the AdComm ingest captured the Jul 30 CTGTAC meeting but never created the
associated PDUFA row, so the single most time-sensitive catalyst on the site was absent on the eve of
the decision. Facts below are from Replimune's own 8-K exhibit / press release following the AdComm.

Idempotent: does nothing if a REPL PDUFA on that date already exists.
"""
import json, os, re, sys
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
SRC = ("https://www.sec.gov/Archives/edgar/data/0001737953/000110465926088857/"
       "tm2621708d1_ex99-1.htm")

DATE = "2026-08-02"
DRUG = "RP1 (vusolimogene oderparepvec) + nivolumab"
IND = "Advanced melanoma previously treated with an anti-PD-1 regimen"

# ---- data.js slate ----------------------------------------------------------------------
src = open(DATA, encoding="utf-8").read()
i = src.find("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(src[i + len("const SLATE="):])
already = any(c.get("ticker") == "REPL" and str(c.get("date"))[:10] == DATE
              for c in slate.get("catalysts", []))
if already:
    print("data.js: REPL PDUFA already present")
else:
    today = dt.date.today()
    slate["catalysts"].append({
        "ticker": "REPL", "name": "Replimune Group, Inc.", "date": DATE,
        "t_minus": (dt.date.fromisoformat(DATE) - today).days,
        "drug": DRUG, "indication": IND,
        "price": None, "mcap": None, "cap": "", "adv": None, "cash_months": None,
    })
    slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
    head = src[:i + len("const SLATE=")]
    tail = src[i + len("const SLATE=") + end:]
    open(DATA, "w", encoding="utf-8").write(head + json.dumps(slate, separators=(",", ":")) + tail)
    print("data.js: added REPL PDUFA 2026-08-02")

# ---- dataset.mjs (the machine-readable API) --------------------------------------------
ds = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
j = ds.find("[")
arr, dend = json.JSONDecoder().raw_decode(ds[j:])
if any(r.get("t") == "REPL" and r.get("type") == "PDUFA" and str(r.get("d"))[:10] == DATE for r in arr):
    print("dataset.mjs: REPL PDUFA already present")
else:
    arr.append({
        "id": f"pdufa_repl_{DATE}", "t": "REPL", "company": "Replimune Group, Inc.",
        "d": DATE, "dp": "day", "name": DRUG, "type": "PDUFA", "ta": "Oncology",
        "cap": "", "st": "Upcoming", "url": SRC, "ua": NOW,
        "_d": {"nct_id": "NCT03767348", "indication": IND, "market_cap_usd": None,
               "bla": "BLA 125827", "review": "Class 1 resubmission (third submission)",
               "adcomm": "CTGTAC 2026-07-30, voted 10-3 favorable"},
    })
    arr.sort(key=lambda r: (str(r.get("d") or "9999"), str(r.get("t") or "")))
    open(DATASET, "w", encoding="utf-8").write(
        ds[:j] + json.dumps(arr, separators=(",", ":"), ensure_ascii=False) + ds[j + dend:])
    print("dataset.mjs: added REPL PDUFA 2026-08-02")

print("\nFDA goal date 2026-08-02 falls on a Sunday; agency action is customarily communicated on an "
      "adjacent business day. The published date is the company-disclosed goal date.")
