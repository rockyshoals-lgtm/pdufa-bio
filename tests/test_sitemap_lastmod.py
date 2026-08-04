# -*- coding: utf-8 -*-
"""test_sitemap_lastmod.py -- the sitemap's <lastmod> has to mean something.

Origin: build_sitemap.py set lastmod from os.path.getmtime. That is correct on a developer machine
and silently wrong in CI, because actions/checkout writes every file fresh, so every mtime is the
checkout time. The published sitemap therefore claimed all 430 pages changed today, every day.

Nothing on the site looked broken. The costs were entirely external:

  * Google's documented behaviour is to ignore lastmod on sites where the value is not trustworthy.
    "Everything changed today, forever" is the textbook untrustworthy signal, so we were paying our
    credibility for zero information.
  * ping_search_engines.py submits recently-changed URLs to IndexNow. With every date equal to
    today, that re-pushed all 430 URLs nightly, which is how you get de-prioritised by Bing/Yandex.

This guard fails when lastmod stops carrying information. It does not check "is the date correct" --
it checks "could this date possibly be correct", which is the failure mode that actually occurred.

Checks:
  1. no lastmod is in the future (a sitemap claiming tomorrow discredits every other date in it)
  2. the dates are not all identical
  3. not every URL claims today

    python tests/test_sitemap_lastmod.py
"""
import collections, datetime as dt, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITEMAP = os.path.join(HERE, "pdufa_site_src", "sitemap.xml")

# Below this many URLs the "all one date" checks are meaningless (a brand-new site legitimately
# has every page dated the same day).
MIN_URLS = 25


def main():
    if not os.path.exists(SITEMAP):
        print("FAIL: sitemap.xml does not exist")
        sys.exit(1)

    xml = open(SITEMAP, encoding="utf-8", errors="replace").read()
    dates = re.findall(r"<lastmod>([^<]+)</lastmod>", xml)
    n_loc = xml.count("<loc>")
    today = dt.date.today().isoformat()

    if not dates:
        print("FAIL: sitemap has no <lastmod> at all")
        sys.exit(1)

    counts = collections.Counter(dates)
    print(f"sitemap: {n_loc:,} URLs, {len(dates):,} lastmod values, "
          f"{len(counts)} distinct date(s); today is {today}")
    for d, n in sorted(counts.items(), reverse=True)[:6]:
        print(f"   {d}  {n:>5} URL(s)")

    ok = True

    future = sorted({d for d in dates if d > today})
    if future:
        ok = False
        print(f"\nFAIL: {len(future)} distinct future lastmod value(s), e.g. {future[-1]}")
        print("   A sitemap that claims tomorrow's date is a reason for a crawler to distrust "
              "every date in the file.")
    else:
        print("  PASS: no future-dated lastmod")

    if n_loc < MIN_URLS:
        print(f"  SKIP: only {n_loc} URLs; uniformity checks need at least {MIN_URLS}")
        sys.exit(0 if ok else 1)

    if len(counts) == 1:
        ok = False
        print(f"\nFAIL: every one of {len(dates):,} URLs carries the same lastmod ({dates[0]}).")
        print("   lastmod is then carrying no information. The known cause is deriving it from "
              "filesystem mtime: a fresh CI checkout stamps every file with the checkout time.")
        print("   build_sitemap.py should read the date from git history instead.")
    else:
        print(f"  PASS: lastmod varies across {len(counts)} distinct dates")

    share_today = counts.get(today, 0) / len(dates)
    if share_today > 0.98:
        ok = False
        print(f"\nFAIL: {share_today:.1%} of URLs claim they changed today.")
        print("   Some pages do change daily (the board, the calendar), but not 98% of a "
              "mostly-archival site. This is the mtime bug reappearing.")
    else:
        print(f"  PASS: {share_today:.1%} of URLs claim today (plausible)")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
