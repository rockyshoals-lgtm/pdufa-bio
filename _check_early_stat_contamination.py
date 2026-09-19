# -*- coding: utf-8 -*-
"""Does the manufactured quarter-end goal date contaminate the published early-decision stat?

/research/fda-decision-timing says how many sourced decisions came BEFORE the PDUFA goal date
and by how much. Its inclusion rule (build_early_decisions.collect) tests the goal date's
FORMAT -- ^\\d{4}-\\d{2}-\\d{2}$ -- not its PRECISION. A goal date we manufactured by rounding
a sponsor's "third quarter of calendar year 2026" up to 2026-09-30 passes that test perfectly.

It also biases in one direction. A quarter-end placeholder is the LATEST day in the stated
quarter, so every real action inside the quarter is scored as "early", and by the maximum
possible margin. That is the flattering direction, which is exactly what the script's own
comment at line 161 warns about for a different number.

This reproduces collect() exactly, then reports the statistic with and without the four rows.
"""
import datetime as dt
import io
import json
import os
import re
import statistics

SITE = "pdufa_site_src"
SUSPECT = {("PFE", "2026-09-30"), ("ROIV", "2026-09-30"),
           ("PTGX", "2026-09-30"), ("TAK", "2026-09-30")}

s = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
            encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(s[s.find("["):])

inc = []
for r in rows:
    if r.get("type") != "PDUFA" or str(r.get("st", "")).lower() != "decided":
        continue
    goal, actual = str(r.get("d") or ""), str(r.get("dcd") or "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", goal) or \
       not re.match(r"^\d{4}-\d{2}-\d{2}$", actual):
        continue
    tk = str(r.get("t") or "").upper()
    page = os.path.join(SITE, "fda-decision", f"{tk}-{actual}", "index.html")
    if not os.path.exists(page):
        continue
    doc = io.open(page, encoding="utf-8", errors="replace").read()
    low = doc.lower()
    if "price-only" in low or "outcome unverified" in low:
        continue
    if not re.search(r'href="https?://(?!www\.pdufa\.bio)', doc):
        continue
    delta = (dt.date.fromisoformat(actual) - dt.date.fromisoformat(goal)).days
    inc.append({"tk": tk, "goal": goal, "actual": actual, "delta": delta,
                "dp": r.get("dp"), "suspect": (tk, goal) in SUSPECT})

print(f"rows feeding the published statistic: {len(inc)}")
sus = [x for x in inc if x["suspect"]]
print(f"...of which are quarter-end placeholders: {len(sus)}")
for x in sus:
    print(f"    {x['tk']:<5} goal {x['goal']} actual {x['actual']} "
          f"delta {x['delta']:+d} dp={x['dp']}")

alld = [x["delta"] for x in inc]
cln = [x["delta"] for x in inc if not x["suspect"]]
if alld:
    print(f"\n  AS PUBLISHED : n={len(alld)} median {statistics.median(alld):+.1f} "
          f"early {sum(1 for d in alld if d < 0)} on-day {sum(1 for d in alld if d == 0)} "
          f"late {sum(1 for d in alld if d > 0)}")
if cln:
    print(f"  IF EXCLUDED  : n={len(cln)} median {statistics.median(cln):+.1f} "
          f"early {sum(1 for d in cln if d < 0)} on-day {sum(1 for d in cln if d == 0)} "
          f"late {sum(1 for d in cln if d > 0)}")
