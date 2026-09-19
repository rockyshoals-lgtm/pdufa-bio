# -*- coding: utf-8 -*-
import io, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
t = io.open("pdufa_site_src/calendar/index.html", encoding="utf-8").read()
rows = re.findall(r'<a class="row"[^>]*>.*?</a>', t, re.S)
print("rows:", len(rows))
for r in rows:
    if re.search(r"MRK|CORT|CAPR|Mim8|NUVL|VTRS", r):
        print(r[:420].replace("\n", " "))
        print("---")
