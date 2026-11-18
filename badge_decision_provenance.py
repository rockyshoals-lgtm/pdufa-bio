# -*- coding: utf-8 -*-
"""badge_decision_provenance.py -- every link to an inferred or unsourced FDA decision says so where it is listed.

Design red team 2026-11-18 (change 5). The homepage promised "every date links its source", while 107 decision pages
give an outcome inferred from the stock's price move and 17 cite no source at all. Each of those pages says so on the
page, but the lists that link them (/decisions and its year, approval and CRL lists, /calendar, the ticker and event
hubs, drug pages, the CRL months, the HTML sitemap) showed them exactly like a decision read from an FDA letter.

This pass puts a small badge inside every <a> that links /fda-decision/<slug> when that page is inferred ("Inferred")
or unsourced ("Unsourced"), as refresh_provenance_counts.page_kind() reads it, the same reader /decisions counts with.
The badge sits at the end of the link's last block (after the drug name or "FDA decision"), between <!--PV:B--> and
<!--PV:E-->. Every run strips the old badges first, so a page that gains a source loses its badge. Idempotent.

Runs late in the rebuild (after inject_site_links.py, before inject_mobile_polish.py), and quarantine_leads.py apply
re-runs it on any page it restores from the last commit. tests/test_provenance_badges.py fails if a link is missing
its badge or carries the wrong one.

    python badge_decision_provenance.py [--dry-run]
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
sys.path.insert(0, HERE)
from refresh_provenance_counts import page_kind  # noqa: E402

STYLE = ("font-size:11px;font-weight:600;line-height:1.5;border:1px solid {b};color:{c};border-radius:4px;"
         "padding:0 5px;margin-left:6px;white-space:nowrap;vertical-align:1px")
BADGE = {
    "inferred": ("Inferred", "#6b5a2f", "#f0c86a",
                 "Outcome inferred from the stock's move, not read from an FDA record or a filing"),
    "unsourced": ("Unsourced", "#6b2f3a", "#ff9fae", "Its decision page does not yet cite a source"),
}
PV = re.compile(r"<!--PV:B-->.*?<!--PV:E-->", re.S)
LINK = re.compile(r'(<a\b[^>]*\bhref="(?:https://www\.pdufa\.bio)?/fda-decision/([A-Z][A-Z0-9.]*-\d{4}-\d{2}-\d{2})/?"'
                  r'[^>]*>)(.*?)(</a>)', re.S)
AMB = re.compile(r'<span class="badge amb">unverified</span>')
# the last closing tag of the link's last block, when the link ends on one ("...: BRAFTOVI</div></a>")
TAIL = re.compile(r"((?:</(?:div|span|small|b|strong|em)>\s*)+)$")


def badge(kind):
    word, border, colour, title = BADGE[kind]
    return (f'<!--PV:B--><span class="pv pv-{kind}" title="{title}" style="{STYLE.format(b=border, c=colour)}">'
            f'{word}</span><!--PV:E-->')


_KINDS = {}


def kinds():
    if not _KINDS:
        for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
            _KINDS[os.path.basename(os.path.dirname(p))] = page_kind(io.open(p, encoding="utf-8",
                                                                             errors="replace").read())
    return _KINDS


def apply(doc, kind_of=None):
    kind_of = kind_of or kinds()
    if "/fda-decision/" not in doc and "<!--PV:B-->" not in doc:
        return doc
    doc = PV.sub("", doc)

    def one(m):
        k = kind_of.get(m.group(2))
        if k not in BADGE:
            return m.group(0)
        inner = m.group(3)
        if not re.sub(r"<[^>]+>", "", inner).strip():
            return m.group(0)
        if k == "inferred":
            # enrich_ticker_hubs.py swaps an inferred row's outcome mark for an amber "unverified"; the badge says it
            inner = AMB.sub("", inner)
        # inside the link's last block, after anything nested in it: before the outermost closing tag of the run
        # that ends the link ("<div class="d">...: BRAFTOVI</div>" gets it before that </div>)
        t = TAIL.search(inner)
        cut = len(inner)
        if t:
            closes = list(re.finditer(r"</[a-z]+>", t.group(1)))
            cut = t.start() + closes[-1].start()
        return m.group(1) + inner[:cut] + badge(k) + inner[cut:] + m.group(4)

    # skip <script> and <style> bodies: a link written inside a script string is not a listed row
    out, pos = [], 0
    for s in re.finditer(r"<(script|style)\b.*?</\1>", doc, re.S):
        out.append(LINK.sub(one, doc[pos:s.start()]))
        out.append(s.group(0))
        pos = s.end()
    out.append(LINK.sub(one, doc[pos:]))
    return "".join(out)


def pages():
    return sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    n = links = 0
    for p in pages():
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        new = apply(doc)
        if new != doc:
            n += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
        links += new.count("<!--PV:B-->")
    k = kinds()
    print(f"provenance badges: {links} link(s) badged on the site's pages, {n} page(s) "
          + ("would change [dry run]" if a.dry_run else "written")
          + f"; {sum(v == 'inferred' for v in k.values())} inferred, {sum(v == 'unsourced' for v in k.values())} "
            "unsourced decision pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
