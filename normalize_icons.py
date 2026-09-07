# -*- coding: utf-8 -*-
"""One canonical favicon link set on every page.

Fourteen builders each wrote their own <link rel="icon"> (three styles across 1,881 pages
on 2026-09-06, one of them an inline data: URI). This finishing pass replaces whatever
icon/apple-touch links a page carries with the canonical set, so a favicon change is one
file change plus a rebuild, never a fourteen-builder hunt. Idempotent; runs with the other
finishing passes.
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CANON = ('<link rel="icon" type="image/svg+xml" href="/favicon.svg">'
         '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">'
         '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">')
ICON_RE = re.compile(r'<link rel="(?:icon|apple-touch-icon|shortcut icon)"[^>]*>')


def main():
    n = 0
    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "<head" not in doc:
            continue
        links = ICON_RE.findall(doc)
        if links == [CANON[:CANON.index(">") + 1]] and doc.count("apple-touch-icon.png") == 1:
            continue
        new = ICON_RE.sub("", doc)
        # put the canonical set where the first icon link was, else right after <head...>
        if links:
            first = doc.find(links[0])
            head_end = doc.find(">", doc.find("<head")) + 1
            insert_at = first if first >= 0 else head_end
            new = ICON_RE.sub("", doc[:insert_at]) + CANON + ICON_RE.sub("", doc[insert_at:])
        else:
            hm = re.search(r"<head[^>]*>", new)
            if not hm:
                continue
            new = new[:hm.end()] + CANON + new[hm.end():]
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
            n += 1
    print(f"icons normalized on {n} page(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
