# -*- coding: utf-8 -*-
"""Read back the two new readout hubs."""
import io
import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

for s in ("oncology", "rare-disease"):
    p = f"pdufa_site_src/readouts/{s}/index.html"
    d = io.open(p, encoding="utf-8", errors="replace").read()
    t = re.search(r"<title>(.*?)</title>", d, re.S)
    de = re.search(r'<meta name="description" content="([^"]{0,200})', d)
    sub = re.search(r'<div class="sub">(.*?)</div>', d, re.S)
    ok = True
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', d, re.S):
        try:
            json.loads(b)
        except Exception as e:  # noqa: BLE001
            ok = False
            print("   JSON-LD BROKEN:", str(e)[:70])
    print(f"\n=== /readouts/{s}   {len(d)} bytes   jsonld_ok={ok}")
    print(f"  title: {(t.group(1) if t else '')[:95]}")
    print(f"  desc : {(de.group(1) if de else '')[:130]}")
    print(f"  sub  : {re.sub(r'<[^>]+>', ' ', sub.group(1))[:190] if sub else '?'}")
    print(f"  rows : {len(re.findall(r'<a class=.row.', d))}")
    fl = re.search(r"This is a floor[^<]{0,260}", re.sub(r"<[^>]+>", " ", d))
    print(f"  floor: {fl.group(0)[:230] if fl else 'MISSING'}")

d = io.open("pdufa_site_src/readouts/index.html", encoding="utf-8", errors="replace").read()
print(f"\n/readouts links both hubs: "
      f"{'/readouts/oncology' in d and '/readouts/rare-disease' in d}")
