# -*- coding: utf-8 -*-
"""CI guard: every indexable per-conference page is linked from /conferences.

2026-09-27 (audit item 5): /conference/AASLD and /conference/SABCS carried dates, location, the
sourced presenters and a four-question FAQ -- and no page on the site linked to either, so the
"aasld 2026 dates" / "sabcs 2026" queries arriving on Bing could only land on the hub. Fails when
an indexable /conference/{CODE} page is not linked from the hub (a conference that has ended and
left the hub's upcoming list is exempt).

    python tests/test_conference_pages_linked.py
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def main():
    hub = io.open(os.path.join(SITE, "conferences", "index.html"), encoding="utf-8").read()
    linked = set(re.findall(r'href="/conference/([A-Za-z0-9-]+)"', hub))
    on_hub = set(re.findall(r'<b class="lit" style="color:#eef4fc;font-size:15px">([A-Za-z0-9-]+)</b>', hub))
    fails = []
    for p in glob.glob(os.path.join(SITE, "conference", "*", "index.html")):
        code = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if re.search(r'name="robots"[^>]*noindex', doc[:4000]) or code not in on_hub:
            continue
        if code not in linked:
            fails.append(f"/conference/{code} is indexable and on the hub's list but not linked from /conferences")
    if fails:
        print(f"FAIL: {len(fails)} orphaned conference page(s) (run build_conferences.py):")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- every upcoming conference with a page is linked from /conferences ({len(linked)} links).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
