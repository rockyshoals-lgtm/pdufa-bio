# -*- coding: utf-8 -*-
"""add_ticker_crosslinks.py -- give the 377 long-tail pages a path in from the hubs.

The competitive teardown found the thing that actually decides this: Assyro, BiopharmaWatch and
FDA Tracker keep their event data behind query parameters, so their whole catalyst dataset ranks on
one URL. We have ~377 per-ticker, per-decision and per-catalyst pages they have no equivalent of.

Except /calendar and /decisions linked to exactly ZERO of them. The army existed and had no roads to
it. That is also the mechanical reason 421 URLs sit in "Discovered, currently not indexed": Google
found them in the sitemap, but nothing on the site argues they matter, and a sitemap entry with no
internal links is the weakest possible signal.

One structural constraint drove the design. Calendar and archive rows are themselves <a> elements,
so a ticker link cannot go inside a row: nested anchors are invalid and browsers silently unnest
them. So each hub gets a "Companies on this page" index underneath the list. That is valid, it is
genuinely useful to a reader scanning for one name, and every entry is a real crawl path into a page
that currently has none.

    python add_ticker_crosslinks.py [--dry-run]
"""
import argparse, glob, html, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--TICKERIDX:BEGIN-->", "<!--TICKERIDX:END-->"

# Hubs that list catalysts and should therefore route to the company pages.
TARGETS = (["calendar/index.html", "decisions/index.html", "decisions/approvals/index.html",
            "decisions/crl/index.html", "adcomm/index.html"]
           + [os.path.relpath(p, SITE).replace("\\", "/")
              for p in glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html"))])


def redirect_map():
    """/ticker/X -> wherever vercel.json actually sends it.

    Two companies (VKTX, SLS) have a richer deep-dive at the site root, and /ticker/<T> 301s to it.
    Linking at the redirect wastes the hop and, worse, spreads our internal links across two URLs
    for one company, which is the exact authority-splitting the competitive brief says to avoid.
    Read the map from the config so the links and the redirects can never disagree."""
    try:
        import json
        cfg = json.load(open(os.path.join(SITE, "vercel.json"), encoding="utf-8"))
        return {r["source"]: r["destination"] for r in cfg.get("redirects", [])
                if str(r.get("source", "")).startswith("/ticker/")}
    except Exception:
        return {}


def hubs_ticker(tk):
    return (os.path.isdir(os.path.join(SITE, "ticker", tk))
            or ("/ticker/" + tk) in redirect_map())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    total_links = pages = 0
    for rel in TARGETS:
        p = os.path.join(SITE, rel)
        if not os.path.exists(p):
            continue
        doc = open(p, encoding="utf-8", errors="replace").read()

        # Tickers this page already talks about, taken from the rows themselves so the index can
        # never advertise a company the page does not actually list.
        found = set()
        for m in re.finditer(r'<div class="t">([A-Z]{1,6})\s*(?:&middot;|·|&#183;)', doc):
            found.add(m.group(1))
        for m in re.finditer(r'href="/(?:pdufa|fda-decision|adcomm)/([A-Z]{1,6})[-/"]', doc):
            found.add(m.group(1))
        live = sorted(t for t in found if hubs_ticker(t))
        if not live:
            continue

        rmap = redirect_map()
        links = "".join(
            f'<a href="{rmap.get("/ticker/" + t, "/ticker/" + t)}" style="display:inline-block;padding:3px 8px;margin:2px;'
            f'border:1px solid var(--line);border-radius:7px;font-size:12.5px;'
            f'text-decoration:none" class="lit">{html.escape(t)}</a>' for t in live)

        block = (
            f'{B}<section style="margin:26px 0 8px;padding-top:14px;'
            f'border-top:1px solid var(--line)">'
            f'<h2 style="font-size:15px;margin:0 0 4px">Companies on this page</h2>'
            f'<div style="font-size:12.5px;color:var(--mut2);line-height:1.6;margin:0 0 8px">'
            f'Every company listed above, with its full catalyst history, past FDA decisions and '
            f'measured run-up into each one.</div>'
            f'<div>{links}</div></section>{E}')

        if B in doc:
            doc = doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
        else:
            anchor = '<div class="legal"'
            if anchor not in doc:
                anchor = "<footer"
            if anchor not in doc:
                print(f"  skip {rel}: no insertion point")
                continue
            doc = doc.replace(anchor, block + anchor, 1)

        if not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc)
        pages += 1
        total_links += len(live)
        print(f"  {rel:<38} {len(live):>3} company link(s)")

    print(f"\n{total_links} internal link(s) added across {pages} hub page(s)"
          + (" [dry run]" if a.dry_run else ""))
    print("Each one is a crawl path into a page that previously had none reachable from a hub.")


if __name__ == "__main__":
    main()
