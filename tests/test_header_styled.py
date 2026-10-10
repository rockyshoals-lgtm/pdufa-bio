# -*- coding: utf-8 -*-
"""CI guard: every indexable page's shared header is styled by the page's own inline CSS (audit 2026-10-04, UX P0).

/patent-cliff/exclusivity shipped with a 373-character stub stylesheet: on a phone the page opened as a raw
list of nav links a full screen tall before the headline. Every page inlines its CSS, so a template that
forgets the header rules renders unstyled. This reads each indexable page's header markup (the element that
wraps <a class="brand">, and whether the links sit in <nav> or <div class="nav">) and requires the combined
inline CSS to carry: the wrapper's class rule, .brand, and the nav-link rule. Proved by planting the stub.

    python tests/test_header_styled.py
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def main():
    fails, n = [], 0
    for p in sorted(glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True)):
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
        if re.search(r"/_[^/]*bak", rel):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        rob = re.search(r'<meta name="robots" content="([^"]*)"', doc)
        if rob and "noindex" in rob.group(1):
            continue
        m = re.search(r'<(div|header)[^>]*class="([^"]+)"[^>]*>\s*<a class="brand"', doc)
        if not m:
            continue
        n += 1
        css = " ".join(re.findall(r"<style[^>]*>(.*?)</style>", doc, re.S))
        wrapper = m.group(2).split()[0]
        after = doc[m.end():m.end() + 400]
        need = [f".{wrapper}", ".brand"]
        if "<nav" in after:
            need.append("nav a")
        elif 'class="nav"' in after:
            need.append(".nav a")
        miss = [k for k in need if k not in css]
        if miss:
            fails.append(f"{rel}: header rules missing from inline CSS: {miss} (first <style> {len(css)} chars total)")
    if fails:
        print(f"FAIL: {len(fails)} indexable page(s) whose header is unstyled:")
        for f in fails[:20]:
            print("   " + f)
        return 1
    print(f"OK -- {n} indexable pages carry the CSS their header markup uses.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
