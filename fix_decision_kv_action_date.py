# -*- coding: utf-8 -*-
"""fix_decision_kv_action_date.py -- a decision page's key facts give the FDA's own action day, not the day it was announced.

2026-11-17 (David: "ensure everything is current"). build_decision_page.py already writes two rows when the FDA's
date and the public day differ ("FDA decision date" = the FDA's day, "Announced" = the public day), but only for
pages built after the FDA's record was known. Eight pages were built from the announcement and later gained the
FDA's day in their h1, title and Verified line, while key facts still showed the announcement day as the "FDA
decision date" (SMMT: h1 Nov 13, key facts 2026-11-15). Each FDA day was re-read at its source on 2026-11-17:
  ACHV  CRL NDA 218995 letter 06/20/2026          UNCY  CRL NDA 218607 letter 06/29/2026
  SMMT  CRL BLA 761524 letter 11/13/2026          TLX   NDA 218592 ORIG-1 AP 2026-09-11 (Drugs@FDA)
  MRK   NDA 220848 ORIG-1 AP 2026-07-15           MRK   BLA 761363 S-012/16/17 AP 2026-09-21
  MNKD  NDA 209988 S-007 AP 2026-07-23            VTRS  NDA 219990 ORIG-1 AP 2026-07-28

Rule: the FDA day comes ONLY from the page's own Verified line, and only when that line names a linked FDA record
for it (the line itself is written from _d.fda_action_date by inject_verified_against.py and guarded). The
announcement day kept is the one key facts already showed. Pages whose Verified line says the FDA day is not on
record are left to label_announcement_only_dates.py. Idempotent; facts only, not investment advice.
"""
import datetime as dt, glob, io, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
VF = re.compile(r'<!--VERIFIED:BEGIN-->.*?FDA action day ([A-Z][a-z]+ \d{1,2}, \d{4}) \(<a href="https://', re.S)
KV = re.compile(r'<div class="kv"><span>FDA decision date</span><b>(\d{4}-\d{2}-\d{2})</b></div>'
                r'(?!<div class="kv"><span>Announced</span>)')


def main():
    n = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        v, m = VF.search(doc), KV.search(doc)
        if not v or not m:
            continue
        fad = dt.datetime.strptime(v.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
        ann = m.group(1)
        if fad == ann or fad > ann:      # an announcement cannot precede the FDA's action
            continue
        new = (f'<div class="kv"><span>FDA decision date</span><b>{fad}</b></div>'
               f'<div class="kv"><span>Announced</span><b>{ann}</b></div>')
        doc = doc[:m.start()] + new + doc[m.end():]
        io.open(p, "w", encoding="utf-8", newline="").write(doc)
        n += 1
        print(f"  /fda-decision/{os.path.basename(os.path.dirname(p))}: key facts FDA decision date {ann} -> {fad} "
              f"(announced {ann})")
    print(f"decision key facts: {n} page(s) now give the FDA's own action day")


if __name__ == "__main__":
    main()
