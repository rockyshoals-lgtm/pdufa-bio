# -*- coding: utf-8 -*-
import csv, re, sys, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
rows = list(csv.DictReader(open("pdufa_runup_bifrost_v2.csv", encoding="utf-8-sig", errors="replace")))
r = [x for x in rows if x.get("pdufa_date", "").startswith("2026")][-1]
print("SAMPLE 2026 ROW:")
for k, v in r.items():
    print(f"  {k:14s} = {v!r}")
print("\noutcome values:", collections.Counter(x.get("outcome") for x in rows).most_common(8))
print("outcome_bin  :", collections.Counter(x.get("outcome_bin") for x in rows).most_common(5))
print("mcap_tier    :", collections.Counter(x.get("mcap_tier") for x in rows).most_common(8))
print("ta_bucket    :", collections.Counter(x.get("ta_bucket") for x in rows).most_common(8))
# which archive decisions are missing from the study?
have = {(x["ticker"], x["pdufa_date"][:10]) for x in rows}
html = open("pdufa_site_src/decisions/index.html", encoding="utf-8", errors="replace").read()
dec = sorted({(m.group(1), m.group(2)) for m in
              re.finditer(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', html)}, key=lambda x: x[1])
missing = [d for d in dec if d not in have]
print(f"\narchive decisions: {len(dec)} | already in study: {len(dec)-len(missing)} | MISSING: {len(missing)}")
print("missing by year:", dict(sorted(collections.Counter(d[1][:4] for d in missing).items())))
print("newest 10 missing:", missing[-10:])
