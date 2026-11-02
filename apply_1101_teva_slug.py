# -*- coding: utf-8 -*-
"""apply_1101_teva_slug.py -- IGALMI's event page follows its sponsor: /pdufa/BTAI-igalmi -> /pdufa/TEVA-igalmi.

BioXcel sold IGALMI, BXCL501 and the pending sNDA to Teva on 2026-10-26 (BioXcel 8-K 2026-10-30). The dataset row
moved to TEVA this pass, but its page kept the BTAI slug, so every listing rendered a /pdufa/BTAI-* link for a
ticker the slate no longer carries (test_static_pages_match_slate). The page moves; a permanent redirect keeps
the old URL. The BXCL501 readout row (2027) moves to TEVA as well. Facts only; not investment advice.
"""
import glob
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
OLD, NEW = "/pdufa/BTAI-igalmi", "/pdufa/TEVA-igalmi"

src = io.open(DATASET, encoding="utf-8").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
for r in rows:
    if r["id"] == "pdufa_btai_2026-11-14":
        r["url"] = NEW
        r.setdefault("_d", {})["event_slug"] = "TEVA-igalmi"
    if r["id"] == "readout_btai_2027-07-15" and r.get("t") == "BTAI":
        d = r.setdefault("_d", {})
        d.setdefault("ticker_history", []).append({"ticker": "BTAI", "until": "2026-10-26",
                                                   "why": "BXCL501 sold to Teva with IGALMI (BioXcel 8-K 2026-10-30, Item 2.01)."})
        r.update({"t": "TEVA", "company": "Teva Pharmaceutical Industries", "url": "/ticker/TEVA", "cap": "Large"})
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print("  dataset: IGALMI row -> /pdufa/TEVA-igalmi; BXCL501 readout -> TEVA")

n = 0
for p in glob.glob(os.path.join(SITE, "**", "*"), recursive=True):
    if not os.path.isfile(p) or os.path.splitext(p)[1] not in (".html", ".xml", ".txt", ".json", ".js", ".mjs"):
        continue
    if os.path.basename(p) == "vercel.json" or os.sep + "pdufa" + os.sep + "BTAI-igalmi" + os.sep in p:
        continue
    try:
        s = io.open(p, encoding="utf-8").read()
    except UnicodeDecodeError:
        continue
    if OLD in s:
        io.open(p, "w", encoding="utf-8").write(s.replace(OLD + '"', NEW + '"').replace(OLD + "<", NEW + "<")
                                               .replace("https://www.pdufa.bio" + OLD, "https://www.pdufa.bio" + NEW))
        n += 1
print(f"  links repointed in {n} file(s)")

vj = os.path.join(SITE, "vercel.json")
cfg = json.load(io.open(vj, encoding="utf-8"))
if not any(r.get("source") == OLD for r in cfg.get("redirects", [])):
    cfg["redirects"].append({"source": OLD, "destination": NEW, "permanent": True})
    json.dump(cfg, io.open(vj, "w", encoding="utf-8"), indent=1)
    print(f"  vercel.json: 301 {OLD} -> {NEW}")
