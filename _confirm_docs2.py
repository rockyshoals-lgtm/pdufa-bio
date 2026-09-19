# -*- coding: utf-8 -*-
import re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
DOCS = [
    ("bepirovirsen", "October 26, 2026", "https://www.sec.gov/Archives/edgar/data/874015/000114036126029960/ef20078953_ex99-1.htm"),
    ("neladalkib", "November 27, 2026", "https://www.sec.gov/Archives/edgar/data/1802768/000180276826000014/rprx-20260630rpplcpressxre.htm"),
    ("Ultomiris", "December 2026", "https://www.sec.gov/Archives/edgar/data/901832/000110465926086846/azn-20260630x6k.htm"),
    ("Ultomiris", "December 2026", "https://www.sec.gov/Archives/edgar/data/901832/000165495426004047/a2999c.htm"),
]
for drug, phrase, u in DOCS:
    try:
        t = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8", "replace")
    except Exception as e:
        print(drug, u, "ERR", e); continue
    t = re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", t)))
    print(f"== {drug} / {phrase} | {u[-48:]}")
    n = 0
    for m in re.finditer(re.escape(phrase), t):
        win = t[max(0, m.start() - 400): m.end() + 200]
        if drug.lower() in win.lower():
            n += 1
            if n <= 3:
                print("   ...", win.strip()[:600])
    if not n:
        print("   (phrase not within 400 chars of the drug)")
