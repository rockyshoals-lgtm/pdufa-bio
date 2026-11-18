# -*- coding: utf-8 -*-
"""test_screener_filters.py -- the screener's area filter is built from its rows, and every row opens a page here.

Design red team 2026-11-18 (change 9). The "Therapeutic area" dropdown was typed in by hand: 8 of its 23 areas matched
no row (Oncology - lung, Neuro - MS, ...), 102 rows sat in areas it did not offer (Dermatology, Respiratory, ...), 117
had no area at all, and spelling twins split one area in two (Cardiology / Cardiovascular, Rare disease / Rare Disease).
456 readouts linked straight to a registry or press release while every other row opened its page on pdufa.bio. This
fails if:

  1. an area option finds no row, prints a count (the page hides past rows by default, so a count over every row
     promises rows it does not show), or a row's area has no option;
  2. two options differ only in case or spacing, or a row has no area (it must say "Not classified");
  3. the page filters on anything but the folded area (e.ar), or a known label folds to another area than PINNED;
  4. a row links off-site while a page for it exists here, links a page that does not exist, or links a #readouts
     list that does not hold that readout.

    python tests/test_screener_filters.py
"""
import collections
import html
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


PINNED = {"Cardiology": "Cardiovascular", "Cardiovascular": "Cardiovascular", "Rare Disease": "Rare disease",
          "Lysosomal and rare metabolic disease": "Rare disease", "Neuro-oncology": "Oncology",
          "Oncology, lung": "Oncology", "Haematology": "Hematology", "Infectious": "Infectious disease",
          "CNS/Neurology": "Neurology / CNS", "Endocrinology / Metabolic": "Metabolic / endocrine",
          "GI and hepatology": "Gastroenterology / hepatology", "Pulmonary and critical care": "Respiratory",
          "Allergy and immunology": "Immunology / rheumatology", "Bronchiectasis": "Bronchiectasis",
          "Adrenal insufficiency": "Adrenal insufficiency", "Drug delivery": "Drug delivery",
          "Plasma disorders": "Plasma disorders", "": "Not classified", "Other": "Other"}


def main():
    doc = open(os.path.join(SITE, "screener", "index.html"), encoding="utf-8", errors="replace").read()
    m = re.search(r"const DATA=(\[.*?\]);\s*\nconst q=", doc, re.S)
    if not m:
        print("FAIL /screener: no DATA array")
        sys.exit(1)
    data = json.loads(m.group(1).replace("<\\/", "</"))
    if os.environ.get("PLANT") == "offsite":
        data[0]["url"] = "https://clinicaltrials.gov/study/NCT00000000"
    bad = []
    sys.path.insert(0, HERE)
    from sync_screener_data import area
    for raw, want in PINNED.items():
        if area(raw) != want:
            bad.append(f"sync_screener_data.area({raw!r}) = {area(raw)!r}, want {want!r}")
    sel = re.search(r'<select id="ta"[^>]*>(.*?)</select>', doc, re.S)
    opts = re.findall(r'<option value="([^"]*)">([^<]*)</option>', sel.group(1)) if sel else []
    if not opts:
        bad.append("/screener: no therapeutic-area options")
    have = collections.Counter(e.get("ar") for e in data)
    for e in data:
        if not e.get("ar"):
            bad.append(f"/screener {e['t']} {e['d']}: row has no area (want 'Not classified')")
    seen = {}
    for val, text in opts:
        if not val:
            continue
        val = val.replace("&amp;", "&")
        key = re.sub(r"\s+", " ", val).strip().lower()
        if key in seen:
            bad.append(f"/screener: options '{seen[key]}' and '{val}' are the same area")
        seen[key] = val
        if have.get(val, 0) == 0:
            bad.append(f"/screener: area option '{val}' finds no row")
        if re.search(r"\(\d+\)$", text):
            bad.append(f"/screener: area option '{text}' prints a count of every row, past ones included")
    for a, n in have.items():
        if a and a not in seen.values():
            bad.append(f"/screener: {n} row(s) in area '{a}' have no option to find them")
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", " ".join(re.findall(r"<script>(.*?)</script>", doc, re.S)), flags=re.S)
    if "(!ta||e.ar===ta)" not in code or "e.ta===ta" in code:
        bad.append("/screener: the area filter does not test the folded area (!ta||e.ar===ta)")
    hubs = {}
    for e in data:
        u = str(e.get("url") or "")
        if not u.startswith("/"):
            if os.path.exists(os.path.join(SITE, "ticker", e["t"], "index.html")):
                bad.append(f"/screener {e['t']} {e['type']} {e['d']}: links off-site ({u[:60]}); /ticker/{e['t']} exists")
            continue
        path, _, frag = u.partition("#")
        f = os.path.join(SITE, path.strip("/").split("?")[0], "index.html")
        if not os.path.exists(f):
            bad.append(f"/screener {e['t']} {e['d']}: links {u}, which is not a page here")
        elif frag:
            if f not in hubs:
                hubs[f] = open(f, encoding="utf-8", errors="replace").read()
            sec = re.search(r'<h2 id="%s">.*?(?=<h2|$)' % re.escape(frag), hubs[f], re.S)
            if not sec:
                bad.append(f"/screener {e['t']} {e['d']}: links {u}, which has no #{frag}")
            elif frag == "readouts" and e["name"][:40] not in html.unescape(sec.group(0)):
                bad.append(f"/screener {e['t']} {e['d']}: links {u}, whose list does not hold {e['name']!r}")
    print(f"/screener: {len(data)} rows, {len(opts) - 1} area option(s)")
    if bad:
        for b in bad[:30]:
            print("  FAIL " + b)
        if len(bad) > 30:
            print(f"  ... and {len(bad) - 30} more")
        print("  fix: python build_ticker_hubs.py && python sync_screener_data.py && python build_screener_rows.py")
        sys.exit(1)
    print("  PASS: every area option finds its rows, every row has an option, and every row opens a page here")


if __name__ == "__main__":
    main()
