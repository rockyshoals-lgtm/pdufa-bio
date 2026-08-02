# -*- coding: utf-8 -*-
"""add_sls_nav.py -- add the SLS tab to the site nav (idempotent).

Inserts a server-rendered <a href="/sls">SLS</a> anchor into the standard nav, immediately before the
Pro link, on every page that carries the nav. Server-rendered anchors are the point: they give the new
hub real internal links from every page rather than sitemap-only discovery (the SEO playbook's B2
finding). Skips pages that already have it.
"""
import glob, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
LINK = '<a href="/sls" style="color:#46d17f;font-weight:700">SLS</a>'
# insert before the Pro link in the main nav
PRO = re.compile(r'(<a class="pro" href="/pricing")')
# secondary nav style used by some pages (.nav div, no Pro link) -> put after Decisions
DEC = re.compile(r'(<a href="/decisions">Decisions</a>)')

changed, skipped = [], 0
for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
    rel = os.path.relpath(p, SITE)
    if any(rel.startswith(x) for x in ("_", "preview", "index_redesign")):
        continue
    try:
        h = open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    if 'href="/sls"' in h:
        skipped += 1
        continue
    new = h
    if PRO.search(new):
        new = PRO.sub(LINK + r'\1', new, count=1)
    elif DEC.search(new):
        new = DEC.sub(r'\1' + LINK, new, count=1)
    else:
        continue
    if new != h:
        open(p, "w", encoding="utf-8").write(new)
        changed.append(rel)

print(f"added SLS nav link to {len(changed)} page(s); {skipped} already had it")
for c in changed[:15]:
    print("  ", c)
if len(changed) > 15:
    print(f"   ... and {len(changed)-15} more")
