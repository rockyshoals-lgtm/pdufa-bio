# -*- coding: utf-8 -*-
"""sync_calendar_row_ta.py -- a pending calendar row's therapeutic-area tag follows the dataset (2026-11-17 audit).

Calendar rows are written once ("Drug: Area", ensure_calendar_rows.row_html) and never re-rendered. When the
dataset's area was corrected later, the row kept the old one: /calendar/2026/december showed Corcept's GRACE
relacorilant (hypercortisolism) as "Infectious", while the dataset says "Endocrinology / Metabolic".

Only a pending day row is touched, only when exactly one dataset row has that ticker and date, and only when the
row's trailing ": X" is itself an area label used in the dataset (so a drug's own text after a colon is never
rewritten). Idempotent.
"""
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
ROW = re.compile(r'(<a class="row"(?![^>]*data-dec)[^>]*>\s*<div class="t">([A-Z]{1,6}) &middot; (\d{4}-\d{2}-\d{2})</div>'
                 r'\s*<div class="d">)([^<]*?): ([^<:]+)(</div>|<)')


def main():
    s = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(s[s.index("["):s.rindex("]") + 1])
    areas = {str(r.get("ta")).strip() for r in rows if r.get("ta")}
    by = {}
    for r in rows:
        if r.get("type") == "PDUFA" and r.get("st") in ("Upcoming", "Awaiting"):
            for t in str(r.get("t") or "").split("/"):
                by.setdefault((t.strip().upper(), str(r.get("d") or "")), []).append(r)
    n = 0
    for p in [os.path.join(SITE, "calendar", "index.html")] + sorted(glob.glob(os.path.join(SITE, "calendar", "20*", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()

        def fix(m):
            nonlocal n
            pre, tk, d, drug, area, tail = m.groups()
            rs = by.get((tk, d), [])
            want = str(rs[0].get("ta") or "").strip() if len(rs) == 1 else ""
            if area.strip() not in areas or not want or want == area.strip():
                return m.group(0)
            n += 1
            print(f"  {os.path.relpath(p, SITE)}: {tk} {d} area '{area.strip()}' -> '{want}'")
            return f"{pre}{drug}: {want}{tail}"

        new = ROW.sub(fix, doc)
        if new != doc:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"calendar row areas synced to the dataset: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
