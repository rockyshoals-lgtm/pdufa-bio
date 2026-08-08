# -*- coding: utf-8 -*-
"""noindex_empty_months.py -- a month page with no events has nothing to say to a crawler yet.

The GSC audit flagged calendar month pages sitting in the sitemap with zero events -- real URLs
advertising nothing, on a domain whose crawl budget is the binding constraint (421 pages never
fetched). By the time the fix was written the flagged months had gained rows and earned their
place, which is exactly the lifecycle this script manages in both directions:

  * A month page with 0 catalyst rows gets robots noindex. build_sitemap.py already excludes
    noindex pages, so it leaves the sitemap in the same build.
  * The moment it gains a row, the noindex comes OFF. A one-way switch would quietly bury a page
    that now has real content, which is worse than the problem being solved.

Runs before build_sitemap.py in the workflow, so the sitemap reflects the toggles made here.

    python noindex_empty_months.py [--dry-run]
"""
import argparse, glob, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
TAG = '<meta name="robots" content="noindex" data-empty-month>'
ROW = re.compile(r'<a class="row"')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    hidden = revealed = 0
    for p in sorted(glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html"))):
        doc = open(p, encoding="utf-8", errors="replace").read()
        rows = len(ROW.findall(doc))
        has = TAG in doc
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")

        if rows == 0 and not has:
            # Only our own tag: a hand-placed noindex on a month page stays whatever we think.
            if "</head>" not in doc or "noindex" in doc[:4000]:
                continue
            doc = doc.replace("</head>", TAG + "</head>", 1)
            hidden += 1
            print(f"  noindex ON   {rel}  (0 rows)")
        elif rows > 0 and has:
            doc = doc.replace(TAG, "", 1)
            revealed += 1
            print(f"  noindex OFF  {rel}  ({rows} rows -- it has content now)")
        else:
            continue
        if not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc)

    print(f"hidden {hidden}, revealed {revealed}"
          + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
