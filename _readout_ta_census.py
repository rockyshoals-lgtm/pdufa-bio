# -*- coding: utf-8 -*-
"""What do we actually hold for /readouts/oncology and /readouts/rare-disease?

Audit 09-14 item 7, promoted to highest-return: the two readout grounding queries went 28 -> 77
and 75 -> 102 citations in six days at 66.38% and 32.59% share, both answered off a generic hub.

Before building a page I need to know the page is BACKED: how many readout rows carry an
oncology / rare-disease therapeutic area, how many have a source, how many have an NCT id, and
what date precision they carry. A hub with nothing behind it would be the unbacked-Q4 mistake
in a new place.
"""
import collections
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
ro = [r for r in rows if r.get("type") == "Readout"]
print(f"readout rows: {len(ro)}")
print("therapeutic areas:")
for ta, n in collections.Counter(str(r.get("ta") or "(blank)") for r in ro).most_common(20):
    print(f"   {ta:<28} {n}")

print("\nstatus:", dict(collections.Counter(str(r.get("st")) for r in ro)))
print("precision:", dict(collections.Counter(str(r.get("dp")) for r in ro)))

ONC = {"oncology", "onc", "cancer"}
RARE_WORDS = ("rare", "orphan", "genetic", "gene therapy", "neuromuscular", "metabolic")


def is_onc(r):
    return str(r.get("ta") or "").strip().lower() in ONC


def is_rare(r):
    dd = r.get("_d") or {}
    blob = " ".join(str(x) for x in (r.get("ta"), r.get("name"), dd.get("indication"))).lower()
    return any(w in blob for w in RARE_WORDS)


for label, fn in (("ONCOLOGY", is_onc), ("RARE-DISEASE-ish", is_rare)):
    sel = [r for r in ro if fn(r)]
    fwd = [r for r in sel if str(r.get("st")) in ("Guided", "Estimated")]
    src_n = sum(1 for r in sel if (r.get("_d") or {}).get("source_url")
                or str(r.get("url") or "").startswith("http"))
    nct = sum(1 for r in sel
              if ((r.get("_d") or {}).get("nct_id")))
    print(f"\n=== {label}: {len(sel)} rows, {len(fwd)} forward, "
          f"{src_n} with an external link, {nct} with an NCT id")
    print("    precision:", dict(collections.Counter(str(r.get("dp")) for r in sel)))
    for r in sorted(sel, key=lambda r: str(r.get("d")))[:8]:
        print(f"      {r.get('t'):<6} {r.get('d')} {str(r.get('dp')):<8} {str(r.get('st')):<10}"
              f" | {str(r.get('name'))[:40]}")
