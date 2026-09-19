# -*- coding: utf-8 -*-
import io, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "pdufa_site_src/calendar/index.html"
t = io.open(p, encoding="utf-8").read()
for m in re.finditer(r'<a class="row"[^>]*href="/pdufa/NUVL-neladalkib"[^>]*>.*?</a>', t, re.S):
    print("BEFORE:", repr(m.group(0)[:260]))
new, n = re.subn(r'(<a class="row"[^>]*href="/pdufa/NUVL-neladalkib"[^>]*>\s*<div class="t">\s*)GSK \(formerly NUVL\)(\s*(?:&middot;|·)\s*2026-11-27\s*</div>\s*<div class="d">\s*Neladalkib \(NVL-655\))',
                 r"\1GSK\2, formerly Nuvalent (NUVL),", t, flags=re.S)
print("subs:", n)
io.open(p, "w", encoding="utf-8").write(new)
for m in re.finditer(r'<a class="row"[^>]*href="/pdufa/NUVL-neladalkib"[^>]*>.*?</a>', new, re.S):
    print("AFTER :", repr(m.group(0)[:260]))
