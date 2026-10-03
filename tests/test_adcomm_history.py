# -*- coding: utf-8 -*-
"""CI guard: /adcomm carries the 2020-2026 advisory committee calendar from Federal Register notices (audit 4.2).

Fails, on the rendered /adcomm page, when the section is missing; when the count in its heading differs from
its rows; when a row does not link a federalregister.gov notice; when fewer than 95% of the CSV seed's 140
notices that are drug/biologic meeting notices appear; or when the section states a vote or names a ticker
(notices only: votes stay hand-sourced, no company or drug).

    python tests/test_adcomm_history.py
"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    doc = io.open(os.path.join(HERE, "pdufa_site_src", "adcomm", "index.html"), encoding="utf-8").read()
    m = re.search(r"<!--ADCH:BEGIN-->(.*?)<!--ADCH:END-->", doc, re.S)
    if not m:
        print("FAIL: /adcomm has no advisory committee history section")
        return 1
    sec = m.group(1)
    fails = []
    hm = re.search(r"2020 to 2026: (\d+) Federal Register notices", sec)
    rows = re.findall(r"<tr><td.*?</tr>", sec, re.S)
    if not hm or int(hm.group(1)) != len(rows):
        fails.append(f"heading states {hm.group(1) if hm else '?'}, section lists {len(rows)} rows")
    nolink = [r for r in rows if "federalregister.gov" not in r]
    if nolink:
        fails.append(f"{len(nolink)} row(s) without a Federal Register link")
    if re.search(r"\bvot(ed|e)\s+\d|\bin favou?r\b|/ticker/", sec, re.I):
        fails.append("section states a vote or links a ticker (notices only)")
    cp = os.path.join(HERE, "Odin Perfection", "fda_adcom_historical_meetings_2020-2026.csv")
    seed = list(csv.DictReader(io.open(cp, encoding="utf-8"))) if os.path.exists(cp) else []   # local-only file
    want = [r["doc_num"] for r in seed if not re.search(r"Devices|Tobacco", r["title"])]
    have = sum(1 for d in want if f"FR {d}<" in sec)
    if want and have < 0.95 * len(want):
        fails.append(f"only {have}/{len(want)} CSV seed notices rendered")
    if fails:
        print("FAIL: /adcomm history:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- /adcomm lists {len(rows)} FR meeting notices ({have}/{len(want)} of the CSV seed), each linked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
