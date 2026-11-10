# -*- coding: utf-8 -*-
"""build_decision_subhubs.py -- /decisions/approvals, /decisions/crl and the year pages, from /decisions' own rows.

2026-11-10 (audit 11-09 §5 items 5 and 10): /decisions carries 491 decided rows through October 2026, but
/decisions/approvals had stopped at July 2026 (82 rows under headings claiming "2026 · 15" and "2025 · 221", and an
EMPTY 2025 grid) and /decisions/crl at June 2026 (47 of 115). Nothing rebuilt them. /decisions/2025 and /decisions/2026
did not exist (404). Every page here is now cut from /decisions' published rows at build time, so the sub-hubs cannot
hold a different decision than the archive they belong to. Facts only, not investment advice.

    python build_decision_subhubs.py [--dry-run]
"""
import argparse
import html
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
BASE = "https://www.pdufa.bio"
ROW = re.compile(r'<a class="row"[^>]*>.*?</a>', re.S)
HEAD = re.compile(r'<div class="mhead">(\d{4})[^<]*</div><div class="grid">(.*?)</div>(?=<div class="mhead">|<!--TICKERIDX)',
                  re.S)


def read(rel):
    return io.open(os.path.join(SITE, rel, "index.html"), encoding="utf-8").read()


def sections(doc):
    """[(year, [row_html, ...])] in page order."""
    return [(y, ROW.findall(g)) for y, g in HEAD.findall(doc)]


def is_ok(r):
    return 'class="ok">Approved' in r or '<span class="ok">' in r.split('class="d"', 1)[-1][:60]


def is_crl(r):
    return 'class="no">CRL' in r or '<span class="no">' in r.split('class="d"', 1)[-1][:60]


def grid(secs):
    return "".join(f'<div class="mhead">{y} &middot; {len(rs)}</div><div class="grid">{"".join(rs)}</div>'
                   for y, rs in secs if rs)


def swap_grid(doc, secs):
    a = doc.index('<div class="mhead">')
    b = doc.index("<!--TICKERIDX:BEGIN-->")
    return doc[:a] + grid(secs) + doc[b:]


def set_head(doc, title, desc, url, h1):
    e = lambda s: html.escape(s, quote=True)
    doc = re.sub(r"(<title[^>]*>).*?(</title>)", lambda m: m.group(1) + e(title) + m.group(2), doc, count=1, flags=re.S)
    for pat in (r'(<meta name="description" content=")[^"]*(")', r'(<meta property="og:description" content=")[^"]*(")',
                r'(<meta name="twitter:description" content=")[^"]*(")'):
        doc = re.sub(pat, lambda m: m.group(1) + e(desc) + m.group(2), doc, count=1)
    for pat in (r'(<meta property="og:title" content=")[^"]*(")', r'(<meta name="twitter:title" content=")[^"]*(")'):
        doc = re.sub(pat, lambda m: m.group(1) + e(title.split(" | ")[0]) + m.group(2), doc, count=1)
    for pat in (r'(<link rel="canonical" href=")[^"]*(")', r'(<meta property="og:url" content=")[^"]*(")'):
        doc = re.sub(pat, lambda m: m.group(1) + url + m.group(2), doc, count=1)
    doc = re.sub(r"(<h1[^>]*>).*?(</h1>)", lambda m: m.group(1) + e(h1) + m.group(2), doc, count=1, flags=re.S)
    return doc


def year_page(template, year, rows):
    ap = sum(1 for r in rows if is_ok(r)); crl = sum(1 for r in rows if is_crl(r))
    title = f"FDA Decisions {year}: {len(rows)} PDUFA Outcomes, {ap} Approvals, {crl} CRLs | pdufa.bio"
    desc = (f"Every FDA PDUFA decision pdufa.bio tracked in {year}: {len(rows)} outcomes, {ap} approvals and {crl} "
            f"Complete Response Letters, each with its source and measured stock reaction. Not advice.")[:158]
    doc = set_head(template, title, desc, f"{BASE}/decisions/{year}", f"FDA decisions in {year}")
    doc = swap_grid(doc, [(year, rows)])
    # Archive-wide blocks state archive-wide numbers (491 decisions, 371 verified): a year page must not carry them.
    for k in ("HUBFAQ", "PROVENANCE"):
        doc = re.sub(rf"<!--{k}:BEGIN-->.*?<!--{k}:END-->", "", doc, flags=re.S)
    doc = re.sub(r'<script type="application/ld\+json"[^>]*>\{"@context":"https://schema.org","@type":"FAQPage".*?</script>',
                 "", doc, flags=re.S)
    tp = os.path.join(SITE, "research", "fda-decision-timing", "index.html")
    if os.path.exists(tp):
        t = io.open(tp, encoding="utf-8").read()
        if f"in {year}" in t or f" {year} " in t:
            link = (f'<!--TIMINGLINK:BEGIN--><div class="card" style="margin:10px 0">Early, on the day or late: '
                    f'<a href="/research/fda-decision-timing">FDA decision timing</a> counts the {year} decisions whose '
                    f'goal date and action date are both stated in a document we link.</div><!--TIMINGLINK:END-->')
            doc = doc.replace("<!--LEDE:END-->", "<!--LEDE:END-->" + link, 1)
    crumbs = ('{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": ['
              '{"@type": "ListItem", "position": 1, "name": "FDA Decisions", "item": "' + BASE + '/decisions"}, '
              '{"@type": "ListItem", "position": 2, "name": "' + year + '", "item": "' + BASE + '/decisions/' + year + '"}]}')
    doc = re.sub(r'(<script type="application/ld\+json"[^>]*>)\{"@context": "https://schema.org", "@type": "BreadcrumbList".*?(</script>)',
                 lambda m: m.group(1) + crumbs + m.group(2), doc, count=1, flags=re.S)
    return doc


def browse_line(doc, years):
    links = " &nbsp;&middot;&nbsp; ".join(f'<a href="/decisions/{y}">{y}</a>' for y in years)
    blk = f'<!--YEARS:BEGIN--><div class="card" style="margin:10px 0"><b>By year:</b> {links}</div><!--YEARS:END-->'
    if "<!--YEARS:BEGIN-->" in doc:
        return re.sub(r"<!--YEARS:BEGIN-->.*?<!--YEARS:END-->", lambda _: blk, doc, flags=re.S)
    i = doc.index('<div class="mhead">')
    return doc[:i] + blk + doc[i:]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    arch = read("decisions")
    secs = sections(arch)
    n = sum(len(rs) for _, rs in secs)
    if n < 100:
        sys.exit(f"/decisions parse found only {n} rows; refusing to rebuild the sub-hubs from it")
    years = [y for y, _ in secs]
    out = {}
    for rel, keep in (("decisions/approvals", is_ok), ("decisions/crl", is_crl)):
        doc = read(rel)
        sub = [(y, [r for r in rs if keep(r)]) for y, rs in secs]
        out[rel] = browse_line(swap_grid(doc, sub), years)
        print(f"  /{rel:22s} {sum(len(rs) for _, rs in sub):4d} rows  " +
              ", ".join(f"{y}: {len(rs)}" for y, rs in sub))
    out["decisions"] = browse_line(arch, years)
    for y, rs in secs:
        out[f"decisions/{y}"] = browse_line(year_page(arch, y, rs), years)
        print(f"  /decisions/{y:13s} {len(rs):4d} rows  approvals {sum(1 for r in rs if is_ok(r))}, "
              f"CRLs {sum(1 for r in rs if is_crl(r))}")
    if a.dry_run:
        print("dry run"); return 0
    for rel, doc in out.items():
        p = os.path.join(SITE, rel, "index.html")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "w", encoding="utf-8").write(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
