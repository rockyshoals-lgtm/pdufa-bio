# -*- coding: utf-8 -*-
"""TLX101-Px (Pixclara): its PDUFA goal date was 2026-09-11 and we carry no outcome.

A countdown that has run out is the worst row on the site, so this looks for an answer in both
places that could hold one: Telix's own filings (Nasdaq-listed, so 6-K/20-F) and the FDA's
approval database. A null result in both is itself the finding -- it means the decision is
genuinely pending or unannounced, and the row should read "Awaiting", not "Upcoming".
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


def fts(phrase, forms="6-K,20-F,8-K"):
    url = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(phrase)
           + "&forms=" + forms)
    try:
        d = json.loads(get(url))
    except Exception as e:  # noqa: BLE001
        return f"ERR {e}", []
    return (d.get("hits", {}).get("total", {}).get("value", 0),
            [(", ".join(x["_source"].get("display_names", [])),
              x["_source"].get("form"), x["_source"].get("file_date"), x.get("_id"))
             for x in d.get("hits", {}).get("hits", [])[:8]])


def doc_url(display, doc_id):
    m = re.search(r"CIK\s*(\d{10})", display)
    acc, _, fn = str(doc_id).partition(":")
    return (f"https://www.sec.gov/Archives/edgar/data/{int(m.group(1))}/"
            f"{acc.replace('-', '')}/{fn}") if m else None


def read(url, pats, w=(300, 380)):
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


o = io.open("_verify_tlx_0911.txt", "w", encoding="utf-8")

o.write("=== EDGAR: Telix filings naming Pixclara / TLX101\n")
seen = 0
for ph in ['"Pixclara"', '"TLX101"', '"Telix" "Complete Response"',
           '"Telix" "approval"']:
    total, hits = fts(ph)
    o.write(f"\n-- {ph}: total={total}\n")
    for disp, form, fdate, did in hits:
        o.write(f"   {form} {fdate}  {disp[:56]}\n")
        if "TELIX" not in disp.upper() or str(fdate) < "2026-08-01" or seen >= 3:
            continue
        u = doc_url(disp, did)
        if not u:
            continue
        o.write(f"   -> {u}\n")
        for s in read(u, [r"Pixclara[^.]{0,260}", r"(?:approv|Complete Response)[^.]{0,240}",
                          r"September\s+11[^.]{0,200}"]):
            o.write("      " + s[:700] + "\n")
        seen += 1

o.write("\n\n=== openFDA: any approval record for the drug\n")
for q in ['openfda.generic_name:"paraiodobenzyl+guanidine"',
          'openfda.brand_name:"PIXCLARA"',
          'openfda.generic_name:"iopofosine"',
          'sponsor_name:"TELIX"']:
    url = ("https://api.fda.gov/drug/drugsfda.json?search="
           + urllib.parse.quote(q, safe=':+"') + "&limit=5")
    o.write(f"\n-- {q}\n")
    try:
        d = json.loads(get(url))
        for r in d.get("results", []):
            o.write(f"   app={r.get('application_number')} sponsor={r.get('sponsor_name')}\n")
            for p in r.get("products", [])[:3]:
                o.write(f"     product {p.get('brand_name')}\n")
            for s in sorted(r.get("submissions", []),
                            key=lambda s: str(s.get("submission_status_date") or ""))[-4:]:
                o.write(f"     {s.get('submission_type')}-{s.get('submission_number')} "
                        f"{s.get('submission_status')} {s.get('submission_status_date')}\n")
    except Exception as e:  # noqa: BLE001
        o.write(f"   none / {e}\n")
o.close()
print("done")
