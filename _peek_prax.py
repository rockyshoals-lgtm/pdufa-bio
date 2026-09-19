# -*- coding: utf-8 -*-
import io, json, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
for r in rows:
    if r["t"] in ("PRAX", "COGT") and r["type"] == "PDUFA":
        print(json.dumps({k: v for k, v in r.items() if k != "_d"}, ensure_ascii=False))
        print("   _d:", json.dumps({k: v for k, v in (r.get("_d") or {}).items() if k in ("source", "source_url", "review", "date_note", "date_history", "indication")}, ensure_ascii=False)[:700])
for s in ("PRAX", "COGT"):
    t = io.open(f"pdufa_site_src/pdufa/{s}/index.html", encoding="utf-8").read()
    print(f"== /pdufa/{s}")
    for m in re.finditer(r"(Sep(?:tember)? 27,? 2026|2026-09-27|Dec(?:ember)? 27,? 2026|2026-12-27|Nov(?:ember)? 30,? 2026|2026-11-30|Dec(?:ember)? 30,? 2026|2026-12-30)", t):
        print("   ", m.group(1), "|", re.sub(r"<[^>]+>", " ", t[max(0, m.start()-120):m.end()+60]).replace("\n", " ")[:220])
