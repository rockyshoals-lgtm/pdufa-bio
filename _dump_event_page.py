# -*- coding: utf-8 -*-
"""Show every place a Dec-31 event page states the day, so the rewrite can be marker-precise."""
import io
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

for slug in ("ABBV-tavapadon", "LLY"):
    p = f"pdufa_site_src/pdufa/{slug}/index.html"
    d = io.open(p, encoding="utf-8", errors="replace").read()
    print(f"\n{'=' * 78}\n=== /pdufa/{slug}   ({len(d)} bytes)")
    for m in re.finditer(r"Dec(?:ember)? 31,? 2026|2026-12-31", d):
        s = max(0, m.start() - 150)
        seg = d[s:m.end() + 130].replace("\n", " ")
        print(f"  ...{seg}...")
        print()
