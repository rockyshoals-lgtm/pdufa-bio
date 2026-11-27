# -*- coding: utf-8 -*-
"""apply_1127_kpti_pdufa.py -- Karyopharm selinexor + ruxolitinib sNDA goal date (currency sweep 2026-11-27).

Karyopharm release, Nov 17, 2026 (PR Newswire): the FDA accepted its supplemental New Drug Application for XPOVIO
(selinexor) in combination with ruxolitinib for patients with myelofibrosis, "Prescription Drug User Fee Act Target
Action Date of June 28, 2027", sNDA based primarily on the Phase 3 SENTRY trial. Company release is the primary
source (no 8-K was filed for it). Market cap $419,608 = FMP quote for KPTIQ (OTC), 2026-11-27.
Also adds the date to the homepage slate (api/data.js). Facts only; not investment advice. Idempotent.
"""
import datetime as dt
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
RID, TK, D, SLUG = "pdufa_kpti_2027-06-28", "KPTI", "2027-06-28", "KPTI-xpovio-myelofibrosis"
URL = ("https://www.prnewswire.com/news-releases/karyopharm-announces-fda-acceptance-of-supplemental-new-drug-"
       "application-for-xpovio-selinexor-plus-ruxolitinib-for-the-treatment-of-patients-with-myelofibrosis-302941279.html")

src = io.open(DATASET, encoding="utf-8").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
assert json.dumps(rows, indent=1, ensure_ascii=True) == src[i:j], "dataset is not in canonical form"
if not any(r["id"] == RID for r in rows):
    company = next((r["company"] for r in rows if r.get("t") == TK and r.get("company")), "Karyopharm Therapeutics Inc.")
    row = {"id": RID, "t": TK, "company": company, "d": D, "dp": "day",
           "name": "XPOVIO (selinexor) + ruxolitinib - myelofibrosis (sNDA)", "type": "PDUFA", "ta": "Hematology",
           "cap": "Nano", "st": "Upcoming", "ua": NOW, "url": f"/pdufa/{SLUG}",
           "_d": {"indication": "Myelofibrosis, in combination with ruxolitinib", "event_slug": SLUG,
                  "application": "sNDA", "pivotal_trial": "SENTRY (Phase 3)",
                  "source": "Karyopharm press release 2026-11-17 (PR Newswire)", "source_url": URL,
                  "source_quote": "Prescription Drug User Fee Act Target Action Date of June 28, 2027",
                  "source_note": "Release: the FDA accepted Karyopharm's sNDA for XPOVIO (selinexor) in combination "
                                 "with ruxolitinib for patients with myelofibrosis, based primarily on the Phase 3 "
                                 "SENTRY trial. Found 2026-11-27 by the readout currency sweep; the date is the "
                                 "sponsor's own statement. The release gives the company's listing as OTC Pink: KPTIQ.",
                  "market_cap_usd": 419608.0}}
    # insert after the last row dated on or before D, so the file stays date-ordered where it already is
    k = max((n for n, r in enumerate(rows) if str(r.get("d") or "") <= D and r.get("type") == "PDUFA"), default=len(rows) - 1)
    rows.insert(k + 1, row)
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=True) + src[j:])
    print(f"  + {RID}")
else:
    print(f"  = {RID} already on file")

DATAJS = os.path.join(HERE, "pdufa_site_src", "api", "data.js")
s_ = io.open(DATAJS, encoding="utf-8").read()
k = s_.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(s_[k:])
if not any(c.get("ticker") == TK and c.get("date") == D for c in slate["catalysts"]):
    slate["catalysts"].append({"ticker": TK, "name": "Karyopharm Therapeutics", "date": D,
                               "t_minus": (dt.date.fromisoformat(D) - dt.date.today()).days,
                               "drug": "XPOVIO (selinexor) + ruxolitinib - myelofibrosis (sNDA)",
                               "indication": "Myelofibrosis, in combination with ruxolitinib", "price": 0.0185,
                               "mcap": 419608.0, "cap": "Nano", "adv": None, "cash_months": None})
    slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
    io.open(DATAJS, "w", encoding="utf-8").write(s_[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":")) + s_[k + end:])
    print("  + slate KPTI 2027-06-28")
