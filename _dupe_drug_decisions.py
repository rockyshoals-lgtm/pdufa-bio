# -*- coding: utf-8 -*-
"""Does any /drug page list the same /fda-decision twice, and does its count then overstate?"""
import io, os, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = "pdufa_site_src/drug"
bad = []
for slug in sorted(os.listdir(SITE)):
    p = os.path.join(SITE, slug, "index.html")
    if not os.path.isfile(p):
        continue
    t = io.open(p, encoding="utf-8", errors="replace").read()
    links = re.findall(r'href="(/fda-decision/[A-Z]{1,6}-\d{4}-\d{2}-\d{2})"', t)
    c = Counter(links)
    dupes = {k: v for k, v in c.items() if v > 1}
    m = re.search(r"(\d+) FDA decisions? (?:are |is )?on record", t)
    stated = int(m.group(1)) if m else None
    uniq = len(set(links))
    if dupes or (stated is not None and stated != uniq):
        bad.append((slug, stated, uniq, dict(list(dupes.items())[:2])))
print(f"{len(bad)} drug page(s) with a duplicated decision link or a count that overstates")
for b in bad[:25]:
    print(f"   /drug/{b[0]:<28} says {b[1]}  unique {b[2]}  dupes {b[3]}")
