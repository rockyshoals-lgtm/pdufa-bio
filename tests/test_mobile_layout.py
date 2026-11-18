# -*- coding: utf-8 -*-
"""CI guard: pdufa.bio stays usable on a phone (mobile red team 2026-11-17).

A real browser is not available in CI, so this checks the things that broke layouts on phones, in the HTML itself:

  1. every public page is at its inject_mobile_polish.py state: style#mobilepolish present and current, and every
     <table> inside a horizontally scrolling box (a bare 8-column table made the whole run-up study scroll sideways);
  2. every public page declares a responsive viewport and does not disable pinch-zoom;
  3. no page's own CSS fixes an element wider than a small phone (360px) outside a media query;
  4. the rebuild workflow and the local chain both run inject_mobile_polish.py, before the sitemap;
  5. the search button (cmdk.js) uses its compact, keyboard-reachable form up to the 720px menu breakpoint.

A planted bare table and a planted no-zoom viewport must each be caught, so the guard cannot pass vacuously.

    python tests/test_mobile_layout.py
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import inject_mobile_polish as M  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
VIEWPORT = re.compile(r'<meta[^>]+name="viewport"[^>]*content="([^"]*)"', re.I)
WIDE = re.compile(r"(?<![-\w])(?:min-)?width\s*:\s*(\d{3,})px")


def top_level_css(doc):
    css = "".join(re.findall(r"<style[^>]*>(.*?)</style>", doc, re.S))
    css = re.sub(r'<style id="mobilepolish">.*?</style>', "", css, flags=re.S)
    out, i = [], 0
    while True:
        m = re.search(r"@(?:media|supports)[^{]*\{", css[i:])
        if not m:
            out.append(css[i:])
            return "".join(out)
        out.append(css[i:i + m.start()])
        j, depth = i + m.end(), 1
        while depth and j < len(css):
            depth += {"{": 1, "}": -1}.get(css[j], 0)
            j += 1
        i = j


def page_problems(rel, doc):
    probs = []
    if M.apply(doc)[0] != doc:
        bare = M.wrap_tables(doc)[0] != doc
        probs.append(f"{rel}: not at its mobile-polish state"
                     + (" (a <table> has no scroll box)" if bare else " (style#mobilepolish missing or stale)"))
    m = VIEWPORT.search(doc)
    if not m or "width=device-width" not in m.group(1).replace(" ", ""):
        probs.append(f"{rel}: no responsive viewport meta")
    elif re.search(r"user-scalable\s*=\s*(no|0)|maximum-scale\s*=\s*1(\.0)?\b", m.group(1)):
        probs.append(f"{rel}: viewport disables pinch-zoom ({m.group(1)})")
    for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", top_level_css(doc)):
        if "max-width" in decl or re.search(r"\b(table|th|td|svg|canvas)\b", sel):
            continue
        for w in WIDE.findall(decl):
            if int(w) > 360:
                probs.append(f"{rel}: '{sel.strip()[:40]}' fixed at {w}px, wider than a small phone")
    return probs


def main():
    fails, n = [], 0
    for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)):
        if M.SKIP.search(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace", newline="").read()
        if "</head>" not in doc or "pdufa.bio: locked" in doc:
            continue
        n += 1
        fails += page_problems(os.path.relpath(p, SITE).replace("\\", "/"), doc)

    # the guard must catch what it guards against
    good = M.apply('<html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head>'
                   '<body><table><tr><td>x</td></tr></table></body></html>')[0]
    if page_problems("planted", good):
        fails.append("guard self-check: a correct page was flagged")
    if not page_problems("planted", good.replace(M.TW_OPEN, "").replace(M.TW_CLOSE, "")):
        fails.append("guard self-check: a bare table was not caught")
    if not page_problems("planted", good.replace("initial-scale=1", "initial-scale=1,maximum-scale=1")):
        fails.append("guard self-check: a no-zoom viewport was not caught")

    wf = open(os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml"), encoding="utf-8").read()
    a, b = wf.find("python inject_mobile_polish.py"), wf.rfind("run: python build_sitemap.py")
    if a < 0 or b < 0 or a > b:
        fails.append("pdufa-rebuild.yml must run inject_mobile_polish.py before the final build_sitemap.py")
    chain = open(os.path.join(HERE, "_chain_0919.bat"), encoding="utf-8", errors="replace").read()
    a, b = chain.find("inject_mobile_polish.py"), chain.find("build_sitemap.py")
    if a < 0 or a > b:
        fails.append("_chain_0919.bat must run inject_mobile_polish.py before the final build_sitemap.py")

    js = open(os.path.join(SITE, "cmdk.js"), encoding="utf-8").read()
    if "@media (max-width:720px){#cmdkBtn{" not in js or "innerWidth<=720" not in js:
        fails.append("cmdk.js: the search button's compact phone form must apply up to 720px")
    if "'tabindex','0'" not in js:
        fails.append("cmdk.js: the search button must be reachable by keyboard (tabindex=0)")

    if fails:
        print(f"FAIL: {len(fails)} mobile layout problem(s)  (fix: python inject_mobile_polish.py)")
        for f in fails[:25]:
            print("   " + f)
        return 1
    print(f"OK -- {n} pages: tables scroll in place, mobile polish current, responsive viewport with zoom allowed, "
          f"no fixed width over 360px; workflow and chain run the pass before the sitemap; search button compact "
          f"to 720px. Self-check caught a planted bare table and a planted no-zoom viewport.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
