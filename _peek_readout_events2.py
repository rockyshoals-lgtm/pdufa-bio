# -*- coding: utf-8 -*-
import io, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
t = io.open("pdufa_site_src/readouts/index.html", encoding="utf-8").read()
n = 0
for e in re.findall(r'\{"@type":"Event"(?:[^{}]|\{[^{}]*\})*\}', t):
    m = re.search(r'"startDate":"(\d{4}-\d{2}-\d{2})', e)
    if m:
        n += 1
        if n <= 20:
            print(e[:190])
print("day-stamped Events left:", n)
