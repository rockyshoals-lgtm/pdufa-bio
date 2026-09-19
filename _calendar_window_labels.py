# -*- coding: utf-8 -*-
"""What window labels does the calendar actually render? The event pages must match these."""
import glob
import io
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROW = re.compile(r'<div class="t">([A-Z]{1,6}) (?:&middot;|·) ([^<]+)</div>'
                 r'<div class="d">(.*?)</div>', re.S)

seen = {}
for p in ["pdufa_site_src/calendar/index.html"] + \
        glob.glob("pdufa_site_src/calendar/2026/*/index.html"):
    d = io.open(p, encoding="utf-8", errors="replace").read()
    for m in ROW.finditer(d):
        tk, lab = m.group(1), m.group(2).strip()
        txt = re.sub(r"<[^>]+>", "", m.group(3))[:44]
        if re.match(r"^\d{4}-\d{2}-\d{2}", lab):
            continue
        seen.setdefault(lab, []).append(f"{tk}  {txt}")

for lab, v in sorted(seen.items()):
    print(f"{lab!r}  x{len(v)}")
    for x in v[:8]:
        print(f"      {x}")
