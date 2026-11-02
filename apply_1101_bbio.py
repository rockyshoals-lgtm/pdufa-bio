# -*- coding: utf-8 -*-
"""apply_1101_bbio.py -- a goal date the calendar did not carry (red team 2026-11-01).

BridgeBio 8-K EX-99.1, October 6, 2026: the FDA accepted the NDA for oral infigratinib in children with
achondroplasia with Priority Review and "has assigned a Prescription Drug User Fee Act (PDUFA) target action
date of February 4, 2027". The dataset had no infigratinib row; BBIO showed only BBP-418 and encaleret.
New day-precision row + slate entry; the chain's ensure_calendar_rows and build_pdufa_event_pages place the
calendar row and write /pdufa/BBIO-infigratinib. Facts only; not investment advice.
"""
import datetime as dt
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
URL = "https://www.sec.gov/Archives/edgar/data/1743881/000114036126039334/ef20083591_ex99-1.htm"
RID = "pdufa_bbio_2027-02-04"
NAME = "Oral infigratinib - achondroplasia in children (PROPEL 3)"
IND = "Children with achondroplasia"

src = io.open(DATASET, encoding="utf-8").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
if not any(r["id"] == RID for r in rows):
    ref = next(r for r in rows if r.get("t") == "BBIO")
    rows.append({"id": RID, "t": "BBIO", "company": ref.get("company") or "BridgeBio Pharma, Inc.", "d": "2027-02-04",
                 "dp": "day", "name": NAME, "type": "PDUFA", "ta": "Rare Disease", "cap": ref.get("cap") or "Mid",
                 "st": "Upcoming", "ua": NOW, "url": "/pdufa/BBIO-infigratinib",
                 "_d": {"indication": IND, "inn": "infigratinib", "trial": "PROPEL 3", "event_slug": "BBIO-infigratinib",
                        "source": "BridgeBio 8-K 2026-10-06 (EX-99.1, NDA accepted, priority review)",
                        "source_url": URL,
                        "source_quote": "The FDA has assigned a Prescription Drug User Fee Act (PDUFA) target action date of February 4, 2027"}})
    rows.sort(key=lambda x: (str(x.get("d") or "9999"), str(x.get("t") or "")))
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    print(f"  + {RID}")

DATAJS = os.path.join(SITE, "api", "data.js")
s_ = io.open(DATAJS, encoding="utf-8").read()
k = s_.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(s_[k:])
if not any(c.get("ticker") == "BBIO" and "nfigratinib" in str(c.get("drug")) for c in slate["catalysts"]):
    ref = next((c for c in slate["catalysts"] if c.get("ticker") == "BBIO"), {})
    slate["catalysts"].append({"ticker": "BBIO", "name": ref.get("name") or "BridgeBio Pharma", "date": "2027-02-04",
                               "t_minus": (dt.date(2027, 2, 4) - dt.date.today()).days, "drug": NAME, "indication": IND,
                               "price": ref.get("price"), "mcap": ref.get("mcap"), "cap": ref.get("cap"),
                               "adv": ref.get("adv"), "cash_months": ref.get("cash_months")})
    slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
    io.open(DATAJS, "w", encoding="utf-8").write(s_[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":")) + s_[k + end:])
    print("  + slate BBIO infigratinib 2027-02-04")
