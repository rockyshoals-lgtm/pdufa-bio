# -*- coding: utf-8 -*-
"""add_og_tags.py -- every indexable page carries a complete Open Graph / Twitter card set.

SEO audit 2026-09-23: 168 indexable pages had no og:title at all (94 decision pages built before
the template carried one, 39 /patent-cliff pages, 30 /pdufa event pages, /calendar/2025, one
/learn page, /surges), and the pages that did have og:title mostly lacked og:description and
og:site_name. Bing, LinkedIn, Slack, X and the AI answer engines that unfurl a link all read
these; a page without them is shared as a bare URL.

Rules (idempotent -- each tag is added only when absent, never rewritten):
  og:type         article for /fda-decision, /pdufa, /learn, /research, /readouts, /adcomm,
                  /drug, /conferences; website otherwise
  og:site_name    pdufa.bio
  og:url          the page's canonical (skipped if the page has no canonical)
  og:title        <title>
  og:description  <meta name="description">
  twitter:card    summary

Existing og:title/og:description are left exactly as their owners wrote them (rewrite_decision_
snippets, mark_event_pages_decided, fix_meta_lengths all own those strings on their pages).
Noindex pages are skipped. Run before build_date_modified (og:updated_time is its).

    python add_og_tags.py [--dry-run]
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
SKIP = re.compile(r"[\\/]_[a-z]+bak|[\\/]_pdufa_|[\\/]_site_attic|[\\/]_[^\\/]*\.html$")
ARTICLE = ("/fda-decision/", "/pdufa/", "/learn/", "/research/", "/readouts/", "/adcomm/",
           "/drug/", "/conferences/")


def og_type(rel):
    return "article" if any(rel.startswith(p) for p in ARTICLE) else "website"


def process(path, dry):
    doc = io.open(path, encoding="utf-8", errors="replace").read()
    head_end = doc.find("</head>")
    if head_end < 0:
        return 0
    head = doc[:head_end]
    if re.search(r'name="robots"[^>]*noindex', head):
        return 0
    rel = "/" + os.path.relpath(path, SITE).replace("\\", "/")
    rel = re.sub(r"/index\.html$", "", rel) or "/"
    title = re.search(r"<title>([^<]*)</title>", head)
    desc = re.search(r'<meta name="description" content="([^"]*)"', head)
    canon = re.search(r'<link rel="canonical" href="([^"]*)"', head)
    if not title:
        return 0
    add = []
    have = lambda p: re.search(r'<meta (?:property|name)="' + re.escape(p) + '"', head)
    if not have("og:type"):
        add.append(f'<meta property="og:type" content="{og_type(rel)}">')
    if not have("og:site_name"):
        add.append('<meta property="og:site_name" content="pdufa.bio">')
    if canon and not have("og:url"):
        add.append(f'<meta property="og:url" content="{canon.group(1)}">')
    if not have("og:title"):
        add.append(f'<meta property="og:title" content="{title.group(1)}">')
    if desc and not have("og:description"):
        add.append(f'<meta property="og:description" content="{desc.group(1)}">')
    if not have("twitter:card"):
        add.append('<meta name="twitter:card" content="summary">')
    if not add:
        return 0
    block = "".join(add)
    # after the description meta when there is one, else after <title>
    anchor = desc.end() if desc else title.end()
    doc = doc[:anchor] + block + doc[anchor:]
    if not dry:
        io.open(path, "w", encoding="utf-8", newline="").write(doc)
    return len(add)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    pages = tags = 0
    for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)):
        if SKIP.search(p):
            continue
        n = process(p, a.dry_run)
        if n:
            pages += 1
            tags += n
    print(f"open graph: {tags} tag(s) added on {pages} page(s){' (dry run)' if a.dry_run else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
