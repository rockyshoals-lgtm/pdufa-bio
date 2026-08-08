# -*- coding: utf-8 -*-
"""test_no_download_dupes.py -- keep browser-download duplicates out of the repo.

Windows appends " (1)" when a file is downloaded twice, and those copies land in the working tree
looking exactly like the real thing. Five of them (index (1).html in retired decision folders) got
committed once already. That one was harmless because _retired_ directories are excluded from the
build, but the same accident one directory over ships a stale duplicate of a live page: two files
with near-identical content, one of them frozen at whatever the data said the day it was downloaded.

The first version of this check only walked pdufa_site_src, which is why a later sweep still found
35 of them sitting in the repo root -- including a duplicate of the ODIN training CSV and of several
build scripts, where the risk is editing the copy and wondering why nothing changed.

So this walks the whole repo. Anything matching " (N)" before the extension fails.
"""
import os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUPE = re.compile(r" \(\d+\)(\.[A-Za-z0-9]+)?$")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "orats_backtest_cache",
             "backtest_progress"}


def main():
    hits = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if DUPE.search(f):
                hits.append(os.path.relpath(os.path.join(root, f), ROOT).replace("\\", "/"))

    if hits:
        print(f"FAIL: {len(hits)} browser-download duplicate(s) in the repo.")
        for h in sorted(hits)[:25]:
            print(f"   {h}")
        if len(hits) > 25:
            print(f"   ... and {len(hits) - 25} more")
        print("\n   These are ' (1)' copies created by downloading a file twice. Delete them.")
        print("   A duplicate of a page ships stale content; a duplicate of a script gets edited")
        print("   by mistake and the change silently does nothing.")
        return 1

    print("  PASS: no browser-download duplicates anywhere in the repo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
