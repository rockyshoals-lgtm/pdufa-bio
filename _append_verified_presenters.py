# -*- coding: utf-8 -*-
"""Append the two presenter rows I read and verified myself to the VERIFIED file.

David asked for a deeper presenter mine (2026-09-09). The 120-day EDGAR walk returned 517
candidate filings and three rows we did not already hold. House rule 8 says a miner hit is a
lead, so I fetched each filing and read the sentence that names the congress:

  NVCR / ASTRO  "The results from TRIDENT have been accepted for presentation at the American
                 Society for Radiation Oncology (ASTRO) 2026 Annual Meeting."  -> ACCEPTED
  IBIO / EASD   "The full data will be highlighted in a presentation at the 2026 EASD Annual
                 Meeting, taking place September 28 - October 2 in Milan."     -> COMMITTED
  TLSA / ECTRIMS "Topline data is expected in late Q3/early Q4 of 2026, and is planned to be
                 presented at the ... ACTRIMS and ECTRIMS meeting"             -> NOT PUBLISHED

TLSA is excluded on purpose: "planned to be presented" and contingent on topline data that has
not read out. That is an intention, not an accepted abstract, and it must not sit on a page
titled Biotech Presenters next to companies whose abstracts were accepted. It stays in the
mined file, which renders under "Filings that mention this meeting (unreviewed)".

Only the two firm rows are appended, each with the reviewer note the file's schema requires.
Idempotent: a row already present for (ticker, conference, conf_start) is skipped.
"""
import csv
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(HERE, "catalysts_out", "conference_presenters_VERIFIED_2026-08-12.csv")

NEW = [
    dict(ticker="NVCR", cik="1645113", company="NovoCure Ltd", conference="ASTRO",
         conf_start="2026-09-26", drug="", pres_type="presentation",
         filing_url="https://www.sec.gov/Archives/edgar/data/1645113/000164511326000053/nvcr-20260618.htm",
         accession="0001645113-26-000053", filed="2026-06-18",
         matched_sentence="The results from TRIDENT have been accepted for presentation at the "
                          "American Society for Radiation Oncology (ASTRO) 2026 Annual Meeting.",
         retrieved_at="2026-09-09T23:40:00Z", reviewer="cowork-builder 2026-09-09",
         review_note='"accepted for presentation at ASTRO 2026 Annual Meeting" (TRIDENT)'),
    dict(ticker="IBIO", cik="1420720", company="iBio, Inc.", conference="EASD",
         conf_start="2026-09-28", drug="IBIO-610", pres_type="presentation",
         filing_url="https://www.sec.gov/Archives/edgar/data/1420720/000142072026000010/ibio-20260701xex99d1.htm",
         accession="0001420720-26-000010", filed="2026-07-01",
         matched_sentence="The full data will be highlighted in a presentation at the 2026 EASD "
                          "Annual Meeting, taking place September 28 - October 2 in Milan.",
         retrieved_at="2026-09-09T23:40:00Z", reviewer="cowork-builder 2026-09-09",
         review_note='"full data will be highlighted in a presentation at the 2026 EASD Annual '
                     'Meeting"; filing states the meeting dates'),
]


def main():
    rows = list(csv.DictReader(io.open(V, encoding="utf-8-sig", errors="replace")))
    fields = list(rows[0].keys())
    have = {(r["ticker"], r["conference"], r["conf_start"]) for r in rows}
    added = 0
    for n in NEW:
        k = (n["ticker"], n["conference"], n["conf_start"])
        if k in have:
            print(f"  already present: {k}")
            continue
        rows.append({f: n.get(f, "") for f in fields})
        added += 1
        print(f"  + {n['ticker']} at {n['conference']} {n['conf_start']} ({n['filed']} filing)")
    if added:
        with io.open(V, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    print(f"verified presenters: {added} added, {len(rows)} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
