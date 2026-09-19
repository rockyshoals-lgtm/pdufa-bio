# -*- coding: utf-8 -*-
"""Verify the CORT relacorilant (Cushing's) PDUFA date against Corcept's own filing."""
import io
import json
import re
import urllib.parse
import urllib.request

UA = "pdufa.bio builder rockyshoals@gmail.com"


def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    return urllib.request.urlopen(r, timeout=60).read().decode("utf-8", "replace")


def fts(q):
    u = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(q)
         + "&forms=8-K,10-Q")
    d = json.loads(get(u))
    return [(", ".join(x["_source"].get("display_names", [])), x["_source"].get("form"),
             x["_source"].get("file_date"), x.get("_id"))
            for x in d.get("hits", {}).get("hits", [])[:6]]


out = io.open("_verify_cort.txt", "w", encoding="utf-8")
for q in ['"relacorilant" "December 17, 2026"', '"relacorilant" "PDUFA" "Cushing"']:
    out.write(f"\n== {q}\n")
    for disp, form, fdate, did in fts(q):
        out.write(f"  {form} {fdate} {disp[:50]}\n")
        if "CORCEPT" not in disp.upper():
            continue
        m = re.search(r"CIK\s*(\d{10})", disp)
        acc, _, fn = did.partition(":")
        u = f"https://www.sec.gov/Archives/edgar/data/{int(m.group(1))}/{acc.replace('-', '')}/{fn}"
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", get(u)))
        for pat in [r"December 17, 2026", r"PDUFA[^.]{0,200}", r"Cushing[^.]{0,120}"]:
            mm = re.search(pat, t)
            if mm:
                out.write(f"    [{pat[:18]}] ...{t[max(0, mm.start()-260):mm.end()+200]}...\n")
        out.write(f"    {u}\n")
        break
out.close()
print("done")
