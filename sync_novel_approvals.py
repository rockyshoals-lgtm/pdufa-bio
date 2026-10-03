# -*- coding: utf-8 -*-
"""sync_novel_approvals.py -- the FDA's "Novel Drug Approvals for 2026" list, cached (audit 2026-10-03, 2.2).

The answer-box sentence for JUVMO that beat us read "...the 43rd novel drug approval of 2026". We hold
the data the moment the FDA lists it. This reads CDER's table (No., Drug Name, Active Ingredient,
Approval Date, FDA-approved use) into _fda_novel_approvals.json. A failed read keeps the last good cache
and says so (never a silent zero). The list is CDER's; CBER biologics are not on it, and the page says
so too, so a CBER approval never gets a number.

    python sync_novel_approvals.py [--file saved.html]
"""
import argparse
import datetime as dt
import html
import io
import json
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_fda_novel_approvals.json")
YEAR = 2026
URL = f"https://www.fda.gov/drugs/novel-drug-approvals-fda/novel-drug-approvals-{YEAR}"
UA = {"User-Agent": "pdufa.bio watcher rockyshoals@gmail.com"}


def parse(doc):
    out = []
    for tr in re.findall(r"<tr>(.*?)</tr>", doc, re.S):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(cells) < 4 or not re.match(r"^\d+\.?$", cells[0]):
            continue
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", cells[3])
        if not m:
            continue
        use = re.sub(r"\s*(Drug Trials Snapshot|Press Release)\s*$", "", cells[4] if len(cells) > 4 else "").strip()
        out.append({"n": int(cells[0].rstrip(".")), "brand": cells[1], "ingredient": cells[2],
                    "date": dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2))).isoformat(),
                    "use": use})
    return sorted(out, key=lambda r: r["n"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    a = ap.parse_args()
    old = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    try:
        if a.file:
            doc = io.open(a.file, encoding="utf-8", errors="replace").read()
        else:
            doc = urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=40).read().decode("utf-8", "replace")
        rows = parse(doc)
        cur = re.search(r"Content current as of:.*?(\d\d)/(\d\d)/(\d{4})", doc, re.S)
    except Exception as e:  # noqa: BLE001
        print(f"novel approvals: BLIND this run ({e}); keeping the cache of {old.get('read_at')}")
        return 0
    if not rows or (old.get("rows") and len(rows) < len(old["rows"])):
        print(f"novel approvals: parsed {len(rows)} row(s), fewer than the cached {len(old.get('rows', []))}; "
              f"keeping the cache (a shrinking FDA list means a bad read, not a withdrawal)")
        return 0
    data = {"source": URL, "year": YEAR, "read_at": dt.date.today().isoformat(),
            "fda_content_current_as_of": f"{cur.group(3)}-{cur.group(1)}-{cur.group(2)}" if cur else None,
            "note": "CDER's Novel Drug Approvals list. CBER-regulated products are not on it.",
            "rows": rows}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"novel approvals {YEAR}: {len(rows)} on the FDA list (FDA page current as of "
          f"{data['fda_content_current_as_of']}); latest #{rows[-1]['n']} {rows[-1]['brand']} {rows[-1]['date']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
