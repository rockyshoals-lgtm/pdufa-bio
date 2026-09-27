# -*- coding: utf-8 -*-
"""CI guard: no decision page cites an aggregator as its source, and no dataset source field
points at one.

Audit 2026-09-26: /fda-decision/LNTH-2026-08-13's "primary source" was the Lantheus release as
re-hosted by StockTitan -- a page that does not support the August 13 date we print (the FDA's
letter does) and that sends a link to a competitor. /fda-decision/TRAW-2025-06-03 linked a
StockTitan copy of an SEC filing. Sources must be the FDA, EDGAR, or the sponsor.

    python tests/test_no_aggregator_sources.py
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
AGG = re.compile(r"https?://(?:www\.|[a-z]{2}\.)?(stocktitan\.net|rttnews\.com|seekingalpha\.com|investing\.com|"
                 r"finance\.yahoo\.com|benzinga\.com|gurufocus\.com|marketbeat\.com|fool\.com|zacks\.com|"
                 r"tipranks\.com|marketwatch\.com|marketscreener\.com|biopharmawatch\.com|webull\.com|"
                 r"bitget\.com|msn\.com|simianx\.ai|allsci\.com|biopharmcatalyst\.com)/", re.I)


def main():
    fails = []
    for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        for m in AGG.finditer(doc):
            fails.append(f"/fda-decision/{os.path.basename(os.path.dirname(p))}: links {m.group(1)}")
            break
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    for r in json.loads(src[src.index("["):src.rindex("]") + 1]):
        d = r.get("_d") or {}
        for k in ("source_url", "source_url_2", "decision_source_url", "announcement_url", "fda_action_source_url"):
            m = AGG.match(str(d.get(k) or ""))
            if m:
                fails.append(f"dataset {r['id']}._d.{k}: {m.group(1)}")
        m = AGG.match(str(r.get("url") or ""))
        if m:
            fails.append(f"dataset {r['id']}.url: {m.group(1)}")
    if fails:
        print(f"FAIL: {len(fails)} aggregator source(s) (cite the FDA, EDGAR or the sponsor instead):")
        for f in fails[:25]:
            print("   " + f)
        return 1
    print("OK -- no decision page or dataset source field cites an aggregator.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
