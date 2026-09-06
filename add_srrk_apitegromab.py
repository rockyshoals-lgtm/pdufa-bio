# -*- coding: utf-8 -*-
"""add_srrk_apitegromab.py -- add the Scholar Rock (SRRK) apitegromab BLA, FDA goal date 2026-09-30.

Audit 2026-09-05 (0800 slot) ORDER 2, P0: a dated PDUFA 25 days out, on a drug we already hold a
decision page for (/fda-decision/SRRK-2025-09-23, the first-cycle CRL), was on no surface at all:
no API row, /pdufa/SRRK 404, /drug/apitegromab said "0 upcoming", /fda-this-month omitted it.

Why it was missing: the first BLA resolved with a CRL on 2025-09-23 and its row left the slate; the
March 2026 resubmission's goal date was disclosed only in the sponsor's own releases and 8-K
exhibits, which the event path does not mine for NEW dated events (it watches events it already
holds). Nothing compared "drugs with a CRL on file" against "sponsor releases naming a new action
date".

Facts and wording below are from Scholar Rock's own releases (Business Wire), verified 2026-09-06:
  Aug 7, 2026  https://investors.scholarrock.com/news-releases/news-release-details/scholar-rock-announces-fda-review-apitegromab-biologics-license
               "The BLA remains on track for potential FDA approval by the September 30, 2026
                Prescription Drug User Free Act (PDUFA) action date."  [sic: "Free"]
  Aug 21, 2026 https://www.businesswire.com/news/home/20260821050366/en/
               "Scholar Rock continues to expect an FDA approval decision by the September 30, 2026
                Prescription Drug User Fee Act (PDUFA) date."

Idempotent: does nothing if an SRRK PDUFA on that date already exists.
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
SRC = ("https://investors.scholarrock.com/news-releases/news-release-details/"
       "scholar-rock-announces-fda-review-apitegromab-biologics-license")
SRC2 = ("https://www.businesswire.com/news/home/20260821050366/en/"
        "Scholar-Rock-Provides-Update-on-Global-Apitegromab-Regulatory-Progress-Across-U.S.-Europe-and-Japan")

TICKER = "SRRK"
COMPANY = "Scholar Rock Holding Corporation"
DATE = "2026-09-30"
DRUG = "Apitegromab - (SAPPHIRE)"
IND = "Spinal muscular atrophy (SMA), children and adults (BLA)"
# The company's own caveat, verbatim (house rule 3), from the Aug 7, 2026 release.
CAVEAT = ("Scholar Rock will continue to collaborate closely with the FDA and under their guidance, "
          "will remove Catalent Indiana from the apitegromab BLA. FDA review of the apitegromab BLA "
          "will progress solely with the second fill-finish facility.")
REVIEW = ("BLA submitted March 2026 after the September 23, 2025 Complete Response Letter on the "
          "first application. On August 7, 2026 the company disclosed that the FDA classified the "
          "April 2026 inspection of Catalent Indiana LLC (a fill-finish site named in the BLA) as "
          "Official Action Indicated; on August 21, 2026 it said Catalent Indiana had been removed "
          "from the BLA and that it continues to expect a decision by the September 30, 2026 goal "
          "date. Fast Track, Orphan Drug and Rare Pediatric Disease designations per the sponsor.")

# ---- data.js slate ----------------------------------------------------------------------
src = open(DATA, encoding="utf-8").read()
i = src.find("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(src[i + len("const SLATE="):])
already = any(c.get("ticker") == TICKER and str(c.get("date"))[:10] == DATE
              for c in slate.get("catalysts", []))
if already:
    print(f"data.js: {TICKER} PDUFA already present")
else:
    today = dt.date.today()
    slate["catalysts"].append({
        "ticker": TICKER, "name": COMPANY, "date": DATE,
        "t_minus": (dt.date.fromisoformat(DATE) - today).days,
        "drug": DRUG, "indication": IND,
        "price": None, "mcap": None, "cap": "", "adv": None, "cash_months": None,
    })
    slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
    head = src[:i + len("const SLATE=")]
    tail = src[i + len("const SLATE=") + end:]
    open(DATA, "w", encoding="utf-8").write(head + json.dumps(slate, separators=(",", ":")) + tail)
    print(f"data.js: added {TICKER} PDUFA {DATE}")

# ---- dataset.mjs (the machine-readable API) --------------------------------------------
ds = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
j = ds.find("[")
arr, dend = json.JSONDecoder().raw_decode(ds[j:])
if any(r.get("t") == TICKER and r.get("type") == "PDUFA" and str(r.get("d"))[:10] == DATE for r in arr):
    print(f"dataset.mjs: {TICKER} PDUFA already present")
else:
    arr.append({
        "id": f"pdufa_{TICKER.lower()}_{DATE}", "t": TICKER, "company": COMPANY,
        "d": DATE, "dp": "day", "name": DRUG, "type": "PDUFA", "ta": "CNS/Neurology",
        "cap": "", "st": "Upcoming", "url": SRC, "ua": NOW,
        "_d": {"nct_id": None, "indication": IND, "market_cap_usd": None,
               "bla": "BLA (apitegromab), submitted March 2026",
               "review": REVIEW, "sponsor_caveat": CAVEAT,
               "source": "company press release (Business Wire), Aug 7 and Aug 21, 2026",
               "source_url_2": SRC2,
               "prior_decision": "/fda-decision/SRRK-2025-09-23"},
    })
    arr.sort(key=lambda r: (str(r.get("d") or "9999"), str(r.get("t") or "")))
    open(DATASET, "w", encoding="utf-8").write(
        ds[:j] + json.dumps(arr, indent=1) + ds[j + dend:])   # same shape as the file we read
    print(f"dataset.mjs: added {TICKER} PDUFA {DATE}")

print("\nThe published date is the company-disclosed FDA goal date (September 30, 2026). "
      "Informational only; not investment advice.")
