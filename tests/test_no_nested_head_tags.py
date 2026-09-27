# -*- coding: utf-8 -*-
"""CI guard: no tag in <head> opens inside another tag's attribute list.

2026-09-26: add_og_tags.py (09-23) inserted its Open Graph block after the description meta's
closing quote instead of its '>', on 1,055 pages: content="..."<meta property=...>. Every
presence check passed (the strings were all there); the markup was broken. This asserts the
shape: a quote immediately followed by '<tag' means a tag was spliced into an attribute list.

    python tests/test_no_nested_head_tags.py
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
PAT = re.compile(r'"<(meta|link|script|title|style)\b')


def main():
    bad = []
    for f in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        doc = io.open(f, encoding="utf-8", errors="replace").read()
        head = doc[:doc.find("</head>")] if "</head>" in doc else doc[:20000]
        m = PAT.search(head)
        if m:
            bad.append(f"/{os.path.relpath(f, SITE).replace(os.sep, '/')}: ...{head[max(0, m.start() - 40):m.start() + 30]}...")
    if bad:
        print(f"FAIL: {len(bad)} page(s) with a tag spliced into another tag's attributes (run repair_meta_nesting.py):")
        for b in bad[:10]:
            print("   " + b)
        return 1
    print("OK -- no head tag opens inside another tag.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
