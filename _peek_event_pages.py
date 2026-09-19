# -*- coding: utf-8 -*-
import io, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for s in sys.argv[1:]:
    t = io.open(f"pdufa_site_src/pdufa/{s}/index.html", encoding="utf-8").read()
    ti = re.search(r"<title>(.*?)</title>", t, re.S)
    kv = re.search(r"PDUFA target date</span><b>([^<]+)</b>", t)
    sd = re.search(r'"startDate":"([^"]+)"', t)
    dr = re.search(r"Drug / candidate</span><b>([^<]+)</b>", t)
    rb = re.search(r'name="robots" content="([^"]+)"', t)
    print(f"/pdufa/{s:<30} {ti.group(1)[:62] if ti else '?':<64} kv={kv.group(1) if kv else '-':<12} sd={sd.group(1)[:10] if sd else '-':<11} drug={dr.group(1)[:30] if dr else '-'} robots={rb.group(1)[:7] if rb else '-'}")
