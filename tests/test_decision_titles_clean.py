# -*- coding: utf-8 -*-
"""CI guard: no decision-page <title> ends its drug name on a dangling word (2026-10-16).

The title budget (100 characters) trims the drug name at a word boundary. /fda-decision/TEVA-2026-09-25 was titled
"Degevma (denosumab-adet), biosimilar to and Approved Sep 25, 2026", a cut that reads as broken in a search result.
Fails when the text before the outcome word (Approved / Approval Announced / CRL / Withdrawn) ends in a connector
(and, or, to, of, with, for, the, in, plus, a) or a comma.
Plant: PLANT_TITLE=1 injects the Degevma title in memory and must FAIL.

    python tests/test_decision_titles_clean.py
"""
import glob
import html
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
RX = re.compile(r"^(.*?)\s+(?:FDA Approval Announced|Approval Announced|Approved|CRL|Withdrawn)\b")
BAD = re.compile(r"(?:\s(?:and|or|to|of|with|for|the|in|plus|a)|,)$", re.I)


def main():
    fails, n = [], 0
    titles = []
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        m = re.search(r"<title>(.*?)</title>", io.open(p, encoding="utf-8", errors="replace").read(), re.S)
        if m:
            titles.append((os.path.basename(os.path.dirname(p)), html.unescape(m.group(1)).strip()))
    if os.environ.get("PLANT_TITLE") == "1":
        titles.append(("TEVA-2026-09-25", "Degevma (denosumab-adet), biosimilar to and Approved Sep 25, 2026 | TEVA FDA Decision | pdufa.bio"))
    for slug, t in titles:
        m = RX.match(t)
        if not m:
            continue
        n += 1
        if BAD.search(m.group(1)):
            fails.append(f"/fda-decision/{slug}: '{t}'")
    if fails:
        print(f"FAIL: {len(fails)} decision title(s) cut on a dangling word:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} decision titles end the drug name cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
