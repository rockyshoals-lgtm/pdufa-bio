# -*- coding: utf-8 -*-
import io, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = "pdufa_site_src"
for slug in ("AZN-2026-06-12", "GSK-2026-06-17", "SPRO-2026-06-17", "VRDN-2026-06-26"):
    p = f"{SITE}/fda-decision/{slug}/index.html"
    t = io.open(p, encoding="utf-8", errors="replace").read()
    ti = re.search(r"<title>(.*?)</title>", t, re.S)
    print(f"{slug:<18} {ti.group(1)[:96] if ti else '?'}")
print("\n== who generates /decisions/approvals ==")
import subprocess
for f in sorted(os.listdir(".")):
    if f.endswith(".py"):
        try:
            s = io.open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "decisions/approvals" in s or '"approvals"' in s:
            print("   ", f)
