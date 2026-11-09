# -*- coding: utf-8 -*-
"""apply_1108_new_pdufas.py -- goal dates from the EDGAR sweep of Nov 5-8, 2026 (each from the sponsor's own exhibit).

COGT: Cogent 8-K EX-99.1, Nov 5, 2026 -- "AdvSM PDUFA target action date June 29, 2027" (bezuclastinib, advanced
      systemic mastocytosis; the GIST Nov 30 and NonAdvSM Dec 30 dates are already on the site).
VSTM: Verastem 8-K EX-99.1, Nov 5, 2026 -- "FDA decision on NDA for AVMAPKI FAKZYNJA CO-PACK Blister Pack by
      February 7, 2027" (priority review; a new blister-pack presentation of the approved co-pack).
Facts only; not investment advice.
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
NEW = [
    ("pdufa_cogt_2027-06-29", "COGT", "2027-06-29", "Bezuclastinib - advanced systemic mastocytosis (AdvSM)", "Oncology",
     "Advanced systemic mastocytosis", "Cogent 8-K 2026-11-05 (EX-99.1, Q3 2026 results)",
     "https://www.sec.gov/Archives/edgar/data/1622229/000119312526449926/cogt-ex99_1.htm",
     "AdvSM PDUFA target action date June 29, 2027", "COGT-bezuclastinib-advsm"),
    ("pdufa_vstm_2027-02-07", "VSTM", "2027-02-07", "AVMAPKI FAKZYNJA CO-PACK blister pack (NDA)", "Oncology",
     "New blister-pack presentation of the approved AVMAPKI FAKZYNJA co-pack (priority review)",
     "Verastem 8-K 2026-11-05 (EX-99.1, Q3 2026 results presentation)",
     "https://www.sec.gov/Archives/edgar/data/1526119/000110465926123386/tm2628982d2_ex99-1.htm",
     "FDA decision on NDA for AVMAPKI FAKZYNJA CO-PACK Blister Pack by February 7, 2027", "VSTM-avmapki-fakzynja-blister-pack"),
]
src = io.open(DATASET, encoding="utf-8").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
s_ = io.open(DATAJS, encoding="utf-8").read()
k = s_.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(s_[k:])
for rid, tk, d, name, ta, ind, sname, url, quote, slug in NEW:
    if any(r["id"] == rid for r in rows):
        continue
    m = mcap_on(tk)
    known = next((r for r in rows if r.get("t") == tk and r.get("company")), {})
    rows.append({"id": rid, "t": tk, "company": known.get("company") or tk, "d": d, "dp": "day", "name": name,
                 "type": "PDUFA", "ta": ta, "cap": tier_short(m) or known.get("cap", ""), "st": "Upcoming", "ua": NOW,
                 "url": f"/pdufa/{slug}", "_d": {"indication": ind, "event_slug": slug, "source": sname,
                                                 "source_url": url, "source_quote": quote}})
    ref = next((c for c in slate["catalysts"] if c.get("ticker") == tk), {})
    slate["catalysts"].append({"ticker": tk, "name": ref.get("name") or known.get("company") or tk, "date": d,
                               "t_minus": (dt.date.fromisoformat(d) - dt.date.today()).days, "drug": name, "indication": ind,
                               "price": ref.get("price"), "mcap": m or ref.get("mcap"), "cap": tier_short(m),
                               "adv": ref.get("adv"), "cash_months": ref.get("cash_months")})
    print(f"  + {rid} ({tier_short(m)})")
rows.sort(key=lambda x: (str(x.get("d") or "9999"), str(x.get("t") or "")))
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
io.open(DATAJS, "w", encoding="utf-8").write(s_[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":")) + s_[k + end:])
