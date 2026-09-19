# -*- coding: utf-8 -*-
"""How complete is the therapeutic-area tagging, and what are the far-out rare rows?

"37 oncology readouts" reads as a complete count. It is not: 130 readout rows are tagged
"Other" and 62 carry no tag at all, so anything selected on `ta` under-counts by an unknown
amount. A page that states an n without stating that is quietly overclaiming, which is the same
family of defect as everything else this week.
"""
import collections
import datetime as dt
import io
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8",
              errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
today = dt.date.today().isoformat()

fwd = [r for r in rows if r.get("type") == "Readout"
       and str(r.get("st") or "") in ("Guided", "Estimated")
       and str(r.get("d") or "") >= today]
print(f"forward readouts: {len(fwd)}")
c = collections.Counter(str(r.get("ta") or "(untagged)").strip() or "(untagged)" for r in fwd)
for ta, n in c.most_common():
    print(f"   {ta:<28} {n}")
untagged = sum(v for k, v in c.items() if k in ("(untagged)", "Other"))
print(f"\nuntagged or 'Other': {untagged} of {len(fwd)} "
      f"({untagged / max(1, len(fwd)):.0%})")

print("\nrare-disease rows and their dates:")
for r in sorted((r for r in fwd if str(r.get("ta") or "").strip().lower()
                 in ("rare disease", "rare")), key=lambda r: str(r.get("d"))):
    dd = r.get("_d") or {}
    print(f"   {r.get('t'):<6} {r.get('d')} dp={str(r.get('dp')):<8} st={r.get('st'):<10} "
          f"| {str(r.get('name'))[:40]} | {str(dd.get('indication'))[:36]}")

print("\noncology rows beyond 2027:")
for r in sorted((r for r in fwd if str(r.get("ta") or "").strip().lower() == "oncology"
                 and str(r.get("d")) > "2027-12-31"), key=lambda r: str(r.get("d"))):
    print(f"   {r.get('t'):<6} {r.get('d')} | {str(r.get('name'))[:44]}")
