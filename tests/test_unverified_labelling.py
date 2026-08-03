# -*- coding: utf-8 -*-
"""test_unverified_labelling.py -- an inferred outcome must never look like a verified one.

Origin: we published /fda-decision/SLS-2025-02-20 asserting that the FDA issued SELLAS a Complete
Response Letter. No such decision exists; SELLAS has never submitted a marketing application. The
page was produced by the price-only tier, which infers an outcome from the share-price reaction,
and then rendered it with the same definitive title, headline and badge as a primary-sourced
record. An external audit caught it. This guard exists so the class of error cannot come back.

A price-only page must:
  * not assert Approved / CRL in its <title> or <h1>
  * not use the verified outcome badges
  * carry the unverified banner
  * stay noindex

    python tests/test_unverified_labelling.py
"""
import glob, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")

VERDICT_TITLE = re.compile(r"<title>[^<]*\d{4}-\d{2}-\d{2}:\s*(Approved|CRL)\b", re.I)
VERDICT_H1 = re.compile(r"<h1>.*?<span class=\"g\">\s*(Approved|CRL)\s*</span>", re.S)
VERIFIED_BADGE = re.compile(r'class="badge (?:app|crl)"')
NOINDEX = re.compile(r'name="robots"[^>]*content="[^"]*noindex', re.I)


def main():
    bad_title, bad_h1, bad_badge, no_banner, indexable = [], [], [], [], []
    n = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        html = open(p, encoding="utf-8", errors="replace").read()
        if "price-only" not in html:
            continue
        n += 1
        rel = os.path.relpath(p, SITE)
        if VERDICT_TITLE.search(html):
            bad_title.append(rel)
        if VERDICT_H1.search(html):
            bad_h1.append(rel)
        if VERIFIED_BADGE.search(html):
            bad_badge.append(rel)
        if "Unverified record." not in html:
            no_banner.append(rel)
        if not NOINDEX.search(html):
            indexable.append(rel)

    print(f"checked {n} price-inferred decision page(s)")
    ok = True
    for label, rows, fix in (
            ("assert an outcome in <title>", bad_title, "python relabel_price_only.py"),
            ("assert an outcome in <h1>", bad_h1, "python relabel_price_only.py"),
            ("use a verified outcome badge", bad_badge, "python relabel_price_only.py"),
            ("are missing the unverified banner", no_banner, "python relabel_price_only.py"),
            ("are indexable", indexable, "add noindex to the generator")):
        if rows:
            ok = False
            print(f"\nFAIL: {len(rows)} page(s) {label}:")
            for r in rows[:8]:
                print(f"   {r}")
            if len(rows) > 8:
                print(f"   ... and {len(rows) - 8} more")
            print(f"   fix: {fix}")
    if ok:
        print("  PASS: every inferred outcome is labelled unverified, banner present, noindex set")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
