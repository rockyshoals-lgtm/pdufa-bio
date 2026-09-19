# -*- coding: utf-8 -*-
"""Last two quarter-end rows: NVO denecimig (Mim8) and AZN Truqap (capivasertib).

Both were "no source found" in the earlier sweeps, but in each case the earlier sweep had a
weakness worth closing before I downgrade a published date:

NVO -- pass 1 searched '"denecimig" "target action date"' and got only a Genmab hit, whose
passage turned out to be about epcoritamab. But Novo Nordisk DOES file, and five Novo filings
name denecimig (6-K 2026-08-04, 6-K 2026-05-06, 6-K 2026-02-03, 6-K 2026-02-04, 20-F
2026-02-04). Read them for a date rather than concluding from a phrase search that missed.

AZN -- pass 2 fetched three AstraZeneca 6-Ks and matched no needle, but I only looked for
"June 30, 2026" and "target action date". AstraZeneca's house style is often "PDUFA date" or
"action date in H1 2026" or a quarter. Read the 2026 filings and look for any capivasertib /
Truqap regulatory sentence at all, then judge.

The AZN row is DECIDED (approved 2026-06-12), so its goal date is not a forward-looking claim
-- but it still feeds /research/fda-decision-timing as "18 days early", so a manufactured goal
date there is a contaminated statistic, not a harmless one.
"""
import io
import json
import re
import urllib.parse
import urllib.request

UA = "pdufa.bio builder rockyshoals@gmail.com"

NVO_DOCS = [("353278", "0001104659-26-090086"), ("353278", "0001104659-26-000000")]


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


def read(url, pats, w=(300, 300)):
    try:
        raw = get(url)
    except Exception as e:  # noqa: BLE001
        return [f"FETCH ERROR {e}"]
    txt = re.sub(r"\s+", " ", re.sub(r"&#x?\w+;|&nbsp;|&amp;", " ",
                                     re.sub(r"<[^>]+>", " ", raw)))
    out = []
    for p in pats:
        for m in re.finditer(p, txt, re.I):
            out.append("..." + txt[max(0, m.start() - w[0]):m.end() + w[1]].strip() + "...")
            if len(out) > 6:
                break
    return out or ["(no pattern matched)"]


o = io.open("_verify_nvo_azn.txt", "w", encoding="utf-8")

o.write("=== NVO denecimig / Mim8: read Novo's own filings\n")
done = 0
for phrase in ['"denecimig"', '"Mim8" "haemophilia"', '"Mim8"']:
    total, hits = fts(phrase)
    for disp, form, fdate, did in hits:
        if "NOVO" not in disp.upper() or not str(fdate).startswith("2026"):
            continue
        u = doc_url(disp, did)
        if not u:
            continue
        o.write(f"\n  {form} {fdate}\n  {u}\n")
        for s in read(u, [r"denecimig[^.]{0,260}", r"Mim8[^.]{0,260}",
                          r"(?:PDUFA|action date)[^.]{0,200}"]):
            o.write("    " + s[:760] + "\n")
        done += 1
        if done >= 3:
            break
    if done >= 3:
        break

o.write("\n\n=== AZN capivasertib / Truqap: any 2026 regulatory sentence\n")
done = 0
for phrase in ['"capivasertib" "PDUFA"', '"Truqap" "PDUFA"',
               '"capivasertib" "action date"', '"Truqap" "prostate"']:
    total, hits = fts(phrase)
    o.write(f"\n-- {phrase}: total={total}\n")
    for disp, form, fdate, did in hits:
        if "ASTRAZENECA" not in disp.upper() or not str(fdate).startswith("202"):
            continue
        u = doc_url(disp, did)
        if not u:
            continue
        o.write(f"\n  {form} {fdate}\n  {u}\n")
        for s in read(u, [r"capivasertib[^.]{0,240}", r"Truqap[^.]{0,240}"]):
            o.write("    " + s[:700] + "\n")
        done += 1
        if done >= 3:
            break
    if done >= 3:
        break

o.close()
print("done")
