# -*- coding: utf-8 -*-
"""fix_calendar_row_labels.py -- a pending calendar row says what the application is, on every calendar page.

Round-4 audit 2026-11-21: Bing Copilot cites /calendar/2026/december as its main source for December PDUFA dates, and
that page's month rows were written by a different generator from the /calendar hub's. Three pending rows read wrong:
  /pdufa/COGT-bezuclastinib-summit (Dec 30) said "CGT9486: Advanced Gastrointestinal Stromal Tumors". The Dec 30 goal
    is the SUMMIT application in nonadvanced systemic mastocytosis; GIST is the separate Nov 30 PEAK application
    (Cogent 8-K, August 10, 2026). Copilot repeated the GIST label.
  /pdufa/VRTX-povetacicept (Nov 30) said "Lupus nephritis, IgA nephropathy" on the hub; the BLA is IgAN only (Vertex
    8-K, August 3, 2026).
  /pdufa/MLYS-lorundrostat (Dec 22) said "lorundrostat Dose 1" on the month page.
Labels come from `_calendar_row_labels.json` (hand-verified, each with its source). Only PENDING rows are touched: a
decided row (data-dec="1") is written by the decided-row markers. Idempotent; run after every calendar row writer.
"""
import glob
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")


def main():
    try:
        labels = json.load(io.open(os.path.join(HERE, "_calendar_row_labels.json"), encoding="utf-8"))["labels"]
    except Exception as ex:
        print(f"calendar row labels: no ledger ({ex})")
        return 0
    n = 0
    pages = [os.path.join(SITE, "calendar", "index.html")] + glob.glob(
        os.path.join(SITE, "calendar", "20[0-9][0-9]", "*", "index.html"))
    for p in pages:
        if not os.path.isfile(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        new = doc
        for x in labels:
            lab = html.escape(x["label"], quote=False)
            rx = re.compile(r'(<a class="row" href="' + re.escape(x["href"]) + r'">\s*<div class="t">[^<]*</div>'
                            r'<div class="d">)([^<]*)')
            new = rx.sub(lambda m: m.group(1) + lab, new)
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
            n += 1
            print(f"  {os.path.relpath(p, SITE)}: row labels set from the ledger")
    print(f"calendar row labels: {n} page(s) written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
