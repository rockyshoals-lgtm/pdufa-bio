# -*- coding: utf-8 -*-
import io, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = io.open("pdufa_site_src/drug/inluriyo/index.html", encoding="utf-8", errors="replace").read()
print("-- decision rows listed on /drug/inluriyo --")
for m in re.finditer(r'href="(/fda-decision/[^"]+)"[^>]*>(.*?)</a>', d, re.S):
    print("   ", m.group(1), "|", re.sub(r"<[^>]+>", " ", m.group(2))[:110].strip())
print("\n-- catalyst-history block --")
i = d.find("Catalyst history")
print(re.sub(r"<[^>]+>", " ", d[i:i + 900])[:800])

print("\n-- was it 1 before my change? --")
out = subprocess.run(["git", "show", "HEAD:pdufa_site_src/drug/inluriyo/index.html"],
                     capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
m = re.search(r"(\d+) FDA decisions? on record", out)
print("   HEAD said:", m.group(0) if m else "?")
for mm in re.finditer(r'href="(/fda-decision/[^"]+)"', out):
    print("     HEAD row:", mm.group(1))
