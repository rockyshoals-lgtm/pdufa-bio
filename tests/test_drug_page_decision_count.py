# -*- coding: utf-8 -*-
"""CI guard: a /drug page lists each FDA decision once, and the count it states is that number.

Found 2026-09-18. /drug/* is fed by the dataset AND by the decisions archive. When a decided
row's goal date equals its action date, both sources yield the same (ticker, day) event and the
page rendered it twice, then counted it twice:

    /drug/zanidatamab   "4 FDA decisions on record"   over 2 distinct decisions
    /drug/ziihera       "4 FDA decisions on record"   over 2
    /drug/zoryve        "4"                           over 3
    /drug/lipfendra     "2"                           over 1
    /drug/mflusiva      "2"                           over 1
    /drug/inluriyo      "3"                           over 2

That sentence is exactly what an answer engine quotes, and /drug/zanidatamab holds the only
100%-citation-share grounding query on the property. Two invariants:

  1. no /drug page links the same /fda-decision/TICKER-DATE twice;
  2. the "N FDA decisions on record" it states equals the number of distinct decision links.

    python tests/test_drug_page_decision_count.py
"""
import io
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRUGS = os.path.join(HERE, "pdufa_site_src", "drug")


def main():
    if not os.path.isdir(DRUGS):
        print("  SKIP no /drug pages")
        return 0
    fail = pages = 0
    for slug in sorted(os.listdir(DRUGS)):
        p = os.path.join(DRUGS, slug, "index.html")
        if not os.path.isfile(p):
            continue
        pages += 1
        t = io.open(p, encoding="utf-8", errors="replace").read()
        links = re.findall(r'href="(/fda-decision/[A-Z]{1,6}-\d{4}-\d{2}-\d{2})"', t)
        dupes = {k: v for k, v in Counter(links).items() if v > 1}
        if dupes:
            print(f"  FAIL /drug/{slug}: lists the same decision more than once: {dupes}. "
                  f"One decision, one row (build_drug_pages.py dedups on the decision href).")
            fail += 1
        m = re.search(r"(\d+) FDA decisions? (?:are |is )?on record", t)
        if m and int(m.group(1)) != len(set(links)):
            print(f"  FAIL /drug/{slug}: says '{m.group(0)}' but links "
                  f"{len(set(links))} distinct decision(s). The count is the sentence answer "
                  f"engines quote; it must be the number of distinct decisions.")
            fail += 1
    if fail:
        print(f"\n{fail} drug-page decision-count defect(s). DO NOT PUBLISH.")
        return 1
    print(f"OK -- {pages} drug page(s): every FDA decision listed once, every stated count equal "
          f"to the number of distinct decisions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
