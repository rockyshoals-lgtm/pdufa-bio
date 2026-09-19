# -*- coding: utf-8 -*-
"""TLX TLX101-Px -> Pixclara (floretyrosine F 18), NDA approved; announced 2026-09-14.

Read first-hand: Telix 6-K filed 2026-09-14, EX-99.1 (ASX announcement dated September 14, 2026,
accession 0001628280-26-061892): "Telix Pharmaceuticals Limited (ASX: TLX, NASDAQ: TLX) today
announces that the United States (U.S.) Food and Drug Administration (FDA) has approved its New
Drug Application (NDA) for Pixclara (floretyrosine F 18 or 18F-FET)" -- the first FDA-approved
FET-PET imaging drug for glioma.

DATE DISCIPLINE. The announcement is dated September 14 and says the FDA "has approved"; it does
not state the day the FDA acted, and Drugs@FDA holds no Pixclara record yet. The decision date
recorded is the sponsor's announcement date, 2026-09-14, and the row says so. Against the sourced
goal date of September 11 that is 3 days after; if the FDA's letter turns out to be dated earlier
the margin will be corrected from the letter, not guessed.

WHY THE SITE SAID "AWAITING" FOR FIVE DAYS: a diagnostic imaging agent gets no FDA press release
and no prompt Drugs@FDA entry, and Telix is a foreign filer whose newsroom returns 403 to a
non-browser client. The sponsor's 6-K was in EDGAR from day one and nothing looked there.
"""
import datetime as dt, io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
K6 = "https://www.sec.gov/Archives/edgar/data/2007191/000162828026061892/pixclaraapprovalvfinal.htm"
src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
n = 0
for r in rows:
    if r["id"] != "pdufa_tlx_2026-09-11":
        continue
    assert r["d"] == "2026-09-11" and r["dp"] == "day" and r["st"] in ("Upcoming", "Awaiting"), r
    r["st"], r["oc"], r["dcd"] = "Decided", "Approved", "2026-09-14"
    r["name"] = "Pixclara (floretyrosine F 18; TLX101-Px)"
    r["ua"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    dd = r.setdefault("_d", {})
    dd["brand"] = "Pixclara"
    dd["decision_source"] = "Telix 6-K 2026-09-14 (EX-99.1, ASX announcement)"
    dd["decision_source_url"] = K6
    dd["decision_quote"] = ("Telix Pharmaceuticals Limited (ASX: TLX, NASDAQ: TLX) today announces that the "
                            "United States (U.S.) Food and Drug Administration (FDA) has approved its New Drug "
                            "Application (NDA) for Pixclara (floretyrosine F 18 or 18F-FET)")
    dd["decision_date_note"] = ("2026-09-14 is the date of Telix's announcement, which says the FDA 'has "
                                "approved' without stating the action day; Drugs@FDA holds no Pixclara record "
                                "yet. The margin against the September 11 goal date will be corrected from the "
                                "FDA letter if it is dated earlier.")
    dd["review"] = ("NDA approved (announced September 14, 2026; goal date September 11) after a March 16, 2026 "
                    "resubmission following an earlier Complete Response Letter. Pixclara is the first "
                    "FDA-approved FET-PET imaging agent for glioma, indicated to help differentiate recurrent "
                    "or progressive glioma from treatment-related change in adults and pediatric patients.")
    n += 1
    print(f"  {r['id']}: {r.get('st')} -> Decided/Approved, announced 2026-09-14 (goal 09-11)")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print(f"{n} row(s)")
