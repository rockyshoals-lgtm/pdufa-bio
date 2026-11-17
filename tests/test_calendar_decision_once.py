# -*- coding: utf-8 -*-
"""CI guard: on each calendar page a decision is listed once per ticker, and a decided row on a day other than
its decision says when the decision came.

2026-11-17 (currency audit, read in a real browser): /calendar listed five approvals twice -- on the decision
day and again on the goal window the period marker matched them to -- and still showed "PFE / ROIV ·
2026-09-30", a quarter-end day withdrawn on 2026-09-10, as a second row for the 2026-08-27 brepocitinib
approval. Decided rows on their goal day ("RHHBY · 2026-12-18 ✓", approved 2026-11-16) did not say the
decision came five weeks earlier. calendar_decided_rows_once.py fixes both; this holds them.

Rows of different tickers for one decision (partner, royalty holder) are legal.
PLANT=dup duplicates a decided row on /calendar and must FAIL; PLANT=nodate strips one decision-date span.

    python tests/test_calendar_decision_once.py
"""
import collections
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from calendar_decided_rows_once import action_dates  # noqa: E402  one owner for the FDA action date
SITE = os.path.join(HERE, "pdufa_site_src")
ROW = re.compile(r'<a class="row"([^>]*)>\s*<div class="t">(.*?)</div>\s*<div class="d">(.*?)</div>\s*</a>', re.S)


def main():
    pages = [os.path.join(SITE, "calendar", "index.html")] + sorted(
        glob.glob(os.path.join(SITE, "calendar", "[0-9][0-9][0-9][0-9]", "*", "index.html")))
    plant = os.environ.get("PLANT", "")
    fad = action_dates()
    fails = []
    for p in pages:
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if plant and p.endswith(os.path.join("calendar", "index.html")):
            m = next(x for x in ROW.finditer(doc) if "data-dec" in x.group(1))
            if plant == "dup":
                doc = doc[:m.end()] + m.group(0) + doc[m.end():]
            elif plant == "nodate":
                m = next(x for x in ROW.finditer(doc) if 'class="dd"' in x.group(2))
                doc = doc[:m.start()] + re.sub(r'\s*<span class="dd".*?</span>', "", m.group(0), flags=re.S) + doc[m.end():]
        seen = collections.Counter()
        for m in ROW.finditer(doc):
            if "data-dec" not in m.group(1):
                continue
            h = re.search(r'href="(/fda-decision/[A-Z0-9./-]+-(\d{4}-\d{2}-\d{2}))"', m.group(1))
            if not h:
                continue
            t = re.sub(r"<[^>]+>", "", m.group(2))
            label = re.sub(r"\s*(?:&middot;|·).*$", "", t, flags=re.S).strip()
            seen[(h.group(1), label)] += 1
            shown = re.search(r"\d{4}-\d{2}-\d{2}", t)
            on_decision = shown and shown.group(0) in (h.group(2), fad.get(h.group(1)))
            if not on_decision and 'class="dd"' not in m.group(2):
                fails.append(f"{os.path.relpath(p, SITE)}: '{t.strip()}' is decided ({h.group(1)}) but does not "
                                 f"say when -- run calendar_decided_rows_once.py")
        for (href, label), n in seen.items():
            if n > 1:
                fails.append(f"{os.path.relpath(p, SITE)}: {label} lists {href} {n} times -- one decision, one row")
    if fails:
        for f in fails[:25]:
            print("  FAIL " + f)
        print(f"\n{len(fails)} calendar decision-row failure(s).")
        return 1
    print(f"OK -- {len(pages)} calendar pages: each decision once per ticker; decided rows off their decision date say when.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
