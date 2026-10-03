# -*- coding: utf-8 -*-
"""sync_decisions_listing.py -- every decision page gets its /decisions row, automatically.

THE FAILURE THIS ENDS (task #42, made urgent by the 2026-09-01b re-audit): new decision
pages were inserted into the /decisions listing BY HAND, and CI's daily refresh
regenerates the listing from its own store -- so a hand-inserted row survives only until
the next refresh. REGN's Pasatru approval was published on 09-01, its listing row was
gone by the next CI run, and because sync_api_from_pages mirrors the LISTING into the
dataset, the reversion propagated: the API went back to "Awaiting", the timing page fell
back to n=27, and a 33%-CTR page told readers an approved drug was pending -- while the
decision page itself sat right there in the repo the whole time.

The decision pages are the durable artifacts. This script walks fda-decision/*/index.html
and guarantees each has a listing row: outcome and drug read from the page itself,
inserted newest-first under the right year header, year counts recomputed from the rows
actually present. Idempotent. Runs in CI immediately before sync_api_from_pages, so the
chain becomes: pages (durable) -> listing -> dataset -> every downstream surface.
"""
import datetime as dt
import glob
import html as _html
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
LISTING = os.path.join(SITE, "decisions", "index.html")


def page_facts(path):
    """(outcome, drug) read from a decision page; None if unparseable."""
    doc = io.open(path, encoding="utf-8", errors="replace").read()
    tm = re.search(r"<title[^>]*>(.*?)</title>", doc, re.S)
    ttl = _html.unescape(re.sub(r"\s+", " ", tm.group(1))).strip() if tm else ""
    oc = ("Approved" if re.search(r"\bApproved\b", ttl)
          else "CRL" if re.search(r"CRL|Complete Response", ttl, re.I) else None)
    dm = (re.match(r"^[A-Z]{1,6} FDA Decision [^:]+: (?:Approved|Complete Response "
                   r"Letter|CRL)\s*-\s*(.+?)\s*\|", ttl)
          or re.match(r"^[A-Z]{1,6} FDA Decision \([^)]+\):\s*(.+?):\s*(?:Approved|"
                      r"Complete Response Letter|CRL)\s*\|", ttl, re.I))
    drug = dm.group(1).strip() if dm else ""
    return oc, drug


def retired_slugs():
    """Decision slugs vercel.json REDIRECTS elsewhere -- goal-date duplicates whose real
    page lives at the actual decision date. Their page dirs may still exist on disk (the
    first run of this script resurrected five of them into the listing, two with wrong
    dates); a redirected slug must never get a row."""
    import json as _json
    try:
        v = _json.load(io.open(os.path.join(SITE, "vercel.json"), encoding="utf-8"))
        return {r["source"].split("/fda-decision/")[1]
                for r in v.get("redirects", [])
                if r.get("source", "").startswith("/fda-decision/")}
    except Exception as e:
        print(f"  WARN: vercel.json unreadable ({e}); no redirect filtering")
        return set()


def main():
    sys.path.insert(0, HERE)
    doc = io.open(LISTING, encoding="utf-8", errors="replace").read()
    have = set(re.findall(r'href="/fda-decision/([A-Z]{1,6}-\d{4}-\d{2}-\d{2})"', doc))
    retired = retired_slugs()
    # rows pointing at redirected slugs are removed, whoever added them
    for slug in sorted(retired & have):
        doc, n = re.subn(r'<a class="row" href="/fda-decision/' + slug + r'".*?</a>',
                         "", doc, flags=re.S)
        if n:
            print(f"  - {slug}: row removed (slug is redirected; page is a retired "
                  f"duplicate)")
            have.discard(slug)

    added = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")),
                    reverse=True):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]{1,6})-(\d{4})-(\d{2})-(\d{2})$", slug)
        if not m or slug in have or slug in retired:
            continue
        oc, drug = page_facts(p)
        _kv = re.search(r"<span>Drug / candidate</span><b>(.*?)</b>", io.open(p, encoding="utf-8", errors="replace").read())
        if _kv:
            from drug_names import clean_drug_name as _cdn
            drug = _cdn(_html.unescape(_kv.group(1))) or drug
        if not oc:
            print(f"  !! {slug}: page has no readable outcome; NOT inserting a row blind")
            continue
        tk, yr, dfull = m.group(1), m.group(2), f"{m.group(2)}-{m.group(3)}-{m.group(4)}"
        ok = oc == "Approved"
        word, cls, icon = (("Approved", "ok", "&#10003;") if ok
                           else ("CRL", "bad", "&#10007;"))
        row = (f'<a class="row" href="/fda-decision/{slug}"><div class="t">{tk} '
               f'&middot; {dfull} <span class="{cls}">{icon}</span></div>'
               f'<div class="d"><span class="{cls}">{word}</span>'
               + (f': {_html.escape(drug[:60])}' if drug else "") + "</div></a>")
        hdr = re.search(r'<div class="mhead">' + yr + r'[^<]*</div><div class="grid">',
                        doc)
        if not hdr:
            print(f"  !! {slug}: no {yr} section header found; row not inserted")
            continue
        # newest-first within the year: insert directly after the header; the daily
        # fix_decisions_order pass owns exact ordering.
        doc = doc[:hdr.end()] + row + doc[hdr.end():]
        have.add(slug)
        added += 1
        print(f"  + {slug}: {word}" + (f" ({drug[:40]})" if drug else ""))

    # 4.7 (#65, audit 2026-10-03): a row's drug text written from a cut archive name
    # ("PAPZIMEOS (zopapogene imadenov") is replaced by the page's own "Drug / candidate" fact,
    # cleaned by drug_names.py. Rows whose text is already whole are left alone.
    import sys as _sys
    _sys.path.insert(0, HERE)
    from drug_names import clean_drug_name, looks_cut_name

    def fix_row(m):
        slug, cls, word, text = m.group(1), m.group(2), m.group(3), _html.unescape(m.group(4))
        pp = os.path.join(SITE, "fda-decision", slug, "index.html")
        kv = None
        if os.path.exists(pp):
            kv = re.search(r"<span>Drug / candidate</span><b>(.*?)</b>", io.open(pp, encoding="utf-8", errors="replace").read())
        full = _html.unescape(kv.group(1)) if kv else ""
        # cut = the archive's widths, an open parenthesis, or a strict prefix of the page's own
        # name that stops mid-word ("TRUQAP (capivasertib) in combi")
        midword = bool(full) and full.startswith(text) and len(full) > len(text) and full[len(text)].isalnum()
        if not (looks_cut_name(text) or text.count("(") != text.count(")") or midword):
            return m.group(0)
        new = clean_drug_name(full or text)
        return m.group(0).replace(m.group(4), _html.escape(new, quote=False)) if new else m.group(0)
    doc = re.sub(r'href="/fda-decision/([A-Z]{1,6}-\d{4}-\d{2}-\d{2})">.{0,200}?<span class="(ok|bad)">(Approved|CRL)</span>: ([^<]{2,80})</div>',
                 fix_row, doc, flags=re.S)

    # year counts recomputed from the rows actually present -- a hand-bumped count and a
    # regenerated listing had already disagreed twice.
    def fix_count(m):
        yr = m.group(1)
        n = len(re.findall(r'href="/fda-decision/[A-Z]{1,6}-' + yr + r'-', doc))
        return f'<div class="mhead">{yr} &middot; {n}</div>'
    doc2 = re.sub(r'<div class="mhead">(\d{4})[^<]*</div>', fix_count, doc)

    if added or doc2 != doc:
        io.open(LISTING, "w", encoding="utf-8").write(doc2)
    print(f"listing sync: {added} row(s) added; year counts recomputed from rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
