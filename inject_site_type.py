# -*- coding: utf-8 -*-
"""inject_site_type.py -- every public page uses the site's two fonts and carries the logo mark.

Design red team 2026-11-18 (change 11, "one look everywhere"). The homepage loads Space Grotesk and IBM Plex Mono
(/fonts/fonts.css), sets headings, the wordmark and tickers/dates in them (<style id="typesys">) and draws the logo
mark beside the wordmark. Pages from older builders did not: 129 public pages loaded no site font at all
(/pdufa/CAPR-deramiocel, every /crl month, /tickers, /corrections), 918 lacked the type rules, and 1,371 showed
the wordmark without its mark (every /fda-application page, every /ticker hub). This pass runs late in the build,
after the last page builder, and adds whatever a page lacks:

  1. the font preloads and /fonts/fonts.css, inside <!--TYPE:B-->...<!--TYPE:E--> (build_sitemap.py strips the
     marked block, so adding it does not count as a content change);
  2. <style id="typesys"> (already stripped from the sitemap hash);
  3. the logo mark inside <a class="brand" href="/">, inside <!--LM:B-->...<!--LM:E--> (also stripped);
  4. the navmatch style (rebuild_nav.nav_match) on a page whose nav was written after rebuild_nav.py ran.

A page that already has an item is left alone. Idempotent; --dry-run writes nothing.

    python inject_site_type.py [--dry-run]
"""
import argparse
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
SKIP = re.compile(r"(_bak|_xbak|/_|\\_|app\.html|holding\.html|preview\.html|ping\.html|today\.html|index_redesign)",
                  re.I)

FONTS = ('<!--TYPE:B--><link rel="preload" href="/fonts/SpaceGrotesk-700.woff2" as="font" type="font/woff2" crossorigin>'
         '<link rel="preload" href="/fonts/IBMPlexMono-600.woff2" as="font" type="font/woff2" crossorigin>'
         '<link rel="stylesheet" href="/fonts/fonts.css"><!--TYPE:E-->')
TYPESYS = ("<style id=\"typesys\">h1,h2,h3,.brand{font-family:'Space Grotesk',-apple-system,BlinkMacSystemFont,"
           "'Segoe UI',sans-serif !important;letter-spacing:-.5px}body{font-variant-numeric:tabular-nums;"
           "font-feature-settings:\"tnum\" 1}.tk,.dt,.dd,.row .t,.count{font-family:'IBM Plex Mono',ui-monospace,"
           "SFMono-Regular,Menlo,monospace;font-variant-numeric:tabular-nums;letter-spacing:-.2px}</style>")
MARK = ('<!--LM:B--><svg class="lm" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" '
        'style="flex:none;vertical-align:-4px;margin-right:7px"><rect x="1" y="1" width="22" height="22" rx="6" '
        'fill="#081426" stroke="#294d80"/><rect x="6.5" y="9" width="2.4" height="9" rx="1" fill="#f0c86a"/>'
        '<rect x="7" y="5.5" width="1.4" height="14" rx=".7" fill="#f0c86a"/><rect x="11.6" y="6.5" width="2.4" '
        'height="11" rx="1" fill="#46d17f"/><rect x="12.1" y="4" width="1.4" height="16" rx=".7" fill="#46d17f"/>'
        '<circle cx="18" cy="8" r="2" fill="#46d17f"/></svg><!--LM:E-->')
BRAND = re.compile(r'(<a class="brand" href="/">)(?!<svg|<!--LM:B-->)(pdufa<b>\.bio</b></a>)')


def public(p, doc):
    return not SKIP.search(p) and "</head>" in doc and 'http-equiv="refresh"' not in doc[:4000]


def apply(doc):
    """(new doc, list of what was added)."""
    added = []
    if "/fonts/fonts.css" not in doc:
        m = re.search(r"<meta charset=[^>]*>", doc[:doc.find("</head>")])
        at = m.end() if m else doc.find("</head>")
        doc = doc[:at] + FONTS + doc[at:]
        added.append("fonts")
    if 'id="typesys"' not in doc:
        doc = doc.replace("</head>", TYPESYS + "</head>", 1)
        added.append("type rules")
    if BRAND.search(doc):
        doc = BRAND.sub(lambda m: m.group(1) + MARK + m.group(2), doc, count=1)
        added.append("logo mark")
    if 'class="navddb"' in doc:
        # rebuild_nav.py writes it, but a page built after that step would miss it
        import rebuild_nav
        want = rebuild_nav.nav_match(doc)
        cur = re.search(r'<style id="navmatch">.*?</style>', doc, re.S)
        if not cur:
            doc = doc.replace("</head>", want + "</head>", 1)
            added.append("nav style")
        elif cur.group(0) != want:
            doc = doc[:cur.start()] + want + doc[cur.end():]
            added.append("nav style")
    return doc, added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    n, tally = 0, {"fonts": 0, "type rules": 0, "logo mark": 0, "nav style": 0}
    for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if not public(p, doc):
            continue
        new, added = apply(doc)
        if new == doc:
            continue
        n += 1
        for k in added:
            tally[k] += 1
        if not a.dry_run:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"site type: {n} page(s) " + ("would change" if a.dry_run else "updated") + " ("
          + ", ".join(f"{v} {k}" for k, v in tally.items()) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
