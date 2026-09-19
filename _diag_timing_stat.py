# -*- coding: utf-8 -*-
"""Does the 2026 decision-timing statistic count rows whose 'goal date' is just the decision date
copied over? Those have no sourced goal, so a 0-day margin is not a measurement."""
import importlib.util
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bed", os.path.join(HERE, "build_early_decisions.py"))
bed = importlib.util.module_from_spec(spec)
sys.argv = ["build_early_decisions.py"]
spec.loader.exec_module(bed)

s = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(s[s.find("["):])
same = {r["id"] for r in rows if r["type"] == "PDUFA" and str(r.get("st")) == "Decided"
        and r.get("d") and r.get("d") == r.get("dcd")}
by_tk_date = {(r["t"], str(r.get("d"))): r for r in rows}

got = bed.collect(2026)
print(f"collect(2026) -> {len(got)} sourced decisions in the timing statistic")
early = sum(1 for x in got if x["delta"] < 0)
on = sum(1 for x in got if x["delta"] == 0)
late = sum(1 for x in got if x["delta"] > 0)
print(f"   early {early} / on-the-day {on} / late {late}")

print("\n-- of those, which have goal == actual (goal date is the decision date copied) --")
n = 0
for x in got:
    if x["goal"] == x["actual"]:
        n += 1
        r = by_tk_date.get((x["ticker"], x["goal"]))
        src = (r.get("_d") or {}).get("source_url") if r else None
        print(f"   {x['ticker']:<7} goal={x['goal']} actual={x['actual']} delta={x['delta']:>3}  "
              f"row_source_url={'yes' if src else 'NO'}  id={r['id'] if r else '?'}")
print(f"   -> {n} of the {on} 'landed on it' rows are goal==actual")
print("\nIf those rows have no separately sourced goal date, a 0-day margin is an artefact of the\n"
      "encoding, not a measurement of FDA punctuality.")
