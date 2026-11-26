# -*- coding: utf-8 -*-
"""test_screener_drug_links.py -- /screener's crawlable rows send a drug-name reader to that drug's page.

GSC 2026-11-26: /screener drew 383 impressions at position 6.6 with no click, all on drug-name queries
("donidalorsen", "abcl635", "eyp-1901"). Each of those drugs has a /drug page, but the readout rows printed the
name as plain text. This fails if:
  1. a server-rendered row with no page of its own leaves its drug unlinked although readout_links.drug_page
     finds a page for it (the link is the fix);
  2. a /drug link in the rows points at a page that is not on disk, or at a drug page that never names the
     row's company (a shared first word landing on another company's drug);
  3. the workflow stops running build_screener_rows.py after build_drug_pages.py (a link to a page the build
     removed would ship for a day).
PLANT=nolink strips the drug links from the page under test; PLANT=noworkflow drops the second pass. Both FAIL.

    python tests/test_screener_drug_links.py
"""
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
from readout_links import drug_page  # noqa: E402
from build_screener_rows import esc  # noqa: E402


def main():
    plant = os.environ.get("PLANT", "")
    doc = open(os.path.join(SITE, "screener", "index.html"), encoding="utf-8", errors="replace").read()
    m = re.search(r"<!--ssr-rows-->(.*?)<!--/ssr-rows-->", doc, re.S)
    if not m:
        print("FAIL /screener: no server-rendered rows block")
        return 1
    block = m.group(1)
    if plant == "nolink":
        block = re.sub(r'<a href="/drug/[^"]+">([^<]*)</a>', r"\1", block)
    wf = open(os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml"), encoding="utf-8").read()
    if plant == "noworkflow":
        wf = wf.replace('run: python build_screener_rows.py\n', "run: true\n")

    src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.JSONDecoder().raw_decode(src[src.find("["):])[0]
    by_key = {}
    for r in rows:
        by_key.setdefault((str(r.get("t") or ""), esc(r.get("name") or "")[:52]), r)

    bad, linked = [], 0
    for tr in re.findall(r"<tr>(.*?)</tr>", block, re.S):
        cells = re.findall(r"<td>(.*?)</td>", tr, re.S)
        if len(cells) != 5:
            continue
        tk = re.sub(r"<[^>]+>", "", cells[0])
        cell = cells[3]
        a = re.match(r'<a href="([^"]+)">(.*)</a>$', cell, re.S)
        if a and a.group(1).startswith("/drug/"):
            linked += 1
            u = a.group(1)
            p = os.path.join(SITE, *u.strip("/").split("/"), "index.html")
            if not os.path.isfile(p):
                bad.append(f"{tk}: {u} is not a built page")
            elif f'href="/ticker/{tk}"' not in open(p, encoding="utf-8", errors="replace").read():
                bad.append(f"{tk}: {u} never names {tk}")
        elif not a:
            r = by_key.get((tk, cell))
            if r is not None and drug_page(r):
                bad.append(f"{tk}: '{cell[:40]}' is plain text but {drug_page(r)} exists")

    steps = re.findall(r"run: python (build_drug_pages|build_screener_rows)\.py", wf)
    if "build_drug_pages" not in steps or "build_screener_rows" not in steps[steps.index("build_drug_pages"):]:
        bad.append("workflow: build_screener_rows.py no longer runs after build_drug_pages.py")

    print(f"screener drug links: {linked} row(s) link a /drug page")
    if bad:
        print(f"FAIL: {len(bad)} problem(s)")
        for b in bad[:15]:
            print("  " + b)
        return 1
    print("  PASS: every row with a drug page links it, each link is built and names the row's company")
    return 0


if __name__ == "__main__":
    sys.exit(main())
