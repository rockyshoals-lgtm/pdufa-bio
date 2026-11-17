# -*- coding: utf-8 -*-
"""link_application_pages.py -- a one-line link from each /drug page to its /fda-application page.

The application page joins a drug's brand, ingredient and code names; it only helps searchers who
reach it. The drug pages are where the site's drug-name traffic already lands, so each one whose drug
has an application page gets a single line under its lede: "FDA application: NDA 215390 (IGALMI):
applicant, code names, owner." Idempotent: the line sits between markers and is rewritten (or
removed) every run, so a page whose application page goes away loses the link the same day.

Which drug pages: the application page's own "Drug page" links, i.e. the /drug/<slug> dirs that
build_fda_application_pages.py found for that application. Run it after that builder.

    python link_application_pages.py [--dry-run]
"""
import argparse
import glob
import html
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
APPS = os.path.join(SITE, "fda-application")
START, END = "<!--FDAAPPL-->", "<!--/FDAAPPL-->"
BLOCK = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    want = {}  # drug slug -> [(appl slug, label)]
    for p in sorted(glob.glob(os.path.join(APPS, "*", "index.html"))):
        aslug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        h1 = re.search(r"<h1>(.*?)</h1>", doc, re.S)
        label = html.unescape(h1.group(1)).strip() if h1 else aslug.upper()
        for d in sorted(set(re.findall(r'href="/drug/([a-z0-9-]+)"', doc))):
            want.setdefault(d, []).append((aslug, label))
    changed = 0
    for p in sorted(glob.glob(os.path.join(SITE, "drug", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        new = BLOCK.sub("", doc)
        if slug in want:
            links = " &middot; ".join(
                f'<a class="lit" href="/fda-application/{a_}">{html.escape(lab)}</a>' for a_, lab in want[slug])
            line = (f'{START}<p class="d">FDA application record: {links}. Brand, ingredient, code names, '
                    f'FDA applicant and owner, each with its source.</p>{END}')
            # under the h1's lede paragraph: right after the first </p> following </h1>
            m = re.search(r"</h1>.*?</p>", new, re.S)
            if not m:
                print(f"  skip /drug/{slug}: no lede paragraph to anchor on")
                continue
            new = new[:m.end()] + line + new[m.end():]
        if new != doc:
            changed += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(new)
    print(f"drug pages linked to an FDA application page: {sum(1 for s in want)} wanted, {changed} changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
