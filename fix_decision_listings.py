# -*- coding: utf-8 -*-
"""fix_decision_listings.py -- /decisions/approvals and /decisions/crl must list only what we verified.

The false SELLAS CRL survived my first two fixes because I only cleaned the individual decision
pages and the ticker hubs. These two listing pages were still live, still indexable, still in the
sitemap, still linked from /decisions, and still carrying "SLS - 2025-02-20 X CRL".

Worse than one row: 236 of 326 rows on /decisions/approvals and 82 of 119 on /decisions/crl were
price-inferred. A page titled "FDA Complete Response Letters" is about the strongest factual claim
this site makes, and two thirds of it had never been checked against a document.

So these pages now list VERIFIED records only, and say so. The inferred records still exist and are
still reachable from /decisions; they are simply not presented under a headline that asserts the FDA
did something.

    python fix_decision_listings.py [--dry-run]
"""
import argparse, glob, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
ROW = re.compile(r'<a class="row" href="/fda-decision/([A-Z]+-\d{4}-\d{2}-\d{2})".*?</a>', re.S)

NOTE = ('<div class="note" style="border:1px solid #6b5a2f;background:rgba(240,200,106,.07);'
        'border-radius:10px;padding:11px 13px;margin:12px 0;color:#e8d9a8;font-size:13px;'
        'line-height:1.6"><b>Verified records only.</b> This page lists {kept} decision(s) confirmed '
        'against an FDA, SEC or company document. A further {dropped} record(s) in our archive have '
        'their outcome inferred from the share-price reaction rather than read from a filing, and '
        'they are deliberately not listed under a heading that asserts what the FDA did. They remain '
        'in the <a href="/decisions" style="color:#f0c86a">full archive</a>, labelled unverified. '
        'We published one such inference that turned out to be impossible; see '
        '<a href="/corrections" style="color:#f0c86a">corrections</a>.</div>')


def verified_slugs():
    """A decision is verified if its own page does not carry the price-only marker."""
    ok = set()
    for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        t = open(p, encoding="utf-8", errors="replace").read()
        if "price-only" not in t:
            ok.add(os.path.basename(os.path.dirname(p)))
    return ok


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ok = verified_slugs()
    print(f"verified decision pages: {len(ok)}")

    for name in ("approvals", "crl"):
        p = os.path.join(SITE, "decisions", name, "index.html")
        if not os.path.exists(p):
            continue
        t = open(p, encoding="utf-8", errors="replace").read()
        kept = dropped = 0
        missing = []

        def keep(m):
            nonlocal kept, dropped
            slug = m.group(1)
            if slug in ok:
                kept += 1
                return m.group(0)
            dropped += 1
            missing.append(slug)
            return ""

        t2 = ROW.sub(keep, t)
        note = NOTE.format(kept=kept, dropped=dropped)
        t2 = re.sub(r'<div class="note" style="border:1px solid #6b5a2f.*?</div>', "", t2, flags=re.S)
        anchor = re.search(r"</h1>", t2)
        if anchor:
            t2 = t2[:anchor.end()] + note + t2[anchor.end():]
        # any headline count on the page must follow the list it describes
        t2 = re.sub(r"(\d+)\s+(decisions?|CRLs?|approvals?)\s+logged",
                    lambda m: f"{kept} verified {m.group(2)} logged", t2, flags=re.I)

        print(f"  /decisions/{name}: kept {kept} verified, removed {dropped} inferred")
        if "SLS-2025-02-20" in t and "SLS-2025-02-20" not in t2:
            print("    (removed the retracted SELLAS row)")
        if not a.dry_run:
            open(p, "w", encoding="utf-8").write(t2)


if __name__ == "__main__":
    main()
