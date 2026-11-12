# -*- coding: utf-8 -*-
"""CI guard: every indexable sitemap URL is within 3 clicks of / in the built HTML (audit 2026-11-11 order 2).

Google had 1,568 pages "Discovered - currently not indexed" while the homepage linked to none of the event, decision
or study pages. Crawls follow links; a page three hops deep is found, a page only in sitemap.xml is often not.
Asserts, over the built pdufa_site_src tree:
  * every URL in sitemap.xml is reachable from / in at most 3 clicks;
  * no sitemap URL has zero inbound links from other pages (orphans 0);
  * the median inbound link count across sitemap URLs is at least 5.
"""
import collections
import glob
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
HREF = re.compile(r'<a\s[^>]*href="(/[^"#?]*)')


def norm(u):
    u = u.split("#")[0].split("?")[0]
    return (u.rstrip("/") or "/") if not u.endswith((".xml", ".json", ".txt", ".png", ".csv", ".ics", ".js")) else None


def main():
    pages = {}
    for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
        rel = os.path.relpath(os.path.dirname(p), SITE).replace(os.sep, "/")
        pages["/" if rel == "." else "/" + rel] = p
    links = {}
    inbound = collections.Counter()
    for u, p in pages.items():
        doc = open(p, encoding="utf-8", errors="replace").read()
        outs = {n for n in (norm(h) for h in HREF.findall(doc)) if n and n != u}
        links[u] = outs
        for v in outs:
            inbound[v] += 1
    sm = open(os.path.join(SITE, "sitemap.xml"), encoding="utf-8").read()
    want = [re.sub(r"^https://www\.pdufa\.bio", "", x).rstrip("/") or "/" for x in re.findall(r"<loc>([^<]+)</loc>", sm)]
    depth = {"/": 0}
    frontier = ["/"]
    for d in (1, 2, 3):
        nxt = []
        for u in frontier:
            for v in links.get(u, ()):
                if v not in depth:
                    depth[v] = d
                    nxt.append(v)
        frontier = nxt
    far = [u for u in want if u not in depth]
    orphans = [u for u in want if u != "/" and inbound[u] == 0]
    med = statistics.median(inbound[u] for u in want) if want else 0
    fails = []
    if far:
        fails.append(f"{len(far)} sitemap URL(s) more than 3 clicks from / (or unreachable), e.g. {far[:5]}")
    if orphans:
        fails.append(f"{len(orphans)} orphan(s) with no inbound link, e.g. {orphans[:5]}")
    if med < 5:
        fails.append(f"median inbound links {med} < 5")
    if fails:
        print("FAIL: internal-link reachability:")
        for f in fails:
            print("   " + f)
        return 1
    hist = collections.Counter(depth[u] for u in want)
    print(f"OK -- {len(want)} sitemap URLs all within 3 clicks of / (depth {dict(sorted(hist.items()))}); "
          f"0 orphans; median inbound links {med}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
