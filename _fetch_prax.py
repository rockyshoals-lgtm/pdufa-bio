# -*- coding: utf-8 -*-
import re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
for url in ["https://www.sec.gov/Archives/edgar/data/1689548/000168954826000082/praxisq22026pr.htm",
            "https://www.sec.gov/Archives/edgar/data/1689548/000168954826000069/prax-20260629.htm"]:
    t = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "replace")
    t = re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", t)))
    print("==", url)
    for m in re.finditer(r"PDUFA|target action date", t):
        print("  ...", t[max(0, m.start()-300):m.end()+200])
        print()
