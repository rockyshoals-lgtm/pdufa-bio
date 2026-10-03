# -*- coding: utf-8 -*-
"""CI guard: a decided event page states the FDA's action date and the brand (audit 2026-10-03, 2.3 / 3.1).

/pdufa/ABBV-tavapadon went live on 10-03 titled "Tavapadon, Approved September 28, 2026" (AbbVie's
release day) over a banner saying the FDA decided on September 25, and without the brand JUVMO the
FDA approved it under. Fails, for every Decided row with an /pdufa/ page and an FDA action date on the
row, when the rendered page's <title> carries the announcement day instead of the FDA's, or when an
approved row with a brand lacks it in the <title> or <h1>.

    python tests/test_event_page_fda_date_brand.py
"""
import datetime as dt
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
M = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
     "November", "December"]


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{M[d.month - 1]} {d.day}, {d.year}"


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))
    fails, n = [], 0
    for r in rows:
        d = r.get("_d") or {}
        fad, dcd, url = d.get("fda_action_date"), r.get("dcd"), str(r.get("url") or "")
        if r.get("st") != "Decided" or not fad or not dcd or not url.startswith("/pdufa/"):
            continue
        p = os.path.join(SITE, url.strip("/"), "index.html")
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"<title>(.*?)</title>", doc, re.S)
        title = html.unescape(m.group(1)) if m else ""
        if "FDA decision:" not in title:
            continue                     # pages not (yet) in decided form are another guard's job
        n += 1
        if fad != dcd and pretty(dcd) in title and pretty(fad) not in title:
            fails.append(f"{url}: title dates the decision {pretty(dcd)} (announcement), FDA acted {pretty(fad)}")
        brand = str(d.get("brand") or "").strip()
        if brand and r.get("oc") == "Approved":
            h1 = re.search(r"<h1>(.*?)</h1>", doc, re.S)
            if brand.lower() not in title.lower() or not h1 or brand.lower() not in html.unescape(h1.group(1)).lower():
                fails.append(f"{url}: brand {brand} missing from the title or h1")
    if fails:
        print(f"FAIL: {len(fails)} decided event page(s) off the FDA record:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} decided event page(s) with an FDA action date state the FDA's day and the brand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
