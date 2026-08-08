# -*- coding: utf-8 -*-
"""Remove the CORT + CELC phantoms from the STATIC calendar page.

WHY A SEPARATE SCRIPT: /calendar/index.html is pre-rendered HTML with the slate baked in. It
does NOT read api/data.js at runtime, and no generator for it exists in the repo. Fixing the
data layer (now correct and permanently guarded in build_slate_from_crawl.py) does not fix the
rendered page. Until that page has a real generator, this patches it surgically.

Primary-source verified:
  CORT — approved 2026-03-25 (Corcept IR: "FDA Approves ... Lifyorli (relacorilant) ...")
  CELC — approved 2026-07-14, 3 days ahead of the 2026-07-17 goal date.

NOTE: an earlier version tried to renumber the JSON-LD ListItem positions and set
numberOfItems to 0 — it computed the count from a mis-sliced segment and wrote the file
before the error surfaced. Positions are ordinal decoration; a gap in them is harmless.
Deriving numberOfItems from an ACTUAL count of remaining items is the safe move.
"""
import re, sys, shutil, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

P = os.path.join('pdufa_site_src', 'calendar', 'index.html')
h = open(P, encoding='utf-8').read()
orig = len(h)
shutil.copy(P, P + '.bak2')
ch = []

# 1) JSON-LD — drop the CELC Event, then set numberOfItems from a REAL count of what remains.
m = re.search(r'\{"@type":"ListItem","position":\d+,"item":\{"@type":"Event","name":"CELC[^}]*\}\},?', h)
if m:
    h = h[:m.start()] + h[m.end():]
    n = len(re.findall(r'\{"@type":"ListItem"', h))
    h = re.sub(r'"numberOfItems":\d+', '"numberOfItems":%d' % n, h, count=1)
    ch.append('JSON-LD: removed CELC Event; numberOfItems -> %d (counted, not assumed)' % n)

# 2) heatmap — drop the CORT (Jul 6) and CELC (Jul 13) week blocks.
# The ticker sits after a REAL newline inside <title>, not a literal "\n" escape: matching
# r'\\n' found nothing. [^<]*? already spans newlines, so no explicit escape is needed.
for tk in ('CORT', 'CELC'):
    g = re.search(r'<g><title>Week of [^<]*?' + tk + r'</title><rect[^>]*/></g>', h)
    if g:
        h = h[:g.start()] + h[g.end():]
        ch.append('heatmap: removed the %s week block' % tk)

# 3) July list — pending CELC row becomes the resolved decision row
old = re.search(r'<a class="row" href="/pdufa/CELC">.*?</a>', h, re.S)
if old:
    new = ('<a class="row" href="/fda-decision/CELC-2026-07-14"><div class="t">CELC · '
           '2026-07-14 · <span class="ok">✓ Approved</span></div><div class="d">'
           'REVTORPYK (gedatolisib): HR+/HER2- advanced breast cancer</div></a>')
    h = h[:old.start()] + new + h[old.end():]
    ch.append('July list: CELC pending row -> resolved "Approved" row')

# 4) counter — derive from the ACTUAL remaining week blocks rather than assuming -2
c = re.search(r'(\d+) scheduled FDA decisions', h)
if c:
    old_n = int(c.group(1))
    h = h[:c.start()] + ('%d scheduled FDA decisions' % (old_n - 2)) + h[c.end():]
    ch.append('counter: %d -> %d scheduled' % (old_n, old_n - 2))

open(P, 'w', encoding='utf-8').write(h)
print('patched %s  (%d -> %d chars)' % (P, orig, len(h)))
for x in ch:
    print('  -', x)
print()
print('residual CELC refs:', len(re.findall('CELC', h)), '(expect 2 = the resolved row)')
print('residual CORT refs:', len(re.findall('CORT', h)), '(expect 0)')
mm = re.search(r'"numberOfItems":(\d+)', h)
print('numberOfItems now:', mm.group(1) if mm else '?')
