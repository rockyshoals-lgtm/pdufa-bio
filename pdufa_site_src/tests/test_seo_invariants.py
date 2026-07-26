#!/usr/bin/env python3
"""SEO invariants — must pass before any deploy is considered good.
The canonical/sitemap fix has been reported 'reverted' twice by audit; this proves state
and blocks a real regression. Run: python3 tests/test_seo_invariants.py
"""
import sys, urllib.request, xml.etree.ElementTree as ET

BASE = 'https://www.pdufa.bio'
NS = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
MUST_BE_IN_SITEMAP = ['/conferences', '/adcomm', '/screener', '/developers',
                      '/research/conference-runup', '/research/short-interest-fda', '/research/readout-reaction', '/calendar', '/decisions', '/runup-by-year']
MUST_BE_WWW_CANONICAL = ['/', '/calendar', '/conferences', '/decisions',
                         '/research/conference-runup', '/readouts']

def get(path):
    req = urllib.request.Request(BASE + path, headers={'User-Agent': 'pdufa-seo-guard',
                                                       'Cache-Control': 'no-cache'})
    return urllib.request.urlopen(req, timeout=25).read().decode('utf-8', 'ignore')

errs, notes = [], []

# 1. sitemap: host + coverage
sm = get('/sitemap.xml')
locs = [e.text for e in ET.fromstring(sm).iter(NS + 'loc')]
notes.append(f'sitemap: {len(locs)} urls')
bad = [l for l in locs if l.startswith('https://pdufa.bio')]
if bad:
    errs.append(f'FATAL: sitemap emits {len(bad)} non-www URLs (e.g. {bad[0]})')
if not all(l.startswith('https://www.pdufa.bio') for l in locs):
    errs.append('FATAL: sitemap contains URLs on an unexpected host')
for p in MUST_BE_IN_SITEMAP:
    if not any(l.rstrip('/').endswith(p.rstrip('/')) for l in locs):
        errs.append(f'FATAL: {p} missing from sitemap')

# 2. canonicals must be www
for p in MUST_BE_WWW_CANONICAL:
    html = get(p)
    if 'rel="canonical" href="https://www.pdufa.bio' not in html:
        errs.append(f'FATAL: {p} canonical is not www')

# 3. robots must point at the www sitemap
robots = get('/robots.txt')
if 'https://www.pdufa.bio/sitemap.xml' not in robots:
    errs.append('FATAL: robots.txt does not reference the www sitemap')

# 4. flagship research page must carry schema (it is the link-bait asset)
for page in ['/research/conference-runup', '/research/short-interest-fda', '/research/readout-reaction']:
    cr = get(page)
    for t in ['"Dataset"', '"Article"', '"BreadcrumbList"', '"FAQPage"']:
        if t not in cr:
            errs.append(f'FATAL: {page} missing {t} schema')

# 5. no page that ranks may be gated
for p in ['/', '/calendar', '/pdufa/CELC', '/readouts', '/conferences', '/decisions', '/research/conference-runup']:
    h = get(p)
    if len(h) < 2000:
        errs.append(f'FATAL: {p} body suspiciously small ({len(h)}b) — is it gated?')

print('\n'.join('  ' + n for n in notes))
if errs:
    print('\n'.join(errs)); sys.exit(1)
print(f'OK — sitemap {len(locs)} urls all www; canonicals www; robots ok; research schema present; no content gated.')
