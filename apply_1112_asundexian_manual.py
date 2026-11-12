# -*- coding: utf-8 -*-
"""apply_1112_asundexian_manual.py -- /drug/asundexian still said "under FDA review" after the approval was published.

The page merges dataset rows with _drug_pages_manual.json, which held a hand row for asundexian (st "Under review",
NDA accepted with Priority Review 2026-05-19, goal undisclosed). The dataset now records the Nov 9, 2026 approval
(pdufa_bayry_2026-11-09_asundexian), so the manual row is retired; its review history moves to the dataset row's
_d.review so the page keeps it. Facts only, not investment advice.
"""
import io, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
MP = os.path.join(HERE, "_drug_pages_manual.json")
m = json.load(io.open(MP, encoding="utf-8"))
lst = m if isinstance(m, list) else m.get("rows")
keep, gone = [], None
for r in lst:
    if str(r.get("name", "")).lower() == "asundexian" and str(r.get("st", "")).lower() == "under review":
        gone = r
    else:
        keep.append(r)
if isinstance(m, list):
    m = keep
else:
    m["rows"] = keep
io.open(MP, "w", encoding="utf-8").write(json.dumps(m, indent=1, ensure_ascii=False) + "\n")
P = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
s = io.open(P, encoding="utf-8").read(); i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
for r in rows:
    if r.get("id") == "pdufa_bayry_2026-11-09_asundexian" and gone:
        r["_d"]["review"] = (gone.get("_d") or {}).get("review") or gone.get("when_text")
        r["_d"]["review_source_url"] = gone.get("url")
io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
print("manual asundexian row retired:", bool(gone))
