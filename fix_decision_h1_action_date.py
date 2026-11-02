# -*- coding: utf-8 -*-
"""fix_decision_h1_action_date.py -- a decision page's h1 states the FDA's action day, not the day it was announced.

Red team 2026-11-01. /fda-decision/ABBV-2026-09-28 is titled "JUVMO (tavapadon) Approved Sep 25, 2026" and its
description says "approved on September 25, 2026 (announced September 28, 2026)", but its h1 read
"ABBV FDA decision: Sep 28, 2026" -- the URL's date, which is the announcement day. Same on MRK-2026-09-22
(action Sep 21), TLX-2026-09-14 (Sep 11) and others. Two dates for one decision on one page is the kind of
contradiction an AI answer engine resolves by picking one at random.

Rule: when the page's <title> states "Approved|CRL|... <Mon D, YYYY>" and the meta description says
"(announced <Month D, YYYY>)", the h1 date becomes the action day from the title and gains
"(announced Mon D)". Pages whose title and h1 already agree are untouched. Idempotent.

    python fix_decision_h1_action_date.py [--dry-run]
"""
import argparse
import datetime as dt
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
H1 = re.compile(r'(<h1>[A-Z][A-Z./ ]{0,12} <span class="g">FDA decision</span>: )([A-Z][a-z]{2} \d{1,2}, \d{4})'
                r'((?: \(announced [A-Z][a-z]{2} \d{1,2}\))?)(</h1>)')
TITLE_DATE = re.compile(r"<title>[^<]*?\b(?:Approved|CRL|Complete Response Letter|Rejected|Withdrawn|Decided)\b[^<]*?"
                        r"([A-Z][a-z]{2} \d{1,2}, \d{4})")
ANN = re.compile(r'<meta name="description" content="[^"]*\(announced ([A-Z][a-z]+ \d{1,2}, \d{4})\)')


def short(long_date):
    return dt.datetime.strptime(long_date, "%B %d, %Y").strftime("%b %-d, %Y") if os.name != "nt" else \
        dt.datetime.strptime(long_date, "%B %d, %Y").strftime("%b %#d, %Y")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    n = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        h, t, an = H1.search(doc), TITLE_DATE.search(doc), ANN.search(doc)
        if not (h and t and an):
            continue
        act = t.group(1)
        ann_short = short(an.group(1))
        if ann_short == act:
            continue
        want = f" (announced {ann_short.rsplit(',', 1)[0]})"
        if h.group(2) == act and h.group(3) == want:
            continue
        new = doc[:h.start()] + h.group(1) + act + want + h.group(4) + doc[h.end():]
        n += 1
        print(f"  /fda-decision/{os.path.basename(os.path.dirname(p))}: h1 {h.group(2)} -> {act}{want}")
        if not a.dry_run:
            io.open(p, "w", encoding="utf-8").write(new)
    print(f"decision h1 action dates: {n} page(s) " + ("[dry run]" if a.dry_run else "written"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
