# -*- coding: utf-8 -*-
"""inject_month_crosslinks.py -- a month's PDUFA page and its readout page link each other (OMW, 2026-11-27).

/calendar/<year>/<month> lists the FDA goal dates in a month and /readouts/<year>/<month> lists the trial readouts
in it, but neither led to the other: a reader planning December saw half of its catalysts. This writes one
marker-bounded line (<!--MXL:BEGIN--> ... <!--MXL:END-->) right under each page's month-to-month links
(<div class="pn">), pointing at the other kind of page for the same month, only when that page exists and is
indexable. A page whose twin is missing or noindex loses the line. Idempotent; run after every generator that
writes either kind of month page (build_readout_months.py, retitle_calendar_months.py), before inject_site_links.py.

    python inject_month_crosslinks.py [--site DIR]
"""
import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--MXL:BEGIN-->", "<!--MXL:END-->"
BLOCK = re.compile(re.escape(B) + r".*?" + re.escape(E), re.S)
PN = re.compile(r'<div class="pn">.*?</div>', re.S)
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
TWIN = {"calendar": ("readouts", "Clinical-trial readouts"), "readouts": ("calendar", "FDA PDUFA dates")}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def indexable(site, *parts):
    p = os.path.join(site, *parts, "index.html")
    if not os.path.isfile(p):
        return False
    head = io.open(p, encoding="utf-8", errors="replace").read(6000)
    return not re.search(r'<meta name="robots" content="[^"]*noindex', head)


def block(site, kind, y, m):
    other, words = TWIN[kind]
    if not indexable(site, other, y, m):
        return ""
    return (B + f'<p class="note" style="margin:6px 0 12px;color:#94a9c9;font-size:13px;line-height:1.5">Same month: <a href="/{other}/{y}/{m}">{words} in '
            f'{m.capitalize()} {y}</a></p>' + E)


def apply(doc, blk):
    doc = BLOCK.sub("", doc)
    if not blk:
        return doc
    pn = PN.search(doc)
    return doc[:pn.end()] + blk + doc[pn.end():] if pn else doc


def pages(site):
    for kind in TWIN:
        root = os.path.join(site, kind)
        for y in sorted(os.listdir(root)) if os.path.isdir(root) else []:
            if not re.match(r"^\d{4}$", y) or not os.path.isdir(os.path.join(root, y)):
                continue
            for m in MONTHS:
                p = os.path.join(root, y, m, "index.html")
                if os.path.isfile(p):
                    yield kind, y, m, p


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=SITE)
    a = ap.parse_args(argv)
    n = n_with = 0
    for kind, y, m, p in pages(a.site):
        doc = io.open(p, encoding="utf-8").read()
        new = apply(doc, block(a.site, kind, y, m))
        n_with += B in new
        if new != doc:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
            n += 1
    print(f"month cross-links: {n} page(s) changed; {n_with} link the same month's other catalyst page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
