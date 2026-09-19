# -*- coding: utf-8 -*-
import re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
for u in ["https://www.sec.gov/Archives/edgar/data/872589/000087258926000023/exhibit991q22026.htm",
          "https://www.sec.gov/Archives/edgar/data/1178670/000117867026000060/alny2026q2earningsrelease.htm"]:
    t = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8", "replace")
    t = re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+;", " ", re.sub(r"<[^>]+>", " ", t))))
    print("==", u[-50:])
    for m in re.finditer(r"target action date|PDUFA", t):
        win = t[max(0, m.start() - 350): m.end() + 200]
        if "cemdisiran" in win.lower() or "pozelimab" in win.lower():
            print("   ...", win.strip()[:560]); print()
