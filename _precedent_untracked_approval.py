# -*- coding: utf-8 -*-
"""How does this site record an FDA approval it never carried as an upcoming PDUFA?"""
import io, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
s = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(s[s.find("["):])
dec = [r for r in rows if r["type"] == "PDUFA" and str(r.get("st")) == "Decided"]
print(f"{len(dec)} decided PDUFA rows")
print("\n-- decided rows where the goal date == the decision date (no separately sourced goal) --")
n = 0
for r in sorted(dec, key=lambda x: str(x.get("dcd"))):
    d, dcd = str(r.get("d") or ""), str(r.get("dcd") or "")
    if d and dcd and d == dcd:
        n += 1
        print(f"   {r['id']:<30} d={d} dcd={dcd} {str(r.get('name'))[:36]:<36} "
              f"src={'y' if (r.get('_d') or {}).get('source_url') else 'n'}")
print(f"   ({n} such rows)")
print("\n-- most recent 6 decided rows --")
for r in sorted(dec, key=lambda x: str(x.get("dcd")))[-6:]:
    print(f"   {r['id']:<30} goal={r.get('d')} decided={r.get('dcd')} oc={r.get('oc')} {str(r.get('name'))[:32]}")

arch = "pdufa_site_src/decisions/index.html"
t = io.open(arch, encoding="utf-8", errors="replace").read() if os.path.exists(arch) else ""
for p in ("daraxonrasib", "imlunestrant", "inluriyo", "camizestrant"):
    print(f"\n/decisions mentions {p}:", p in t.lower(),
          "| /fda-decision page:", [d for d in os.listdir("pdufa_site_src/fda-decision")
                                    if p[:6] in d.lower()][:3] if os.path.isdir("pdufa_site_src/fda-decision") else "?")
# RVMD daraxonrasib: tracked at all?
for r in rows:
    if "daraxonrasib" in (str(r.get("name")) + json.dumps(r.get("_d") or {})).lower():
        print("   daraxonrasib row:", r["id"], r["t"], r.get("d"), r.get("st"), r.get("dcd"))
