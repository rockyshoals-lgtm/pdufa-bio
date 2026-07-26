"""CI guard: a static HTML page must never render a company the data layer doesn't know.

WHY THIS EXISTS — the gap that let P0-A ship twice
The ticker fan-out (BNTX/CTMX/EVAX/MIRM on decisions they weren't parties to) was "fixed" in
api/data.js, and every existing guard read the DATA layer — api/data.js, dataset.mjs, the CSVs.
None read the rendered HTML. So the homepage, screener, month calendars and condition pages kept
rendering the phantom rows while every test passed. The defect was found by hand, not by CI.

This guard closes that gap. The authoritative truth is:
    the SLATE (api/data.js — forward catalysts) + the decisions archive (past decisions).
Every ticker a static listing page renders as a `/pdufa/{TICKER}` row must appear in one of those.
BNTX/CTMX/EVAX/MIRM were in NEITHER (pure join artifacts); ALPMY was removed from the slate when
its event was decided. All five would fail here.

Scope: the forward/listing pages that render catalyst rows. NOT the /pdufa detail pages themselves
(they're being retired/redirected separately), and not backups.

    python tests/test_static_pages_match_slate.py
"""
import json, os, re, sys, glob

SITE = 'pdufa_site_src'
API = os.path.join(SITE, 'api', 'data.js')
DECISIONS = os.path.join(SITE, 'decisions', 'index.html')


def allowed_tickers():
    """Tickers the data layer legitimately knows: forward slate + decisions archive."""
    tk = set()
    src = open(API, encoding='utf-8').read()
    i = src.find('const SLATE=')
    slate, _ = json.JSONDecoder().raw_decode(src[i + len('const SLATE='):])
    for c in slate['catalysts']:
        if c.get('ticker'):
            tk.add(c['ticker'].upper())
    arch = open(DECISIONS, encoding='utf-8').read()
    for t in re.findall(r'/fda-decision/([A-Z]{1,6})-\d{4}-\d{2}-\d{2}', arch):
        tk.add(t.upper())
    return tk


# static listing pages that render catalyst rows (glob + explicit)
def listing_pages():
    pages = ['index.html', 'calendar/index.html', 'screener/index.html']
    pages += [os.path.relpath(p, SITE) for p in glob.glob(os.path.join(SITE, 'calendar', '2026', '*', 'index.html'))]
    pages += [os.path.relpath(p, SITE) for p in glob.glob(os.path.join(SITE, 'calendar', '2027', '*', 'index.html'))]
    pages += [os.path.relpath(p, SITE) for p in glob.glob(os.path.join(SITE, 'condition', '*', 'index.html'))]
    seen, out = set(), []
    for p in pages:
        if p not in seen and os.path.exists(os.path.join(SITE, p)):
            seen.add(p); out.append(p)
    return out


def main():
    if not os.path.exists(API):
        print(f'  SKIP {API} not found'); return 0
    allowed = allowed_tickers()
    fail = 0
    checked = 0
    for rel in listing_pages():
        html = open(os.path.join(SITE, rel), encoding='utf-8').read()
        checked += 1
        # every /pdufa/{slug} link rendered on this page -> leading ticker
        rendered = set()
        for slug in re.findall(r'href="/pdufa/([A-Za-z0-9-]+)"', html):
            m = re.match(r'([A-Za-z]{1,6})', slug)
            if m:
                rendered.add(m.group(1).upper())
        unknown = sorted(t for t in rendered if t not in allowed)
        if unknown:
            print(f'  FAIL {rel}: renders /pdufa rows for tickers absent from the slate AND the '
                  f'decisions archive: {unknown}')
            fail += 1
    if fail:
        print(f'\n{fail} static page(s) render a company the data layer does not know. This is the '
              f'ticker-fan-out class — the page must match the slate. DO NOT PUBLISH.')
        return 1
    print(f'OK -- {checked} listing pages, every rendered /pdufa ticker is in the slate or the '
          f'decisions archive ({len(allowed)} known tickers).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
