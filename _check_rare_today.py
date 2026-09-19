# -*- coding: utf-8 -*-
"""RARE UX111 (ABO-102) goal date is TODAY 2026-09-19. Any FDA action or Ultragenyx 8-K yet?"""
import json, re, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()


print("== openFDA: any UX111 / ABO-102 / Sanfilippo BLA ==")
for q in ('openfda.generic_name:"UX111"', 'openfda.brand_name:"UX111"', 'openfda.substance_name:"ABO-102"'):
    try:
        j = json.loads(get("https://api.fda.gov/drug/drugsfda.json?search=" + urllib.parse.quote(q) + "&limit=3"))
        print("  ", q, "->", len(j.get("results", [])), "result(s)")
    except Exception as e:
        print("  ", q, "->", e)

print("\n== EDGAR: Ultragenyx 8-Ks filed since 2026-09-15 ==")
u = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote('"Ultragenyx"') +
     "&forms=8-K&dateRange=custom&startdt=2026-09-15&enddt=2026-09-19&ciks=0001515673")
try:
    j = json.loads(get(u))
    hits = j["hits"]["hits"]
    print("  ", len(hits), "hit(s)")
    for h in hits[:6]:
        s = h["_source"]; adsh, fn = h["_id"].split(":", 1)
        print("   ", s["file_date"], s["form"], s.get("file_description"),
              f"https://www.sec.gov/Archives/edgar/data/1515673/{adsh.replace('-', '')}/{fn}")
except Exception as e:
    print("   EDGAR:", e)

print("\n== FDA press releases feed: anything today naming Ultragenyx / Sanfilippo / UX111 ==")
try:
    t = get("https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml").decode("utf-8", "replace")
    for m in re.finditer(r"<item>(.*?)</item>", t, re.S):
        it = m.group(1)
        if re.search(r"Ultragenyx|Sanfilippo|UX111|MPS III", it, re.I):
            ti = re.search(r"<title>(.*?)</title>", it, re.S); pd = re.search(r"<pubDate>(.*?)</pubDate>", it)
            print("   HIT:", pd.group(1) if pd else "", "|", ti.group(1)[:120] if ti else "")
    print("   (scan complete)")
except Exception as e:
    print("   feed:", e)
