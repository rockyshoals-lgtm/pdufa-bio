# -*- coding: utf-8 -*-
"""GSK completed its acquisition of Nuvalent in July 2026 (Nuvalent 8-K 2026-07-15). The dataset
row for neladalkib moved to ticker GSK; this carries the change to the rendered surfaces:
  - /calendar and /calendar/2026/november: the row's ticker cell "NUVL" -> "GSK (formerly NUVL)"
  - /pdufa/NUVL-neladalkib: an acquisition notice under the h1, title/og ticker prefix, and the
    sub line's company; the slug stays (inbound links) and the page is not duplicated
  - /ticker/NUVL: the same notice at the top of the hub
Idempotent (markers)."""
import glob, io, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
SRC = "https://www.sec.gov/Archives/edgar/data/1861560/000119312526304126/d52896d8k.htm"
NOTE = ('<!--ACQ:BEGIN--><div class="sub" style="background:#0c1d38;border:1px solid #f0c86a;border-radius:10px;'
        'padding:10px 14px;margin:8px 0 12px"><b style="color:#f0c86a">Sponsor change.</b> GSK completed its '
        'acquisition of Nuvalent in July 2026 (tender offer at $124.00 per share; <a class="lit" href="' + SRC +
        '" rel="nofollow">Nuvalent 8-K, July 15, 2026</a>). NUVL no longer trades; this application now belongs '
        'to GSK and is listed under <a href="/ticker/GSK">GSK</a>.</div><!--ACQ:END-->')

n = 0
for p in [os.path.join(SITE, "calendar", "index.html"), os.path.join(SITE, "calendar", "2026", "november", "index.html")]:
    if not os.path.exists(p):
        continue
    t = io.open(p, encoding="utf-8").read()
    t2 = re.sub(r'(<a class="row"[^>]*href="/pdufa/NUVL-neladalkib"[^>]*>\s*<div class="t">\s*)NUVL(\s*(?:&middot;|·)\s*2026-11-27)',
                r"\1GSK (formerly NUVL)\2", t)
    if t2 != t:
        io.open(p, "w", encoding="utf-8").write(t2); n += 1; print("calendar row relabelled:", os.path.relpath(p, SITE))

p = os.path.join(SITE, "pdufa", "NUVL-neladalkib", "index.html")
t = io.open(p, encoding="utf-8").read()
if "<!--ACQ:BEGIN-->" not in t:
    t = t.replace("<h1", NOTE + "<h1", 1)
    t = t.replace("<title>NUVL PDUFA date:", "<title>GSK (formerly NUVL) PDUFA date:")
    t = t.replace('content="NUVL PDUFA date:', 'content="GSK (formerly NUVL) PDUFA date:')
    t = t.replace("&middot; Nuvalent, Inc. &middot;", "&middot; GSK plc (acquired Nuvalent, July 2026) &middot;")
    t = t.replace("· Nuvalent, Inc. ·", "· GSK plc (acquired Nuvalent, July 2026) ·")
    io.open(p, "w", encoding="utf-8").write(t); n += 1; print("event page annotated")

p = os.path.join(SITE, "ticker", "NUVL", "index.html")
if os.path.exists(p):
    t = io.open(p, encoding="utf-8").read()
    if "<!--ACQ:BEGIN-->" not in t:
        t = t.replace("<h1", NOTE + "<h1", 1)
        io.open(p, "w", encoding="utf-8").write(t); n += 1; print("ticker hub annotated")
print(n, "surface(s) updated")
