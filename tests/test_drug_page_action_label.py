# -*- coding: utf-8 -*-
"""CI guard: a drug page never labels an FDA ACTION date as a PDUFA goal (red team 2026-10-04).

/drug/jaypirca listed "PDUFA . Oct 2, 2026" for an approval whose goal date pdufa.bio does not hold;
the day is the FDA's action day. Fails, on the rendered /drug pages, when a catalyst-history row
linking to /fda-decision/{TK}-{day} says "PDUFA" while the dataset row for that (ticker, day) is
goal_unsourced. Also fails when the About text starts an approved indication with a capital
"Adult" mid-sentence.

    python tests/test_drug_page_action_label.py
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")


def main():
    s = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows = json.loads(s[s.index("["):s.rindex("]") + 1])
    unsourced = {(str(r.get("t") or "").upper(), r.get("d")) for r in rows
                 if (r.get("_d") or {}).get("goal_unsourced") and str(r.get("st")) == "Decided"}
    fails, n = [], 0
    for p in glob.glob(os.path.join(SITE, "drug", "*", "index.html")):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        slug = os.path.basename(os.path.dirname(p))
        for m in re.finditer(r'<a class="row" href="/fda-decision/([A-Z0-9.]+)-(\d{4}-\d{2}-\d{2})"[^>]*>'
                             r'<span class="t">([^<]*)', doc):
            n += 1
            if (m.group(1), m.group(2)) in unsourced and m.group(3).strip().upper().startswith("PDUFA"):
                fails.append(f"/drug/{slug}: {m.group(1)} {m.group(2)} labelled PDUFA (no goal date on record)")
        if re.search(r"(tracked on pdufa\.bio|FDA-approved for|in our records): Adult\b", doc):
            fails.append(f"/drug/{slug}: capitalised 'Adult' mid-sentence")
    if fails:
        print(f"FAIL: {len(fails)} drug-page label problem(s):")
        for f in fails[:20]:
            print("   " + f)
        return 1
    print(f"OK -- {n} decision rows on drug pages; no FDA action day labelled as a PDUFA goal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
