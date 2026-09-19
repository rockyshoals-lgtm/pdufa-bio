# -*- coding: utf-8 -*-
"""For each of the 9 'landed on the goal date' rows, ask EDGAR whether the SPONSOR ever stated a
PDUFA goal date, and what day it was. If the stated goal differs from the action date, the row's
goal date was filled from its decision date and the statistic's 'on the day' bucket is an artefact.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}

NINE = [
    ("ARQT", "2026-06-29", "ZORYVE roflumilast cream 0.3%", "roflumilast"),
    ("VERA", "2026-07-07", "Atacicept (ORIGIN 3)", "atacicept"),
    ("MRK",  "2026-07-16", "Lipfendra (enlicitide)", "enlicitide"),
    ("OTSKY", "2026-07-24", "Centanafadine", "centanafadine"),
    ("MRNA", "2026-08-05", "MFLUSIVA influenza mRNA", "mRNA-1010"),
    ("LNTH", "2026-08-13", "MK-6240 (Lantheus)", "MK-6240"),
    ("JAZZ", "2026-08-25", "Ziihera zanidatamab", "zanidatamab"),
    ("ZYME", "2026-08-25", "Ziihera zanidatamab", "zanidatamab"),
    ("GILD", "2026-08-27", "Bictegravir + Lenacapavir", "bictegravir"),
]
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August",
       "September", "October", "November", "December"]


def http(u, t=45):
    for i in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()
        except Exception:
            if i == 2:
                raise
            time.sleep(1.2 * (i + 1))


def efts(q, forms="8-K,10-Q,10-K,6-K,20-F", start="2025-06-01", end="2026-09-18"):
    u = (f"https://efts.sec.gov/LATEST/search-index?q={urllib.parse.quote(q)}&forms={forms}"
         f"&dateRange=custom&startdt={start}&enddt={end}")
    return json.loads(http(u))["hits"]["hits"]


def clean(b):
    return re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", b.decode("utf-8", "replace"))))


for tk, d, label, drug in NINE:
    print(f"\n=== {tk} {d}  {label}")
    found = []
    try:
        hits = efts(f'"{drug}" "PDUFA"')
    except Exception as e:
        print("   search error:", e)
        continue
    seen = set()
    for h in hits[:8]:
        s = h["_source"]
        adsh, fn = h["_id"].split(":", 1)
        m = re.search(r"CIK (\d+)", s["display_names"][0])
        if not m or adsh in seen:
            continue
        seen.add(adsh)
        url = f"https://www.sec.gov/Archives/edgar/data/{int(m.group(1))}/{adsh.replace('-', '')}/{fn}"
        try:
            t = clean(http(url))
        except Exception:
            continue
        for mm in re.finditer(r"PDUFA[^.]{0,120}?((?:January|February|March|April|May|June|July|August|"
                              r"September|October|November|December) \d{1,2},? \d{4})", t):
            if drug.lower()[:7] in t[max(0, mm.start() - 700): mm.end() + 300].lower():
                found.append((s["file_date"], s["form"], mm.group(1), url))
        if found:
            break
        time.sleep(0.3)
    if not found:
        print("   NO sponsor filing states a PDUFA date for this drug (EDGAR full-text)")
        continue
    for fd, form, datestr, url in found[:3]:
        try:
            p = re.match(r"([A-Za-z]+) (\d{1,2}),? (\d{4})", datestr)
            iso = f"{p.group(3)}-{MON.index(p.group(1)):02d}-{int(p.group(2)):02d}"
        except Exception:
            iso = "?"
        verdict = "MATCHES our goal date" if iso == d else f"DIFFERS from our goal date {d}"
        print(f"   {fd} {form}: PDUFA '{datestr}' -> {iso}   *** {verdict} ***")
        print(f"      {url}")
