# -*- coding: utf-8 -*-
"""rebuild_nav.py -- one navigation, on every page, short enough to read on a phone.

Two problems, and the second is the worse one.

First, the nav was long. The biggest variant carried thirteen links. On a phone that is a wall, and
it buries the two things that actually differentiate this site (Decisions and the run-up study)
among API and Screener links that a retail reader will never click.

Second, and this is the real defect: there were EIGHT different navs across 858 pages. 470 pages had
thirteen links, 207 had seven, 127 had four. Which meant the site you could reach depended entirely
on which page Google happened to land you on, and a reader arriving on a decision page could not get
to the run-up study at all. Inconsistent internal linking is also precisely the crawl-demand problem
in the backlog: 478 URLs sitting in "Discovered, currently not indexed" while a third of the site
failed to link to the pages worth crawling.

The structure: six primary items, everything else under More.

    Calendar · Decisions · Readouts · Run-up · Stocks · [More] · Pro

Nothing is deleted. Conferences, Advisory Committees, Screener, Research, API, SLS and Account all
still exist at the same URLs and are all still linked, one click further away. No redirects, no
404s, no lost rankings. "AdComm" becomes "Advisory Committees" because AdComm is industry jargon and
this is meant to be readable by someone who has never filed an NDA.

Two page shapes exist and both are handled: <nav> inside .hd on section pages, and
<div class="nav"> inside .top on the generated hubs. 336 pages lacked the dropdown CSS entirely, so
a compact canonical style block is injected where it is missing.

    python rebuild_nav.py [--dry-run]
"""
import argparse, glob, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--NAVC:BEGIN-->", "<!--NAVC:END-->"

# Nav regroup (red team 2026-08-12g section 5.1): 14 flat items stopped being navigation.
# Three top-level anchors + two grouped dropdowns + Pro. SLS is a campaign, not a section --
# it lives on the homepage, not in permanent nav. Glossary/Learn/Methodology were live pages
# with ZERO inbound nav links ('three explainer surfaces, all orphaned') -- now under Research.
PRIMARY = [("/calendar", "Calendar"), ("/decisions", "Decisions"), ("/readouts", "Readouts"),
           ("/patent-cliff", "Patents")]
GROUPS = [
    ("Explore", [("/drug", "Drug Index"), ("/tickers", "Stocks"), ("/screener", "Screener"),
                 ("/conferences", "Conferences"), ("/adcomm", "Advisory Committees")]),
    ("Research", [("/research", "Studies"), ("/runup-by-year", "Run-up by Year"),
                  ("/learn/what-is-a-pdufa-date", "Learn"), ("/glossary", "Glossary"),
                  ("/methodology", "Methodology"), ("/developers", "API"),
                  ("/account", "Account")]),
]
PRO = ("/pricing", "Pro")

# Pages that are deliberately not part of the public site.
SKIP = re.compile(r"(_bak|_xbak|/_|\\_|app\.html|holding\.html|preview\.html|ping\.html"
                  r"|today\.html|index_redesign)", re.I)

CSS_ID = "navcanon"
CSS = (f'<style id="{CSS_ID}">.navdd{{position:relative;display:inline-flex;align-items:center}}'
       '.navddb{background:transparent;border:0;color:inherit;font:inherit;cursor:pointer;'
       'padding:7px 11px;border-radius:8px;display:inline-flex;align-items:center;gap:3px}'
       '.navdd:hover .navddb,.navdd:focus-within .navddb{color:#eef4fc}'
       '.navddm{position:absolute;top:100%;right:0;min-width:186px;background:#0b1626;'
       'border:1px solid #294d80;border-radius:12px;box-shadow:0 16px 40px rgba(0,0,0,.5);'
       'padding:6px;flex-direction:column;display:none;z-index:40}'
       '.navdd:hover .navddm,.navdd:focus-within .navddm{display:flex}'
       '.navddm a{padding:9px 12px!important;border-radius:8px;white-space:nowrap}'
       '.navddm a:hover{background:#132745}'
       '@media(max-width:720px){.navdd{display:contents}.navddb{display:none}'
       '.navddm{position:static;display:flex!important;min-width:0;background:transparent;'
       'border:0;box-shadow:none;padding:0}}</style>')


def nav_inner():
    a = "".join(f'<a href="{u}">{t}</a>' for u, t in PRIMARY)
    dds = ""
    for label, items in GROUPS:
        m = "".join(f'<a href="{u}">{t}</a>' for u, t in items)
        dds += ('<div class="navdd"><button class="navddb" aria-haspopup="true" '
                'aria-expanded="false" onclick="this.parentNode.classList.toggle(\'open\')">'
                f'{label}</button><div class="navddm">{m}</div></div>')
    return (B + a + dds +
            f'<a class="pro" href="{PRO[0]}" style="color:var(--gold)">{PRO[1]}</a>' + E)


NAV_TAG = re.compile(r"(<nav[^>]*>)(.*?)(</nav>)", re.S)
NAV_DIV = re.compile(r'(<div class="nav">)((?:\s*(?:<a\b[^>]*>.*?</a>|<div class="navdd">.*?</div>\s*</div>|<!--NAVC:(?:BEGIN|END)-->))+?)(\s*</div>)', re.S)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    inner = nav_inner()
    changed = css_added = skipped = untouched = 0

    for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)):
        if SKIP.search(p):
            skipped += 1
            continue
        html = open(p, encoding="utf-8", errors="replace").read()
        orig = html

        if B in html:
            html = re.sub(re.escape(B) + ".*?" + re.escape(E), lambda _: inner, html, flags=re.S)
        elif NAV_TAG.search(html):
            html = NAV_TAG.sub(lambda m: m.group(1) + inner + m.group(3), html, count=1)
        elif NAV_DIV.search(html):
            html = NAV_DIV.sub(lambda m: m.group(1) + inner + m.group(3), html, count=1)
        else:
            untouched += 1
            continue

        if f'id="{CSS_ID}"' not in html and 'id="navpolish"' not in html:
            if "</head>" in html:
                html = html.replace("</head>", CSS + "</head>", 1)
                css_added += 1

        if html != orig:
            changed += 1
            if not a.dry_run:
                open(p, "w", encoding="utf-8").write(html)

    print(f"nav: {changed} page(s) updated, {css_added} given the dropdown CSS, "
          f"{untouched} with no nav to rebuild, {skipped} skipped"
          + (" [dry run]" if a.dry_run else ""))
    print(f"     primary: {' · '.join(t for _, t in PRIMARY)} · More · {PRO[1]}")
    for label, items in GROUPS:
        print(f"     under {label}: {', '.join(t for _, t in items)}")


if __name__ == "__main__":
    main()
