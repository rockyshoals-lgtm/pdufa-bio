# -*- coding: utf-8 -*-
"""/decisions/approvals linked five decision pages that do not exist, and showed the wrong date
for each -- the goal date, not the action date.

    shown                                    real decision page
    AZN  2026-06-30  Truqap                   AZN-2026-06-12   (goal date shown; Truqap was the
                                                                09-10 quarter-end withdrawal)
    GSK  2026-06-18  Utebzi                   GSK-2026-06-17
    SPRO 2026-06-18  Utebzi                   SPRO-2026-06-17
    VRDN 2026-06-29  Lumvoa                   VRDN-2026-06-26
    VRDN 2026-06-30  Lumvoa                   VRDN-2026-06-26   (a SECOND row for one approval)

Each row's href and its visible date move to the decision page's own date, and the duplicate VRDN
row is removed. Every target was opened and its title read before this script was written, so the
drug on the row matches the drug on the page.

    python fix_approvals_listing_dates.py [--dry-run]
"""
import argparse
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "decisions", "approvals", "index.html")
MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONL = ["", "January", "February", "March", "April", "May", "June", "July", "August",
        "September", "October", "November", "December"]
# wrong-slug -> right-slug   (verified by opening each target and reading its <title>)
FIX = {"AZN-2026-06-30": "AZN-2026-06-12",
       "GSK-2026-06-18": "GSK-2026-06-17",
       "SPRO-2026-06-18": "SPRO-2026-06-17",
       "VRDN-2026-06-29": "VRDN-2026-06-26"}
DROP = "VRDN-2026-06-30"   # duplicate of VRDN-2026-06-26


def forms(iso):
    y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    return [iso, f"{MON[m]} {d}, {y}", f"{MON[m]} {d} {y}", f"{MONL[m]} {d}, {y}"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    doc = io.open(PAGE, encoding="utf-8", errors="replace").read()
    orig = doc

    # drop the duplicate row first, anchored on its own href
    m = re.search(r'<a[^>]*href="/fda-decision/' + DROP + r'"[^>]*>.*?</a>', doc, re.S)
    if m:
        doc = doc[:m.start()] + doc[m.end():]
        print(f"  removed duplicate row {DROP} (one approval, two rows)")
    else:
        print(f"  {DROP}: row not present (already removed)")

    for wrong, right in FIX.items():
        if not os.path.isfile(os.path.join(SITE, "fda-decision", right, "index.html")):
            print(f"  SKIP {wrong}: target {right} does not exist")
            continue
        m = re.search(r'<a[^>]*href="/fda-decision/' + wrong + r'"[^>]*>.*?</a>', doc, re.S)
        if not m:
            print(f"  {wrong}: row not found")
            continue
        row = m.group(0)
        new = row.replace(f"/fda-decision/{wrong}", f"/fda-decision/{right}")
        w_iso, r_iso = wrong[-10:], right[-10:]
        for wf, rf in zip(forms(w_iso), forms(r_iso)):
            new = new.replace(wf, rf)
        doc = doc[:m.start()] + new + doc[m.end():]
        print(f"  {wrong} -> {right}  (href and visible date both moved)")

    if doc != orig and not a.dry_run:
        io.open(PAGE, "w", encoding="utf-8").write(doc)
    print("written" if (doc != orig and not a.dry_run) else
          ("dry run" if a.dry_run else "no change"))

    # report: every decision link on the page must resolve
    dead = [h for h in set(re.findall(r'href="(/fda-decision/[^"]+)"', doc))
            if not os.path.isfile(os.path.join(SITE, h.strip("/"), "index.html"))]
    print("remaining dead decision links on /decisions/approvals:", dead or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
