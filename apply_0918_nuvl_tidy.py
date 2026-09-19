# -*- coding: utf-8 -*-
"""Tidy the NUVL->GSK carry-over: calendar row wording, the slate row, and one company spelling."""
import io, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")

p = os.path.join(SITE, "calendar", "index.html")
t = io.open(p, encoding="utf-8").read()
t2 = t.replace("Neladalkib (NVL-655), formerly Nuvalent (NUVL),: ALK",
               "Neladalkib (NVL-655) (formerly Nuvalent, NUVL): ALK")
if t2 != t:
    io.open(p, "w", encoding="utf-8").write(t2); print("calendar row wording tidied")
else:
    print("calendar row wording already fine")

p = os.path.join(SITE, "api", "data.js")
t = io.open(p, encoding="utf-8").read()
old = '{"ticker":"NUVL","name":"Nuvalent"'
if old in t:
    i = t.index(old)
    j = t.index("}", i) + 1
    row = json.loads(t[i:j])
    row.update({"ticker": "GSK", "name": "GSK plc", "cap": "Large",
                "price": None, "mcap": None, "adv": None, "cash_months": None,
                "former_ticker": "NUVL"})
    io.open(p, "w", encoding="utf-8").write(t[:i] + json.dumps(row, separators=(",", ":")) + t[j:])
    print("slate row NUVL -> GSK (price/mcap nulled: the $123.96 was the tender price)")
else:
    print("slate row already moved")

p = os.path.join(SITE, "api", "v1", "dataset.mjs")
s = io.open(p, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
n = 0
for r in rows:
    if r["id"] == "pdufa_nuvl_2026-11-27" and r.get("company") != "GSK plc":
        r["company"] = "GSK plc"; n += 1
if n:
    io.open(p, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
print(f"company spelling normalised on {n} row(s)")
