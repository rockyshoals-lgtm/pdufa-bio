# -*- coding: utf-8 -*-
"""Audit 09-15 ORDER 7: two pairs of /pdufa pages describe one event each and both members
index. Search engines pick one at random; AI engines cite both and count two events.

  /pdufa/ABBV-tavapadon-2  ->  /pdufa/ABBV-tavapadon   (one NDA, one goal window; the -2 slug is
                                                       a second generation of the same page)
  /pdufa/NVO-cagrisema     ->  /pdufa/NVO-am833        (AM833 IS CagriSema; the dataset row's own
                                                       name is "CagriSema (AM833)")

The MRK-trodelvy / GILD-trodelvy pair stays: the same sBLA, but two sponsors' tickers and two
pages a reader of either ticker hub expects ("David rules" -- auditor 09-15).

Treatment of the duplicate: its <link rel=canonical> points at the primary, its robots meta
becomes noindex,follow (a canonical alone is a hint; noindex is an instruction), every internal
link to it is rewritten to the primary, and it drops out of sitemap.xml. The page itself stays
so any inbound link still lands on the content. Idempotent; the guard
tests/test_duplicate_event_pages_canonical.py holds the map.

    python canonicalise_duplicate_event_pages.py
"""
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DUPES = {"ABBV-tavapadon-2": "ABBV-tavapadon", "NVO-cagrisema": "NVO-am833",
         # Found by the guard's title census on its first run (2026-09-15), not by the audit:
         # seven decided events each had a bare-ticker page (the one the dataset, the drug
         # pages and the screener link) and a thinner drug-slug twin with zero inbound links.
         "BFRI-ameluz": "BFRI", "JAZZ-ziihera": "JAZZ", "PHAR-leniolisib": "PHAR",
         "PTGX-rusfertide": "PTGX", "ROIV-brepocitinib": "ROIV", "TAK-oveporexton": "TAK",
         "ZYME-ziihera": "ZYME",
         # a truncated-slug twin of the same decision (the title census missed it because the
         # truncation reached the title too)
         "GILD-bictegravir-and": "GILD-bictegravir-and-lenacapavi"}
SKIP = re.compile(r"[\\/]_pdufa_(x?bak\d*|bak\d*)[\\/]|[\\/]_[a-z]+bak")


def main():
    for dup, prim in DUPES.items():
        p = os.path.join(SITE, "pdufa", dup, "index.html")
        if not os.path.exists(os.path.join(SITE, "pdufa", prim, "index.html")):
            print(f"FAIL primary /pdufa/{prim} missing"); return 1
        t = io.open(p, encoding="utf-8").read()
        t, n1 = re.subn(r'<link rel="canonical" href="[^"]*"',
                        f'<link rel="canonical" href="https://www.pdufa.bio/pdufa/{prim}"', t)
        t, n2 = re.subn(r'<meta name="robots" content="[^"]*"',
                        '<meta name="robots" content="noindex,follow"', t)
        if "<!--DUPLICATE-OF-->" not in t:
            t = t.replace("<h1", f'<p class="sub" style="margin:0 0 8px"><!--DUPLICATE-OF-->This page duplicates '
                                 f'<a href="/pdufa/{prim}">/pdufa/{prim}</a>, which is the page we maintain.</p><h1', 1)
        io.open(p, "w", encoding="utf-8").write(t)
        print(f"/pdufa/{dup}: canonical -> /pdufa/{prim} ({n1}), robots noindex,follow ({n2})")

    # internal links: every page except the duplicate itself
    changed = 0
    for f in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        if SKIP.search(f):
            continue
        rel = os.path.relpath(f, SITE).replace("\\", "/")
        t = io.open(f, encoding="utf-8", errors="replace").read()
        o = t
        for dup, prim in DUPES.items():
            if rel == f"pdufa/{dup}/index.html":
                continue
            t = re.sub(rf'(href=")(?:https://www\.pdufa\.bio)?/pdufa/{re.escape(dup)}(["/#?])', rf"\g<1>/pdufa/{prim}\2", t)
        if t != o:
            io.open(f, "w", encoding="utf-8").write(t); changed += 1
    print(f"internal links rewritten on {changed} page(s)")

    sm = os.path.join(SITE, "sitemap.xml")
    if os.path.exists(sm):
        t = io.open(sm, encoding="utf-8").read()
        o = t
        for dup in DUPES:
            t = re.sub(rf"\s*<url>\s*<loc>https://www\.pdufa\.bio/pdufa/{re.escape(dup)}/?</loc>.*?</url>", "", t, flags=re.S)
        if t != o:
            io.open(sm, "w", encoding="utf-8").write(t); print("sitemap.xml: duplicates removed")
        else:
            print("sitemap.xml: duplicates already absent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
