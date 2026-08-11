# -*- coding: utf-8 -*-
"""build_breadcrumbs.py -- BreadcrumbList on every indexable page, sitewide, daily.

Sitelinks groundwork (owner request 2026-08-11): the sub-links Bing and Google show under a
dominant result are not paid and cannot be requested -- the engines pick them when they are
confident about a site's hierarchy. Breadcrumb structured data is one of the signals they read.
The audit found the LEAF pages carry BreadcrumbList (848 of 1455, via the per-event injectors)
while the HUB tier -- /readouts, /drug, /tickers, /conferences, /adcomm, /screener,
/runup-by-year, /developers, /sls, /learn/* -- mostly does not. Those hubs are precisely the
pages an engine would surface as sitelinks.

The rule: every indexable index.html carries exactly one BreadcrumbList, derived from its URL
path with human section labels, leaf name from the page's own <h1>. Idempotent via the BC:BEGIN
marker; pages that already carry a BreadcrumbList from another builder are left alone (one
breadcrumb per page -- duplicates are schema spam). noindex pages are skipped: structured data
on a page we ask engines not to index is noise.

The homepage gets a WebSite node (site name + url) instead of a breadcrumb -- a one-item trail
is meaningless, but the WebSite node is what lets engines display the site name confidently.

    python build_breadcrumbs.py [--dry-run]
"""
import argparse, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
BASE = "https://www.pdufa.bio"

LABELS = {
    "calendar": "PDUFA Calendar", "decisions": "FDA Decisions", "fda-decision": "FDA Decisions",
    "readouts": "Trial Readouts", "readout": "Trial Readouts", "drug": "Drug Index",
    "tickers": "Stocks", "ticker": "Stocks", "pdufa": "PDUFA Calendar",
    "conferences": "Conferences", "adcomm": "Advisory Committees", "screener": "Screener",
    "research": "Research", "developers": "API", "sls": "SLS Tracker", "learn": "Learn",
    "runup-by-year": "Run-up by Year", "condition": "Conditions", "about": "About",
    "corrections": "Corrections", "methodology": "Methodology", "account": "Account",
    "pricing": "Pricing", "search": "Search", "login": "Sign in",
}
# Path segments that map to a real hub page get a link; others are labels only.


def leaf_name(doc, fallback):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S)
    if m:
        t = html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
        t = re.sub(r"\s+", " ", t).strip()
        if 2 <= len(t) <= 110:
            return t
    return fallback


def crumb_for(rel, doc):
    """BreadcrumbList dict for a page at rel path like 'drug/dtx401/index.html'."""
    segs = rel.replace("\\", "/").split("/")[:-1]      # drop index.html
    items = [{"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"}]
    pos = 2
    for i, s in enumerate(segs):
        last = i == len(segs) - 1
        pretty = LABELS.get(s.lower(), re.sub(r"[-_]+", " ", s).strip().title())
        if last:
            pretty = leaf_name(doc, pretty)
        entry = {"@type": "ListItem", "position": pos, "name": pretty}
        target = "/".join(segs[:i + 1])
        if not last and os.path.exists(os.path.join(SITE, target, "index.html")):
            entry["item"] = f"{BASE}/{target}"
        elif last:
            entry["item"] = f"{BASE}/{target}"
        items.append(entry)
        pos += 1
    if len(items) < 2:
        return None
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": items}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    added = kept = skipped_noindex = 0
    for root, _, files in os.walk(SITE):
        if "index.html" not in files:
            continue
        p = os.path.join(root, "index.html")
        rel = os.path.relpath(p, SITE).replace("\\", "/")
        doc = open(p, encoding="utf-8", errors="replace").read()

        if re.search(r'<meta[^>]+name="robots"[^>]+noindex', doc):
            skipped_noindex += 1
            continue

        if rel == "index.html":
            if '"WebSite"' not in doc:
                ws = {"@context": "https://schema.org", "@type": "WebSite",
                      "name": "pdufa.bio", "url": BASE + "/",
                      "alternateName": "PDUFA FDA Calendar"}
                block = ('<!--BC:BEGIN--><script type="application/ld+json">'
                         + json.dumps(ws, separators=(",", ":")) + "</script><!--BC:END-->")
                if not a.dry_run:
                    open(p, "w", encoding="utf-8").write(
                        doc.replace("</head>", block + "</head>", 1))
                added += 1
                print("  WebSite node -> / (homepage)")
            else:
                kept += 1
            continue

        if "BreadcrumbList" in doc:
            kept += 1
            continue
        crumb = crumb_for(rel, doc)
        if crumb is None:
            continue
        block = ('<!--BC:BEGIN--><script type="application/ld+json">'
                 + json.dumps(crumb, separators=(",", ":")) + "</script><!--BC:END-->")
        if not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc.replace("</head>", block + "</head>", 1))
        added += 1

    print(f"breadcrumbs/WebSite added: {added}; already carried one: {kept}; "
          f"noindex skipped: {skipped_noindex}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
