# -*- coding: utf-8 -*-
"""repair_meta_nesting.py -- undo the head-tag nesting add_og_tags.py introduced on 2026-09-23.

add_og_tags.py inserted its block at the end of the description regex match, which is the
closing QUOTE of content="...", not the '>' of the tag:

    <meta name="description" content="..."<meta property="og:site_name" ...>...<meta ...>>

HTML parsers then treat '<meta' and the first inserted tag's attributes as junk attributes of
the description meta, and drop that tag. This moves the stray '>' back where it belongs:

    <meta name="description" content="..."><meta property="og:site_name" ...>...<meta ...>

Idempotent (a repaired page no longer matches). Kept in the repo as the record of the repair.

    python repair_meta_nesting.py [--dry-run]
"""
import argparse
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PAT = re.compile(r'(<meta name="description" content="[^"]*")((?:<meta [^<>]*>)+)>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    n = 0
    for f in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        doc = io.open(f, encoding="utf-8", errors="replace").read()
        new, k = PAT.subn(lambda m: m.group(1) + ">" + m.group(2), doc, count=1)
        if k and new != doc:
            n += 1
            if not a.dry_run:
                io.open(f, "w", encoding="utf-8", newline="").write(new)
    print(f"meta nesting: {n} page(s) {'would be ' if a.dry_run else ''}repaired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
