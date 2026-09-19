# -*- coding: utf-8 -*-
import io, json, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
for r in rows:
    if r["id"] in ("pdufa_rare_2026-09-19", "pdufa_mrk_2026-09-21", "pdufa_incy_2026-09-26"):
        d = r.get("_d") or {}
        print(r["id"], "|", {k: (str(v)[:90]) for k, v in d.items() if k in ("source", "source_url", "source_url_2", "date_provenance", "review", "accession")})

def efts(q, forms="8-K", start="2026-01-01", end="2026-09-15"):
    u = f"https://efts.sec.gov/LATEST/search-index?q={urllib.parse.quote(q)}&forms={forms}&dateRange=custom&startdt={start}&enddt={end}"
    j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read())
    for h in j["hits"]["hits"][:8]:
        s = h["_source"]; adsh, fn = h["_id"].split(":", 1)
        cik = re.search(r"CIK (\d+)", s["display_names"][0]).group(1)
        print("   ", s["file_date"], s["form"], s["display_names"][0][:40], f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh.replace('-', '')}/{fn}")
import urllib.parse
print("== RARE UX111 September 19")
efts('"September 19, 2026" "UX111"', "8-K,10-Q", "2026-03-01")
print("== MRK sotatercept HYPERION September 21")
efts('"September 21, 2026" "sotatercept"', "8-K,10-Q,10-K", "2026-01-01")
