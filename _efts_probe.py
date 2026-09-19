# -*- coding: utf-8 -*-
import json, re, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
def efts(q, forms="8-K,10-Q,10-K,6-K", start="2026-01-01", end="2026-09-15"):
    u = f"https://efts.sec.gov/LATEST/search-index?q={urllib.parse.quote(q)}&forms={forms}&dateRange=custom&startdt={start}&enddt={end}"
    j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read())
    print(f"== {q}: {j['hits']['total']['value']} hits")
    for h in j["hits"]["hits"][:8]:
        s = h["_source"]; adsh, fn = h["_id"].split(":", 1)
        cik = re.search(r"CIK (\d+)", s["display_names"][0]).group(1)
        print("  ", s["file_date"], s["form"], s["display_names"][0][:38], f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh.replace('-','')}/{fn}")
for q in sys.argv[1:]:
    efts(q)
