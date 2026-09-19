# -*- coding: utf-8 -*-
"""Read the FDA's own approval letter for sevabertinib SUPPL-1 and show our row beside it."""
import io
import json
import re
import urllib.request

UA = "pdufa.bio builder rockyshoals@gmail.com"
LETTER = ("https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/"
          "219972Orig1s001ltr.pdf")

src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8",
              errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
print("OUR BAYRY ROWS:")
for r in rows:
    if str(r.get("t") or "").upper() == "BAYRY":
        dd = r.get("_d") or {}
        print(f"  {r.get('type'):<8} d={r.get('d')} dp={r.get('dp')} st={r.get('st')} "
              f"| {r.get('name')}")
        print(f"      indication={dd.get('indication')}  source={dd.get('source_url')}")
        print(f"      review={str(dd.get('review'))[:200]}")

print(f"\nFDA APPROVAL LETTER {LETTER}")
try:
    req = urllib.request.Request(LETTER, headers={"User-Agent": UA})
    raw = req and urllib.request.urlopen(req, timeout=60).read()
    txt = raw.decode("latin-1", "replace")
    # crude PDF text extraction: pull readable runs out of the content streams
    chunks = re.findall(r"\(([^)\\]{3,120})\)", txt)
    joined = " ".join(chunks)
    joined = re.sub(r"\s+", " ", joined)
    for key in ["INDICATION", "indicated for", "supplemental new drug application",
                "approve", "HYRNUO"]:
        m = re.search(re.escape(key), joined, re.I)
        if m:
            print(f"  [{key}] ...{joined[max(0, m.start()-200):m.end()+420]}...")
except Exception as e:  # noqa: BLE001
    print(f"  FETCH/PARSE ERROR {e}")
