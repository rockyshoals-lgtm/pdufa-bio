# -*- coding: utf-8 -*-
"""apply_1101_page_text.py -- text corrections found by the 2026-11-01 red team.

MNKD-2026-07-24: the title and description say approved July 23 (FDA letter), 3 days before the July 26 goal
  (MannKind 8-K 2026-05-06); the body still said "two days ahead of its PDUFA goal date (Jul 24 2026)" and "The FDA
  approved on July 24, 2026, two days early" -- the announcement day, and a goal date that is wrong.
REGN-2026-08-19: Regeneron stated the goal only as "August 2026" (release 2026-02-19, Q1 8-K, Q2 10-Q), so the row
  moved to month precision today and the "12 days early" margin has no document behind it. Withdrawn from every
  surface of the page (house rule: no margin unless both dates come from a document that states them).
/fda-this-month: two doubled-word typos.
Facts only; not investment advice.
"""
import io
import os

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdufa_site_src")
FIX = {
    "fda-decision/MNKD-2026-07-24/index.html": [
        ("two days ahead of its PDUFA goal date (Jul 24 2026)", "three days ahead of its PDUFA goal date (Jul 26 2026)"),
        ("The FDA approved on July 24, 2026, two days early.",
         "The FDA approved on July 23, 2026 (FDA letter), three days early; MannKind announced it on July 24."),
    ],
    "fda-decision/REGN-2026-08-19/index.html": [
        ("Garetosmab Approved Aug 19, 2026, 12 Days Early", "Garetosmab Approved Aug 19, 2026"),
        ("12 days before its August 31, 2026 PDUFA goal date.", "within its August 2026 PDUFA goal month."),
        ("approved on August 19, 2026 - twelve days before its August 31 PDUFA goal date - as",
         "approved on August 19, 2026, in its August 2026 PDUFA goal month, as"),
        ("The PDUFA target action date was August 31, 2026; the FDA approved the BLA on August 19, twelve days early, under Priority Review.",
         "Regeneron stated the PDUFA target action date as August 2026; the FDA approved the BLA on August 19 under Priority Review."),
    ],
}


def main():
    for rel, pairs in FIX.items():
        p = os.path.join(SITE, *rel.split("/"))
        doc = io.open(p, encoding="utf-8").read()
        for old, new in pairs:
            n = doc.count(old)
            doc = doc.replace(old, new)
            print(f"  {rel}: {n}x {old[:60]!r}")
        io.open(p, "w", encoding="utf-8").write(doc)
    p = os.path.join(SITE, "fda-this-month", "index.html")
    if os.path.exists(p):
        doc = io.open(p, encoding="utf-8").read()
        for old, new in ((" in in combination", " in combination"), (" in with BCG", " with BCG")):
            print(f"  fda-this-month: {doc.count(old)}x {old!r}")
            doc = doc.replace(old, new)
        io.open(p, "w", encoding="utf-8").write(doc)


if __name__ == "__main__":
    main()
