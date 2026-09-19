# -*- coding: utf-8 -*-
"""The four pages the audit's list of twelve did not include. Are they duplicates or wrong?"""
import io
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

for slug in ("ABBV-tavapadon", "ABBV-tavapadon-2", "NVO-am833", "NVO-cagrisema",
             "MRK-trodelvy", "GILD-trodelvy", "NVO-mim8"):
    p = f"pdufa_site_src/pdufa/{slug}/index.html"
    try:
        d = io.open(p, encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        print(f"{slug:<22} MISSING")
        continue
    ti = re.search(r"<title>(.*?)</title>", d, re.S)
    can = re.search(r'<link rel="canonical" href="([^"]+)"', d)
    rob = re.search(r'<meta name="robots" content="([^"]+)"', d)
    drug = re.search(r'<span>Drug / candidate</span><b>([^<]+)</b>', d)
    comp = re.search(r'<span>Company</span><b>([^<]+)</b>', d)
    print(f"\n{slug}")
    print(f"   title    : {(ti.group(1) if ti else '')[:76]}")
    print(f"   canonical: {can.group(1) if can else '(none)'}")
    print(f"   robots   : {rob.group(1) if rob else '(none)'}")
    print(f"   drug     : {drug.group(1) if drug else '?'}   company: "
          f"{comp.group(1) if comp else '?'}")
    print(f"   bytes    : {len(d)}")
