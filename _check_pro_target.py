# -*- coding: utf-8 -*-
import io, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = io.open("pdufa_site_src/developers/index.html", encoding="utf-8", errors="replace").read()
print("== /developers anchors ==")
for m in re.finditer(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', d, re.S):
    print("   #%-16s %s" % (m.group(1), re.sub(r"<[^>]+>", " ", m.group(2)).strip()[:60]))
i = d.find("Pro:")
print("\n== the Pro block ==")
print(re.sub(r"<[^>]+>", " ", d[max(0, i - 150): i + 700]).strip()[:620])

print("\n== /pdufa/LLY ==")
t = io.open("pdufa_site_src/pdufa/LLY/index.html", encoding="utf-8", errors="replace").read()
print("   title:", re.search(r"<title>(.*?)</title>", t, re.S).group(1)[:90])
kv = re.search(r"PDUFA target date</span><b>([^<]+)</b>", t)
print("   target fact:", kv.group(1) if kv else "-")
print("   robots:", (re.search(r'name="robots" content="([^"]+)"', t) or [None, "-"])[1])
