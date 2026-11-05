# -*- coding: utf-8 -*-
"""inject_mobile_nav.py -- every page with the site nav gets the mobile menu button the homepage already has.

UX audit 2026-11-05 (375 px phone viewport). On 1,208 pages -- every /pdufa event page, /fda-decision page, /drug and
/ticker page -- the nav had no mobile menu: at phone width the two dropdowns flatten (by design, for the burger panel)
but nothing hides the panel, so the first full screen of the pages that rank was eighteen stacked links and the h1
started below the fold. The homepage and ~680 other pages carried the fix (style#navpolish + button.pd-burger);
this applies the same markup and CSS, verbatim, everywhere else. Idempotent.

    python inject_mobile_nav.py [--dry-run]
"""
import argparse
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
BTN = ('<button class="pd-burger" aria-label="Open menu" aria-expanded="false" onclick="var o=document.body.classList'
       '.toggle(\'pd-navopen\');this.setAttribute(\'aria-expanded\',o)"><span></span></button>')


def css():
    home = io.open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
    m = re.search(r'<style id="navpolish">.*?</style>', home, re.S)
    return m.group(0) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    style = css()
    if not style:
        print("::warning::homepage style#navpolish not found; nothing injected")
        return 0
    n = 0
    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        if os.sep + "api" + os.sep in p:
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "<!--NAVC:BEGIN-->" not in doc or "pd-burger" in doc:
            continue
        m = re.search(r'(<div class="nav">|<nav[^>]*>)\s*<!--NAVC:BEGIN-->', doc)
        if not m:
            continue
        new = doc[:m.start()] + BTN + doc[m.start():]
        if 'id="navpolish"' not in new:
            new = new.replace("</head>", style + "</head>", 1)
        if new != doc:
            n += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(new)
    print(f"mobile nav button: {n} page(s)" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
