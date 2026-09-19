# -*- coding: utf-8 -*-
import re, sys, json, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
def raw(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
def txt(u):
    return re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", raw(u).decode("utf-8", "replace"))))
t = txt("https://www.sec.gov/Archives/edgar/data/1861560/000119312526304126/d52896d8k.htm")
i = t.find("Merger")
print(t[max(0, i - 200): i + 1000])
print("-----")
u = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote('"neladalkib" "November 27"')
     + "&forms=8-K&dateRange=custom&startdt=2026-05-01&enddt=2026-07-31&ciks=0001861560")
j = json.loads(raw(u))
for h in j["hits"]["hits"][:6]:
    adsh, fn = h["_id"].split(":", 1)
    print(h["_source"]["file_date"], h["_source"]["form"], f"https://www.sec.gov/Archives/edgar/data/1861560/{adsh.replace('-', '')}/{fn}")
