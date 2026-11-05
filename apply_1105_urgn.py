# -*- coding: utf-8 -*-
"""apply_1105_urgn.py -- UroGen UGN-103 goal date (EDGAR sweep 2026-11-05).

UroGen 8-K EX-99.1, Nov 4, 2026: "The FDA accepted UroGen's NDA for UGN-103 (next-generation novel mitomycin-based
formulation) for review; PDUFA goal date set for June 14, 2027", in low-grade intermediate-risk non-muscle invasive
bladder cancer (LG-IR-NMIBC). Facts only; not investment advice.
"""
import datetime as dt
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fmp_mcap import mcap_on, tier_short  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
DATAJS = os.path.join(SITE, "api", "data.js")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
RID, TK, D = "pdufa_urgn_2027-06-14", "URGN", "2027-06-14"
NAME = "UGN-103 (mitomycin) - low-grade intermediate-risk NMIBC"
IND = "Low-grade intermediate-risk non-muscle invasive bladder cancer (LG-IR-NMIBC)"
URL = "https://www.sec.gov/Archives/edgar/data/1668243/000143774926034769/ex_1036873.htm"

src = io.open(DATASET, encoding="utf-8").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
m = mcap_on(TK)
cap = tier_short(m)
if not any(r["id"] == RID for r in rows):
    known = next((r for r in rows if r.get("t") == TK and r.get("company")), {})
    rows.append({"id": RID, "t": TK, "company": known.get("company") or "UroGen Pharma Ltd.", "d": D, "dp": "day",
                 "name": NAME, "type": "PDUFA", "ta": "Oncology", "cap": cap, "st": "Upcoming", "ua": NOW,
                 "url": "/pdufa/URGN-ugn-103",
                 "_d": {"indication": IND, "event_slug": "URGN-ugn-103",
                        "source": "UroGen 8-K 2026-11-04 (EX-99.1, Q3 2026 results)", "source_url": URL,
                        "source_quote": "The FDA accepted UroGen's NDA for UGN-103 (next-generation novel mitomycin-based formulation) for review; PDUFA goal date set for June 14, 2027"}})
    rows.sort(key=lambda x: (str(x.get("d") or "9999"), str(x.get("t") or "")))
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    print(f"  + {RID} ({cap})")
s_ = io.open(DATAJS, encoding="utf-8").read()
k = s_.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(s_[k:])
if not any(c.get("ticker") == TK and c.get("date") == D for c in slate["catalysts"]):
    ref = next((c for c in slate["catalysts"] if c.get("ticker") == TK), {})
    slate["catalysts"].append({"ticker": TK, "name": ref.get("name") or "UroGen Pharma", "date": D,
                               "t_minus": (dt.date.fromisoformat(D) - dt.date.today()).days, "drug": NAME,
                               "indication": IND, "price": ref.get("price"), "mcap": m or ref.get("mcap"), "cap": cap,
                               "adv": ref.get("adv"), "cash_months": ref.get("cash_months")})
    slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
    io.open(DATAJS, "w", encoding="utf-8").write(s_[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":")) + s_[k + end:])
    print("  + slate URGN 2027-06-14")
