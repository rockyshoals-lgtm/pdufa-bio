# -*- coding: utf-8 -*-
"""build_sitemap.py -- regenerate sitemap.xml from the pages that actually exist on disk.

The problem this fixes: the sitemap was a stale static list. It carried 145 of the 448 live
/fda-decision/ pages -- 303 were missing, including every July 2026 decision (VTRS, OTLK, OTSKY, MRK).
The newest decision URL in it was from late June. Those are the freshest, most linkable pages on the
site, and they were invisible to the one file Google uses to prioritise recrawl.

The durable fix is to stop maintaining a list: walk pdufa_site_src for index.html files and emit one
URL per real page.

<lastmod> comes from git history, NOT the filesystem mtime. That distinction is the whole point:
actions/checkout writes every file fresh, so in CI every mtime is the checkout time, and the sitemap
was telling Google that all 430 pages changed today, every single day. Two costs, both real:

  * Google says explicitly that it ignores lastmod on sites where it finds the value untrustworthy.
    A sitemap where everything changed today, forever, is the canonical example. We were spending our
    credibility to say nothing.
  * ping_search_engines.py submits "recently changed" URLs to IndexNow. With every date equal to
    today, that meant re-pushing all 430 URLs nightly, which its own docstring warns is how you train
    Bing and Yandex to ignore you.

The last commit that touched a file is the honest answer to "when did this page last change", and it
survives a fresh checkout. Untracked/new files fall back to mtime, capped at today.

Excluded: anything robots.txt disallows (/today, /app), plus internal/backup artifacts.

    python build_sitemap.py [--dry-run]
"""
import argparse, hashlib, json, os, re, subprocess, sys
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
NOINDEX = re.compile(r'name="robots"[^>]*content="[^"]*noindex', re.I)
SKIP_PAT = re.compile(r'(^|/)_'                       # any backup / retired path segment
                      r'|(^|/)(today|app|login|account|preview|index_redesign|ping|holding)\b'
                      r'|\.bak|\.tmp', re.I)

TODAY = dt.date.today().isoformat()
_GIT_DATES = None
_STATE = None
STATE_F = os.path.join(HERE, "_sitemap_lastmod.json")


def git_dates():
    """path (relative to SITE) -> date of the last commit that touched it.

    One `git log --name-only` walk builds the whole map, rather than 430 subprocess calls. Newest
    commits come first, so the first date seen for a path is its last change.
    """
    global _GIT_DATES
    if _GIT_DATES is not None:
        return _GIT_DATES
    out = {}
    try:
        p = subprocess.run(["git", "log", "--format=@%cs", "--name-only", "--", "pdufa_site_src"],
                           cwd=HERE, capture_output=True, text=True, timeout=120)
        cur = None
        for line in p.stdout.splitlines():
            if line.startswith("@"):
                cur = line[1:].strip()
            elif line.endswith(".html") and cur and line not in out:
                out[line] = cur
    except Exception as e:
        print(f"  note: git history unavailable ({type(e).__name__}); falling back to file mtimes. "
              f"In CI that yields today's date for every page, which is not a truthful lastmod.")
    _GIT_DATES = out
    return out


# Boilerplate that appears on every page. A change confined to these is a template change, not a
# content change, and must not advance lastmod.
#
# This is the second version of this logic. The first marked any file with uncommitted changes as
# modified today, which was right until a site-wide nav rebuild touched 846 pages at once and the
# sitemap went straight back to claiming 99.8% of URLs changed today. That is the same
# credibility-burning signal the git-history fix was written to remove, arriving by a different
# route. Google's guidance is that lastmod reflects the last SIGNIFICANT change, and swapping the
# nav on every page is not one.
BOILER = [
    re.compile(r"<!--NAVC:BEGIN-->.*?<!--NAVC:END-->", re.S),
    re.compile(r'<style id="(navcanon|navpolish|typesys)">.*?</style>', re.S),
    re.compile(r"<nav[^>]*>.*?</nav>", re.S),
    re.compile(r'<div class="nav">.*?</div>', re.S),
    re.compile(r'<div class="legal".*?</div>', re.S),
    re.compile(r"<footer.*?</footer>", re.S),
]


def content_hash(html):
    """Hash of the page with template furniture removed, so lastmod tracks content."""
    for rx in BOILER:
        html = rx.sub("", html)
    return hashlib.sha1(re.sub(r"\s+", " ", html).encode("utf-8", "replace")).hexdigest()[:16]


def load_state():
    global _STATE
    if _STATE is None:
        try:
            _STATE = json.load(open(STATE_F, encoding="utf-8"))
        except Exception:
            _STATE = {}
    return _STATE


def last_changed(rel, full, html):
    """Date this page's CONTENT last changed.

    Seeded from git history the first time a page is seen, then advanced only when the
    boilerplate-stripped hash actually moves. The state file is committed, so this survives a fresh
    CI checkout where every mtime is the checkout time.
    """
    key = "pdufa_site_src/" + rel
    st = load_state()
    h = content_hash(html)
    prev = st.get(key)

    if prev and prev.get("hash") == h:
        d = prev.get("date") or git_dates().get(key) or TODAY
    elif prev:
        d = TODAY                                   # a real content change
    else:
        d = (git_dates().get(key)
             or dt.datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d"))

    d = min(d, TODAY)             # a sitemap claiming tomorrow is a reason to distrust all of it
    st[key] = {"hash": h, "date": d}
    return d


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


def redirect_sources():
    """Paths that vercel.json 301s away. Advertising a URL in the sitemap that immediately
    redirects is a self-inflicted duplicate-content signal: the crawler is told a page is
    canonical and then bounced off it. Read them from the config so the two can never disagree."""
    p = os.path.join(SITE, "vercel.json")
    if not os.path.exists(p):
        return set()
    try:
        import json
        cfg = json.load(open(p, encoding="utf-8"))
        return {r.get("source", "").rstrip("/") for r in cfg.get("redirects", [])}
    except Exception:
        return set()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    redirected = redirect_sources()
    urls = {}
    for root, dirs, files in os.walk(SITE):
        # Underscore-prefixed directories are backups and retired page sets (_pdufa_bak8,
        # _pdufa_xbak, _retired_*). They were being walked, so the sitemap was actively inviting
        # Google to index 203 stale duplicate pages -- near-duplicate thin content pointing at
        # superseded data, which is the worst possible thing to volunteer to a crawler.
        dirs[:] = [d for d in dirs
                   if d not in SKIP_DIRS and not d.startswith(".") and not d.startswith("_")]
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
            if SKIP_PAT.search(path) or path.rstrip("/") in redirected:
                continue
            # A sitemap entry says "crawl this, it matters". Listing a page that then serves
            # noindex is a contradiction that burns crawl budget on pages we have decided not to
            # rank. 324 of the price-only decision pages were doing exactly that.
            try:
                doc = open(full, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if NOINDEX.search(doc[:4000]):
                continue
            urls[path] = last_changed(rel, full, doc)

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

    # Committed, so a fresh CI checkout keeps knowing when each page's content last really changed.
    st = load_state()
    json.dump(st, open(STATE_F, "w", encoding="utf-8"), indent=0, sort_keys=True)
    today_n = sum(1 for v in st.values() if v.get("date") == TODAY)
    print(f"lastmod state: {len(st):,} pages tracked, {today_n:,} with a content change today")


if __name__ == "__main__":
    main()
