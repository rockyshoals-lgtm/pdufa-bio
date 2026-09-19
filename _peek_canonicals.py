# -*- coding: utf-8 -*-
import io, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for s in ("ABBV-tavapadon", "ABBV-tavapadon-2", "NVO-am833", "NVO-cagrisema", "MRK-trodelvy", "GILD-trodelvy"):
    t = io.open(f"pdufa_site_src/pdufa/{s}/index.html", encoding="utf-8").read()
    c = re.search(r'<link rel="canonical" href="([^"]+)"', t)
    ti = re.search(r"<title>(.*?)</title>", t, re.S)
    rb = re.search(r'<meta name="robots" content="([^"]+)"', t)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S)
    print(s, "| canonical:", c.group(1) if c else None, "| robots:", rb.group(1) if rb else None)
    print("    title:", (ti.group(1) if ti else "")[:90])
    print("    h1   :", re.sub(r"<[^>]+>", "", h1.group(1) if h1 else "")[:90])
