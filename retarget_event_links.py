# -*- coding: utf-8 -*-
"""retarget_event_links.py -- every internal link to an event lands on the event's own page, in one hop.

Design red team 2026-11-18 (change 4, "One canonical page per event"). Capricor's Nov 22 decision had three pages,
and the site's surfaces split between them: the home cards and the calendar linked /pdufa/CAPR-deramiocel, the
home list, the screener, the condition pages, /fda-decisions-today and /pdufa-date-changes linked /pdufa/CAPR.
build_pdufa_ticker_index.py now keeps one page per event (rules 4 to 6); this pass rewrites the links:

  1. A link to a /pdufa/ URL that vercel.json redirects (an old drug slug, a retired bare /pdufa/{T}) points at
     where the redirect lands, followed to the end of a chain, when that is a page of this site. A reader gets
     there in one hop and a crawler sees the page it should index.
  2. A link to a bare /pdufa/{T} whose ticker has exactly one upcoming PDUFA, when that event has its own page and
     no dataset row links /pdufa/{T} itself, points at the event's own page. Before this change /pdufa/{T} WAS
     that event's page, so every such link meant the event; now /pdufa/{T} is the ticker's index (it keeps a
     past decision on record), and the event is one click further in.
  3. A link to a known duplicate event page (canonicalise_duplicate_event_pages.py DUPES) points at its primary;
     that step rewrites links once, and a pass after it (inject_site_links.py) could link the duplicate again.

Only href attributes and absolute https://www.pdufa.bio/pdufa/... strings (JSON-LD) are rewritten, never a page's
own URL (its canonical and og:url), and never inside the page the link names. Runs after inject_site_links.py and
before build_sitemap.py. Idempotent; tests/test_one_event_one_page.py fails on any link this pass would change.

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
LINKS = re.compile(r'href="[^"]*"|"https://www\.pdufa\.bio/pdufa/[^"]*"')


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
    srcd = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(srcd[srcd.find("["):])
    up, linked = {}, set()
    for r in rows:
        if r.get("type") != "PDUFA" or not r.get("t"):
            continue
        t = str(r["t"]).upper()
        u = str(r.get("url") or "").split("#")[0].split("?")[0].rstrip("/")
        linked.add((t, u))
        if str(r.get("st", "")).lower() not in ("decided", "withdrawn") and str(r.get("d", "")) >= today:
            up.setdefault(t, []).append(u)
    # 3. a known duplicate event page (canonicalise_duplicate_event_pages.py) is linked by its primary, even from a
    #    pass that writes links after that step (inject_site_links.py)
    try:
        sys.path.insert(0, HERE)
        from canonicalise_duplicate_event_pages import active
        for dup, prim in active().items():
            if f"/pdufa/{dup}" not in out and exists(f"/pdufa/{prim}"):
                out[f"/pdufa/{dup}"] = f"/pdufa/{prim}"
    except ImportError:
        pass
    for t, urls in up.items():
        bare = f"/pdufa/{t}"
        if bare in out or len(urls) != 1 or (t, bare) in linked:
            continue
        u = urls[0]
        if re.match(rf"^/pdufa/{SLUG}$", u) and u != bare and exists(u):
            out[bare] = u
    return out


def apply(doc, rel, tg):
    """The page with its links retargeted. rel is its path under the site ("pdufa/CAPR/index.html")."""
    own = "/" + rel[:-len("/index.html")] if rel.endswith("/index.html") else None
    if not tg:
        return doc
    alt = "|".join(re.escape(s[len("/pdufa/"):]) for s in sorted(tg, key=len, reverse=True))
    href = re.compile(rf'(href=")(?:{re.escape(BASE)})?/pdufa/({alt})(?=["/#?])/?')
    absu = re.compile(rf'(")({re.escape(BASE)})/pdufa/({alt})(?=["/#?])/?')

    def h(m):
        src = "/pdufa/" + m.group(2)
        return m.group(0) if src == own else m.group(1) + tg[src]

    def a(m):
        src = "/pdufa/" + m.group(3)
        return m.group(0) if src == own else m.group(1) + m.group(2) + tg[src]

    # a page's own URL stays its own: the canonical link and og:url are left as they are
    keep = re.compile(r'<link rel="canonical"[^>]*>|<meta property="og:url"[^>]*>')
    out, pos = [], 0
    for k in keep.finditer(doc):
        seg = doc[pos:k.start()]
        out.append(absu.sub(a, href.sub(h, seg)))
        out.append(k.group(0))
        pos = k.end()
    out.append(absu.sub(a, href.sub(h, doc[pos:])))
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
