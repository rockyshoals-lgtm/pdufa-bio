# -*- coding: utf-8 -*-
"""CI guard: known duplicate /pdufa pages canonicalise to their primary, are noindex, are absent
from the sitemap, and nothing links to them (audit 09-15 ORDER 7). Also: no two INDEXABLE
/pdufa pages share a title -- that is how the ABBV and NVO pairs were found, and a new pair
would fail here before it ships.

    python tests/test_duplicate_event_pages_canonical.py
"""
import glob
import io
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from canonicalise_duplicate_event_pages import DUPES  # one map, one owner
# the same sBLA under two sponsors' tickers; both pages are intentional (auditor 09-15)
ALLOWED_TWINS = {("GILD-trodelvy", "MRK-trodelvy")}
SKIP = re.compile(r"[\\/]_pdufa_(x?bak\d*|bak\d*)[\\/]|[\\/]_[a-z]+bak")


def main():
    fail = 0
    for dup, prim in DUPES.items():
        p = os.path.join(SITE, "pdufa", dup, "index.html")
        if not os.path.exists(p):
            continue
        t = io.open(p, encoding="utf-8", errors="replace").read()
        c = re.search(r'<link rel="canonical" href="([^"]+)"', t)
        if not c or c.group(1).rstrip("/") != f"https://www.pdufa.bio/pdufa/{prim}":
            print(f"  FAIL /pdufa/{dup} canonical is {c.group(1) if c else None}, want /pdufa/{prim}"); fail += 1
        if not re.search(r'<meta name="robots" content="noindex', t):
            print(f"  FAIL /pdufa/{dup} is indexable; it duplicates /pdufa/{prim}"); fail += 1
    sm = os.path.join(SITE, "sitemap.xml")
    if os.path.exists(sm):
        s = io.open(sm, encoding="utf-8").read()
        for dup in DUPES:
            if re.search(rf"/pdufa/{re.escape(dup)}/?</loc>", s):
                print(f"  FAIL sitemap.xml lists the duplicate /pdufa/{dup}"); fail += 1

    titles = defaultdict(list)
    for f in glob.glob(os.path.join(SITE, "pdufa", "*", "index.html")):
        if SKIP.search(f):
            continue
        slug = os.path.basename(os.path.dirname(f))
        t = io.open(f, encoding="utf-8", errors="replace").read()
        for dup, prim in DUPES.items():
            if slug != dup and re.search(rf'href="(?:https://www\.pdufa\.bio)?/pdufa/{re.escape(dup)}["/#?]', t):
                print(f"  FAIL /pdufa/{slug} links to the duplicate /pdufa/{dup}; link /pdufa/{prim}"); fail += 1
        if re.search(r'<meta name="robots" content="noindex', t):
            continue
        m = re.search(r"<title>(.*?)</title>", t, re.S)
        if m:
            titles[re.sub(r"\s+", " ", m.group(1)).strip()].append(slug)
    for hubs in glob.glob(os.path.join(SITE, "ticker", "*", "index.html")):
        t = io.open(hubs, encoding="utf-8", errors="replace").read()
        for dup, prim in DUPES.items():
            if re.search(rf'href="(?:https://www\.pdufa\.bio)?/pdufa/{re.escape(dup)}["/#?]', t):
                print(f"  FAIL {os.path.relpath(hubs, SITE)} links to the duplicate /pdufa/{dup}"); fail += 1
    for title, slugs in titles.items():
        if len(slugs) > 1 and tuple(sorted(slugs)) not in ALLOWED_TWINS:
            print(f"  FAIL {len(slugs)} indexable /pdufa pages share a title: {slugs} -- {title[:70]!r}. "
                  f"Canonicalise one to the other (canonicalise_duplicate_event_pages.py)."); fail += 1

    if fail:
        print(f"\n{fail} duplicate-page failure(s). DO NOT PUBLISH."); return 1
    print(f"OK -- {len(DUPES)} known duplicates canonicalised + noindex + unlinked; "
          f"{sum(len(v) for v in titles.values())} indexable /pdufa pages carry distinct titles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
