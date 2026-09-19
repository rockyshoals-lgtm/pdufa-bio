# -*- coding: utf-8 -*-
"""Show the remaining 2026-12-31 occurrences after a dry run, in context.

Some are legitimate: a December window's Event schema END date IS 2026-12-31. Others are not.
Look before deciding.
"""
import io
import re
import subprocess
import sys

sys.path.insert(0, ".")

# run the fixer to a scratch copy by applying it in-memory is awkward; instead just show what
# the CURRENT (unmodified) pages hold, and reason about which occurrences the fixer leaves.
for slug in ("ABBV-tavapadon", "NVO-cagrisema", "NVO-mim8"):
    d = io.open(f"pdufa_site_src/pdufa/{slug}/index.html",
                encoding="utf-8", errors="replace").read()
    print(f"\n{'=' * 78}\n=== /pdufa/{slug}")
    for m in re.finditer(r"2026-12-31|Dec 31,? 2026", d):
        s = max(0, m.start() - 90)
        print("   ..." + d[s:m.end() + 70].replace("\n", " ") + "...")
