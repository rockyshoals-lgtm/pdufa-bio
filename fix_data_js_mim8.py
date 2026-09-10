# -*- coding: utf-8 -*-
"""Move the NVO Mim8 slate entry to match the dataset's withdrawn date.

/calendar renders from the data.js SLATE; /api/v1/* serves dataset.mjs. On 2026-09-10 the
denecimig (Mim8) PDUFA lost its unsourced 2026-09-30 day and moved to year precision on the
2026-12-31 sentinel. The slate still said 2026-09-30, so the page would show an event the API
denies -- exactly what test_calendar_two_sources exists to catch.

The slate has no precision field, so it cannot express "sometime in 2026". Aligning its date to
the dataset's sentinel keeps the two sources telling the same story; the calendar ROW for it has
already been removed (a year-precision event has no honest month page), so the slate entry is
now data the page carries but does not render as a dated row.
"""
import io
import os
import re
import sys

SITE = "pdufa_site_src"
P = os.path.join(SITE, "api", "data.js")

src = io.open(P, encoding="utf-8", errors="replace").read()
orig = src

# the entry is a JS object literal; retarget only the one whose drug text names Mim8/denecimig
n = 0
for m in re.finditer(r"\{[^{}]*\}", src):
    seg = m.group(0)
    if not re.search(r"mim8|denecimig", seg, re.I):
        continue
    if "2026-09-30" not in seg:
        continue
    new = seg.replace("2026-09-30", "2026-12-31")
    src = src[:m.start()] + new + src[m.end():]
    n += 1
    print(f"  slate: NVO Mim8 2026-09-30 -> 2026-12-31")
    break

if src != orig:
    io.open(P, "w", encoding="utf-8").write(src)
print(f"{n} slate entry(ies) retargeted")
sys.exit(0)
