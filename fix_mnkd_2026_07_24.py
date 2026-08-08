# -*- coding: utf-8 -*-
"""Resolve MNKD FUROSCIX ReadyFlow Autoinjector (SCP-111) FDA approval, 2026-07-24.

VERIFIED: MannKind press release "MannKind Announces FDA Approval of Furoscix ReadyFlow(TM)...",
2026-07-24 06:30 ET (FinancialModelingPrep mirror of GlobeNewswire release, company code 29517).
Approved two days ahead of the 2026-07-26 PDUFA goal date. Indication: edema in adults with CHF
or CKD. NOTE: MNKD already has ONE unrelated prior archive entry, MNKD-2026-05-29 (Afrezza /
Technosphere Insulin) -- a completely different product. This adds a SECOND, independent row.

Idempotent. Run with --dry-run first.
"""
import os, re, json, shutil, sys, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, 'pdufa_site_src')
DEC  = os.path.join(SITE, 'decisions', 'index.html')
SMAP = os.path.join(SITE, 'sitemap.xml')
VJSON= os.path.join(SITE, 'vercel.json')
PDUFA_DIR = os.path.join(SITE, 'pdufa', 'MNKD')
TODAY = '2026-07-24'

TICKER, DATE = 'MNKD', '2026-07-24'
LABEL = 'FUROSCIX ReadyFlow Autoinjector (SCP-111)'   # matches api/data.js "drug" field verbatim
REDIRECT_SRC = '/pdufa/MNKD'
REDIRECT_DST = f'/fda-decision/{TICKER}-{DATE}'


def row_html(tk, d, label):
    return (f'<a class="row" href="/fda-decision/{tk}-{d}"><div class="t">{tk} · {d} '
            f'<span class="ok">✓</span></div><div class="d"><span class="ok">Approved</span> '
            f': {label}</div></a>')


def fix_archive(dry):
    h = open(DEC, encoding='utf-8').read()
    orig = h
    if f'/fda-decision/{TICKER}-{DATE}"' in h:
        print(f'  = {TICKER}-{DATE} already in archive (idempotent)')
        return
    m = re.search(r'<div class="mhead">2026 · (\d+)</div><div class="grid">', h)
    if not m:
        sys.exit('  *** 2026 grid header not found')
    gs = m.end()
    pos = None
    for r in re.finditer(r'<a class="row" href="/fda-decision/[A-Z]+-(\d{4}-\d{2}-\d{2})"', h[gs:]):
        if r.group(1) < DATE:
            pos = gs + r.start(); break
    if pos is None:
        pos = gs
    h = h[:pos] + row_html(TICKER, DATE, LABEL) + h[pos:]
    print(f'  + added archive row {TICKER}-{DATE}')

    n2026 = len(re.findall(r'<a class="row" href="/fda-decision/[A-Z]+-2026-\d{2}-\d{2}"', h))
    h = re.sub(r'<div class="mhead">2026 · \d+</div>', f'<div class="mhead">2026 · {n2026}</div>', h, count=1)
    print(f'  = 2026 count set to {n2026} (recounted from rows, not incremented)')

    if h != orig and not dry:
        shutil.copy2(DEC, DEC + '.bak_' + TODAY)
        open(DEC, 'w', encoding='utf-8').write(h)
        print('  wrote decisions/index.html')


def fix_sitemap(dry):
    h = open(SMAP, encoding='utf-8').read(); orig = h
    # remove the stale /pdufa/MNKD entry
    h2 = re.sub(r'<url><loc>https://www\.pdufa\.bio' + re.escape(REDIRECT_SRC) + r'</loc>.*?</url>\s*', '', h, flags=re.S)
    if h2 != h:
        print('  - removed /pdufa/MNKD from sitemap')
        h = h2
    else:
        print('  = /pdufa/MNKD already absent from sitemap (idempotent)')

    loc = f'https://www.pdufa.bio{REDIRECT_DST}'
    if loc + '</loc>' in h:
        print(f'  = {TICKER}-{DATE} already in sitemap')
    else:
        entry = f'<url><loc>{loc}</loc><lastmod>{TODAY}</lastmod><changefreq>weekly</changefreq></url>\n'
        anchor = re.search(r'<url><loc>https://www\.pdufa\.bio/fda-decision/[^<]*</loc>.*?</url>\n', h, re.S)
        if anchor:
            h = h[:anchor.start()] + entry + h[anchor.start():]
        else:
            h = h.replace('</urlset>', entry + '</urlset>')
        print(f'  + added {TICKER}-{DATE} to sitemap')

    if h != orig and not dry:
        shutil.copy2(SMAP, SMAP + '.bak_' + TODAY)
        open(SMAP, 'w', encoding='utf-8').write(h)
        print('  wrote sitemap.xml')


def fix_redirects(dry):
    j = json.load(open(VJSON, encoding='utf-8'))
    have = {r['source'] for r in j.get('redirects', [])}
    ch = False
    if REDIRECT_SRC in have:
        print(f'  = redirect {REDIRECT_SRC} already present')
    else:
        j.setdefault('redirects', []).append(
            {'source': REDIRECT_SRC, 'destination': REDIRECT_DST, 'permanent': True})
        print(f'  + redirect {REDIRECT_SRC} -> {REDIRECT_DST} (301)'); ch = True
    if ch and not dry:
        shutil.copy2(VJSON, VJSON + '.bak_' + TODAY)
        open(VJSON, 'w', encoding='utf-8').write(json.dumps(j, indent=1) + '\n')
        print('  wrote vercel.json')


def retire_pdufa_page(dry):
    if os.path.isdir(PDUFA_DIR):
        dest = os.path.join(HERE, '_retired_pdufa_MNKD_' + TODAY)
        if not dry:
            shutil.copytree(PDUFA_DIR, dest)
            shutil.rmtree(PDUFA_DIR)
        print(f'  - retired /pdufa/MNKD static page (backup copied to {os.path.basename(dest)}, '
              f'now 301 -> {REDIRECT_DST})')
    else:
        print('  = /pdufa/MNKD page already retired')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if a.dry_run: print('*** DRY RUN -- nothing will be written ***')
    print('1) decisions archive');    fix_archive(a.dry_run)
    print('2) sitemap');              fix_sitemap(a.dry_run)
    print('3) vercel redirects');     fix_redirects(a.dry_run)
    print('4) retire stale /pdufa/MNKD page'); retire_pdufa_page(a.dry_run)
    print('\nNext: build_slate_from_crawl.py --dry-run  (the sweep should now drop MNKD)')
