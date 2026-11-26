# -*- coding: utf-8 -*-
"""CI guard: no page's meta tag ends its content with stray quotes.

2026-11-26 (CRL red team): 176 /fda-decision pages carried
    <meta name="description" content="... run-up into the date." followed by two more quote marks
since 2026-09-02. rewrite_decision_snippets.py replaced the text up to the first quote and kept the extra ones on
every run. A browser reads the leftovers as a junk attribute, and the snippet search engines show can lose them or
the tag. The writer now takes every quote and writes one back; this fails if any built page still has one.

    python tests/test_meta_no_stray_quotes.py      (PLANT=1 adds one; the guard must fail)
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
BAD = re.compile(r'<meta [^>]*content="[^"]*""+\s*/?>')


def main():
    bad = []
    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if os.environ.get("PLANT") == "1" and not bad and "<meta name=\"description\" content=\"" in doc:
            doc = re.sub(r'(<meta name="description" content="[^"]*")', r'\1""', doc, count=1)
        m = BAD.search(doc)
        if m:
            bad.append(f"{os.path.relpath(p, SITE)}: {m.group(0)[:120]}")
    if bad:
        print(f"FAIL test_meta_no_stray_quotes: {len(bad)} page(s) with stray quotes in a meta tag; "
              f"fix: python rewrite_decision_snippets.py")
        for b in bad[:20]:
            print("   " + b)
        return 1
    print("OK -- no meta tag ends its content with stray quotes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
