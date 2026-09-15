# -*- coding: utf-8 -*-
"""Found 2026-09-15 while aligning API urls to the calendar: /pdufa/PRAX told readers relutrigine's
PDUFA date was September 27, 2026 -- twelve days out -- while the dataset held December 27. The
dataset was right: Praxis 8-K 2026-06-29 (acc 0001689548-26-000069) reports the FDA extended the
review "from September 27, 2026 to December 27, 2026" after a major amendment. The page had been
stale for 78 days because refresh_moved_pdufa_pages.py skips a ticker with two live events.

Praxis 8-K 2026-08-06 EX-99.1 (acc 0001689548-26-000082) restates both dates: relutrigine
December 27, 2026 and ulixacaltamide January 29, 2027 (mid-cycle meetings complete, no AdComm).

Both rows get source + source_url; relutrigine gets a sourced date_history so the move reaches
/pdufa-date-changes and the page refresher can identify the page by the date it moved from.
CAPR's history entry gets its announcement url for the same reason.
"""
import io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
EXT = "https://www.sec.gov/Archives/edgar/data/1689548/000168954826000069/prax-20260629.htm"
Q2 = "https://www.sec.gov/Archives/edgar/data/1689548/000168954826000082/praxisq22026pr.htm"
CAPR = ("https://www.globenewswire.com/news-release/2026/08/24/capricor-therapeutics-announces-extension-"
        "of-pdufa-target-action-date-as-fda-continues-review-of-deramiocel-bla.html")

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
n = 0
for r in rows:
    dd = r.setdefault("_d", {})
    if r["id"] == "pdufa_prax_2026-12-27":
        assert r["d"] == "2026-12-27" and r["dp"] == "day"
        dd["source"] = "Praxis 8-K 2026-06-29 (extension); 8-K 2026-08-06 EX-99.1 (restated)"
        dd["source_url"] = EXT
        dd["prior_pdufa_date"] = "2026-09-27"
        dd["date_provenance"] = EXT
        dd["date_history"] = [
            {"date": "2026-09-27", "note": "original PDUFA target action date"},
            {"date": "2026-12-27", "changed": "2026-06-29", "url": EXT,
             "why": "The FDA extended the review period by three months after Praxis submitted "
                    "additional sensitivity analyses the agency deemed a major amendment; Praxis "
                    "8-K of June 29, 2026 states the new PDUFA target action date of December 27, 2026."}]
        dd["review"] = ("NDA for SCN2A and SCN8A developmental and epileptic encephalopathies. Review "
                        "extended by three months (major amendment) to December 27, 2026; mid-cycle "
                        "meeting complete with no major safety or efficacy concerns identified to date "
                        "and no advisory committee planned (Praxis, August 6, 2026).")
        n += 1
    elif r["id"] == "pdufa_prax_2027-01-29":
        assert r["d"] == "2027-01-29" and r["dp"] == "day"
        dd["source"] = "Praxis 8-K 2026-08-06 (EX-99.1)"
        dd["source_url"] = Q2
        dd["indication"] = "Essential tremor"
        dd["review"] = ("NDA for essential tremor; Breakthrough Therapy designation December 2025. "
                        "PDUFA date January 29, 2027; mid-cycle meeting complete with no major safety "
                        "or efficacy concerns identified to date and no advisory committee planned "
                        "(Praxis, August 6, 2026).")
        n += 1
    elif r["id"] == "pdufa_capr_2026-08-22":
        for h in dd.get("date_history", []):
            if h.get("date") == "2026-11-22":
                h["url"] = CAPR
        dd.setdefault("prior_pdufa_date", "2026-08-22")
        dd.setdefault("date_provenance", CAPR)
        n += 1
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print(f"{n} row(s) updated")
