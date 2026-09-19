# -*- coding: utf-8 -*-
"""The two still-Upcoming quarter-end rows: SRRK apitegromab and NVO Mim8.

SRRK is the one that smells wrong. Every "apitegromab" + "target action date" hit in pass 1 was
a 2025 filing about September 22, 2025 -- apitegromab's ORIGINAL PDUFA date, a year before the
2026-09-30 we publish. So read Scholar Rock's 2026 8-Ks (2026-03-31, 2026-05-07, 2026-08-06)
and find what date, if any, is actually pending now. A row that is a wrong-year echo of a
decided 2025 event is worse than an imprecise one.

NVO: no Novo Nordisk filing mentions Mim8/denecimig with a PDUFA date at all -- the only hits
were Genmab's, and the Genmab passage was about epcoritamab, a different drug. Re-check with
the brand name Novo uses, in case the search term was the problem rather than the date.
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
             for x in d.get("hits", {}).get("hits", [])[:10]])


def doc_url(display, doc_id):
    m = re.search(r"CIK\s*(\d{10})", display)
    acc, _, fn = str(doc_id).partition(":")
    return (f"https://www.sec.gov/Archives/edgar/data/{int(m.group(1))}/"
            f"{acc.replace('-', '')}/{fn}") if m else None


def read(url, needles, w=(360, 320)):
    try:
        raw = get(url)
    except Exception as e:  # noqa: BLE001
        return [f"FETCH ERROR {e}"]
    txt = re.sub(r"\s+", " ", re.sub(r"&#x?\w+;|&nbsp;|&amp;", " ",
                                     re.sub(r"<[^>]+>", " ", raw)))
    out = []
    for n in needles:
        for m in re.finditer(n, txt, re.I):
            out.append(f"[{n}] ..." + txt[max(0, m.start() - w[0]):m.end() + w[1]].strip() + "...")
            break
    return out or ["(no needle matched)"]


o = io.open("_verify_srrk_nvo.txt", "w", encoding="utf-8")

o.write("=== SRRK apitegromab: what is pending in 2026?\n")
seen = set()
for phrase in ['"apitegromab" "target action date"', '"apitegromab" "PDUFA"',
               '"apitegromab" "Complete Response"', '"apitegromab" "resubmission"']:
    total, hits = fts(phrase)
    o.write(f"\n-- {phrase}: total={total}\n")
    for disp, form, fdate, did in hits:
        if "Scholar Rock" not in disp or not str(fdate).startswith("2026"):
            continue
        if did in seen:
            continue
        seen.add(did)
        u = doc_url(disp, did)
        o.write(f"\n  {form} {fdate}\n  {u}\n")
        for s in read(u, [r"target action date[^.]{0,120}",
                          r"PDUFA[^.]{0,160}", r"Complete Response[^.]{0,160}",
                          r"resubmi\w+[^.]{0,160}"]):
            o.write("    " + s[:800] + "\n")

o.write("\n\n=== NVO Mim8 / denecimig: any Novo filing at all\n")
for phrase in ['"Mim8"', '"denecimig"', '"denecimig" "Novo"', '"Mim8" "Novo Nordisk"']:
    total, hits = fts(phrase)
    o.write(f"\n-- {phrase}: total={total}\n")
    for h in hits:
        o.write(f"    {h[0][:60]} | {h[1]} | {h[2]}\n")

o.close()
print("done")
