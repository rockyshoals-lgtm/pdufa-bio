# -*- coding: utf-8 -*-
"""Verify the 09-10b ORDER's date claims against EDGAR, first-hand.

Items 1-3. The auditor supplied quotes and accession numbers for VRTX and MIRM, and reported
no sponsor filing for ABBV tavapadon or NVO CagriSema. House rule 8 says a supplied quote is
a lead until I read the filing, so this fetches each document and prints the sentence, and
re-runs the negative searches rather than inheriting them.

Also checks the fourth December 31 row (AZN Ultomiris IgAN) that was never tested, and notes
where EDGAR cannot answer: BAYRY (Bayer) is not an SEC registrant, so a null result there is
not evidence of anything.
"""
import io
import json
import re
import urllib.parse
import urllib.request

UA = "pdufa.bio builder rockyshoals@gmail.com"
FTS = "https://efts.sec.gov/LATEST/search-index?q={q}&forms={f}"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "identity"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")


def fts(phrase, forms="8-K,10-Q,10-K,6-K,20-F"):
    url = FTS.format(q=urllib.parse.quote(phrase), f=forms)
    try:
        d = json.loads(get(url))
    except Exception as e:  # noqa: BLE001
        return f"FTS ERROR {e}", []
    hits = d.get("hits", {}).get("hits", [])
    total = d.get("hits", {}).get("total", {}).get("value", 0)
    rows = []
    for h in hits[:8]:
        s = h.get("_source", {})
        rows.append((", ".join(s.get("display_names", []))[:52],
                     s.get("form"), s.get("file_date"), h.get("_id", "")))
    return total, rows


def sentence(url, needles):
    try:
        raw = get(url)
    except Exception as e:  # noqa: BLE001
        return [f"FETCH ERROR {e}"]
    txt = re.sub(r"<[^>]+>", " ", raw)
    txt = re.sub(r"&#\d+;|&nbsp;|&amp;", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    out = []
    for n in needles:
        for m in re.finditer(re.escape(n), txt, re.I):
            out.append("..." + txt[max(0, m.start() - 320):m.end() + 220].strip() + "...")
            break
    return out or ["(needles not found in extracted text)"]


o = io.open("_verify_0910b.txt", "w", encoding="utf-8")

o.write("=== ITEM 2: VRTX povetacicept, Vertex 8-K 2026-08-03, acc 0000875320-26-000256\n")
t, rows = fts('"povetacicept" "PDUFA target action date"')
o.write(f"  FTS total={t}\n")
for r in rows:
    o.write(f"    {r}\n")
for _, form, date, doc_id in rows[:3]:
    acc, _, fn = doc_id.partition(":")
    cik = "875320"
    u = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{fn}"
    o.write(f"  -> {u}\n")
    for s in sentence(u, ["PDUFA target action date", "November 30, 2026"]):
        o.write("     " + s[:700] + "\n")
    break

o.write("\n=== ITEM 3: MIRM zilurgisertib, Mirum 8-K 2026-08-05, acc 0001759425-26-000044\n")
t, rows = fts('"zilurgisertib" "Prescription Drug User Fee Act"')
o.write(f"  FTS total={t}\n")
for r in rows:
    o.write(f"    {r}\n")
for _, form, date, doc_id in rows[:3]:
    acc, _, fn = doc_id.partition(":")
    for cik in ("1759425", "879169"):
        u = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{fn}"
        got = sentence(u, ["September 26, 2026", "fibrodysplasia", "licensed zilurgisertib"])
        if not got[0].startswith("FETCH ERROR"):
            o.write(f"  -> {u}\n")
            for s in got:
                o.write("     " + s[:700] + "\n")
            break
    break

o.write("\n=== ITEM 1: the December 31 rows\n")
for label, phrase in [
        ("ABBV tavapadon", '"tavapadon" "PDUFA"'),
        ("NVO CagriSema", '"CagriSema" "PDUFA"'),
        ("AZN Ultomiris IgAN", '"Ultomiris" "PDUFA"'),
        ("BAYRY finerenone", '"finerenone" "PDUFA"')]:
    t, rows = fts(phrase)
    o.write(f"\n  {label}: FTS total={t}\n")
    for r in rows:
        o.write(f"    {r}\n")

o.close()
print("done")
