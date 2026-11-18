# -*- coding: utf-8 -*-
"""CI guard: pdufa.bio stays usable on a phone (mobile red team 2026-11-17).

A real browser is not available in CI, so this checks the things that broke layouts on phones, in the HTML itself:

  1. every public page is at its inject_mobile_polish.py state: style#mobilepolish present and current, and every
     <table> inside a horizontally scrolling box (a bare 8-column table made the whole run-up study scroll sideways);
  2. every public page declares a responsive viewport and does not disable pinch-zoom;
  3. no page's own CSS fixes an element wider than a small phone (360px) outside a media query;
  4. the rebuild workflow and the local chain both run inject_mobile_polish.py, before the sitemap;
  5. the search button (cmdk.js) uses its compact, keyboard-reachable form up to the 720px menu breakpoint;
  6. no page's CSS sets text smaller than 10px (the homepage countdown labels were 8px);
  7. /decisions is newest-first inside each year (its sorter had silently stopped matching the year headers);
  8. the screener's event-type filters are real buttons, its rows keep their date on a phone, and its two date
     fields may wrap (side by side they made the page 428px wide on every phone);
  9. wide inline charts whose labels would draw under 10px on a phone scroll sideways at a readable size
     (part of 1: a planted 782-unit chart with 9-unit labels must be caught);
 10. every narrower chart whose labels a phone would draw under 11px has a phone-sized drawing (part of 1), and
     every phone drawing's smallest label is 11px or more in a 290px column (a planted run-up chart is checked).

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
import phone_charts as PC  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
VIEWPORT = re.compile(r'<meta[^>]+name="viewport"[^>]*content="([^"]*)"', re.I)
TINY = re.compile(r"font-size\s*:\s*([0-9](?:\.\d+)?)px")
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
    for ph in re.findall(r'<svg class="pd-phs".*?</svg>', doc, re.S):
        px = PC.phone_label_px(ph)
        if px is not None and px < PC.MIN_PX:
            probs.append(f"{rel}: a phone chart drawing has {px:.1f}px labels (fix: python inject_mobile_polish.py)")
    css = "".join(re.findall(r"<style[^>]*>(.*?)</style>", doc, re.S))
    for sel, decl in re.findall(r"([^{}@]+)\{([^{}]*)\}", css):
        for z in TINY.findall(decl):
            if float(z) < 10:
                probs.append(f"{rel}: '{sel.strip()[-40:]}' sets {z}px text, too small to read on a phone")
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
    # a later build step inserting before </head> (freshness stamp, dateModified, schema) must not count as stale:
    # that is what blocked the 2026-11-18 rebuild (issue 113); a stale or missing style block still must be caught
    later = good.replace("</head>", '<meta property="og:updated_time" content="2026-11-18"></head>', 1)
    if page_problems("planted", later):
        fails.append("guard self-check: a tag inserted after the style block by a later step was flagged")
    if not page_problems("planted", later.replace("overscroll-behavior-x:contain", "overscroll-behavior-x:auto")):
        fails.append("guard self-check: a stale style block was not caught")
    if not page_problems("planted", re.sub(r'<style id="mobilepolish">.*?</style>', "", later, flags=re.S)):
        fails.append("guard self-check: a missing style block was not caught")

    if not page_problems("planted", good.replace("</head>", "<style>.x i{font-size:8px}</style></head>")):
        fails.append("guard self-check: 8px text was not caught")
    chart = ('<svg viewBox="0 0 782 150" width="100%" role="img"><text x="1" y="9" font-size="9">Jun</text></svg>')
    wrapped = M.apply(good.replace("</body>", chart + "</body>"))[0]
    if page_problems("planted", wrapped) or "--cxw:956px" not in wrapped:
        fails.append("guard self-check: a wide chart with 9-unit labels was not given its phone scroll box")
    if not page_problems("planted", M.CX_OPEN.sub("", wrapped).replace(M.CX_CLOSE, "")):
        fails.append("guard self-check: a wide chart with unreadable phone labels was not caught")
    runup = ('<svg viewBox="0 0 640 190" role="img" style="width:100%;aspect-ratio:640/190;background:#071528">'
             '<polyline points="14,100 300,12 600,150" fill="none" stroke="#7aa8ff"/>'
             '<circle cx="300" cy="12" r="2.6" fill="#5fd07a"/><text x="300" y="10" font-size="10" '
             'text-anchor="middle">$27.37</text><text x="548" y="177" font-size="10" text-anchor="end">PDUFA 12/15/25'
             '</text><text x="14" y="164" font-size="10">6/30/25</text></svg>')
    phoned = M.apply(good.replace("</body>", runup + "</body>"))[0]
    if page_problems("planted", phoned) or (PC.phone_label_px(phoned[phoned.find('class="pd-phs"'):]) or 0) < 11:
        fails.append("guard self-check: a run-up chart with 10-unit labels did not get an 11px phone drawing")
    if not page_problems("planted", PC.STRIP.sub(r"\1", phoned)):
        fails.append("guard self-check: a run-up chart with no phone drawing was not caught")

    dec = io.open(os.path.join(SITE, "decisions", "index.html"), encoding="utf-8", errors="replace").read()
    for block in re.split(r'<div class="mhead"', dec)[1:]:
        ds = re.findall(r'<a class="row" href="/fda-decision/[^"]*?-(\d{4}-\d{2}-\d{2})"', block)
        if any(b > a for a, b in zip(ds, ds[1:])):
            fails.append("decisions/index.html: a year block is not newest-first (fix: python fix_decisions_order.py)")
            break
    scr = io.open(os.path.join(SITE, "screener", "index.html"), encoding="utf-8", errors="replace").read()
    if 'class="tg' in scr.replace('<button type="button" class="tg', ""):
        fails.append("screener: event-type filters must be <button>s (keyboard and screen readers)")
    if ".dt{display:none}" in scr:
        fails.append("screener: rows hide their date on phones")
    if re.search(r"\.dts\{[^}]*flex-wrap:nowrap", scr):
        fails.append("screener: the From and To date fields must be allowed to wrap on phones")

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
          f"to 720px; no text under 10px; wide charts scroll at a readable size; narrower charts have an 11px phone drawing; /decisions newest-first; screener filters are buttons. Self-check caught a planted bare table, a planted no-zoom viewport, planted 8px text, a planted wide chart with 9-unit labels and a planted run-up chart.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
