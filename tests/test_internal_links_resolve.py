# -*- coding: utf-8 -*-
"""No internal link may point at a path that does not exist in this build.

Final audit 2026-09-02: when the daily refresh deleted 229 drug pages, 63 internal
links kept pointing at them -- live 404s from our own pages. This guard catches that
CLASS: every href="/..." across the built site must resolve to a page in the build, a
file, or a vercel.json redirect/rewrite. A deleted page that anything still links to
now fails the build instead of failing readers.
"""
import glob
import io
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")

# routes served by functions/rewrites rather than static files
DYNAMIC_PREFIXES = ("/api/", "/app", "/account", "/pricing", "/search")


def redirect_sources():
    try:
        v = json.load(io.open(os.path.join(SITE, "vercel.json"), encoding="utf-8"))
    except Exception:
        return set()
    out = set()
    for sec in ("redirects", "rewrites"):
        for r in v.get(sec, []) or []:
            s = str(r.get("source", ""))
            if s and ":" not in s and "*" not in s and "(" not in s:
                out.add(s.rstrip("/") or "/")
    return out


def test_internal_links_resolve():
    redir = redirect_sources()
    exists_cache = {}

    def resolves(path):
        p = path.split("#", 1)[0].split("?", 1)[0].rstrip("/") or "/"
        if p in exists_cache:
            return exists_cache[p]
        ok = (p in redir or p.startswith(DYNAMIC_PREFIXES)
              or os.path.exists(os.path.join(SITE, p.lstrip("/"), "index.html"))
              or os.path.exists(os.path.join(SITE, p.lstrip("/"))))
        exists_cache[p] = ok
        return ok

    bad = {}
    for f in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
        if os.sep + "_" in f:
            continue
        doc = io.open(f, encoding="utf-8", errors="replace").read()
        rel = "/" + os.path.relpath(os.path.dirname(f), SITE).replace("\\", "/")
        for m in re.finditer(r'href="(/[^"#?]*[^"]*)"', doc):
            t = m.group(1)
            if not resolves(t):
                bad.setdefault(t, []).append(rel)

    assert not bad, (f"{len(bad)} internal link target(s) do not exist in this build "
                     f"(the 63-broken-links class):\n  "
                     + "\n  ".join(f"{t}  <- linked from {len(srcs)} page(s), e.g. {srcs[0]}"
                                   for t, srcs in sorted(bad.items())[:15])
                     + (f"\n  ... and {len(bad) - 15} more" if len(bad) > 15 else ""))


if __name__ == "__main__":
    test_internal_links_resolve()
    print("OK")
