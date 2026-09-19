# -*- coding: utf-8 -*-
"""Read back the rewritten event pages: strings, and JSON-LD that still parses."""
import io
import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

for slug in ("ABBV-tavapadon", "LLY", "NVO-mim8", "NVO-cagrisema", "MRK-trodelvy"):
    d = io.open(f"pdufa_site_src/pdufa/{slug}/index.html",
                encoding="utf-8", errors="replace").read()
    ti = re.search(r"<title>(.*?)</title>", d, re.S)
    de = re.search(r'<meta name="description" content="([^"]+)', d)
    kv = re.search(r"<span>FDA PDUFA target date</span><b>([^<]+)</b>", d)
    fq = re.search(r"The FDA PDUFA target date for [^<]{0,175}", d)
    ev = re.findall(r'"startDate":"([^"]*)","endDate":"([^"]*)"', d)
    bad = []
    n_ev = 0
    for blk in LD.findall(d):
        try:
            data = json.loads(blk)
        except Exception as e:  # noqa: BLE001
            bad.append(str(e)[:70])
            continue

        def count(node):
            global n_ev  # noqa: PLW0603
            if isinstance(node, dict):
                if node.get("@type") == "Event":
                    n_ev += 1
                for v in node.values():
                    count(v)
            elif isinstance(node, list):
                for v in node:
                    count(v)
        count(data)
    print(f"\n=== /pdufa/{slug}   jsonld_ok={not bad}  Event_nodes={n_ev}")
    if bad:
        print(f"    BROKEN: {bad}")
    print(f"  title: {(ti.group(1) if ti else '')[:80]}")
    print(f"  desc : {(de.group(1) if de else '')[:125]}")
    print(f"  kv   : {kv.group(1) if kv else '?'}")
    print(f"  event: {ev}")
    print(f"  faq  : {(fq.group(0) if fq else '?')[:155]}")
