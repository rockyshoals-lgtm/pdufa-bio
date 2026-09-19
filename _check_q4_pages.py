# -*- coding: utf-8 -*-
"""Do the seven orphaned Q4 rows have published event pages, and do those pages cite a source?

This decides which side is wrong. If /pdufa/ABBV-rinvoq exists and links a primary source, the
event is real and the DATASET lost it -- the fix is to add the dataset row. If the page is
missing or sourceless, the calendar row is a fossil and comes off.
"""
import io
import os
import re

SITE = "pdufa_site_src"
SLUGS = [
    ("ABBV", "/pdufa/ABBV-rinvoq", "RINVOQ non-segmental vitiligo"),
    ("RHHBY", "/pdufa/RHHBY-lunsumio-polivy", "Lunsumio + Polivy 2L+ DLBCL"),
    ("RHHBY", "/pdufa/RHHBY-gazyva", "Gazyva SLE"),
    ("NVS", "/pdufa/NVS", "Pluvicto end-stage prostate"),
    ("LLY", "/pdufa/LLY", "Tirzepatide CV outcomes"),
    ("PFE", "/pdufa/PFE-tukysa-trastuzumab-and", "TUKYSA+tras+pertu HER2+ MBC"),
    ("AZN", "/pdufa/AZN-gefurulimab", "Gefurulimab gMG"),
]

for tk, slug, what in SLUGS:
    p = os.path.join(SITE, slug.strip("/"), "index.html")
    if not os.path.exists(p):
        print(f"{tk:<6} {slug:<42} PAGE MISSING          -- {what}")
        continue
    doc = io.open(p, encoding="utf-8", errors="replace").read()
    ext = re.findall(r'href="(https?://(?!www\.pdufa\.bio)[^"]+)"', doc)
    ext = [u for u in ext if "schema.org" not in u and "cdn" not in u]
    date = re.search(r'(Q[1-4]\s+\d{4}|\d{4}-\d{2}-\d{2}|'
                     r'(?:January|February|March|April|May|June|July|August|September|'
                     r'October|November|December)\s+\d{1,2},\s+\d{4})', doc)
    print(f"{tk:<6} {slug:<42} page OK, {len(ext)} ext link(s), "
          f"date shown={date.group(1) if date else 'none'} -- {what}")
    for u in ext[:2]:
        print(f"          {u[:120]}")
