# -*- coding: utf-8 -*-
import io, json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
s = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(s[s.find("["):])
for i in ("pdufa_gild_2026-08-27", "pdufa_bayry_2026-11-30"):
    r = next(x for x in rows if x["id"] == i)
    print(json.dumps(r, indent=1, ensure_ascii=False)[:2100])
    print("=" * 60)
