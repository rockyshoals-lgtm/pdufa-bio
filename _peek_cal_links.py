# -*- coding: utf-8 -*-
import io, re, sys, json, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
t = io.open("pdufa_site_src/calendar/index.html", encoding="utf-8").read()
src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
for r in rows:
    if r["type"] != "PDUFA" or r.get("st") != "Upcoming":
        continue
    u = str(r.get("url"))
    tk = r["t"]
    links = sorted(set(re.findall(rf'href="(/pdufa/{re.escape(tk)}[^"]*)"', t)))
    ok = u in links
    both = [l for l in links if os.path.exists(f"pdufa_site_src{l}/index.html")]
    print(f"{'ok ' if ok else 'XX '}{r['id']:<30} api={u:<32} calendar={links}")
