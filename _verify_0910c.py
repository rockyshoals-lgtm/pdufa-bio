# -*- coding: utf-8 -*-
"""Second pass: the exact Vertex 2026 document, and a narrowed AZN Ultomiris search.

First pass took hits[0] for VRTX, which was a 2024 8-K quoting 2025 goal dates -- right
company, wrong year, and a good example of why the accession has to be matched rather than
the search ranked.
"""
import io
import json
import re
import urllib.parse
import urllib.request

UA = "pdufa.bio builder rockyshoals@gmail.com"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "identity"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")


def sentence(url, needles, span=(320, 260)):
    try:
        raw = get(url)
    except Exception as e:  # noqa: BLE001
        return [f"FETCH ERROR {e}"]
    txt = re.sub(r"\s+", " ", re.sub(r"&#\d+;|&nbsp;|&amp;", " ",
                                     re.sub(r"<[^>]+>", " ", raw)))
    out = []
    for n in needles:
        m = re.search(re.escape(n), txt, re.I)
        if m:
            out.append("..." + txt[max(0, m.start() - span[0]):m.end() + span[1]].strip() + "...")
    return out or ["(needles not found)"]


def fts(phrase, forms="8-K,10-Q,10-K,6-K,20-F"):
    url = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(phrase)
           + "&forms=" + forms)
    try:
        d = json.loads(get(url))
    except Exception as e:  # noqa: BLE001
        return f"ERROR {e}", []
    hits = d.get("hits", {}).get("hits", [])
    return (d.get("hits", {}).get("total", {}).get("value", 0),
            [(", ".join(h["_source"].get("display_names", []))[:46],
              h["_source"].get("form"), h["_source"].get("file_date"), h.get("_id"))
             for h in hits[:8]])


o = io.open("_verify_0910c.txt", "w", encoding="utf-8")

o.write("=== VRTX povetacicept: the 2026-08-03 8-K, matched by accession\n")
u = ("https://www.sec.gov/Archives/edgar/data/875320/000087532026000256/"
     "ex-991_q22026.htm")
o.write(f"  {u}\n")
for s in sentence(u, ["povetacicept PDUFA date", "PDUFA target action date of November 30",
                      "November 30, 2026"]):
    o.write("   " + s[:760] + "\n")

o.write("\n=== AZN Ultomiris IgA nephropathy, narrowed\n")
for phrase in ['"Ultomiris" "IgA nephropathy" "PDUFA"',
               '"ravulizumab" "IgA nephropathy" "PDUFA"']:
    t, rows = fts(phrase)
    o.write(f"  {phrase}: total={t}\n")
    for r in rows:
        o.write(f"    {r}\n")

o.write("\n=== ABBV tavapadon / NVO CagriSema: any filing naming an acceptance at all\n")
for phrase in ['"tavapadon" "New Drug Application"', '"CagriSema" "New Drug Application"',
               '"tavapadon" "target action date"', '"CagriSema" "target action date"']:
    t, rows = fts(phrase)
    o.write(f"  {phrase}: total={t}\n")
    for r in rows[:5]:
        o.write(f"    {r}\n")

o.close()
print("done")
