# -*- coding: utf-8 -*-
"""retarget_event_links.py -- every internal link to an event lands on the event's own page, in one hop.

Design red team 2026-11-18 (change 4, "One canonical page per event"). Capricor's Nov 22 decision had three pages,
and the site's surfaces split between them: the home cards and the calendar linked /pdufa/CAPR-deramiocel, the
home list, the screener, the condition pages, /fda-decisions-today and /pdufa-date-changes linked /pdufa/CAPR.
build_pdufa_ticker_index.py now keeps one page per event (rules 4 to 7), and the builders of those surfaces link the
row's own page; this pass rewrites what is left:

  1. A link to a /pdufa/ URL that vercel.json redirects (an old drug slug, a retired bare /pdufa/{T}) points at
     where the redirect lands, followed to the end of a chain, when that is a page of this site. A reader gets
     there in one hop and a crawler sees the page it should index.
  2. A link to a known duplicate event page (canonicalise_duplicate_event_pages.py DUPES) points at its primary;
     that step rewrites links once, and a pass after it (inject_site_links.py) could link the duplicate again.

A link to a bare /pdufa/{T} that is the ticker's index is left alone. An earlier draft sent it to the ticker's one
upcoming event, and the red team found that readout rows, drug pages and ticker hubs use /pdufa/{T} to mean "the
ticker's FDA page": a Zanidatamab readout landed on Jazz's cannabidiol page, and the indexes lost every inbound
link. Surfaces that mean the event link the event's own page in their builders instead.

Only href attributes outside scripts, absolute https://www.pdufa.bio/pdufa/... strings inside JSON-LD and a script's
JSON "url" fields (the /screener rows) are rewritten, never a page's own URL (its canonical, og:url and twitter:url), and never inside the page the link
names. Runs after inject_site_links.py and before build_sitemap.py. Idempotent; tests/test_one_event_one_page.py
fails on any link this pass would change.

    python retarget_event_links.py [--dry-run]
"""
import argparse
import datetime as dt
import glob
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
VJ = os.path.join(SITE, "vercel.json")
BASE = "https://www.pdufa.bio"
SKIP = re.compile(r"[\\/]_[A-Za-z0-9]*bak|[\\/]_pdufa_|[\\/]api[\\/]")
SLUG = r"[A-Za-z0-9.\-]+"
LINKS = re.compile(r'href="[^"]*"|"https://www\.pdufa\.bio/pdufa/[^"]*"|"url"\s*:\s*"[^"]*"')


def today_et():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:  # noqa: BLE001
        return dt.date.today().isoformat()


def exists(u):
    return os.path.exists(os.path.join(SITE, *u.strip("/").split("/"), "index.html"))


def targets(today=None):
    """{"/pdufa/X": "/the/page/it/should/link"} for every /pdufa/ URL a link must not stop at."""
    today = today or today_et()
    cfg = json.load(io.open(VJ, encoding="utf-8"))
    red = {str(r.get("source")): str(r.get("destination")) for r in cfg.get("redirects", [])
           if str(r.get("source", "")).startswith("/")}
    out = {}
    for src in red:
        if not re.match(rf"^/pdufa/{SLUG}$", src):
            continue
        d, seen = red[src], {src}
        while d in red and d not in seen:      # follow a chain to its end
            seen.add(d)
            d = red[d]
        d = d.split("#")[0].split("?")[0].rstrip("/")
        if d.startswith("/") and d != src and exists(d):
            out[src] = d
    # 2. a known duplicate event page (canonicalise_duplicate_event_pages.py) is linked by its primary, even from a
    #    pass that writes links after that step (inject_site_links.py)
    try:
        sys.path.insert(0, HERE)
        from canonicalise_duplicate_event_pages import active
        for dup, prim in active().items():
            if f"/pdufa/{dup}" not in out and exists(f"/pdufa/{prim}"):
                out[f"/pdufa/{dup}"] = f"/pdufa/{prim}"
    except ImportError:
        pass
    return out


def apply(doc, rel, tg):
    """The page with its links retargeted. rel is its path under the site ("pdufa/CAPR/index.html")."""
    own = "/" + rel[:-len("/index.html")] if rel.endswith("/index.html") else None
    if not tg:
        return doc
    alt = "|".join(re.escape(s[len("/pdufa/"):]) for s in sorted(tg, key=len, reverse=True))
    # a trailing slash is consumed only where it ends the URL: /pdufa/CAPR/og.png is a file, not a link to the page
    href = re.compile(rf'(href=")(?:{re.escape(BASE)})?/pdufa/({alt})(?=/?["#?])/?')
    absu = re.compile(rf'(")({re.escape(BASE)})/pdufa/({alt})(?=/?["#?])/?')

    def h(m):
        src = "/pdufa/" + m.group(2)
        return m.group(0) if src == own else m.group(1) + tg[src]

    def a(m):
        src = "/pdufa/" + m.group(3)
        return m.group(0) if src == own else m.group(1) + m.group(2) + tg[src]

    # a page's own URL stays its own (canonical, og:url, twitter:url); a script is left as it is, except JSON-LD,
    # whose absolute URLs are links like any other
    keep = re.compile(r'<link rel="canonical"[^>]*>|<meta (?:property|name)="(?:og|twitter):url"[^>]*>'
                      r'|<script\b(?![^>]*application/ld\+json)[^>]*>.*?</script>', re.S)
    ld = re.compile(r'<script\b[^>]*application/ld\+json[^>]*>.*?</script>', re.S)

    def fix(seg):
        seg = href.sub(h, seg)
        return ld.sub(lambda m: absu.sub(a, m.group(0)), seg)

    # a row a script renders carries its link as a JSON "url" field (the /screener data, built before
    # build_pdufa_ticker_index.py retires a bare /pdufa/{T}); that field is a link like any other
    jurl = re.compile(rf'("url"\s*:\s*")(?:{re.escape(BASE)})?/pdufa/({alt})(?=/?["#?])/?')

    out, pos = [], 0
    for k in keep.finditer(doc):
        out.append(fix(doc[pos:k.start()]))
        out.append(jurl.sub(h, k.group(0)) if k.group(0).startswith("<script") else k.group(0))
        pos = k.end()
    out.append(fix(doc[pos:]))
    return "".join(out)


def pages():
    return [p for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)) if not SKIP.search(p)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    tg = targets()
    n = links = 0
    for p in pages():
        rel = os.path.relpath(p, SITE).replace(os.sep, "/")
        doc = io.open(p, encoding="utf-8", errors="replace", newline="").read()
        new = apply(doc, rel, tg)
        if new != doc:
            n += 1
            links += sum(1 for x, y in zip(LINKS.findall(doc), LINKS.findall(new)) if x != y)
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    bare = sorted(s for s in tg if re.match(r"^/pdufa/[A-Z.]{1,7}$", s))
    print(f"event links: {len(tg)} /pdufa/ URL(s) retargeted ({len(bare)} bare tickers: {', '.join(b[7:] for b in bare)}); "
          f"{links} link(s) on {n} page(s) " + ("would change [dry run]" if a.dry_run else "rewritten"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
