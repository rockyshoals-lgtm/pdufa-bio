# -*- coding: utf-8 -*-
import io, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = "pdufa_site_src"

print("== the remaining /pricing occurrence on /developers ==")
t = io.open(f"{SITE}/developers/index.html", encoding="utf-8", errors="replace").read()
for m in re.finditer(r"/pricing", t):
    print("   ...", re.sub(r"\s+", " ", t[max(0, m.start() - 170): m.end() + 120]))

print("\n== dead /fda-decision targets, and what DOES exist for that ticker ==")
have = sorted(d for d in os.listdir(f"{SITE}/fda-decision")
              if os.path.isfile(f"{SITE}/fda-decision/{d}/index.html"))
for dead in ("AZN-2026-06-30", "GSK-2026-06-18", "SPRO-2026-06-18", "VRDN-2026-06-29", "VRDN-2026-06-30"):
    tk = dead.split("-")[0]
    near = [h for h in have if h.startswith(tk + "-")]
    print(f"   {dead:<22} existing {tk} pages: {near}")

print("\n== how the approvals listing links them ==")
a = io.open(f"{SITE}/decisions/approvals/index.html", encoding="utf-8", errors="replace").read()
for dead in ("AZN-2026-06-30", "GSK-2026-06-18", "SPRO-2026-06-18", "VRDN-2026-06-29", "VRDN-2026-06-30"):
    m = re.search(r'<a[^>]*href="/fda-decision/' + dead + r'"[^>]*>(.*?)</a>', a, re.S)
    print(f"   {dead}: {re.sub(r'<[^>]+>', ' ', m.group(1))[:120].strip() if m else 'link shape not matched'}")
