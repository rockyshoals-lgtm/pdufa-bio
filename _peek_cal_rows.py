# -*- coding: utf-8 -*-
import io, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
t = io.open("pdufa_site_src/calendar/index.html", encoding="utf-8").read()
for tk in sys.argv[1:]:
    hits = [m.start() for m in re.finditer(rf"\b{tk}\b", t)]
    print(f"== {tk}: {len(hits)} mentions")
    for h in hits[:3]:
        seg = t[max(0, h - 200): h + 260]
        print("   links:", re.findall(r'href="([^"]+)"', seg))
        print("   text :", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", seg))[:300])
