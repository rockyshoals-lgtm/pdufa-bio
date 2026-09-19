# -*- coding: utf-8 -*-
"""09-19: put the frozen nav's Pro entry back to /pricing and record the revert in the freeze file."""
import io, json, os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, "_nav_frozen_until_2027.json")
j = json.load(io.open(F, encoding="utf-8"))
j["pro"] = ["/pricing", "Pro"]
j.setdefault("changes", []).append({
    "date": "2026-09-19",
    "what": "PRO target /developers#tiers -> /pricing (REVERT of the 2026-09-18 change)",
    "why": "The 09-18 change was made on a false premise. /pricing has been live throughout: "
           "pdufa_site_src/vercel.json rewrites /pricing to /pricing.html (and redirects "
           "/pricing.html and /pricing-elite to it). The dead-link guard resolved only "
           "<path>/index.html and never read the routing table. The nav is restored exactly as "
           "frozen on 2026-08-29; the guard and fixer now resolve through site_routes.py."})
io.open(F, "w", encoding="utf-8").write(json.dumps(j, indent=1, ensure_ascii=False) + "\n")
print("freeze file: pro ->", j["pro"])
r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "fix_dead_internal_links.py")],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout[-1500:]); print(r.stderr[-800:])
