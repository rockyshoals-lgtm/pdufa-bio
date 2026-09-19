# -*- coding: utf-8 -*-
"""Undo my own error: restore company-GUIDED readout dates that the registry re-sync overwrote.

refresh_readout_registry.py was written to skip only `Reported` rows, so it also rewrote rows
whose status is `Guided` -- dates that come from a company's own guidance, not from
ClinicalTrials.gov. test_guided_readouts_current caught one (SLS REGAL Phase 3 topline, moved
from 2026-12 to NCT04229979's registry primary completion of 2025-12), which is exactly the
wrong direction: a sourced company statement replaced by a number the company did not give.

This reads the committed dataset from git HEAD and restores d / dm / dp for every Guided readout
row, leaving the Estimated rows re-synced as intended. The script itself is now gated on
st == "Estimated" so it cannot happen again.
"""
import io
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REL = "pdufa_site_src/api/v1/dataset.mjs"
DATASET = os.path.join(os.path.dirname(os.path.abspath(__file__)), *REL.split("/"))


def parse(text):
    rows, _ = json.JSONDecoder().raw_decode(text[text.find("["):])
    return rows


head = subprocess.run(["git", "show", f"HEAD:{REL}"], capture_output=True,
                      text=True, encoding="utf-8", errors="replace").stdout
if not head.strip():
    print("could not read HEAD copy; aborting")
    sys.exit(1)

was = {r.get("id"): r for r in parse(head) if r.get("type") == "Readout"}

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
a, b = src.index("["), src.rindex("]") + 1
rows = json.loads(src[a:b])

n = 0
for r in rows:
    if r.get("type") != "Readout" or str(r.get("st") or "") != "Guided":
        continue
    old = was.get(r.get("id"))
    if not old:
        continue
    if (r.get("d"), r.get("dm"), r.get("dp")) != (old.get("d"), old.get("dm"), old.get("dp")):
        print(f"  restore {r.get('t'):<6} {r.get('id')}: "
              f"{r.get('dm') or r.get('d')} -> {old.get('dm') or old.get('d')} (company guidance)")
        for k in ("d", "dm", "dp"):
            if k in old:
                r[k] = old[k]
            else:
                r.pop(k, None)
        n += 1

io.open(DATASET, "w", encoding="utf-8").write(
    src[:a] + json.dumps(rows, indent=1, ensure_ascii=False) + src[b:])
print(f"\n{n} company-guided readout date(s) restored")
