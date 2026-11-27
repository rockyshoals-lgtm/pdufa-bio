# -*- coding: utf-8 -*-
"""/crl letter tables read as cards on a phone.

2026-11-27 phone pass: at 375-500px the six-column letter table on /crl scrolled sideways, and the column a reader
came for (the sections each letter addresses) sat off the right edge of the screen. build_crl_hub.py now gives each
cell a class (dt co ap lk sc ds) and a phone rule lays each row out as a small card by those classes. A row whose
cells lose their classes would fall back to an unlabelled stack, so this checks every row of every letter table:

  - the table is class "crlt" and the page carries the phone rule for it;
  - each data row has exactly six cells, classed dt, co, ap, lk, sc, ds in that order;
  - a sections cell marked empty ("nos") shows no sections, and one not marked shows some;
  - a decision cell marked empty ("noour") has no link, and one not marked links a /fda-decision/ page.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, "pdufa_site_src", "crl", "index.html")
ORDER = ["dt", "co", "ap", "lk", "sc", "ds"]


def check(html):
    bad = []
    if "@media(max-width:640px){table.crlt" not in html:
        bad.append("the phone rule for table.crlt is missing")
    tables = re.findall(r'<table class="crlt">(.*?)</table>', html, re.S)
    if len(tables) < 10:
        bad.append(f"only {len(tables)} letter tables classed crlt (one per year expected)")
    rows = 0
    for t in tables:
        for tr in re.findall(r"<tr>(.*?)</tr>", t, re.S):
            if "<th" in tr:
                continue
            rows += 1
            cells = re.findall(r'<td(?: class="([^"]*)")?[^>]*>(.*?)</td>', tr, re.S)
            cls = [(c or "").split() for c, _ in cells]
            if [c[0] if c else "" for c in cls] != ORDER:
                bad.append(f"row cells classed {[' '.join(c) for c in cls]}: {re.sub('<[^>]+>', ' ', tr)[:90]}")
                continue
            sc, ds = cells[4], cells[5]
            secs_empty = re.sub(r"<[^>]+>|&middot;|\s", "", sc[1]) == ""
            if ("nos" in sc[0].split()) != secs_empty:
                bad.append(f"sections cell marked {sc[0]!r} but reads {sc[1][:40]!r}")
            has_link = "/fda-decision/" in ds[1]
            if ("noour" in ds[0].split()) == has_link:
                bad.append(f"decision cell marked {ds[0]!r} but reads {ds[1][:60]!r}")
    if rows < 100:
        bad.append(f"only {rows} letter rows found")
    return bad, rows


def main():
    if not os.path.exists(PAGE):
        print("SKIP: /crl not built")
        return 0
    bad, rows = check(io.open(PAGE, encoding="utf-8").read())
    # planted cases: the old unclassed row, and a row whose empty mark lies
    planted_old = ('@media(max-width:640px){table.crlt}' + '<table class="crlt"><tr><th>Date</th></tr>'
                   '<tr><td class="dt">Nov 20, 2026</td><td>Capricor, Inc.</td><td>BL 125842</td><td>x</td>'
                   '<td style="font-size:12.5px">&middot;</td><td><a href="/fda-decision/CAPR-2026-11-20">d</a></td></tr>'
                   '</table>' * 1)
    pb, _ = check(planted_old * 1)
    if not any("row cells classed" in b for b in pb):
        bad.append("planted unclassed row was not caught")
    planted_lie = ('<table class="crlt"><tr><td class="dt">a</td><td class="co">b</td><td class="ap">c</td>'
                   '<td class="lk">d</td><td class="sc nos">Clinical</td><td class="ds">n/a</td></tr></table>')
    pb, _ = check(planted_lie)
    if not (any("sections cell" in b for b in pb) and any("decision cell" in b for b in pb)):
        bad.append("planted mislabelled empty cells were not caught")
    if bad:
        print("FAIL test_crl_hub_phone_rows:")
        for b in bad[:20]:
            print("  -", b)
        return 1
    print(f"PASS test_crl_hub_phone_rows: {rows} letter rows classed for the phone layout")
    return 0


if __name__ == "__main__":
    sys.exit(main())
