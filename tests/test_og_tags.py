# -*- coding: utf-8 -*-
"""CI guard: every indexable page carries og:title, og:description and an og:url equal to its
canonical (SEO audit 2026-09-23: 168 pages had no og:title; add_og_tags.py owns the fill).

    python tests/test_og_tags.py
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
SKIP = re.compile(r"[\\/]_[a-z]+bak|[\\/]_pdufa_|[\\/]_site_attic|[\\/]_[^\\/]*\.html$")


def main():
    fails, n = [], 0
    for f in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        if SKIP.search(f):
            continue
        doc = io.open(f, encoding="utf-8", errors="replace").read()
        head = doc[:doc.find("</head>")] if "</head>" in doc else doc[:12000]
        if re.search(r'name="robots"[^>]*noindex', head) or "<title>" not in head:
            continue
        rel = "/" + os.path.relpath(os.path.dirname(f), SITE).replace("\\", "/")
        n += 1
        canon = re.search(r'<link rel="canonical" href="([^"]*)"', head)
        ogu = re.search(r'<meta property="og:url" content="([^"]*)"', head)
        if not re.search(r'<meta property="og:title" content="[^"]+"', head):
            fails.append(f"{rel}: no og:title")
        if re.search(r'<meta name="description"', head) and not re.search(
                r'<meta property="og:description" content="[^"]+"', head):
            fails.append(f"{rel}: no og:description")
        if canon and (not ogu or ogu.group(1) != canon.group(1)):
            fails.append(f"{rel}: og:url {ogu.group(1) if ogu else None} != canonical {canon.group(1)}")
    if fails:
        print(f"FAIL: {len(fails)} Open Graph gap(s) on indexable pages (run add_og_tags.py):")
        for x in fails[:20]:
            print("   " + x)
        return 1
    print(f"OK -- og:title / og:description / og:url==canonical on {n} indexable page(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
