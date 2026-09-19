# -*- coding: utf-8 -*-
import re, sys, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
DOCS = [
    ("Merck 8-K 2026-02-03 EX-99.1", "https://www.sec.gov/Archives/edgar/data/310158/000110465926009495/tm264564d1_ex99-1.htm"),
    ("Merck 10-Q Q2 2026-08-07", "https://www.sec.gov/Archives/edgar/data/310158/000031015826000212/mrk-20260630.htm"),
    ("Merck 10-Q Q1 2026-05-04", "https://www.sec.gov/Archives/edgar/data/310158/000162828026029802/mrk-20260331.htm"),
]
for label, u in DOCS:
    for attempt in range(3):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=70).read()
            break
        except Exception as e:
            if attempt == 2:
                print(f"== {label}: FETCH FAILED {e}"); raw = None
            time.sleep(3 * (attempt + 1))
    if not raw:
        continue
    t = re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", raw.decode("utf-8", "replace"))))
    print(f"\n== {label}")
    hits = 0
    for mm in re.finditer(r"enlicitide|Lipfendra|MK-0616", t, re.I):
        seg = t[max(0, mm.start() - 420): mm.end() + 420]
        if re.search(r"PDUFA|target action date|action date|approved", seg, re.I):
            hits += 1
            print(f"   ...{seg.strip()[:700]}\n")
            if hits >= 2:
                break
    if not hits:
        print("   (drug named, but never within 420 chars of a PDUFA/action-date/approval phrase)")
    time.sleep(1)
