# -*- coding: utf-8 -*-
import io
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

for s in ("CORT", "CORT-relacorilant"):
    d = io.open(f"pdufa_site_src/pdufa/{s}/index.html", encoding="utf-8", errors="replace").read()
    t = re.search(r"<title>(.*?)</title>", d, re.S)
    kv = re.search(r"<span>FDA (?:PDUFA target date|decision|goal date)</span><b>([^<]+)</b>", d)
    ind = re.search(r"<span>Indication</span><b>([^<]+)</b>", d)
    print(f"/pdufa/{s}")
    print(f"   title: {(t.group(1) if t else '?')[:90]}")
    print(f"   kv   : {kv.group(1) if kv else '?'}")
    print(f"   ind  : {ind.group(1)[:60] if ind else '?'}")
