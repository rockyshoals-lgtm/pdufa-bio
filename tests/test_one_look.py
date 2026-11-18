# -*- coding: utf-8 -*-
"""test_one_look.py -- every public page uses the site's fonts, its logo mark and one nav style.

Design red team 2026-11-18 (change 11). 129 public pages loaded no site font (/pdufa/CAPR-deramiocel, every /crl
month), 918 lacked the type rules, 1,371 showed the wordmark without its logo mark, and the nav's Explore and
Research buttons rendered larger and brighter than the links beside them (font:inherit took the body's size). This
fails if a public page:

  1. does not load /fonts/fonts.css, or lacks <style id="typesys">;
  2. shows the pdufa.bio wordmark without the logo mark;
  3. has the Explore/Research buttons without the navmatch rule, or with a size or colour other than its own nav
     links' (rebuild_nav.nav_match reads them from the page).
PLANT=font drops fonts.css from /pdufa/CAPR-deramiocel, PLANT=mark drops its logo mark, PLANT=nav sets home's
buttons to 16px; each must FAIL.

    python tests/test_one_look.py
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

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
import inject_site_type as ist  # noqa: E402
import rebuild_nav as rn  # noqa: E402


def main():
    plant = os.environ.get("PLANT", "")
    bad, pages = [], 0
    for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if not ist.public(p, doc):
            continue
        rel = os.path.relpath(p, SITE).replace(os.sep, "/")
        if plant == "font" and rel == "pdufa/CAPR-deramiocel/index.html":
            doc = re.sub(r'<link rel="stylesheet" href="/fonts/fonts\.css">', "", doc)
        if plant == "mark" and rel == "pdufa/CAPR-deramiocel/index.html":
            doc = re.sub(r'<!--LM:B-->.*?<!--LM:E-->|<svg class="lm".*?</svg>', "", doc, count=1, flags=re.S)
        if plant == "nav" and rel == "index.html":
            doc = re.sub(r'(\.navdd \.navddb\{font-size:)[^;]+', r"\g<1>16px", doc)
        pages += 1
        if "/fonts/fonts.css" not in doc:
            bad.append(f"/{rel}: loads no site font (/fonts/fonts.css)")
        if 'id="typesys"' not in doc:
            bad.append(f"/{rel}: lacks the type rules (<style id=\"typesys\">)")
        if ist.BRAND.search(doc):
            bad.append(f"/{rel}: the wordmark has no logo mark")
        if 'class="navddb"' in doc:
            cur = re.search(r'<style id="navmatch">.*?</style>', doc, re.S)
            if not cur:
                bad.append(f"/{rel}: Explore/Research have no navmatch rule (they render larger than the links)")
            elif cur.group(0) != rn.nav_match(doc):
                bad.append(f"/{rel}: Explore/Research size or colour differs from its nav links: {cur.group(0)[22:90]}")
    print(f"{pages} public page(s) checked")
    if bad:
        for b in bad[:30]:
            print("  FAIL " + b)
        if len(bad) > 30:
            print(f"  ... and {len(bad) - 30} more")
        print("  fix: python rebuild_nav.py && python inject_site_type.py")
        sys.exit(1)
    print("  PASS: every public page has the site fonts, the type rules, the logo mark and one nav style")


if __name__ == "__main__":
    main()
