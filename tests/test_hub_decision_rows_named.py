# -*- coding: utf-8 -*-
"""A company page's decision history names the drug of each decision.

2026-11-27 phone pass: every row under "FDA decision history" on /ticker pages (397 of 397) read only a date, a
badge and "FDA decision". build_ticker_hubs.py took the drug from the /decisions archive row after a "—", and the
archive had since changed to "<span>Approved</span>: NAME", so the name was always empty. The row now carries the
name from the archive row, made whole from the decision page's own names.

This fails when a hub decision row says only "FDA decision" while its decision page names a drug, or names a drug
that is not one of that page's own names (nor a whole name the archive row gives).

    python tests/test_hub_decision_rows_named.py
"""
import glob
import html
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
ROW = re.compile(r'<a class="row" href="/fda-decision/([A-Z][A-Z0-9.]*-\d{4}-\d{2}-\d{2})">\s*<span class="t">(?:(?!</a>).)*?'
                 r'</span><span class="d">([^<]*)', re.S)


def archive_names():
    p = os.path.join(SITE, "decisions", "index.html")
    doc = io.open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else ""
    out = {}
    for s, n in re.findall(r'href="/fda-decision/([A-Z][A-Z0-9.]*-\d{4}-\d{2}-\d{2})"><div class="t">(?:(?!</a>).)*?</div>'
                           r'<div class="d"><span[^>]*>(?:Approved|CRL)</span>:\s*([^<]+)', doc):
        out.setdefault(s, set()).add(html.unescape(n).strip())
    return out


def check(pages, names_of, arch):
    bad, rows = [], 0
    for path, doc in pages:
        tk = os.path.basename(os.path.dirname(path))
        for slug, d in ROW.findall(doc):
            rows += 1
            shown = html.unescape(d).strip()
            names = [n for n in names_of(slug) if n]
            if shown == "FDA decision":
                if names:
                    bad.append(f"/ticker/{tk}: the {slug} row says only 'FDA decision'; its page names {names[0]!r}")
            elif shown not in names and shown not in arch.get(slug, ()) and not any(
                    n.startswith(shown.rstrip("…")) for n in names):
                bad.append(f"/ticker/{tk}: the {slug} row names {shown!r}, not one of its page's names {names}")
    return bad, rows


def main():
    if not os.path.isdir(os.path.join(SITE, "ticker")):
        print("SKIP: no ticker hubs built")
        return 0
    from whole_decision_names import page_names
    pages = [(p, io.open(p, encoding="utf-8", errors="replace").read())
             for p in sorted(glob.glob(os.path.join(SITE, "ticker", "*", "index.html")))]
    bad, rows = check(pages, page_names, archive_names())
    # planted cases: the old bare row, and a row naming another drug
    planted = [("x/ticker/ZZZ/index.html",
                '<a class="row" href="/fda-decision/ZZZ-2026-01-02"><span class="t">Jan 2, 2026<span class="badge app">'
                '✓ Approved</span></span><span class="d">FDA decision</span></a>'
                '<a class="row" href="/fda-decision/ZZZ-2026-01-03"><span class="t">Jan 3, 2026<span class="badge app">'
                '✓ Approved</span></span><span class="d">Otherdrug</span></a>')]
    pb, _ = check(planted, lambda s: ["Ekitna (bezuclastinib)", "Ekitna (bezuclastinib)"], {})
    if len(pb) != 2:
        bad.append(f"planted bare and mismatched rows: {len(pb)} of 2 caught")
    if bad:
        print("FAIL test_hub_decision_rows_named:")
        for b in bad[:20]:
            print("  -", b)
        print("  fix: python build_ticker_hubs.py")
        return 1
    print(f"PASS test_hub_decision_rows_named: {rows} decision rows on ticker hubs, each naming its page's drug")
    return 0


if __name__ == "__main__":
    sys.exit(main())
