# -*- coding: utf-8 -*-
"""One answer to "does this site-relative URL serve?" -- for guards and fixers alike.

Written 2026-09-19 after a guard that only knew about `<path>/index.html` declared /pricing dead
and a fixer rewired the nav on 1,878 pages to route around a page that was live the whole time:
`pdufa_site_src/vercel.json` rewrites /pricing to /pricing.html (and /runup, /surges likewise),
and 551 redirects map retired URLs onto live ones. A URL serves if ANY of these holds:

  1. `<path>` is a file, or `<path>/index.html` is a file            (the static tree)
  2. vercel.json REWRITES `<path>` to a destination that serves      (e.g. /pricing)
  3. vercel.json REDIRECTS `<path>` to a destination that serves     (a 308 is not a 404)

Only literal sources are honoured; a pattern source (":slug", "(.*)") is ignored, so anything
served purely by a wildcard rule still needs an entry in _dead_link_allowlist.json.

    from site_routes import resolves
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
_PATTERN = re.compile(r"[:*(]")
_ROUTES = None


def routes():
    """{source_path: destination} for every literal rewrite and redirect in vercel.json."""
    global _ROUTES
    if _ROUTES is None:
        _ROUTES = {}
        try:
            cfg = json.load(io.open(os.path.join(SITE, "vercel.json"), encoding="utf-8"))
        except Exception:
            cfg = {}
        for key in ("rewrites", "redirects"):
            for r in cfg.get(key) or []:
                src, dst = str(r.get("source") or ""), str(r.get("destination") or "")
                if src and dst and not _PATTERN.search(src):
                    _ROUTES.setdefault(src.rstrip("/") or "/", dst)
    return _ROUTES


def _static(rel):
    p = os.path.join(SITE, rel.replace("/", os.sep))
    return os.path.isfile(p) or os.path.isfile(os.path.join(p, "index.html"))


def resolves(path, _depth=0):
    """True if the site would answer this internal URL with content (200 or a redirect to 200)."""
    if not isinstance(path, str) or not path.startswith("/"):
        return False
    target = path.split("#", 1)[0].split("?", 1)[0]
    rel = target.strip("/")
    if not rel or _static(rel):
        return True
    dst = routes().get("/" + rel)
    if dst is None or _depth > 3:
        return False
    if dst.startswith("http"):
        return True
    return resolves(dst, _depth + 1)


if __name__ == "__main__":
    import sys
    for a in sys.argv[1:] or ["/pricing", "/pricing.html", "/policy", "/today", "/calendar", "/nope"]:
        print(f"{a:<20} {'serves' if resolves(a) else 'DEAD'}   via {routes().get(a.rstrip('/'), 'static tree')}")
