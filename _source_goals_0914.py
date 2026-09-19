# -*- coding: utf-8 -*-
"""Try to SOURCE the three unsourced goal dates before downgrading any of them.

Sourcing beats downgrading. PHAR (2026-10-24 leniolisib), BFRI (2026-09-28 Ameluz) and BAYRY
(2026-11-30 sevabertinib) are all about to be marked Decided; whether their GOAL date is sourced
decides whether the decision may enter /research/fda-decision-timing as a real earliness
measurement. PHAR and BFRI are SEC filers, so EDGAR can settle them. Bayer is not, so its goal
will stay unsourced whatever this finds -- but the FDA letter already gives us the ACTION date,
which is the part that matters most.
"""
import io
import json
import re
import urllib.parse
import urllib.request

UA = "pdufa.bio builder rockyshoals@gmail.com"

CASES = [
    ("PHAR", "October 24, 2026", ['"leniolisib" "target action date"',
                                  '"leniolisib" "PDUFA"', '"Joenja" "PDUFA"']),
    ("BFRI", "September 28, 2026", ['"Ameluz" "target action date"',
                                    '"Ameluz" "PDUFA"',
                                    '"aminolevulinic" "PDUFA"']),
    ("BAYRY", "November 30, 2026", ['"sevabertinib" "target action date"',
                                    '"sevabertinib" "PDUFA"']),
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "identity"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")


def fts(phrase, forms="8-K,6-K,10-Q,10-K,20-F"):
    url = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(phrase)
           + "&forms=" + forms)
    try:
        d = json.loads(get(url))
    except Exception:  # noqa: BLE001
        return 0, []
    return (d.get("hits", {}).get("total", {}).get("value", 0),
            [(", ".join(x["_source"].get("display_names", [])),
              x["_source"].get("form"), x["_source"].get("file_date"), x.get("_id"))
             for x in d.get("hits", {}).get("hits", [])[:8]])


def doc_url(display, doc_id):
    m = re.search(r"CIK\s*(\d{10})", display)
    acc, _, fn = str(doc_id).partition(":")
    return (f"https://www.sec.gov/Archives/edgar/data/{int(m.group(1))}/"
            f"{acc.replace('-', '')}/{fn}") if m else None


def read(url, pats, w=(320, 340)):
    try:
        raw = get(url)
    except Exception as e:  # noqa: BLE001
        return [f"FETCH ERROR {e}"]
    txt = re.sub(r"\s+", " ", re.sub(r"&#x?\w+;|&nbsp;|&amp;", " ",
                                     re.sub(r"<[^>]+>", " ", raw)))
    out = []
    for p in pats:
        m = re.search(p, txt, re.I)
        if m:
            out.append("..." + txt[max(0, m.start() - w[0]):m.end() + w[1]].strip() + "...")
    return out or ["(no pattern matched)"]


o = io.open("_source_goals_0914.txt", "w", encoding="utf-8")
for tk, want, phrases in CASES:
    o.write(f"\n{'=' * 78}\n=== {tk}: looking for a filing that states '{want}'\n")
    hit = 0
    for ph in phrases:
        total, hits = fts(ph)
        o.write(f"  {ph}: total={total}\n")
        for disp, form, fdate, did in hits[:4]:
            o.write(f"    {form} {fdate} {disp[:52]}\n")
        for disp, form, fdate, did in hits[:4]:
            u = doc_url(disp, did)
            if not u:
                continue
            got = read(u, [re.escape(want), r"target action date[^.]{0,160}",
                           r"PDUFA[^.]{0,160}"])
            if any(want.lower() in g.lower() for g in got):
                o.write(f"\n    *** MATCH {form} {fdate} {disp[:50]}\n    {u}\n")
                for g in got:
                    o.write("      " + g[:700] + "\n")
                hit += 1
                break
        if hit:
            break
    if not hit:
        o.write(f"  NO filing found stating {want}\n")
o.close()
print("done")
