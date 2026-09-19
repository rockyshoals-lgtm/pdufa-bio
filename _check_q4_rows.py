# -*- coding: utf-8 -*-
"""What are the seven unmatched "Q4 2026 (est.)" rows on /calendar?

My new windowed-row census flagged them. They pre-date today's change, so before I decide how
the guard should treat them I need to know whether they are (a) real events my check is looking
for under the wrong type, or (b) orphaned rows of the HOOK/CRBP/NCNA kind. Print the row, then
every dataset event for that ticker.
"""
import io
import json
import re

SITE = "pdufa_site_src"
src = io.open(f"{SITE}/api/v1/dataset.mjs", encoding="utf-8",
              errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
doc = io.open(f"{SITE}/calendar/index.html", encoding="utf-8", errors="replace").read()

W = re.compile(r'<a class="row"([^>]*)>\s*<div class="t">([A-Z]{1,6}) (?:&middot;|·) '
               r'(Q[1-4] \d{4})[^<]*</div>.*?<div class="d">(.*?)</div>', re.S)

for attrs, tk, lab, txt in (m.groups() for m in W.finditer(doc)):
    clean = re.sub(r"<[^>]+>", "", txt).strip()
    href = re.search(r'href="([^"]+)"', attrs)
    print(f"\n=== {tk}  {lab}  |  {clean}  |  {href.group(1) if href else '(no href)'}")
    for r in rows:
        if str(r.get("t") or "").upper() != tk:
            continue
        print(f"     dataset: {r.get('type'):<11} d={r.get('d')} dp={r.get('dp')} "
              f"dm={r.get('dm')} st={r.get('st')} | {str(r.get('name'))[:46]}")
