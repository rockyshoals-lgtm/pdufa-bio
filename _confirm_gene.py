# -*- coding: utf-8 -*-
import re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 pdufa.bio builder rockyshoals@gmail.com"}
for u in sys.argv[1:]:
    try:
        t = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8", "replace")
    except Exception as e:
        print("ERR", u, e); continue
    t = re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", t)))
    print("==", u)
    for m in re.finditer(r"decision on approval|expected to make a decision|PDUFA|action date|decision by", t, re.I):
        print("   ...", t[max(0, m.start() - 250): m.end() + 120].strip()[:420]); print()
