# -*- coding: utf-8 -*-
"""CI guard: when a decision page's FDA action day and announcement day differ, the Verified line's
"Announcement" must not link the FDA's own record (2026-11-17: ACHV and UNCY cited the CRL letter as the
company's announcement, under a cut-off label "FDA Complete Response Letter, NDA ..., dated").

PLANT=1 points one page's announcement at its FDA record and must FAIL.

    python tests/test_announcement_not_fda_letter.py
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
FDA = re.compile(r'FDA action day ([A-Z][a-z]+ \d{1,2}, \d{4}) \(<a href="([^"]+)"')
ANN = re.compile(r'Announcement ([A-Z][a-z]+ \d{1,2}, \d{4}) \(<a href="([^"]+)"[^>]*>([^<]*)</a>')


def main():
    fails, n = [], 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        v = re.search(r"<!--VERIFIED:BEGIN-->(.*?)<!--VERIFIED:END-->", doc, re.S)
        if not v:
            continue
        f, a = FDA.search(v.group(1)), ANN.search(v.group(1))
        if not (f and a) or f.group(1) == a.group(1):
            continue
        n += 1
        ann_url = f.group(2) if os.environ.get("PLANT") and n == 1 else a.group(2)
        slug = os.path.basename(os.path.dirname(p))
        if ann_url == f.group(2):
            fails.append(f"{slug}: announcement ({a.group(1)}) links the FDA record dated {f.group(1)}")
        elif re.search(r",?\s+dated$", a.group(3)):
            fails.append(f"{slug}: announcement label is cut off: {a.group(3)!r}")
    if fails:
        for x in fails:
            print("  FAIL " + x + " -- record the sponsor's release as _d.announcement / announcement_url")
        print(f"\n{len(fails)} failure(s).")
        return 1
    print(f"OK -- {n} page(s) with separate FDA and announcement days cite the announcement itself.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
