# -*- coding: utf-8 -*-
"""build_sitemap.py -- regenerate sitemap.xml from the pages that actually exist on disk.

The problem this fixes: the sitemap was a stale static list. It carried 145 of the 448 live
/fda-decision/ pages -- 303 were missing, including every July 2026 decision (VTRS, OTLK, OTSKY, MRK).
The newest decision URL in it was from late June. Those are the freshest, most linkable pages on the
site, and they were invisible to the one file Google uses to prioritise recrawl.

The durable fix is to stop maintaining a list: walk pdufa_site_src for index.html files, emit one URL
per real page, and set <lastmod> from the file's own modification time so it is always truthful.

Excluded: anything robots.txt disallows (/today, /app), plus internal/backup artifacts.

    python build_sitemap.py [--dry-run]
"""
import argparse, os, re, sys
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
OUT = os.path.join(SITE, "sitemap.xml")
BASE = "https://www.pdufa.bio"

SKIP_DIRS = {"api", "fonts", ".well-known", "_next", "assets", "img", "images"}
SKIP_PAT = re.compile(r'(^|/)(today|app|login|account|preview|index_redesign|_home_pdufa_backup)'
                      r'|\.bak|\.tmp', re.I)

# crawl priority / cadence by section -- decisions and the live calendar change most often
def meta(url_path):
    if url_path == "/":
        return "daily", "1.0"
    for pref, (cf, pr) in (("/sls", ("daily", "0.9")),
                           ("/calendar", ("daily", "0.9")),
                           ("/decisions", ("daily", "0.9")),
                           ("/readouts", ("daily", "0.8")),
                           ("/adcomm", ("daily", "0.8")),
                           ("/fda-decision/", ("monthly", "0.7")),
                           ("/pdufa/", ("weekly", "0.7")),
                           ("/ticker/", ("weekly", "0.5")),
                           ("/research", ("weekly", "0.8")),
                           ("/conference", ("weekly", "0.6")),
                           ("/condition/", ("weekly", "0.6"))):
        if url_path.startswith(pref):
            return cf, pr
    return "monthly", "0.5"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    urls = {}
    for root, dirs, files in os.walk(SITE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if f not in ("index.html",) and not (f.endswith(".html") and root == SITE):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, SITE).replace("\\", "/")
            if f == "index.html":
                path = "/" + rel[: -len("index.html")].rstrip("/")
            else:
                path = "/" + rel[: -len(".html")]
            path = path if path else "/"
            if SKIP_PAT.search(path):
                continue
            lastmod = dt.datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d")
            urls[path] = lastmod

    # count by section for the report
    sec = {}
    for p in urls:
        k = ("/fda-decision" if p.startswith("/fda-decision/") else
             "/ticker" if p.startswith("/ticker/") else
             "/pdufa" if p.startswith("/pdufa/") else
             "/calendar" if p.startswith("/calendar") else
             "/research" if p.startswith("/research") else "other")
        sec[k] = sec.get(k, 0) + 1

    body = []
    for p in sorted(urls):
        cf, pr = meta(p)
        body.append(f"<url><loc>{BASE}{p}</loc><lastmod>{urls[p]}</lastmod>"
                    f"<changefreq>{cf}</changefreq><priority>{pr}</priority></url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sepomex.gov/schemas/sitemap/0.9">'.replace(
               "http://www.sepomex.gov/schemas/sitemap/0.9",
               "http://www.sitemaps.org/schemas/sitemap/0.9")
           + "".join(body) + "</urlset>\n")

    old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    old_n = old.count("<loc>")
    newest = max(urls.values()) if urls else "n/a"
    print(f"sitemap: {old_n} URLs before -> {len(urls)} after   (newest lastmod {newest})")
    for k, v in sorted(sec.items(), key=lambda kv: -kv[1]):
        print(f"    {k:16s} {v}")
    if a.dry_run:
        print("DRY RUN -- not written."); return
    open(OUT, "w", encoding="utf-8").write(xml)
    print(f"wrote sitemap.xml ({len(xml)} bytes)")


if __name__ == "__main__":
    main()
