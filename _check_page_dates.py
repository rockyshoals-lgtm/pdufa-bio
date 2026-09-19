# -*- coding: utf-8 -*-
"""Every upcoming day-precision PDUFA row: does the page its url names state the row's date?"""
import io, json, re, sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
bad = 0
for r in rows:
    if r["type"] != "PDUFA" or r.get("st") != "Upcoming" or r.get("dp") != "day":
        continue
    p = f"pdufa_site_src{r['url']}/index.html"
    if not os.path.exists(p):
        print("MISSING", r["id"], r["url"]); continue
    t = io.open(p, encoding="utf-8", errors="replace").read()
    kv = re.search(r"PDUFA target date</span><b>([^<]+)</b>", t)
    sd = re.search(r'"startDate":"(\d{4}-\d{2}-\d{2})', t)
    ti = re.search(r"<title>(.*?)</title>", t, re.S)
    stated = {x for x in [kv.group(1) if kv else None, sd.group(1) if sd else None] if x}
    if stated and r["d"] not in stated:
        bad += 1
        print(f"XX {r['id']:<28} row={r['d']} page says {stated} | {r['url']} | {ti.group(1)[:60] if ti else ''}")
    elif not stated:
        print(f"?? {r['id']:<28} row={r['d']} page states no date kv | {r['url']} | {ti.group(1)[:60] if ti else ''}")
print("mismatches:", bad)
