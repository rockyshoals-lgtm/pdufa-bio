# -*- coding: utf-8 -*-
"""Verify the five flagged approvals against primary sources before anything is published.

check_pdufa_decided.py matches a ticker's approval press release against that ticker's forward
PDUFA rows. That is a LEAD, not a fact, and it has a known failure mode: a company with two
applications gets its row matched to the wrong one. ARQT is the textbook case -- ZORYVE 0.3%
cream for paediatric plaque psoriasis was approved 2026-06-29 and ALREADY has a decision page,
so a 2027-02-23 ARQT row matching that same release is the matcher reaching across
applications, not a missed decision. Same shape for GILD (Bixlenvo approved 2026-08-27 against
a 2027-02-02 row).

So for each: find the sponsor's own 8-K/6-K for the approval date, print the sentence, and print
what our dataset currently holds for that ticker. Then decide per row.
"""
import io
import json
import re
import urllib.parse
import urllib.request

UA = "pdufa.bio builder rockyshoals@gmail.com"

CASES = [
    ("SRRK", "2026-09-30", "apitegromab", ["ISEMBYLD", "apitegromab"]),
    ("PHAR", "2026-10-24", "leniolisib", ["Joenja", "leniolisib"]),
    ("BFRI", "2026-09-28", "Ameluz", ["Ameluz", "aminolevulinic"]),
    ("GILD", "2027-02-02", "?", ["Bixlenvo", "bictegravir"]),
    ("ARQT", "2027-02-23", "?", ["ZORYVE", "roflumilast"]),
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "identity"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")


def fts(phrase, forms="8-K,6-K,10-Q,20-F"):
    url = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(phrase)
           + "&forms=" + forms + "&dateRange=custom&startdt=2026-08-01&enddt=2026-09-14")
    try:
        d = json.loads(get(url))
    except Exception as e:  # noqa: BLE001
        return 0, []
    return (d.get("hits", {}).get("total", {}).get("value", 0),
            [(", ".join(x["_source"].get("display_names", [])),
              x["_source"].get("form"), x["_source"].get("file_date"), x.get("_id"))
             for x in d.get("hits", {}).get("hits", [])[:6]])


def doc_url(display, doc_id):
    m = re.search(r"CIK\s*(\d{10})", display)
    acc, _, fn = str(doc_id).partition(":")
    return (f"https://www.sec.gov/Archives/edgar/data/{int(m.group(1))}/"
            f"{acc.replace('-', '')}/{fn}") if m else None


def read(url, pats, w=(300, 340)):
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


src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8",
              errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])

o = io.open("_verify_0914_approvals.txt", "w", encoding="utf-8")
for tk, listed, drug, needles in CASES:
    o.write(f"\n{'=' * 78}\n=== {tk}  listed {listed}  ({drug})\n")
    o.write("  OUR DATASET ROWS:\n")
    for r in rows:
        if str(r.get("t") or "").upper() != tk:
            continue
        o.write(f"    {r.get('type'):<10} d={r.get('d')} dp={r.get('dp')} st={r.get('st')} "
                f"oc={r.get('oc')} dcd={r.get('dcd')} | {str(r.get('name'))[:48]}\n")
    o.write("  SPONSOR FILINGS (Aug 1 - Sep 14 2026):\n")
    seen = 0
    for nm in needles:
        total, hits = fts(f'"{nm}" "approval"')
        for disp, form, fdate, did in hits:
            if tk.upper() not in disp.upper() and not any(
                    w in disp.upper() for w in [drug.upper()[:6]]):
                continue
            u = doc_url(disp, did)
            if not u:
                continue
            o.write(f"\n    {form} {fdate}  {disp[:56]}\n    {u}\n")
            for s in read(u, [r"(?:approv\w+)[^.]{0,220}", nm + r"[^.]{0,200}"]):
                o.write("      " + s[:640] + "\n")
            seen += 1
            if seen >= 2:
                break
        if seen >= 2:
            break
    if not seen:
        o.write("    (no matching sponsor filing found in window)\n")
o.close()
print("done")
