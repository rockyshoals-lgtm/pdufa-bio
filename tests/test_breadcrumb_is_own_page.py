# -*- coding: utf-8 -*-
"""CI guard: a page's BreadcrumbList names THIS page (red team 2026-10-04).

29 decision pages built from the VERA template shipped VERA's breadcrumb ("VERA FDA decision : Jul 7,
2026") in their structured data. Fails, on the rendered pages, when a BreadcrumbList's last item URL is not
the page's own URL, or (for /fda-decision pages) its last item name does not carry the page's own ticker.

    python tests/test_breadcrumb_is_own_page.py
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
BASE = "https://www.pdufa.bio"


def main():
    fails, n = [], 0
    for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
        rel = os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
        if rel == ".":
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'<script type="application/ld\+json">(\{[^<]*"BreadcrumbList".*?)</script>', doc, re.S):
            try:
                bl = json.loads(m.group(1))
            except ValueError:
                continue
            items = bl.get("itemListElement") or []
            if not items:
                continue
            n += 1
            last = items[-1]
            if last.get("item") and last["item"].rstrip("/") != f"{BASE}/{rel}":
                fails.append(f"/{rel}: breadcrumb ends at {last['item']}")
            # 2026-10-04 red team #2: "first-line CLL/SLL : Oct 2" -- a space left before the colon
            # where an h1 <span> was removed. 152 breadcrumbs carried it.
            for it in items:
                if re.search(r"\s[:;,.](\s|$)", str(it.get("name") or "")):
                    fails.append(f"/{rel}: breadcrumb name has a space before punctuation: {it.get('name')!r}")
            if rel.startswith("fda-decision/"):
                tk = rel.split("/")[1].split("-")[0]
                if tk not in str(last.get("name")) and not re.search(r"\(|FDA approval", str(last.get("name"))):
                    fails.append(f"/{rel}: breadcrumb names {last.get('name')!r}")
    if fails:
        print(f"FAIL: {len(fails)} breadcrumb problem(s):")
        for f in fails[:20]:
            print("   " + f)
        return 1
    print(f"OK -- {n} breadcrumbs, each ending at its own page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
