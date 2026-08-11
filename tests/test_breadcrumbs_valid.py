# -*- coding: utf-8 -*-
"""test_breadcrumbs_valid.py -- hub pages carry breadcrumbs, and every breadcrumb is valid JSON.

Sitelinks groundwork, 2026-08-11. The engines pick sitelinks from a site's hierarchy signals;
breadcrumb structured data is one of them, and the audit found the hub tier -- the exact pages an
engine would surface -- lacked it while leaf pages had it. build_breadcrumbs.py fixes that daily.
This guard keeps two promises:

  1. Every indexable page carries at least one BreadcrumbList (hubs listed explicitly so a
     regression on the pages that matter most is named in the failure).
  2. Every JSON-LD block anywhere on the site PARSES. A malformed block is worse than none:
     engines drop all structured data on the page, silently.
"""
import glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
HUBS = ["calendar", "decisions", "readouts", "drug", "tickers", "conferences", "adcomm",
        "screener", "research", "runup-by-year", "developers", "sls"]


def main():
    bad = []

    for h in HUBS:
        p = os.path.join(SITE, h, "index.html")
        if not os.path.exists(p):
            bad.append(f"hub /{h}: page missing")
            continue
        if "BreadcrumbList" not in open(p, encoding="utf-8", errors="replace").read():
            bad.append(f"hub /{h}: no BreadcrumbList -- run build_breadcrumbs.py")

    missing = parsed = 0
    for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
        doc = open(p, encoding="utf-8", errors="replace").read()
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
        for m in re.finditer(
                r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
            try:
                json.loads(m.group(1))
                parsed += 1
            except Exception as e:
                bad.append(f"{rel}: JSON-LD does not parse ({e}) -- engines drop ALL "
                           f"structured data on a page with one bad block")
        if (not re.search(r'<meta[^>]+name="robots"[^>]+noindex', doc)
                and "BreadcrumbList" not in doc and rel != "/."):
            missing += 1

    if missing:
        bad.append(f"{missing} indexable page(s) lack BreadcrumbList -- run "
                   f"build_breadcrumbs.py")

    if bad:
        print(f"FAIL: {len(bad)} breadcrumb/schema problem(s).")
        for b in bad[:10]:
            print(f"   {b}")
        return 1
    print(f"  PASS: all {len(HUBS)} hubs carry BreadcrumbList; {parsed} JSON-LD blocks parse; "
          f"no indexable page lacks a breadcrumb")
    return 0


if __name__ == "__main__":
    sys.exit(main())
