# -*- coding: utf-8 -*-
"""A per-event /pdufa/{TICKER}-{drug} page that carries a decision banner must not still
speak in the pending tense.

Audit 2026-09-05 (0800 slot) P0-1: /pdufa/AZN-camizestrant said "Camizestrant is under FDA
review" and "FDA PDUFA target date 2026-12-31" two days after the FDA approved it, while
/fda-decision/AZN-2026-09-04 and /drug/camizestrant said approved. The banner injector had
put the outcome on 24 pages and left every one of them still asking "When is the PDUFA
date?" underneath. This asserts the RENDER: on any event page with a DECBAN banner, the
three template phrases of the pending state are gone, and the FAQ names the decision.

Proven 2026-09-06: 0 -> planted "is under FDA review" back into a bannered page -> 1 ->
removed -> 0.
"""
import glob
import io
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
BANNER = "<!--DECBAN:BEGIN-->"
PENDING = ("is under FDA review", "candidate under FDA review",
           "<span>FDA PDUFA target date</span>", "FDA decision (PDUFA) target <b>",
           "The FDA PDUFA target date for")


def test_event_pages_decided_language():
    bad = []
    n = 0
    for p in sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if BANNER not in doc:
            continue
        n += 1
        slug = os.path.basename(os.path.dirname(p))
        hits = [k for k in PENDING if k in doc]
        if hits:
            bad.append(f"/pdufa/{slug}: still says {hits}")
        if not re.search(r"What did the FDA decide on", doc):
            bad.append(f"/pdufa/{slug}: FAQ does not name the decision")
    assert n > 0, "no bannered event pages found -- the injector did not run or the marker changed"
    assert not bad, (f"{len(bad)} decided event page(s) still in the pending tense:\n  "
                     + "\n  ".join(bad[:20]))


if __name__ == "__main__":
    test_event_pages_decided_language()
    print("OK")
