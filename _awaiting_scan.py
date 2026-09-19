# -*- coding: utf-8 -*-
"""Every event whose date has PASSED but which still carries no outcome.

These are the site's worst rows: a countdown that has run out. /api/v1 relabels them "Awaiting",
which is honest, but each one is either a decision we missed or a date that was wrong.
"""
import datetime as dt
import io
import json

TODAY = dt.date.today().isoformat()
src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8",
              errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])

print(f"today {TODAY}\n")
for typ in ("PDUFA", "Readout", "AdComm", "Conference"):
    late = []
    for r in rows:
        if r.get("type") != typ:
            continue
        if str(r.get("st") or "") in ("Decided", "Reported", "Ended", "Held"):
            continue
        d = str(r.get("d") or "")
        if not d or d >= TODAY:
            continue
        late.append(r)
    late.sort(key=lambda r: str(r.get("d")))
    print(f"=== {typ}: {len(late)} past-dated with no outcome")
    for r in late[:25]:
        dd = r.get("_d") or {}
        age = (dt.date.fromisoformat(TODAY) - dt.date.fromisoformat(str(r.get("d")))).days
        print(f"   {r.get('t'):<6} {r.get('d')}  dp={str(r.get('dp')):<7} st={str(r.get('st')):<10}"
              f" {age:>4}d ago  src={'Y' if dd.get('source_url') else '-'}  "
              f"{str(r.get('name'))[:44]}")
    if len(late) > 25:
        print(f"   ... and {len(late) - 25} more")
    print()
