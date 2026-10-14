# -*- coding: utf-8 -*-
"""CI guard: search submission is ordered, hubs first (audit 2026-10-13 order 2).

Bing's AI answer for "fda approval decisions this week" quoted our daily hubs from before Oct 8 while the
hubs had been right for five days: the nightly batch was ~1,300 URLs, unordered, and the 80-URL Bing channel
took whichever came first. ping_search_engines.prioritise() must put every changed daily hub first, then the
pages of the most recently updated dataset rows, then the rest; the Bing batch is its first 80. Planted: a
list with the hubs at the end must come back with them at the front, and the build_sitemap content hash must
be invariant to the modified-time stamps (order 3), else every stamped page counts as changed.

    python tests/test_search_submission_order.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import ping_search_engines as P  # noqa: E402
import build_sitemap as B  # noqa: E402


def main():
    fails = []
    tail = ["https://www.pdufa.bio/ticker/AAA", "https://www.pdufa.bio/drug/zzz", "https://www.pdufa.bio/pdufa/XYZ-drug"]
    planted = tail + list(reversed(P.HUBS))
    got = P.prioritise(planted)
    if got[:len(P.HUBS)] != [u for u in P.HUBS if u in planted]:
        fails.append(f"hubs are not first: {got[:4]}")
    if sorted(got) != sorted(planted) or len(got) != len(set(got)):
        fails.append("prioritise() dropped or duplicated URLs")
    src = io.open(os.path.join(HERE, "ping_search_engines.py"), encoding="utf-8").read()
    if "submission order, first 20" not in src:
        fails.append("ping_search_engines.py does not log the first 20 URLs it submits")
    page = ('<html><head><meta property="og:updated_time" content="2026-10-13T20:00:00-04:00">'
            '<meta property="article:modified_time" content="2026-10-13T20:00:00-04:00">'
            '<script type="application/ld+json">{"@type":"WebPage","name":"x","dateModified":"2026-10-13T20:00:00-04:00"}'
            '</script></head><body><h1>Content</h1></body></html>')
    bare = ('<html><head><script type="application/ld+json">{"@type":"WebPage","name":"x"}'
            '</script></head><body><h1>Content</h1></body></html>')
    if B.content_hash(page) != B.content_hash(bare):
        fails.append("build_sitemap.content_hash changes when only the modified-time stamps differ")
    if fails:
        print("FAIL: search submission order / lastmod invariance:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {len(P.HUBS)} hubs submit first; content hash is invariant to the modified-time stamps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
