# -*- coding: utf-8 -*-
"""apply_readout_ta_manual.py -- hand-assigned therapeutic areas onto forward readout rows (audit 2026-10-03, 3.3).

The readout hubs (/readouts/oncology, /readouts/rare-disease) are proven citation chains, and their ceiling
was tagging: 190 of 323 forward readouts (59%) carried no therapeutic area. The rule from the custirsen
lesson stands: never by keyword widening and never from the drug name. _readout_ta_manual.json holds one
hand decision per row with its basis (the trial's ClinicalTrials.gov conditions where the registry record
names the row's drug, or the sponsor's SEC sentence naming the asset with its indication). This applies it,
every run, only to rows whose ta is empty or "Other" (a tag the pipeline already holds is never overwritten).

    python apply_readout_ta_manual.py
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
MAN = os.path.join(HERE, "_readout_ta_manual.json")

src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
tags = json.load(io.open(MAN, encoding="utf-8")).get("tags", {})
n = 0
for r in rows:
    t = tags.get(r.get("id"))
    if t and r.get("type") == "Readout" and str(r.get("ta") or "") in ("", "Other"):
        r["ta"] = t["ta"]
        r.setdefault("_d", {})["ta_basis"] = t["basis"]
        n += 1
if n:
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
fwd = [r for r in rows if r.get("type") == "Readout" and r.get("st") in ("Estimated", "Guided")]
un = sum(1 for r in fwd if str(r.get("ta") or "") in ("", "Other"))
print(f"readout TA: {n} row(s) tagged from the hand file; forward readouts untagged {un}/{len(fwd)} ({un / max(1, len(fwd)):.0%})")
