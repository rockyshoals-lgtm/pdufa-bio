# -*- coding: utf-8 -*-
"""apply_1125c_uncy_olc_resubmission.py -- Unicycive's third OLC review: PDUFA March 25, 2027 (2026-11-25).

pdufa.bio's UNCY hub and the oxylanthanum carbonate drug page said "no upcoming catalyst on file". That was stale:
after the June 29, 2026 CRL (the second on NDA 218607), Unicycive resubmitted with CMC data from a new third-party
drug product manufacturing vendor (8-K 2026-09-29, EX-99.1), the FDA accepted it as a Class 2 resubmission
(company release 2026-10-21, whose headline gives the PDUFA date of March 25, 2027) and Unicycive restated the
date in its Q3 2026 8-K (2026-11-16, EX-99.1). This adds that row to the dataset and the slate, the same way
apply_1103_new_pdufas.py adds rows. build_pdufa_event_pages.py builds /pdufa/UNCY-olc on the next rebuild.
Market-cap tier is carried from the existing UNCY row (no Polygon key in the cloud session); the rebuild refreshes
market data. Facts only, idempotent.
"""
import datetime as dt
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
DATAJS = os.path.join(SITE, "api", "data.js")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

E = "https://www.sec.gov/Archives/edgar/data/1766140/"
RID = "pdufa_uncy_2027-03-25"
TK = "UNCY"
D = "2027-03-25"
SLUG = "UNCY-olc"
NAME = "Oxylanthanum Carbonate (OLC)"
IND = "Hyperphosphatemia in patients with chronic kidney disease on dialysis (Class 2 resubmission after the June 29, 2026 CRL)"
SRC = "Unicycive press release 2026-10-21 (NDA resubmission accepted)"
SRC_URL = "https://ir.unicycive.com/news/detail/128/unicycive-therapeutics-announces-fda-acceptance-of"
QUOTE = ("Unicycive Therapeutics Announces FDA Acceptance of Oxylanthanum Carbonate New Drug Application "
         "Resubmission and PDUFA Date of March 25, 2027")
NOTE = ("Resubmitted with CMC data from a new third-party drug product manufacturing vendor (Unicycive 8-K 2026-09-29, "
        "EX-99.1: " + E + "000121390026104314/ea030696701ex99-1.htm). The FDA classed it a Class 2 resubmission with "
        "a six-month review (Unicycive release 2026-10-21), and Unicycive restated the date in its Q3 2026 8-K "
        "(2026-11-16, EX-99.1: " + E + "000121390026120261/ea031236501ex99-1.htm). Both earlier CRLs on NDA 218607 (June 27, 2025 and "
        "June 29, 2026) cited inspection deficiencies at a manufacturing facility listed in the application, which "
        "Unicycive says is a third-party vendor; neither letter names a clinical efficacy or safety deficiency.")

src = io.open(DATASET, encoding="utf-8").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
if any(r.get("id") == RID for r in rows):
    print("already present:", RID)
    raise SystemExit(0)
known = next(r for r in rows if r.get("t") == TK and r.get("company"))
row = {"id": RID, "t": TK, "company": known["company"], "d": D, "dp": "day", "name": NAME, "type": "PDUFA",
             "ta": "Nephrology", "cap": known.get("cap") or "", "st": "Upcoming", "ua": NOW, "url": f"/pdufa/{SLUG}",
             "_d": {"indication": IND, "event_slug": SLUG, "source": SRC, "source_url": SRC_URL, "source_quote": QUOTE,
                    "source_note": NOTE}}
# Insert at the first row that sorts after it, leaving every other row where it is (a full re-sort moves
# hundreds of rows and buries the one-row change in the diff).
at = next((n for n, r in enumerate(rows) if (str(r.get("d") or "9999"), str(r.get("t") or "")) > (D, TK)), len(rows))
rows.insert(at, row)
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=True) + src[j:])

s_ = io.open(DATAJS, encoding="utf-8").read()
k = s_.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(s_[k:])
if not any(c.get("ticker") == TK and c.get("date") == D for c in slate["catalysts"]):
    ref = next((c for c in slate["catalysts"] if c.get("ticker") == TK), {})
    slate["catalysts"].append({"ticker": TK, "name": ref.get("name") or known["company"], "date": D,
                               "t_minus": (dt.date.fromisoformat(D) - dt.date.today()).days, "drug": NAME,
                               "indication": IND, "price": ref.get("price"), "mcap": ref.get("mcap"),
                               "cap": known.get("cap") or "", "adv": ref.get("adv"),
                               "cash_months": ref.get("cash_months")})
    slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
    io.open(DATAJS, "w", encoding="utf-8").write(s_[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":"))
                                                 + s_[k + end:])
print("added", RID, D, known.get("cap"))
