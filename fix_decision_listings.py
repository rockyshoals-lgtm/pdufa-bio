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
        'line-height:1.6"><b>Not inferred from price.</b> This page lists {kept} decision(s) whose '
        'outcome was read from a document rather than from the share-price reaction. '
        '<b>{sourced} of them link that document</b>; the rest are older entries we have not yet '
        'gone back and sourced, and we would rather say so than call them all verified. '
        'A further {dropped} record(s) in our archive have '
        'their outcome inferred from the share-price reaction rather than read from a filing, and '
        'they are deliberately not listed under a heading that asserts what the FDA did. They remain '
        'in the <a href="/decisions" style="color:#f0c86a">full archive</a>, labelled unverified. '
        'We published one such inference that turned out to be impossible; see '
        '<a href="/corrections" style="color:#f0c86a">corrections</a>.</div>')


def sourced_slugs():
    """A decision is verified when its page LINKS a primary source.

    This used to be "does not carry the price-only marker", which counted 150 pages as verified
    when only 31 of them showed anything to check. Absence of a disclaimer is not evidence, and the
    difference was published on /decisions as "142 with a primary source". Requiring the source to
    be present is the whole point of the claim.
    """
    import re as _re
    GOOD = _re.compile(r"(fda\.gov|sec\.gov|clinicaltrials\.gov|nih\.gov|doi\.org|nejm\.org|"
                       r"thelancet\.com|jamanetwork\.com|globenewswire\.com|prnewswire\.com|"
                       r"businesswire\.com|accessnewswire\.com|stocktitan\.net|newsroom\.|"
                       r"ir\.|investors?\.)", _re.I)
    ok, sourced = set(), set()
    for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        t = open(p, encoding="utf-8", errors="replace").read()
        if "price-only" in t:
            continue
        slug = os.path.basename(os.path.dirname(p))
        ok.add(slug)                       # not inferred from price: eligible to be listed
        ext = [u for u in _re.findall(r'href="(https?://[^"]+)"', t) if "pdufa.bio" not in u]
        if any(GOOD.search(u) for u in ext):
            sourced.add(slug)              # and it shows you the document
    return ok, sourced


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ok, sourced = sourced_slugs()
    print(f"decisions not inferred from price: {len(ok)}  ({len(sourced)} of them link the document)")

    for name in ("approvals", "crl"):
        p = os.path.join(SITE, "decisions", name, "index.html")
        if not os.path.exists(p):
            continue
        t = open(p, encoding="utf-8", errors="replace").read()
        kept = dropped = 0
        missing, kept_slugs = [], []

        def keep(m):
            nonlocal kept, dropped
            slug = m.group(1)
            if slug in ok:
                kept += 1
                kept_slugs.append(slug)
                return m.group(0)
            dropped += 1
            missing.append(slug)
            return ""

        t2 = ROW.sub(keep, t)
        note = NOTE.format(kept=kept, dropped=dropped,
                           sourced=sum(1 for s in kept_slugs if s in sourced))
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
