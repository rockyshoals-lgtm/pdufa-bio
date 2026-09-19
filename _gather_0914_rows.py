# -*- coding: utf-8 -*-
"""Show exactly what our dataset holds for the rows about to be marked Decided.

Whether each GOAL date is sourced decides whether the decision may feed
/research/fda-decision-timing. A decision with a sourced goal is a real earliness measurement;
one with an unsourced goal is not, and must not enter that statistic (the 09-10 lesson).
"""
import io
import json

src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8",
              errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])

for tk, d in [("SRRK", "2026-09-30"), ("PHAR", "2026-10-24"), ("BFRI", "2026-09-28"),
              ("BAYRY", "2026-11-30")]:
    for r in rows:
        if str(r.get("t") or "").upper() != tk or str(r.get("d") or "") != d:
            continue
        dd = r.get("_d") or {}
        print(f"\n=== {tk} {d}  id={r.get('id')}")
        print(f"    name      : {r.get('name')}")
        print(f"    company   : {r.get('company')}   cap={r.get('cap')}  ta={r.get('ta')}")
        print(f"    dp={r.get('dp')}  st={r.get('st')}  url={r.get('url')}")
        print(f"    indication: {dd.get('indication')}")
        print(f"    source    : {dd.get('source')}")
        print(f"    source_url: {dd.get('source_url')}")
        print(f"    GOAL SOURCED: {'YES' if dd.get('source_url') else 'NO'}")
