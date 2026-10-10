# -*- coding: utf-8 -*-
"""fix_chart_captions.py -- a run-up caption never calls the announcement day the FDA decision when the FDA acted
on a different day (audit 2026-10-04 P2).

JUVMO's chart said "FDA decision 9/28/26" and marked the chart "PDUFA 9/28/26"; the FDA's letter is dated
9/25 and AbbVie announced on 9/28. The chart is keyed on the announcement (the day the price could react),
which is fine; the caption must say so. For every decision page whose dataset row carries an fda_action_date
different from the page's day, the caption becomes "Announced m/d/yy (FDA action m/d/yy)." and the SVG label
"announced m/d/yy". build_decision_page.py writes new pages this way; this repairs the ones already out.

    python fix_chart_captions.py [--dry-run]
"""
import argparse
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")


def mdy(iso):
    y, m, d = iso.split("-")
    return f"{int(m)}/{int(d)}/{y[2:]}"


def pairs():
    """(ticker, page day, fda action day) for rows where the two differ."""
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    out = {}
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st") or "").lower() != "decided":
            continue
        fad = str((r.get("_d") or {}).get("fda_action_date") or "")[:10]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", fad):
            continue
        tk = str(r.get("t") or "").upper()
        for day in {str(r.get("dcd") or "")[:10], str(r.get("d") or "")[:10]}:
            if re.match(r"^\d{4}-\d{2}-\d{2}$", day) and day != fad:
                out[(tk, day)] = fad
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    n = 0
    for (tk, day), fad in sorted(pairs().items()):
        p = os.path.join(SITE, "fda-decision", f"{tk}-{day}", "index.html")
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        new = doc.replace(f"FDA decision {mdy(day)}. ", f"Announced {mdy(day)} (FDA action {mdy(fad)}). ")
        new = re.sub(r'(text-anchor="end">)PDUFA ' + re.escape(mdy(day)) + "<", r"\1announced " + mdy(day) + "<", new)
        if new != doc:
            n += 1
            print(f"  /fda-decision/{tk}-{day}: caption now names FDA action {fad}")
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"chart captions: {n} page(s) corrected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
