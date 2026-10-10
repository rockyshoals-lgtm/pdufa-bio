# -*- coding: utf-8 -*-
"""CI guard: every published 13F row is SHARES of COMMON stock, rendered as a headed table (audit 2026-10-04 UX P1).

Baker Bros' 13F table carries a Celcuity convertible note (sshPrnamtType PRN) and a Surrozen warrant. A note or
a warrant must never be reported as shares. Fails when a row in _13f_specialists.json lacks type SH or a
common-stock titleOfClass, when a rendered F13 block contains a fund line without <table>, or when a planted
PRN row survives inject_13f_block's own filter.

    python tests/test_13f_rows_common_stock.py
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")


def main():
    import inject_13f_block as I
    fails, n_rows = [], 0
    p = os.path.join(HERE, "_13f_specialists.json")
    if os.path.exists(p):
        bt = json.load(io.open(p, encoding="utf-8")).get("by_ticker", {})
        for tk, holds in bt.items():
            for h in holds:
                n_rows += 1
                if not I.is_common_shares(h):
                    fails.append(f"{tk} {h.get('fund')}: type={h.get('type')!r} class={h.get('title_of_class')!r} is not common shares")
    # the renderer refuses a planted note and a planted warrant
    for bad in ({"fund": "X", "shares": 1, "value_usd": 1, "period": "2026-06-30", "filed": "2026-08-14", "url": "u",
                 "type": "PRN", "title_of_class": "NOTE 2.750%"},
                {"fund": "X", "shares": 1, "value_usd": 1, "period": "2026-06-30", "filed": "2026-08-14", "url": "u",
                 "type": "SH", "title_of_class": "WARRANT"}):
        if I.para("T", [bad]):
            fails.append(f"renderer accepted a planted {bad['title_of_class']} row")
    n_pages = 0
    for pg in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")) + glob.glob(os.path.join(SITE, "drug", "*", "index.html")):
        doc = io.open(pg, encoding="utf-8", errors="replace").read()
        m = re.search(r"<!--F13:BEGIN-->(.*?)<!--F13:END-->", doc, re.S)
        if not m:
            continue
        n_pages += 1
        if "<table" not in m.group(1) or "<h2" not in m.group(1):
            fails.append(f"{os.path.relpath(pg, SITE)}: 13F block is not a headed table")
    if fails:
        print(f"FAIL: {len(fails)} 13F problem(s):")
        for f in fails[:15]:
            print("   " + f)
        return 1
    print(f"OK -- {n_rows} 13F rows are common shares (type SH); planted note and warrant refused; {n_pages} pages carry a headed table.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
