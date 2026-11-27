# -*- coding: utf-8 -*-
"""inject_drug_month_links.py -- a drug page links the month pages for the dates it lists (OMW, 2026-11-27).

A drug page's "Catalyst history" lists its readout and PDUFA dates, but nothing led from "Readout, Dec 2026" to
/readouts/2026/december or from "PDUFA, Feb 2027" to /calendar/2027/february, the pages that show what else lands
that month. This writes one marker-bounded line (<!--MLINK:BEGIN--> ... <!--MLINK:END-->) right after the page's
catalyst rows, built from those rows' own labels:

  * a Readout row dated to a day or a month links /readouts/<year>/<month>;
  * a PDUFA row dated to a day or a month links /calendar/<year>/<month>;

each only when that month page exists and is indexable. Quarter and year dates link nothing (a quarter is not a
month). A page whose rows give no such month loses the line. Idempotent; run after build_drug_pages.py and
build_readout_months.py.

    python inject_drug_month_links.py [--site DIR]
"""
import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--MLINK:BEGIN-->", "<!--MLINK:END-->"
BLOCK = re.compile(re.escape(B) + r".*?" + re.escape(E), re.S)
HEAD = "<h2>Catalyst history</h2>"
ROW = re.compile(r'<a class="row"[^>]*><span class="t">(Readout|PDUFA) &middot; '
                 r'([A-Z][a-z]{2}) (?:\d{1,2}, )?(\d{4})</span>.*?</a>', re.S)
ROWS = re.compile(r'(?:<a class="row"[^>]*>.*?</a>)+', re.S)
MON3 = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
BASE = {"Readout": ("readouts", "readouts in"), "PDUFA": ("calendar", "PDUFA dates in")}

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


def rows_span(doc):
    """(start, end) of the catalyst rows right after the Catalyst history heading, or None."""
    i = doc.find(HEAD)
    if i < 0:
        return None
    j = i + len(HEAD)
    m = ROWS.match(doc, j)
    return (j, m.end()) if m else None


def block(doc, site):
    sp = rows_span(doc)
    if not sp:
        return ""
    seen, links = set(), []
    for kind, mon, y in ROW.findall(doc[sp[0]:sp[1]]):
        if mon not in MON3:
            continue
        m = MON3.index(mon)
        base, words = BASE[kind]
        key = (base, y, m)
        if key in seen:
            continue
        seen.add(key)
        if indexable(site, base, y, MONTHS[m].lower()):
            links.append((y, m, base, f'<a href="/{base}/{y}/{MONTHS[m].lower()}">{words} {MONTHS[m]} {y}</a>'))
    if not links:
        return ""
    links.sort(key=lambda t: (t[0], t[1], t[2]))
    return (B + '<p class="note" style="margin:8px 0 14px;color:#94a9c9;font-size:13px;line-height:1.5">Other catalysts the same month: '
            + " &middot; ".join(t[3] for t in links) + "</p>" + E)


def apply(doc, site):
    doc = BLOCK.sub("", doc)
    blk = block(doc, site)
    if not blk:
        return doc
    sp = rows_span(doc)
    return doc[:sp[1]] + blk + doc[sp[1]:]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=SITE)
    a = ap.parse_args(argv)
    root = os.path.join(a.site, "drug")
    n = n_with = 0
    for slug in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        p = os.path.join(root, slug, "index.html")
        if not os.path.isfile(p):
            continue
        doc = io.open(p, encoding="utf-8").read()
        new = apply(doc, a.site)
        n_with += B in new
        if new != doc:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
            n += 1
    print(f"drug month links: {n} page(s) changed; {n_with} link a readout or PDUFA month page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
