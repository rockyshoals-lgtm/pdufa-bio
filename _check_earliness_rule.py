# -*- coding: utf-8 -*-
"""Is my earliness_allowed rule consistent with the STATISTIC's own inclusion rule?

build_early_decisions.collect() includes a decision when the goal date is dp == "day" and the
decision page links a primary source. It does NOT require `_d.source_url` on the dataset row --
most rows simply have not had that field back-filled yet.

My earliness_allowed additionally demanded `_d.source_url`, which is stricter. If that blocks
rows the statistic counts, I have created a NEW cross-surface disagreement while fixing one:
the study would say REGN was 12 days early and REGN's own page would refuse to say it.
"""
import io
import json
import sys

sys.path.insert(0, ".")
from site_windows import earliness_allowed  # noqa: E402

src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8",
              errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])

dec = [r for r in rows if r.get("type") == "PDUFA"
       and str(r.get("st") or "").lower() == "decided"]
print(f"decided PDUFA rows: {len(dec)}")
day = [r for r in dec if str(r.get("dp") or "day") == "day"]
srcd = [r for r in day if (r.get("_d") or {}).get("source_url")]
print(f"  day-precision              : {len(day)}")
print(f"  ...of which have source_url: {len(srcd)}")
print(f"  blocked by my current rule but day-precision: {len(day) - len(srcd)}")
print()
for r in day:
    if not earliness_allowed(r):
        print(f"   WOULD BLOCK {r.get('t'):<6} goal={r.get('d')} dcd={r.get('dcd')} "
              f"dp={r.get('dp')} src=- | {str(r.get('name'))[:40]}")
