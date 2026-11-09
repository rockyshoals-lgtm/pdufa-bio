# -*- coding: utf-8 -*-
"""apply_1108_fill_quotes.py -- verify each quote-less upcoming PDUFA row against its own source and store the sentence.

2026-11-08 date audit: 51 of 62 pending PDUFA rows carry the sentence from the sponsor's document that states their
date; 10 carried a source link but no quote, so their event pages could show "Source:" but not what it says, and the
date had not been re-read against the document. This fetches each row's source_url, finds the sentence that states the
row's date (or month, for month-precision rows), stores it as source_quote, and REPORTS any row whose document does not
state its date instead of writing anything for it. Facts only.
"""
import datetime as dt
import html
import io
import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
M = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
     "December"]
UA = {"User-Agent": "pdufa.bio-research-script/1.0"}

s = io.open(P, encoding="utf-8").read()
i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
for r in rows:
    d = r.get("_d") or {}
    if r.get("type") != "PDUFA" or r.get("st") not in ("Upcoming", "Awaiting") or d.get("source_quote"):
        continue
    url = str(d.get("source_url") or "")
    if not url.startswith("http"):
        print(f"  no source url  {r['id']}"); continue
    try:
        t = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        print(f"  fetch failed   {r['id']} {e}"); continue
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
    y, m, dd = int(r["d"][:4]), int(r["d"][5:7]), int(r["d"][8:10])
    pats = ([rf"{M[m-1]} {dd}(?:st|nd|rd|th)?,? {y}", rf"{dd} {M[m-1]} {y}"] if r.get("dp", "day") == "day"
            else [rf"{M[m-1]} {y}", rf"(?:fourth|4th|Q4)[^.]{{0,30}}{y}"])
    hit = None
    for pat in pats:
        for mm in re.finditer(pat, t):
            a = max(t.rfind(". ", 0, mm.start()), t.rfind("•", 0, mm.start()), mm.start() - 220) + 1
            b = t.find(".", mm.end())
            b = mm.end() if b < 0 or b - mm.end() > 120 else b + 1
            cand = t[a:b].strip(" •")
            if re.search(r"PDUFA|action date|goal date|decision", cand, re.I):
                hit = cand; break
        if hit:
            break
    if hit:
        d["source_quote"] = hit[:300]
        print(f"  OK  {r['id']:32s} {hit[:140]}")
    else:
        print(f"  !!  {r['id']:32s} {r['d']} ({r.get('dp')}) NOT stated in {url}")
io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
