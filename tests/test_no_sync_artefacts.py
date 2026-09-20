# -*- coding: utf-8 -*-
"""CI/local guard: the site tree carries no file-sync artefacts and no page directory is empty.

2026-09-19: 11 "index (1).html" copies appeared under /drug at 13:54 Pacific during a rebuild.
2026-09-20: 260 "index (1).html" copies appeared at 14:01:03 Pacific during a rebuild, and 133
tracked index.html files vanished (their directories left empty) -- /learn/what-is-a-pdufa-date,
/pdufa/NVO-am833, 25 decision pages, 14 drug pages, /calendar/2025. The chain then failed in
three places and the timing statistic collapsed from 30 to 13. GoogleDriveFS was running against
the Documents folder; the " (1)" suffix is a sync client's duplicate naming, and an external
process that deletes and duplicates files under a build is a corruption source the build must
refuse to publish through.

    python tests/test_no_sync_artefacts.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
SKIP = re.compile(r"[\\/]_[a-z]+bak|[\\/]_pdufa_|[\\/]node_modules[\\/]|[\\/]\.vercel[\\/]|[\\/]api[\\/]")
PAGE_ROOTS = ("pdufa", "fda-decision", "drug", "ticker", "calendar", "learn", "research",
              "condition", "conference", "readouts", "company")


def main():
    dupes, empty = [], []
    for root, dirs, files in os.walk(SITE):
        if SKIP.search(root + os.sep):
            continue
        for f in files:
            if re.match(r"^index \(\d+\)\.html$", f) or re.search(r" \(\d+\)\.(html|json|mjs|xml)$", f):
                dupes.append(os.path.relpath(os.path.join(root, f), SITE))
        rel = os.path.relpath(root, SITE).replace("\\", "/")
        top = rel.split("/")[0]
        if top in PAGE_ROOTS and rel.count("/") >= 1 and not files and not dirs:
            empty.append(rel)
    if dupes or empty:
        print(f"FAIL: {len(dupes)} sync-duplicate file(s) and {len(empty)} empty page director(y/ies) in the site tree:")
        for x in (dupes + empty)[:15]:
            print("   " + x)
        print("\n   A file-sync client is writing into the build tree. Delete the ' (N)' copies, restore\n"
              "   missing pages with `git checkout -- <path>`, and keep the sync client out of this folder.")
        return 1
    print("OK -- no ' (N)' duplicate files and no empty page directories in the site tree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
