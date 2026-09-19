# -*- coding: utf-8 -*-
"""Second pass on the quarter-end rows. First pass 404'd on seven of nine.

The bug: I built the Archives path from the accession-number prefix, which is the FILING
AGENT's CIK (0001654954 is a filing agent, not AstraZeneca). EDGAR needs the subject company's
CIK. That is in the display_names string -- "ASTRAZENECA PLC (AZN) (CIK 0000901832)" -- so
parse it from there instead of inferring it.

Two rows are already settled from pass 1 and are NOT re-queried:
  TAK oveporexton  -- Takeda 6-K 2026-02-10: "The Prescription Drug User Fee Act (PDUFA)
                      Target Action Date is the Third Quarter of this Calendar Year."
  PTGX rusfertide  -- Takeda/Protagonist 6-K 2026-03-02: "Prescription Drug User Fee Act
                      (PDUFA) Target Action Date is in the Third Quarter of this Calendar
                      Year."
Both sponsors state a QUARTER. We publish 2026-09-30 at day precision. The last day of the
stated quarter is exactly the manufactured-day defect, in the sponsor's own words.
"""
import io
import json
import re
import urllib.parse
import urllib.request

UA = "pdufa.bio builder rockyshoals@gmail.com"

# (our ticker, our date, search names, which filer's filing would source it)
ROWS = [
    ("AZN", "2026-06-30", ["Truqap", "capivasertib"], "ASTRAZENECA"),
    ("IONS", "2026-06-30", ["olezarsen"], "IONIS"),
    ("VRDN", "2026-06-30", ["veligrotug"], "Viridian"),
    ("NVO", "2026-09-30", ["denecimig", "Mim8"], "NOVO"),
    ("PFE", "2026-09-30", ["brepocitinib"], "Roivant"),
    ("ROIV", "2026-09-30", ["brepocitinib"], "Roivant"),
    ("SRRK", "2026-09-30", ["apitegromab"], "Scholar Rock"),
]

MONTH = {"2026-06-30": "June 30, 2026", "2026-09-30": "September 30, 2026"}


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
        return 0, []
    return (d.get("hits", {}).get("total", {}).get("value", 0),
            [(", ".join(x["_source"].get("display_names", [])),
              x["_source"].get("form"), x["_source"].get("file_date"), x.get("_id"))
             for x in d.get("hits", {}).get("hits", [])[:8]])


def doc_url(display, doc_id):
    m = re.search(r"CIK\s*(\d{10})", display)
    if not m:
        return None
    acc, _, fn = str(doc_id).partition(":")
    return (f"https://www.sec.gov/Archives/edgar/data/{int(m.group(1))}/"
            f"{acc.replace('-', '')}/{fn}")


def read(url, needles, window=(340, 300)):
    try:
        raw = get(url)
    except Exception as e:  # noqa: BLE001
        return [f"FETCH ERROR {e}"]
    txt = re.sub(r"\s+", " ", re.sub(r"&#\d+;|&nbsp;|&amp;", " ",
                                     re.sub(r"<[^>]+>", " ", raw)))
    out = []
    for n in needles:
        for m in re.finditer(re.escape(n), txt, re.I):
            out.append(f"[{n}] ..."
                       + txt[max(0, m.start() - window[0]):m.end() + window[1]].strip() + "...")
            break
    return out or ["(no needle matched)"]


o = io.open("_verify_quarter_end2.txt", "w", encoding="utf-8")
for tk, d, names, filer in ROWS:
    o.write(f"\n{'=' * 78}\n=== {tk} {d}  (want a {filer} filing)\n")
    seen = set()
    for nm in names:
        for suffix in ('"target action date"', '"PDUFA"'):
            total, hits = fts(f'"{nm}" {suffix}')
            for disp, form, fdate, did in hits:
                if filer.lower() not in disp.lower() or did in seen:
                    continue
                seen.add(did)
                u = doc_url(disp, did)
                if not u:
                    continue
                o.write(f"\n  {form} {fdate}  {disp[:60]}\n  {u}\n")
                for s in read(u, [MONTH[d], "target action date", "Target Action Date"]):
                    o.write("    " + s[:820] + "\n")
                if len(seen) >= 3:
                    break
            if len(seen) >= 3:
                break
        if len(seen) >= 3:
            break
    if not seen:
        o.write(f"  NO {filer} filing among the hits.\n")
o.close()
print("done")
