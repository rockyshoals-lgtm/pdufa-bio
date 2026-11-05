# -*- coding: utf-8 -*-
"""apply_1105_inbx_ozekibart.py -- the April 14, 2027 INBX goal date is ozekibart (INBRX-109), not INBRX-106.

Inhibrx 8-K 2026-06-15: the FDA accepted the BLA "seeking approval of ozekibart (INBRX-109) for the treatment of
patients with unresectable or metastatic conventional chondrosarcoma ... PDUFA goal date of April 14, 2027". The row,
its event page (/pdufa/INBX-inbrx-106) and its calendar rows named INBRX-106, a different Inhibrx molecule (an OX40
agonist in a separate trial). Found 2026-11-05 comparing Bing's "pdufa dates 2027" answer with our 2027 rows.
The page moves to /pdufa/INBX-ozekibart; the old URL 301s there. Facts only; not investment advice.
"""
import glob
import io
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
OLD, NEW = "/pdufa/INBX-inbrx-106", "/pdufa/INBX-ozekibart"
NAME = "Ozekibart (INBRX-109) - conventional chondrosarcoma"
IND = "Unresectable or metastatic conventional chondrosarcoma"

src = io.open(DATASET, encoding="utf-8").read()
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
for r in rows:
    if r["id"] == "pdufa_inbx_2027-04-14":
        r.update({"name": NAME, "url": NEW})
        d = r.setdefault("_d", {})
        d.update({"event_slug": "INBX-ozekibart", "indication": IND, "inn": "ozekibart",
                  "source_quote": "has accepted for filing its Biologics License Application (the BLA) seeking approval of "
                                  "ozekibart (INBRX-109) for the treatment of patients with unresectable or metastatic "
                                  "conventional chondrosarcoma ... has assigned a Prescription Drug User Fee Act (PDUFA) "
                                  "goal date of April 14, 2027."})
        print("  dataset row renamed")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])

DATAJS = os.path.join(SITE, "api", "data.js")
s_ = io.open(DATAJS, encoding="utf-8").read()
k = s_.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(s_[k:])
for c in slate["catalysts"]:
    if c.get("ticker") == "INBX" and c.get("date") == "2027-04-14":
        c["drug"], c["indication"] = NAME, IND
io.open(DATAJS, "w", encoding="utf-8").write(s_[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":")) + s_[k + end:])

old_dir = os.path.join(SITE, "pdufa", "INBX-inbrx-106")
if os.path.isdir(old_dir):
    shutil.rmtree(old_dir)   # build_pdufa_event_pages.py writes /pdufa/INBX-ozekibart from the row
n = 0
for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
    t = io.open(p, encoding="utf-8", errors="replace").read()
    if OLD not in t:
        continue
    t2 = t.replace(OLD + '"', NEW + '"').replace("https://www.pdufa.bio" + OLD, "https://www.pdufa.bio" + NEW)
    t2 = t2.replace("<div class=\"d\">INBRX-106</div>", f"<div class=\"d\">{NAME}</div>")
    if t2 != t:
        io.open(p, "w", encoding="utf-8").write(t2); n += 1
print(f"  links repointed in {n} page(s)")
vj = os.path.join(SITE, "vercel.json")
cfg = json.load(io.open(vj, encoding="utf-8"))
if not any(r.get("source") == OLD for r in cfg["redirects"]):
    cfg["redirects"].append({"source": OLD, "destination": NEW, "permanent": True})
    json.dump(cfg, io.open(vj, "w", encoding="utf-8"), indent=1)
    print(f"  301 {OLD} -> {NEW}")
