# -*- coding: utf-8 -*-
"""Where do /pdufa/CELC, /pdufa/VERA and /pricing come from, and what should they be?"""
import io, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = "pdufa_site_src"
s = io.open(f"{SITE}/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(s[s.find("["):])

for tk in ("CELC", "VERA", "LLY", "ANAB"):
    print(f"== {tk}")
    for r in rows:
        if str(r.get("t")).upper() == tk:
            print(f"   {r['id']:<30} {r.get('d')} {r.get('st'):<10} url={r.get('url')}")
    for cand in (f"{SITE}/pdufa/{tk}/index.html", f"{SITE}/ticker/{tk}/index.html"):
        print(f"   exists {cand.replace(SITE,''):<28}", os.path.isfile(cand))

print("\n== who links /pricing ==")
n = 0
for root, dirs, files in os.walk(SITE):
    if "index.html" not in files:
        continue
    p = os.path.join(root, "index.html")
    t = io.open(p, encoding="utf-8", errors="replace").read()
    if 'href="/pricing"' in t:
        n += 1
        if n <= 6:
            print("   ", os.path.relpath(p, SITE).replace("\\", "/"))
print("   total pages linking /pricing:", n)
print("   /pricing exists:", os.path.isfile(f"{SITE}/pricing/index.html"))
for alt in ("developers", "api", "pro"):
    print(f"   /{alt} exists:", os.path.isfile(f"{SITE}/{alt}/index.html"))
