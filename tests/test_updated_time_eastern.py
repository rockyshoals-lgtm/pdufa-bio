# -*- coding: utf-8 -*-
"""Every og:updated_time / article:modified_time on the site is either a bare date or an
Eastern-offset clock time (-04:00 EDT / -05:00 EST). Never UTC, never Pacific.

Audit 2026-09-08 N2: /pdufa/SRRK-apitegromab published `2026-09-06T22:10:35+00:00` while every
page that had changed since 2026-09-07 published `-04:00`. build_sitemap.py records new `ts`
values in Eastern; entries recorded before that carried UTC, and build_date_modified.py copies
`ts` verbatim. normalize_lastmod_tz.py relabelled the 493 legacy entries (same instant). This
asserts the RENDER on every page under pdufa_site_src, not the state file.

Proved 0 -> 1 -> 0 on 2026-09-08 by planting `+00:00` on /pdufa/SRRK-apitegromab.
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
RX = re.compile(r'<meta property="(?:og:updated_time|article:modified_time)" content="([^"]+)"')
OK = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}-0[45]:00)?$")


def main():
    bad, seen = [], 0
    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        head = io.open(p, encoding="utf-8", errors="replace").read(60000)
        for m in RX.finditer(head):
            seen += 1
            if not OK.match(m.group(1)):
                bad.append((os.path.relpath(p, SITE).replace("\\", "/"), m.group(1)))
    print(f"updated_time stamps checked: {seen}; non-Eastern: {len(bad)}")
    for rel, v in bad[:20]:
        print(f"  {rel}: {v}")
    if seen < 500:
        print("FAIL: fewer than 500 stamps found -- stamper did not run?")
        return 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
