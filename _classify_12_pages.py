# -*- coding: utf-8 -*-
"""Classify the twelve Dec-31 event pages: which have a dataset row, at what precision?

The fix differs by class. A page whose dataset row is month/quarter precision should render the
WINDOW. A page with no dataset row at all is asserting a day nothing backs, and per the
auditor's ORDER item 2 the day comes off until it is sourced.
"""
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = "pdufa_site_src"
SLUGS = ["ABBV-tavapadon", "NVO-am833", "AZN-ultomiris", "BAYRY-kerendia", "ABBV-rinvoq",
         "RHHBY-lunsumio-polivy", "RHHBY-gazyva", "NVS", "LLY",
         "PFE-tukysa-trastuzumab-and", "AZN-gefurulimab", "GILD-trodelvy"]
STOP = {"pdufa", "date", "and", "the"}

src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
              encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])


def toks(s):
    return {w for w in re.findall(r"[a-z][a-z0-9]{2,}", str(s or "").lower())
            if w not in STOP}


for slug in SLUGS:
    tk = slug.split("-")[0].upper()
    part = slug[len(tk):].lstrip("-")
    st = toks(part.replace("-", " "))
    cands = [r for r in rows if str(r.get("t") or "").upper() == tk
             and r.get("type") == "PDUFA"
             and str(r.get("st") or "").lower() != "decided"]
    hits = [c for c in cands if (not st) or (st & toks(c.get("name")))]
    p = os.path.join(SITE, "pdufa", slug, "index.html")
    exists = os.path.isfile(p)
    print(f"\n/pdufa/{slug}   page={'yes' if exists else 'MISSING'}")
    if not hits:
        print(f"    NO DATASET ROW  (ticker has {len(cands)} other live PDUFA row(s))")
        for c in cands[:3]:
            print(f"      other: {c.get('d')} dp={c.get('dp')} {str(c.get('name'))[:40]}")
        continue
    for c in hits:
        dd = c.get("_d") or {}
        print(f"    row: d={c.get('d')} dp={c.get('dp')} dm={c.get('dm')} st={c.get('st')} "
              f"src={'Y' if dd.get('source_url') else '-'} | {str(c.get('name'))[:44]}")
