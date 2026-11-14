# -*- coding: utf-8 -*-
"""Restore RHHBY giredestrant (lidERA, goal 2026-11-30) to the slate: the decided-sweep removed it because the decided
Gazyva pMN row shares the key (RHHBY, 2026-11-30). build_slate_from_crawl.py no longer sweeps a catalyst whose drug
matches a pending row on the same key. Facts only."""
import copy, datetime as dt, io, json, os
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(H, "pdufa_site_src")
src = io.open(os.path.join(S, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
row = next(r for r in json.loads(src[src.index("["):src.rindex("]") + 1]) if r["id"] == "pdufa_rhhby_2026-11-30")
p = os.path.join(S, "api", "data.js"); t = io.open(p, encoding="utf-8").read()
k = t.find("const SLATE=") + len("const SLATE="); o, e = json.JSONDecoder().raw_decode(t[k:])
if not any(c.get("ticker") == "RHHBY" and c.get("date") == "2026-11-30" for c in o["catalysts"]):
    base = copy.deepcopy(next(c for c in o["catalysts"] if c.get("ticker") == "RHHBY"))
    base.update({"date": "2026-11-30", "drug": row["name"], "indication": (row.get("_d") or {}).get("indication") or base.get("indication"),
                 "t_minus": (dt.date(2026, 11, 30) - dt.date(2026, 11, 14)).days})
    o["catalysts"].append(base); o["catalysts"].sort(key=lambda c: str(c.get("date")))
    io.open(p, "w", encoding="utf-8").write(t[:k] + json.dumps(o, separators=(",", ":")) + t[k + e:])
    print("restored RHHBY giredestrant 2026-11-30 to the slate")
else:
    print("already present")
