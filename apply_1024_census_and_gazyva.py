# -*- coding: utf-8 -*-
"""apply_1024_census_and_gazyva.py -- timing-census backfill (David, 2026-10-24: "update the early/on time/late count
with the ones we haven't added yet"; scope chosen: tracked rows first) and two Gazyva goal dates found on the way.

1. Census backfill. 14 decided 2026 applications on our calendar carry an FDA action day but no sourced day-precision
   goal date. Searched each sponsor's own releases and SEC filings on 2026-10-24 (results in the builder note).
   One states the day:
     OTSKY centanafadine (SIMTRIYO): Otsuka America release of January 27, 2026, "The Prescription Drug User Fee Act
       (PDUFA) target action date is July 24, 2026." FDA letter NDA 218145 ORIG-1 dated July 24, 2026 (already on the
       row). -> enters the census, on the goal date.
   The other 13 stay out, each with the reason now written on the row (`census_note`): the sponsor stated only a month
   or quarter (rusfertide "August 2026", brepocitinib and oveporexton "third quarter", Jemperli "February 2027"), or
   no goal date at all (AZN Truqap, MRK enlicitide, LLY Inluriyo+Verzenio, LLY Jaypirca 1L CLL, NVS Rhapsido SD,
   RHHBY Gazyva INS, BAYRY Hyrnuo 1L, BAYRY Kerendia T1D-CKD, ABBV Juvmo). LNTH's 2026-06-29 CRL has no FDA record of
   the action day (CRLs are not posted) and stays out on that ground.
2. Gazyva (RHHBY), found while checking Roche:
     primary membranous nephropathy: Genentech release of July 14, 2026, priority review, "is expected to make a
       decision on approval by November 2026" -> NEW row, month precision. It was on no surface of the site.
     systemic lupus erythematosus: Genentech release of April 20, 2026, sBLA accepted, "The FDA is expected to make a
       decision on an approval by December 2026" -> the calendar showed this as "Q4 2026 (est.)" with "no external
       source at all" (_calendar_unbacked_q4_rows.json). It now has a dataset row, month precision, and leaves that
       list (the ratchet baseline goes 9 -> 8).
Facts only; not investment advice.
"""
import datetime as dt
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
OTSUKA = "https://www.otsuka-us.com/news/otsuka-announces-fda-acceptance-and-priority-review-new-drug-application-centanafadine"
PMN = "https://www.gene.com/media/press-releases/15121/2026-07-14/fda-grants-priority-review-to-genentechs"
SLE = "https://www.gene.com/media/press-releases/15107/2026-04-20/fda-accepts-application-for-genentechs-g"

src = io.open(DATASET, encoding="utf-8", errors="replace").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
by = {r["id"]: r for r in rows}

# ---- 1. OTSKY
r = by["pdufa_otsky_2026-07-24"]
d = r.setdefault("_d", {})
if d.get("goal_unsourced"):
    d.pop("goal_unsourced", None)
    d["source"] = "Otsuka America press release 2026-01-27 (NDA accepted, priority review)"
    d["source_url"] = OTSUKA
    d["source_quote"] = "The Prescription Drug User Fee Act (PDUFA) target action date is July 24, 2026."
    d["goal_note"] = ("Goal date July 24, 2026 from Otsuka America's release of January 27, 2026 (found 2026-10-24); "
                      "the FDA's letter for NDA 218145 is dated the same day.")
    r["ua"] = NOW
    print("  ~ pdufa_otsky_2026-07-24: goal date sourced (Otsuka 2026-01-27), enters the timing census")

WHY = {
    "pdufa_azn_2026-06-30": "AstraZeneca stated no goal date for this sNDA (searched 2026-10-24).",
    "pdufa_mrk_2026-07-16": "Merck's releases and filings give no goal date for enlicitide (the Sept 21 PDUFA in its Q4 2025 release is WINREVAIR's).",
    "pdufa_lly_2026-09-18": "Lilly stated no goal date for the Inluriyo + Verzenio sNDA.",
    "pdufa_lly_2026-10-02": "Lilly stated no goal date for the first-line CLL/SLL sNDA.",
    "pdufa_nvs_2026-10-06": "Novartis stated no goal date for the symptomatic dermographism sNDA.",
    "pdufa_rhhby_2026-09-25": "Genentech/Roche stated only that priority review was granted (May 2026), no goal date.",
    "pdufa_bayry_2026-11-30": "Bayer's priority-review release (May 18, 2026) states no goal date.",
    "pdufa_bayry_2026-12-31": "Bayer's priority-review release (May 21, 2026) states no goal date.",
    "pdufa_abbv_2026-12-31": "AbbVie stated no goal date for tavapadon.",
    "pdufa_ptgx_2026-09-30": "Protagonist/Takeda stated the goal only as August 2026 (month), not a day.",
    "pdufa_tak_2026-09-30": "Takeda stated the goal only as the third calendar quarter of 2026.",
    "pdufa_pfe_2026-09-30": "Priovant stated the goal only as the third calendar quarter of 2026.",
    "pdufa_roiv_2026-09-30": "Priovant stated the goal only as the third calendar quarter of 2026.",
    "pdufa_gsk_2027-02-28": "GSK stated the goal only as February 2027 (month).",
    "pdufa_lnth_2026-06-29": "A CRL: the FDA's letter is not public, so no FDA record states the action day.",
}
for rid, why in WHY.items():
    if rid in by:
        by[rid].setdefault("_d", {})["census_note"] = f"Not in the decision-timing census (checked 2026-10-24): {why}"

# ---- 2. Gazyva pMN (new) and SLE (sourced)
def add(rid, d_, name, ind, srcname, url, quote, slug):
    if rid in by:
        return
    rows.append({"id": rid, "t": "RHHBY", "company": "Roche Holding AG", "d": d_, "dp": "month", "dm": d_[:7],
                 "name": name, "type": "PDUFA", "ta": "Nephrology" if "nephro" in ind.lower() else "Immunology",
                 "cap": "Large", "st": "Upcoming", "ua": NOW, "url": f"/pdufa/{slug}",
                 "_d": {"indication": ind, "brand": "Gazyva", "inn": "obinutuzumab", "source": srcname,
                        "source_url": url, "source_quote": quote, "event_slug": slug,
                        "source_note": "Month precision: Genentech states the month of the expected FDA decision, not a day."}})
    print(f"  + {rid}: {name}, {d_[:7]} (month)")


add("pdufa_rhhby_2026-11-30_pmn", "2026-11-30", "Gazyva (obinutuzumab) - primary membranous nephropathy (MAJESTY)",
    "Primary membranous nephropathy (pMN) in adults", "Genentech press release 2026-07-14 (priority review)", PMN,
    "The FDA has already granted Breakthrough Therapy Designation (BTD) to Gazyva in pMN and is expected to make a decision on approval by November 2026.",
    "RHHBY-gazyva-pmn")
add("pdufa_rhhby_2026-12-31_sle", "2026-12-31", "Gazyva (obinutuzumab) - systemic lupus erythematosus (ALLEGORY)",
    "Systemic lupus erythematosus (SLE)", "Genentech press release 2026-04-20 (sBLA accepted)", SLE,
    "The FDA is expected to make a decision on an approval by December 2026.", "RHHBY-gazyva")
rows.sort(key=lambda x: (str(x.get("d") or "9999"), str(x.get("t") or "")))
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])

# slate (the calendar's second source)
DATAJS = os.path.join(SITE, "api", "data.js")
s_ = io.open(DATAJS, encoding="utf-8").read()
k = s_.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(s_[k:])
ref = next((c for c in slate["catalysts"] if c.get("ticker") == "RHHBY"), {})
for date, drug, ind in (("2026-11-30", "Gazyva (obinutuzumab) - primary membranous nephropathy (MAJESTY)", "Primary membranous nephropathy (pMN) in adults"),
                        ("2026-12-31", "Gazyva (obinutuzumab) - systemic lupus erythematosus (ALLEGORY)", "Systemic lupus erythematosus (SLE)")):
    if not any(c.get("ticker") == "RHHBY" and c.get("drug") == drug for c in slate["catalysts"]):
        slate["catalysts"].append({"ticker": "RHHBY", "name": "Roche/Genentech", "date": date,
                                   "t_minus": (dt.date.fromisoformat(date) - dt.date.today()).days, "drug": drug,
                                   "indication": ind, "price": ref.get("price"), "mcap": ref.get("mcap"), "cap": "Large",
                                   "adv": ref.get("adv"), "cash_months": None})
slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
io.open(DATAJS, "w", encoding="utf-8").write(s_[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":")) + s_[k + end:])

# unbacked-window list: the SLE row is now backed
UB = os.path.join(HERE, "_calendar_unbacked_q4_rows.json")
ub = json.load(io.open(UB, encoding="utf-8"))
before = len(ub["rows"])
ub["rows"] = [x for x in ub["rows"] if x.get("page") != "/pdufa/RHHBY-gazyva"]
if len(ub["rows"]) < before and ub.get("baseline_count", 99) > len(ub["rows"]):
    ub["baseline_count"] = len(ub["rows"])
    ub["baseline_note"] += (" Lowered to " + str(len(ub["rows"])) + " on 2026-10-24: /pdufa/RHHBY-gazyva (SLE) is backed by "
                            "Genentech's 2026-04-20 release (decision expected by December 2026).")
io.open(UB, "w", encoding="utf-8").write(json.dumps(ub, indent=1, ensure_ascii=False) + "\n")
print(f"  unbacked window rows: {before} -> {len(ub['rows'])}; baseline {ub['baseline_count']}")


# ---- 3. calendar rows (month rows are placed by hand; ensure_calendar_rows.py handles day rows only)
import re as _re
PMN_ROW = ('<a class="row" href="/pdufa/RHHBY-gazyva-pmn"><div class="t">RHHBY &middot; Nov 2026</div>'
           '<div class="d">Gazyva (obinutuzumab): primary membranous nephropathy (MAJESTY)</div></a>')
SLE_ROW = ('<a class="row" href="/pdufa/RHHBY-gazyva"><div class="t">RHHBY &middot; Dec 2026</div>'
           '<div class="d">Gazyva: Systemic Lupus Erythematosus</div></a>')
for rel, row, after in (("calendar/index.html", PMN_ROW, r'<a class="row" href="/pdufa/GSK-neladalkib">.*?</a>'),
                        ("calendar/2026/november/index.html", PMN_ROW, r'<a class="row" href="/pdufa/GSK-neladalkib">.*?</a>'),
                        ("calendar/2026/december/index.html", SLE_ROW, r'<a class="row" href="/pdufa/NVO[^"]*">.*?</a>')):
    p = os.path.join(SITE, *rel.split("/"))
    doc = io.open(p, encoding="utf-8").read()
    if _re.search(r'href="' + _re.escape(_re.search(r'href="([^"]+)"', row).group(1)) + r'"', doc):
        print(f"  {rel}: row already present"); continue
    m = _re.search(after, doc, _re.S)
    if not m:
        print(f"  {rel}: anchor row not found, nothing written"); continue
    io.open(p, "w", encoding="utf-8").write(doc[:m.end()] + row + doc[m.end():])
    print(f"  + {rel}: {_re.sub(r'<[^>]+>', ' ', row).split()[0:4]}")
