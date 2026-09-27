# -*- coding: utf-8 -*-
"""CI guard: /fda-approval-letters states the count it lists, and lists every FDA action we hold.

Audit 2026-09-27 item 4 ("page live, rows link letters, n stated"). The n in the h1 must equal the
rows in the tables, and equal the distinct FDA actions (record + date) in the dataset; every row
links an fda.gov document.

    python tests/test_fda_letters_hub.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def main():
    p = os.path.join(SITE, "fda-approval-letters", "index.html")
    if not os.path.exists(p):
        print("FAIL: /fda-approval-letters is not built -- run build_fda_letters_hub.py")
        return 1
    doc = io.open(p, encoding="utf-8").read()
    m = re.search(r"<h1>FDA approval letters: <span class=\"g\">(\d+) FDA decisions", doc)
    stated = int(m.group(1)) if m else -1
    body = doc[doc.find("<table"):]
    trs = re.findall(r"<tr><td class=\"dt\">.*?</tr>", body, re.S)
    fda_links = sum(1 for t in trs if re.search(r'href="https://(www\.)?[a-z.]*fda\.gov/', t))
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    acts = {((r.get("_d") or {}).get("fda_action_record") or (r.get("_d") or {}).get("fda_action_source_url"),
             (r.get("_d") or {}).get("fda_action_date"))
            for r in rows if r.get("type") == "PDUFA" and (r.get("_d") or {}).get("fda_action_source_url")
            and (r.get("_d") or {}).get("fda_action_date")
            and re.match(r"https://(www\.)?[a-z.]*fda\.gov/", (r.get("_d") or {}).get("fda_action_source_url"))}
    fails = []
    if stated != len(trs):
        fails.append(f"h1 states {stated}, table lists {len(trs)}")
    if len(trs) != len(acts):
        fails.append(f"table lists {len(trs)}, dataset holds {len(acts)} distinct FDA actions -- run build_fda_letters_hub.py")
    if fda_links != len(trs):
        fails.append(f"{len(trs) - fda_links} row(s) without an fda.gov link")
    if fails:
        print("FAIL: /fda-approval-letters:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- /fda-approval-letters states and lists {stated} FDA actions, each linked to an fda.gov record.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
