# -*- coding: utf-8 -*-
"""CI guard: a decision page that says the FDA action day is not yet posted does not also call the announcement
day the "FDA decision" day (2026-11-17 currency audit: SMMT, CYTK and TEVA did, in the h1, key facts and chart).

PLANT=1 strips the label from one page and must FAIL.

    python tests/test_announcement_only_dates.py
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def main():
    fails, n = [], 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        v = re.search(r"<!--VERIFIED:BEGIN-->(.*?)<!--VERIFIED:END-->", doc, re.S)
        if not v or "FDA action day not yet posted" not in v.group(1):
            continue
        n += 1
        if os.environ.get("PLANT") and n == 1:
            doc = doc.replace("<!--ANNONLY-->announced ", "")
        slug = os.path.basename(os.path.dirname(p))
        if re.search(r'<span class="g">FDA decision</span>: [A-Z][a-z]{2} \d', doc):
            fails.append(f"{slug}: h1 calls the announcement day the FDA decision day")
        if re.search(r'<span>FDA decision date</span><b>\d{4}-\d{2}-\d{2}</b>', doc):
            fails.append(f"{slug}: key facts give a date as the FDA decision date")
        if re.search(r"FDA decision \d{1,2}/\d{1,2}/\d{2}\. ", doc):
            fails.append(f"{slug}: chart caption gives a date as the FDA decision day")
    if fails:
        for f in fails:
            print("  FAIL " + f + " -- run label_announcement_only_dates.py")
        print(f"\n{len(fails)} failure(s): the page's own Verified line says the FDA day is not on record.")
        return 1
    print(f"OK -- {n} announcement-only decision page(s) state the announcement day as the announcement day.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
