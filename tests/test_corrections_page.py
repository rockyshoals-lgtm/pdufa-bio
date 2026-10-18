# -*- coding: utf-8 -*-
"""CI guard: /corrections renders every entry of _corrections.json (audit 2026-10-18, order 2).

Fails when the page is missing, when any entry's date and "was" text are absent from it, when it is noindex, or
when the stated count disagrees with the file. Plant: PLANT_CORR=1 adds an entry in memory and must FAIL.

    python tests/test_corrections_page.py
"""
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def main():
    d = json.load(io.open(os.path.join(HERE, "_corrections.json"), encoding="utf-8"))
    ents = list(d["entries"]) + [{"date": e["date"], "was": e["text"]} for e in d.get("legacy", [])]
    if os.environ.get("PLANT_CORR") == "1":
        ents.append({"date": "2026-10-19", "was": "Planted entry ZZZQ that the page cannot carry."})
    p = os.path.join(SITE, "corrections", "index.html")
    if not os.path.exists(p):
        print("FAIL: /corrections missing"); return 1
    doc = io.open(p, encoding="utf-8", errors="replace").read()
    txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", doc)))
    fails = []
    if re.search(r'name="robots" content="[^"]*noindex', doc):
        fails.append("/corrections is noindex")
    for e in ents:
        key = re.sub(r"\s+", " ", e["was"])[:60]
        if key not in txt:
            fails.append(f"entry {e['date']} missing from the page: '{key}'")
    m = re.search(r"Corrections: (\d+) published facts", txt)
    if not m or int(m.group(1)) != len(ents):
        fails.append(f"stated count {m.group(1) if m else '?'} != {len(ents)} entries in _corrections.json")
    if fails:
        print(f"FAIL: {len(fails)} /corrections failure(s):")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- /corrections carries all {len(ents)} entries, indexable, count stated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
