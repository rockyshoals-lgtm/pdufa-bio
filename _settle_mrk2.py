# -*- coding: utf-8 -*-
import json, re, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
def http(u, t=60): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()
def clean(b): return re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", b.decode("utf-8", "replace"))))
def efts(q, forms="8-K,10-Q,10-K", start="2025-06-01", end="2026-09-18"):
    u = f"https://efts.sec.gov/LATEST/search-index?q={urllib.parse.quote(q)}&forms={forms}&dateRange=custom&startdt={start}&enddt={end}"
    return json.loads(http(u))["hits"]["hits"]

for q in ['"enlicitide" "July 16"', '"Lipfendra"']:
    print(f"\n######## {q}")
    for h in efts(q)[:3]:
        s = h["_source"]; adsh, fn = h["_id"].split(":", 1)
        cik = re.search(r"CIK (\d+)", s["display_names"][0]).group(1)
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh.replace('-', '')}/{fn}"
        print(f"\n-- {s['file_date']} {s['form']} {s['display_names'][0][:34]}\n   {url}")
        try:
            t = clean(http(url))
        except Exception as e:
            print("   fetch:", e); continue
        for key in ("July 16", "Lipfendra"):
            for mm in list(re.finditer(re.escape(key), t))[:3]:
                print(f"   [{key}] ...{t[max(0, mm.start()-330): mm.end()+330].strip()[:640]}")
