# -*- coding: utf-8 -*-
"""The service worker may never serve a document or a data file from its cache.

Audit 2026-09-10 reported that /calendar served a 17,271-byte June 27 snapshot while
/calendar/ served the current 88 KB page, and concluded the deployment carried leftover flat
files. It does not: fetched from this machine, every no-slash/slash pair is byte-identical
(same md5, same last-modified) on both hosts. The split was produced by OUR SERVICE WORKER in
the auditor's browser.

sw.js v3 routed to network-first only when `req.mode === "navigate"`, or the path ended in
".html", or was "/" or "/api/data". Hub URLs are extensionless, and a `fetch()` from page
script is mode "cors"/"same-origin", not "navigate" -- so /calendar fell through to the
cache-first branch and was stored permanently. Every later fetch() got the June copy back
WITH ITS STORED JUNE HEADERS, which is why a forced-revalidation probe reported
last-modified 27 Jun, age 0, x-vercel-cache MISS and looked like a live server response.
/build-info.json was pinned the same way at its 2026-08-08 copy, so the freshness stamp
hydrated from a month-old file despite asking for cache:'no-store'.

Contract on sw.js:
  1. the cache name must not be the poisoned "pdufa-v3" (bumping it is what evicts v3 from
     browsers that already carry it, via the activate handler);
  2. the cache-first path must be reachable only for asset extensions -- an extensionless
     path, .html or .json must never be eligible;
  3. documents must be excluded explicitly, so a request for "/x.png" with destination
     "document" cannot slip through.

Proved 0 -> 1 -> 0 on 2026-09-10 by restoring the v3 routing line.
"""
import io
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SW = os.path.join(HERE, "pdufa_site_src", "sw.js")


def test_sw_never_caches_documents():
    src = io.open(SW, encoding="utf-8", errors="replace").read()
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    code = "\n".join(ln.split("//", 1)[0] for ln in code.splitlines())

    m = re.search(r'const\s+C\s*=\s*"([^"]+)"', code)
    assert m, "sw.js no longer names its cache -- guard cannot see"
    assert m.group(1) != "pdufa-v3", (
        "sw.js still uses the poisoned cache name pdufa-v3; browsers carrying June documents "
        "will keep serving them because activate only deletes caches whose key differs")

    # the asset allowlist decides what may be cached at all
    am = re.search(r"const\s+ASSET\s*=\s*/([^/]+)/", code)
    assert am, ("sw.js must gate its cache on an explicit asset-extension allowlist; without "
                "one, extensionless hub URLs become cacheable again (the /calendar failure)")
    pattern = am.group(1)
    for bad in (r"html", r"json"):
        assert bad not in pattern.lower(), \
            f"the asset allowlist admits .{bad} -- documents and data must never be cached"

    try:
        rx = re.compile(pattern, re.I)
    except re.error as e:                                   # pragma: no cover
        raise AssertionError(f"asset allowlist is not a valid regex: {e}")
    for path in ("/calendar", "/decisions", "/learn/what-is-a-pdufa-date",
                 "/build-info.json", "/api/v1/events", "/index.html"):
        assert not rx.search(path), \
            f"the asset allowlist matches {path}, which is a document or data file"

    assert re.search(r'destination\s*===\s*"document"', code), (
        "sw.js must exclude requests whose destination is 'document' from the cache-first "
        "path; mode==='navigate' alone was what let fetch()ed pages be cached")

    assert re.search(r"e\.respondWith\(\s*fetch\(req\)", code), \
        "sw.js must go to the network first for everything that is not an allowlisted asset"


if __name__ == "__main__":
    test_sw_never_caches_documents()
    print("OK")
