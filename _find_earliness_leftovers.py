# -*- coding: utf-8 -*-
"""Where exactly does each stale earliness figure still live on a decision page?"""
import io
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

for slug in ("BAYRY-2026-09-09", "PFE-2026-08-27", "IONS-2026-09-03"):
    p = f"pdufa_site_src/fda-decision/{slug}/index.html"
    d = io.open(p, encoding="utf-8", errors="replace").read()
    print(f"\n{'=' * 78}\n=== /fda-decision/{slug}")
    for m in re.finditer(r"\d+\s+[Dd]ays?\s+[Ee]arly|\d+\s+days before its", d):
        s = max(0, m.start() - 170)
        print("   ..." + d[s:m.end() + 90].replace("\n", " ") + "...")
        print()

# and the NVCR window-label disagreement
import json  # noqa: E402
src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8",
              errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
print(f"\n{'=' * 78}\n=== NVCR rows")
for r in rows:
    if str(r.get("t") or "").upper() == "NVCR":
        print(f"   {r.get('type')} d={r.get('d')} dp={r.get('dp')} dm={r.get('dm')} "
              f"st={r.get('st')} | {str(r.get('name'))[:44]}")
d = io.open("pdufa_site_src/pdufa/NVCR-ttfields-therapy/index.html",
            encoding="utf-8", errors="replace").read()
for m in re.finditer(r"November 2026 \(window\)", d):
    print("   page ..." + d[max(0, m.start() - 150):m.end() + 60].replace("\n", " ") + "...")
    break
