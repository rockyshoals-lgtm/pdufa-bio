# -*- coding: utf-8 -*-
"""No backup copy of a page is deployed.

2026-11-25: /pdufa/COGT-bezuclastinib-summit/summit_bak was live for 12 days as a second copy of the event page
(robots index,follow), because a folder named "<name>_bak" matched none of .vercelignore's backup patterns. The
sitemap already skipped it; Vercel did not. This holds every backup-looking path under pdufa_site_src to the
deploy ignore list, so the next one fails here instead of going live.
"""
import fnmatch
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
BACKUP = re.compile(r"(_bak|xbak|\.bak)", re.I)


def patterns():
    out = []
    for line in open(os.path.join(SITE, ".vercelignore"), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith(("#", "!")):
            out.append(line.lstrip("/"))
    return out


def ignored(rel, pats):
    """gitignore-style: a pattern without a slash matches any path segment; one with a slash matches from the root."""
    segs = rel.split("/")
    for p in pats:
        if "/" in p:
            if fnmatch.fnmatch(rel, p) or any(fnmatch.fnmatch("/".join(segs[:i]), p) for i in range(1, len(segs))):
                return True
        elif any(fnmatch.fnmatch(s, p) for s in segs):
            return True
    return False


def test_every_backup_path_is_kept_off_the_live_site():
    pats = patterns()
    live = []
    for root, dirs, files in os.walk(SITE):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), SITE).replace(os.sep, "/")
            if BACKUP.search(rel) and not ignored(rel, pats):
                live.append(rel)
    assert not live, f"backup files that Vercel would deploy: {live[:10]}"


def test_the_summit_backup_pattern_is_covered():
    assert ignored("pdufa/COGT-bezuclastinib-summit/summit_bak/index.html", patterns())
    assert not ignored("pdufa/COGT-bezuclastinib-summit/index.html", patterns())


if __name__ == "__main__":
    test_the_summit_backup_pattern_is_covered()
    test_every_backup_path_is_kept_off_the_live_site()
    print("OK -- every backup-looking path under pdufa_site_src is in .vercelignore")
