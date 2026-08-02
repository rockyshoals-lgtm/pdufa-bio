# -*- coding: utf-8 -*-
"""add_ticker_crosslinks.py -- make the ticker link bidirectional (SEO playbook B2 item 2).

Ticker pages link out to events, but events never linked back, so /ticker/* had almost no inbound
equity (measured: homepage 1, /calendar 0, /decisions 0). /decisions rows are themselves <a> elements,
so a link cannot be nested inside them -- instead this links from each individual event page, which is
cleaner and creates one path per page across ~540 pages.

Turns the plain ticker text in the breadcrumb into an anchor:
    Home > Decisions > OTLK 2026-07-24   ->   Home > Decisions > <a href="/ticker/OTLK">OTLK</a> 2026-07-24

Idempotent: skips a page that already links to its ticker hub.
"""
import glob, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")

targets = []
targets += glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))
targets += glob.glob(os.path.join(SITE, "adcomm", "*", "index.html"))
targets += glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))

changed, skipped, no_hub = 0, 0, 0
for p in targets:
    base = os.path.basename(os.path.dirname(p))
    m = re.match(r'^([A-Z]{1,6})(?:-\d{4}-\d{2}-\d{2})?$', base)
    if not m:
        continue
    tk = m.group(1)
    if not os.path.exists(os.path.join(SITE, "ticker", tk, "index.html")):
        no_hub += 1
        continue
    h = open(p, encoding="utf-8", errors="replace").read()
    if f'href="/ticker/{tk}"' in h:
        skipped += 1
        continue
    # link the bare ticker inside the breadcrumb only (avoid touching body prose)
    pat = re.compile(r'(<div class="bc">.*?&rsaquo;\s*)(' + tk + r')(\b)', re.S)
    new, n = pat.subn(lambda mm: mm.group(1) + f'<a href="/ticker/{tk}">{tk}</a>' + mm.group(3), h, count=1)
    if not n:
        continue
    open(p, "w", encoding="utf-8").write(new)
    changed += 1

print(f"ticker cross-links added: {changed} page(s) | already linked: {skipped} | no ticker hub: {no_hub}")
print(f"scanned {len(targets)} event pages")
