# -*- coding: utf-8 -*-
"""CI guard: /decisions says "newest first" and must be.

WHY (red team 2026-11-17)
fix_decisions_order.py re-sorts the list, but its header regex expected "2026 . 183" and the page
had moved to "2026 &middot; 183", so it had silently done nothing for weeks; sync_decisions_listing.py
then inserted each new decision directly under its year header, and 18 rows sat out of order
(TEVA Nov 16 under SMMT Nov 15, GSK Oct 20 under a July row). A script that finds nothing to do
must not look like a script that succeeded, so this guard reads the page itself.

THE INVARIANT: on /decisions, every row's decision date is on or before the row above it, and each
year header's count equals the rows under it.

    python tests/test_decisions_newest_first.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, "pdufa_site_src", "decisions", "index.html")
ROW = re.compile(r'<a class="row" href="/fda-decision/([A-Z0-9\-]+)-(\d{4}-\d{2}-\d{2})"')
HEAD = re.compile(r'<div class="mhead">(\d{4})[^<]*?(\d+)</div>')


def check(doc):
    fails = []
    rows = ROW.findall(doc)
    for (t1, d1), (t2, d2) in zip(rows, rows[1:]):
        if d2 > d1:
            fails.append(f"{t2} {d2} is listed below {t1} {d1}")
    heads = list(HEAD.finditer(doc))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(doc)
        n = len(ROW.findall(doc[h.end():end]))
        if int(h.group(2)) != n:
            fails.append(f"year {h.group(1)} header says {h.group(2)}, {n} rows under it")
    return fails


def self_test():
    good = ('<div class="mhead">2026 &middot; 2</div><a class="row" href="/fda-decision/AA-2026-11-02">'
            '<a class="row" href="/fda-decision/BB-2026-11-01">')
    bad = good.replace("AA-2026-11-02", "AA-2026-10-02")
    ok = not check(good) and len(check(bad)) == 1 and len(check(good.replace("&middot; 2", "&middot; 3"))) == 1
    if not ok:
        print("SELF-TEST FAILED")
    return ok


def main():
    if not self_test():
        return 1
    if not os.path.exists(PAGE):
        print("SKIP: no /decisions page")
        return 0
    fails = check(io.open(PAGE, encoding="utf-8", errors="replace").read())
    if fails:
        print(f"FAIL: /decisions is not newest-first ({len(fails)}); run fix_decisions_order.py:")
        for f in fails[:30]:
            print("   " + f)
        return 1
    print("OK -- /decisions is newest-first and every year count matches its rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
