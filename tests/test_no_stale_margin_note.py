# -*- coding: utf-8 -*-
"""test_no_stale_margin_note.py -- no decision page says the FDA's action day is unstated while it states it.

Red team 2026-11-18: /fda-decision/CYTK-2026-11-16 and TEVA-2026-11-16 were titled "Approved Nov 13, 2026, 1 Day
Early", and their Verified lines named the FDA's record (NDA 219083 S-002, NDA 215390 S-003, both November 13). Yet
each still said the sponsor's release "does not state the FDA's action day, so no margin is stated", and so did the
two rows' decision_note in /api/v1/dataset.mjs. fix_stale_margin_note.py rewrites the sentence once the FDA day is
on record; this guard fails if any page or dataset row holds both.

2026-11-27 (PYPD-2026-11-24): the same holds for "The FDA's own record of the action day had not been read when this
page was published", which fix_stale_margin_note.py now rewrites too; a fixer self-check below proves it.

PLANT=stale puts the old CYTK sentence back on its page and must fail.
"""
import glob
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
UNSTATED = re.compile(r"does not state the FDA(?:'|&#x27;|&#39;|’)s action day|"
                      r"own record of the action day(?:,)? (?:which )?had not been read when this page was published")
NAMED = re.compile(r"Verified against:</b>\s*FDA action day [A-Z][a-z]+ \d{1,2}, \d{4}")


def main():
    plant = os.environ.get("PLANT", "")
    bad, pages = [], 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        slug = os.path.basename(os.path.dirname(p))
        if plant == "stale" and slug == "CYTK-2026-11-16":
            doc = doc.replace("</p><!--VERIFIED:END-->", "</p><!--VERIFIED:END--><p>Cytokinetics' release does not "
                              "state the FDA's action day, so no margin is stated.</p>", 1)
        pages += 1
        if NAMED.search(doc) and UNSTATED.search(doc):
            bad.append(f"/fda-decision/{slug}: names the FDA action day yet says the action day is not stated")
    sys.path.insert(0, HERE)
    import fix_stale_margin_note as F  # noqa: E402
    probe = ("<b>Verified against:</b> FDA action day November 24, 2026 (NDA 1) &middot; Goal date November 28, 2026 "
             "(6-K).<!--VERIFIED:END--><p>The FDA&#x27;s own record of the action day had not been read when this page "
             "was published, so no early or late margin is given yet. pdufa.bio publishes a margin only from the FDA's "
             "own record of the action day, which had not been read when this page was published.</p>")
    fixed = F.fix_page(probe)
    if UNSTATED.search(fixed) or fixed.count("dates the action November 24, 2026, 4 days before the goal date") != 2:
        bad.append("fix_stale_margin_note.fix_page() no longer rewrites the 'had not been read' sentences")
    if pages < 300:
        bad.append(f"only {pages} decision page(s) found; the site path is wrong")
    ds = os.path.join(SITE, "api", "v1", "dataset.mjs")
    s = io.open(ds, encoding="utf-8").read()
    for r in json.loads(s[s.index("["):s.rindex("]") + 1]):
        d = r.get("_d") or {}
        if (d.get("fda_action_date") or r.get("fda_action_date")) and UNSTATED.search(d.get("decision_note") or ""):
            bad.append(f"dataset {r.get('id')}: carries fda_action_date yet its decision_note says the day is not stated")
    if bad:
        print(f"FAIL: {len(bad)} stale margin note(s).")
        for b in bad[:30]:
            print("   " + b)
        return 1
    print(f"  PASS: {pages} decision pages and the dataset; none says the FDA action day is unstated beside the FDA's "
          "own record of it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
