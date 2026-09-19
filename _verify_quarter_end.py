# -*- coding: utf-8 -*-
"""The four December 31 rows were not the whole set.

Extending the guard to quarter-end days surfaced NINE more day-precision PDUFAs sitting on
06-30 and 09-30 with no source_url -- the identical shape the auditor caught at 12-31. Before
shipping a guard that would fail on them, settle each one against EDGAR full-text the same way.

For each: search the drug name with "target action date" and with "PDUFA", print the sponsor,
form, date and accession of every hit, and fetch the top hit's document to read the sentence.
A hit from a third party (a law firm, an index, another sponsor) does not source our row --
only the sponsor's own filing does, so display_names is printed for every hit.

Non-registrant caveat repeats here: TAK and AZN and NVO file 6-K/20-F so EDGAR sees them; a
private or foreign-only filer would return null for reasons that are not evidence.
"""
import io
import json
import re
import urllib.parse
import urllib.request

UA = "pdufa.bio builder rockyshoals@gmail.com"

ROWS = [
    ("AZN", "2026-06-30", "Truqap", ["capivasertib", "Truqap"]),
    ("IONS", "2026-06-30", "Olezarsen", ["olezarsen"]),
    ("VRDN", "2026-06-30", "Veligrotug", ["veligrotug"]),
    ("NVO", "2026-09-30", "Mim8 denecimig", ["denecimig", "Mim8"]),
    ("PFE", "2026-09-30", "Brepocitinib", ["brepocitinib"]),
    ("PTGX", "2026-09-30", "Rusfertide", ["rusfertide"]),
    ("ROIV", "2026-09-30", "Brepocitinib", ["brepocitinib"]),
    ("SRRK", "2026-09-30", "Apitegromab", ["apitegromab"]),
    ("TAK", "2026-09-30", "Oveporexton", ["oveporexton", "TAK-861"]),
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "identity"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")


def fts(phrase, forms="8-K,10-Q,10-K,6-K,20-F"):
    url = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(phrase)
           + "&forms=" + forms)
    try:
        d = json.loads(get(url))
    except Exception as e:  # noqa: BLE001
        return f"ERROR {e}", []
    h = d.get("hits", {})
    return (h.get("total", {}).get("value", 0),
            [(", ".join(x["_source"].get("display_names", []))[:50],
              x["_source"].get("form"), x["_source"].get("file_date"), x.get("_id"))
             for x in h.get("hits", [])[:6]])


def sentence(doc_id, cik_hint, needles):
    acc, _, fn = str(doc_id).partition(":")
    m = re.match(r"(\d{10})-", acc)
    cik = str(int(m.group(1))) if m else cik_hint
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{fn}"
    try:
        raw = get(url)
    except Exception as e:  # noqa: BLE001
        return url, [f"FETCH ERROR {e}"]
    txt = re.sub(r"\s+", " ", re.sub(r"&#\d+;|&nbsp;|&amp;", " ",
                                     re.sub(r"<[^>]+>", " ", raw)))
    out = []
    for n in needles:
        m2 = re.search(re.escape(n), txt, re.I)
        if m2:
            out.append("..." + txt[max(0, m2.start() - 300):m2.end() + 260].strip() + "...")
    return url, out or ["(needle not found)"]


o = io.open("_verify_quarter_end.txt", "w", encoding="utf-8")
for tk, d, label, names in ROWS:
    o.write(f"\n{'=' * 78}\n=== {tk} {d} {label}\n")
    best = None
    for nm in names:
        for suffix in ('"target action date"', '"PDUFA"'):
            phrase = f'"{nm}" {suffix}'
            total, hits = fts(phrase)
            o.write(f"  {phrase}: total={total}\n")
            for h in hits:
                o.write(f"    {h}\n")
            if hits and best is None and total:
                best = (hits[0][3], hits[0][0])
    if best:
        url, sents = sentence(best[0], "0", [d.replace("2026-06-30", "June 30, 2026")
                                             .replace("2026-09-30", "September 30, 2026"),
                                             "target action date", "PDUFA"])
        o.write(f"  -> top hit ({best[1]}): {url}\n")
        for s in sents:
            o.write("     " + s[:700] + "\n")
o.close()
print("done")
