# -*- coding: utf-8 -*-
"""CI guard: no published page links a site-internal URL that does not exist.

Found 2026-09-18 by walking the rendered site: the navigation's "Pro" entry pointed at /pricing
on 954 pages and `pdufa_site_src/pricing/index.html` has never existed in this repository. A dead
link in the site-wide nav is on every page a reader or a crawler ever sees, and nothing in the
suite looked. Five dataset rows also pointed at /pdufa/{TICKER} pages that were never built
(CELC, VERA), so their event links 404ed too.

Checks every internal href on every indexable page against the built tree. Anchors and query
strings are stripped; files with an extension (/api/..., /favicon.svg) are checked as files.

    python tests/test_no_dead_internal_links.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
LEDGER = os.path.join(HERE, "_dead_link_allowlist.json")
SKIP_DIR = re.compile(r"[\\/]_[a-z]+bak|[\\/]_pdufa_")


def exists(path):
    """Is this site-relative path servable?"""
    rel = path.strip("/")
    if not rel:
        return True
    p = os.path.join(SITE, rel.replace("/", os.sep))
    if os.path.isfile(p):
        return True
    if os.path.isfile(os.path.join(p, "index.html")):
        return True
    return False


def main():
    if not os.path.isdir(SITE):
        print("  SKIP no site")
        return 0
    try:
        allow = set(json.load(io.open(LEDGER, encoding="utf-8")).get("allow", []))
    except Exception:
        allow = set()

    dead = {}
    pages = 0
    for root, dirs, files in os.walk(SITE):
        if SKIP_DIR.search(root) or "index.html" not in files:
            continue
        p = os.path.join(root, "index.html")
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if re.search(r'name="robots"[^>]*content="[^"]*noindex', doc[:4000]):
            continue
        pages += 1
        rel_page = os.path.relpath(p, SITE).replace("\\", "/")
        for href in set(re.findall(r'href="(/[^"]*)"', doc)):
            target = href.split("#", 1)[0].split("?", 1)[0]
            if not target or target in allow:
                continue
            if not exists(target):
                dead.setdefault(target, []).append(rel_page)

    if dead:
        n = sum(len(v) for v in dead.values())
        print(f"FAIL: {len(dead)} internal target(s) do not exist, linked from {n} page(s):")
        for t, where in sorted(dead.items(), key=lambda kv: -len(kv[1]))[:12]:
            print(f"   {t:<40} linked from {len(where):>4} page(s), e.g. {where[0]}")
        print("\n   A link that 404s is worse on a site whose pitch is that every claim is "
              "checkable. Build the page, repoint the link, or add a reviewed entry to "
              "_dead_link_allowlist.json.")
        return 1
    print(f"OK -- {pages} indexable page(s): every internal link resolves to a built page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
