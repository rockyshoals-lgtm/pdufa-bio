# -*- coding: utf-8 -*-
"""CI guard: a decision page's key facts give the same FDA action day as its own Verified line (2026-11-17).

SMMT read "FDA decision: Nov 13, 2026 (announced Nov 15)" in its h1 and Verified line while its key facts said
"FDA decision date 2026-11-15"; seven older pages had the same split. When the Verified line names a linked FDA
record for the action day, key facts must show that day as the FDA decision date (the announcement day goes in an
"Announced" row). PLANT=1 restores the announcement day on one page and must FAIL.

    python tests/test_decision_kv_action_date.py
"""
import datetime as dt
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
VF = re.compile(r'<!--VERIFIED:BEGIN-->.*?FDA action day ([A-Z][a-z]+ \d{1,2}, \d{4}) \(<a href="https://', re.S)
KV = re.compile(r'<div class="kv"><span>FDA decision date</span><b>(\d{4}-\d{2}-\d{2})</b></div>')


def main():
    fails, n = [], 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        v, m = VF.search(doc), KV.search(doc)
        if not v or not m:
            continue
        n += 1
        fad = dt.datetime.strptime(v.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
        kv = m.group(1)
        if os.environ.get("PLANT") and "<span>Announced</span>" in doc and not fails:
            kv = re.search(r'<span>Announced</span><b>(\d{4}-\d{2}-\d{2})', doc).group(1)
        if kv != fad:
            fails.append(f"{os.path.basename(os.path.dirname(p))}: key facts say {kv}, Verified line says the FDA "
                         f"acted {fad}")
    if fails:
        for f in fails:
            print("  FAIL " + f)
        print(f"\n{len(fails)} page(s) -- run fix_decision_kv_action_date.py")
        return 1
    print(f"OK -- {n} decision page(s) give the same FDA action day in key facts and the Verified line.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
