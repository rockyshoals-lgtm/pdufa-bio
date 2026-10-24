# -*- coding: utf-8 -*-
"""inject_decision_article_schema.py -- every /fda-decision page states, in machine-readable form, what it is and when.

Audit 2026-10-22 (SEO / Bing / AI citation). The decision pages are the facts answer engines quote ("was X approved,
and when"), yet their structured data was only BreadcrumbList + FAQPage: no NewsArticle, no datePublished, no
publisher, no link to the primary source in schema. og:type was "article" with article:modified_time but no
article:published_time. A citing engine had to guess the page's own date and its source.

This writes one marker-bounded NewsArticle block per decision page:
  headline        the page's <h1> (tags stripped), else its <title> without the site suffix
  description     the page's meta description
  datePublished   the day the page was first committed (git, converted to EASTERN, RULE 1), cached in
                  _decision_published.json so CI's shallow clone never has to compute it; a page first seen in CI
                  gets that run's Eastern date
  dateModified    the page's own article:modified_time (content-change date, build_date_modified.py)
  author/publisher  Organization pdufa.bio
  isBasedOn       the dataset row's decision source (FDA notice / letter / sponsor release), when the row has one
  about           the drug (brand and INN from the row)
and adds article:published_time beside article:modified_time. Idempotent.

    python inject_decision_article_schema.py [--dry-run] [--seed-from-git]
"""
import argparse
import datetime as dt
import glob
import html
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CACHE = os.path.join(HERE, "_decision_published.json")
sys.path.insert(0, HERE)
from site_dates import eastern_today, _ET  # noqa: E402

B = '<script type="application/ld+json" id="ld-article">'
E = "</script>"
ORG = {"@type": "Organization", "name": "pdufa.bio", "url": "https://www.pdufa.bio/"}


def seed_from_git():
    """slug -> Eastern date of the commit that added the page (local full history only)."""
    out = subprocess.run(["git", "log", "--diff-filter=A", "--name-only", "--format=@@%aI", "--",
                          "pdufa_site_src/fda-decision"], cwd=HERE, capture_output=True, text=True, encoding="utf-8")
    first, when = {}, None
    for line in out.stdout.splitlines():
        if line.startswith("@@"):
            t = dt.datetime.fromisoformat(line[2:])
            # RULE 1: git author time carries its own offset (Pacific here); the site speaks Eastern
            when = t.astimezone(_ET).date().isoformat()
        else:
            m = re.match(r"pdufa_site_src/fda-decision/([A-Z]{1,6}-\d{4}-\d{2}-\d{2})/index\.html$", line.strip())
            if m and when:
                first[m.group(1)] = when      # log is newest first: the last assignment is the earliest add
    return first


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seed-from-git", action="store_true")
    a = ap.parse_args()
    cache = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    if a.seed_from_git:
        g = seed_from_git()
        for k, d in g.items():
            if k not in cache or d < cache[k]:
                cache[k] = d
        print(f"seeded {len(g)} first-commit dates from git")
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    byslug = {f"{str(r.get('t') or '').upper()}-{str(r.get('dcd'))[:10]}": r for r in rows
              if r.get("type") == "PDUFA" and r.get("dcd")}
    today = eastern_today().isoformat()
    n = changed = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        if not re.match(r"^[A-Z]{1,6}-\d{4}-\d{2}-\d{2}$", slug):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if re.search(r'<meta name="robots" content="noindex', doc):
            continue
        pub = cache.setdefault(slug, today)
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S)
        title = re.search(r"<title>(.*?)</title>", doc, re.S)
        # 2026-10-24: the <title> leads (rewrite_decision_snippets curates it: "Dupixent Approved Apr 18, 2025"); older
        # pages' h1 reads "REGN FDA Decision Approved · 2025-04-18", which is what the first version put in headline.
        headline = html.unescape(title.group(1)).split(" | ")[0].strip() if title else ""
        if not headline and h1:
            headline = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
        desc = re.search(r'<meta name="description" content="([^"]*)"', doc)
        mod = re.search(r'<meta property="article:modified_time" content="([^"]+)"', doc)
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', doc)
        r = byslug.get(slug) or {}
        d = r.get("_d") or {}
        art = {"@context": "https://schema.org", "@type": "NewsArticle",
               "headline": re.sub(r"\s+", " ", headline)[:110],
               "description": html.unescape(desc.group(1)) if desc else "",
               "datePublished": pub,
               "dateModified": max(pub, (mod.group(1) if mod else pub)[:10]),
               "author": ORG, "publisher": ORG,
               "mainEntityOfPage": canon.group(1) if canon else f"https://www.pdufa.bio/fda-decision/{slug}",
               "isAccessibleForFree": True}
        srcu = d.get("fda_action_source_url") or d.get("decision_source_url") or (r.get("url") if str(r.get("url") or "").startswith("http") else "")
        if srcu:
            art["isBasedOn"] = srcu
        if d.get("brand") or d.get("inn"):
            drug = {"@type": "Drug", "name": d.get("brand") or d.get("inn")}
            if d.get("brand") and d.get("inn"):
                drug["nonProprietaryName"] = d["inn"]
            art["about"] = drug
        block = B + json.dumps(art, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + E
        # 2026-10-24: both tags go BEFORE build_date_modified.py's <!--DMOD:BEGIN--> block, never inside it or after it.
        # The first version put published_time inside DMOD (next to modified_time) and the article block after it;
        # build_date_modified removes DMOD and re-appends it at </head> every run, so the two steps swapped places and
        # "369 written" was printed on every CI run.
        new = re.sub(re.escape(B) + r".*?" + re.escape(E), "", doc, flags=re.S)
        new = re.sub(r'<meta property="article:published_time" content="[^"]*">', "", new)
        tags = f'<meta property="article:published_time" content="{pub}">' + block
        anchor = new.find("<!--DMOD:BEGIN-->")
        if anchor < 0:
            anchor = new.find("</head>")
        if anchor >= 0:
            new = new[:anchor] + tags + new[anchor:]
        n += 1
        if new != doc:
            changed += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(new)
    if not a.dry_run:
        io.open(CACHE, "w", encoding="utf-8").write(json.dumps(dict(sorted(cache.items())), indent=0) + "\n")
    print(f"decision NewsArticle: {n} page(s) carry it, {changed} written" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
