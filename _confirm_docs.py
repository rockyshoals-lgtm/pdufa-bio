# -*- coding: utf-8 -*-
"""Fetch candidate filings and print every PDUFA/target-date sentence mentioning the drug."""
import re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
DOCS = {
    "NUVL neladalkib": ["https://www.sec.gov/Archives/edgar/data/1861560/000186156026000020/nuvl-ex99_1.htm",
                        "https://www.sec.gov/Archives/edgar/data/1861560/000186156026000021/nuvl-20260331.htm"],
    "REGN cemdisiran": ["https://www.sec.gov/Archives/edgar/data/872589/000087258926000014/exhibit991q12026.htm",
                        "https://www.sec.gov/Archives/edgar/data/872589/000087258926000016/regn-20260331.htm"],
    "GSK bepirovirsen": ["https://www.sec.gov/Archives/edgar/data/1131399/000119312526384439/d331501d6k.htm",
                         "https://www.sec.gov/Archives/edgar/data/1131399/000165495426006949/a1493o.htm"],
}
for label, urls in DOCS.items():
    drug = label.split()[1]
    for u in urls:
        try:
            t = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read().decode("utf-8", "replace")
        except Exception as e:
            print(label, u, "ERR", e); continue
        t = re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", t)))
        print(f"== {label} | {u[-45:]}")
        n = 0
        for m in re.finditer(r"PDUFA|target action date|goal date", t):
            win = t[max(0, m.start() - 350): m.end() + 250]
            if drug.lower()[:8] in win.lower():
                n += 1
                if n <= 3:
                    print("   ...", win.strip()[:520])
        if not n:
            print("   (no PDUFA sentence naming the drug)")
