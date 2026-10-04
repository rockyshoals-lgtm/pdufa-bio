# -*- coding: utf-8 -*-
"""CI guard: a decision page whose primary source is the FDA's own notice or letter does not
attribute the announcement to the sponsor.

Audit 2026-09-27 item 2: /fda-decision/MIRM-2026-09-25's meta description read "Atebrioz approval
was announced by the sponsor on September 25, 2026; the FDA action day is not stated ..." -- on a
page whose source is the FDA's CDER notice, posted four hours before the sponsor's release. The
template written for TLX (sponsor-only source) understated what we know, and the lifted sentence
described our method instead of the approval. Bing's answer box went to a site that led with
the fact.

For every decided PDUFA row whose decision_source_url is on fda.gov, the page's <title>, meta
description and og:description must not say "announced by the sponsor", and the description
must state the FDA fact ("the FDA announced its approval of", "was approved on", or a CRL
answer).

    python tests/test_fda_notice_pages_fact_first.py
"""
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
FACT = re.compile(r"the FDA announced its approval of|FDA announced its approval of|was approved on|was approved by the FDA on|"
                  r"received a Complete Response Letter", re.I)


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    fails, n = [], 0
    for r in rows:
        d = r.get("_d") or {}
        if r.get("type") != "PDUFA" or str(r.get("st", "")).lower() != "decided":
            continue
        if not re.match(r"https://(www\.)?fda\.gov/", str(d.get("decision_source_url") or "")):
            continue
        p = os.path.join(SITE, "fda-decision", f"{str(r['t']).upper()}-{r.get('dcd')}", "index.html")
        if not os.path.exists(p):
            continue
        n += 1
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        head = html.unescape(doc[:doc.find("</head>")])
        desc = (re.search(r'<meta name="description" content="([^"]*)"', head) or [None, ""])[1]
        if re.search(r"announced by the sponsor", head, re.I):
            fails.append(f"/fda-decision/{os.path.basename(os.path.dirname(p))}: title/meta says 'announced by the "
                         f"sponsor' but the source is the FDA's own notice")
        elif not FACT.search(desc):
            fails.append(f"/fda-decision/{os.path.basename(os.path.dirname(p))}: description does not state the FDA fact: {desc[:90]}")
    if fails:
        print(f"FAIL: {len(fails)} FDA-sourced decision page(s) not fact-first (run rewrite_decision_snippets.py):")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} decision page(s) sourced to an FDA notice/letter lead with the FDA's fact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
