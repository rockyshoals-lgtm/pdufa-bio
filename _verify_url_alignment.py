# -*- coding: utf-8 -*-
import io, json, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
for r in rows:
    if r["type"] != "PDUFA" or r.get("st") != "Upcoming":
        continue
    u = str(r["url"])
    try:
        t = io.open(f"pdufa_site_src{u}/index.html", encoding="utf-8").read()
    except Exception:
        print(f"MISSING {r['id']} {u}"); continue
    ti = re.search(r"<title>(.*?)</title>", t, re.S)
    print(f"{r['id']:<28} {r['name'][:34]:<34} -> {u:<36} | {ti.group(1)[:60] if ti else '?'}")
