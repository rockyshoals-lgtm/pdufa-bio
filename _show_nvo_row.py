# -*- coding: utf-8 -*-
"""Show every NVO row on /calendar so the skipped one can be judged, not guessed."""
import io
import re

p = "pdufa_site_src/calendar/index.html"
d = io.open(p, encoding="utf-8", errors="replace").read()
pat = re.compile(r'<a class="row"[^>]*>\s*<div class="t">NVO (?:&middot;|·) '
                 r'([^<]+)</div><div class="d">(.*?)</div>\s*</a>', re.S)
for m in pat.finditer(d):
    print(repr(m.group(0))[:400])
    print()
