# -*- coding: utf-8 -*-
"""Resolve the four forward PDUFAs that check_pdufa_decided.py flagged as already decided.

ALL FOUR VERIFIED AGAINST PRIMARY SOURCES (company IR / SEC 8-K), not just the PR headline:

  BIIB  listed 2026-08-24 -> Approved 2026-07-13.
        Biogen IR, 2026-05-08: "the FDA has extended the review period by three months for the
        sBLA for a once-weekly lecanemab-irmb subcutaneous injection (LEQEMBI IQLIK) as a
        STARTING DOSE ... The new PDUFA action date is August 24, 2026." The same release
        distinguishes this from the subcutaneous MAINTENANCE regimen approved 2025-08-26.
        The 2026-07-13 release approves that same starting-dose sBLA. Same application -> closed.

  MRK   listed 2026-08-17 -> Approved 2026-07-10.
  PFE   listed 2026-08-17 -> Approved 2026-07-10.
        Merck Q1-2026 Form 8-K: "In April, FDA granted priority review for KEYTRUDA and
        KEYTRUDA QLEX, each with Padcev, for cisplatin-eligible patients with MIBC, based on
        the Phase 3 KEYNOTE-B15 trial. FDA set PDUFA date of Aug. 17, 2026." That 8-K lists no
        second MIBC action date, so there is no other pending MIBC application to confuse this
        with. Merck and Pfizer/Astellas each announced the approval on 2026-07-10.

  IONS  listed 2026-06-30 -> Approved 2026-06-24.
        Ionis Form 8-K Ex-99.1, 2026-06-24: TRYNGOLZA (olezarsen) approved for sHTG on the
        Phase 3 CORE and CORE2 studies. The slate row is "Olezarsen - (CORE)". Closed.

WHY IONS NEEDED A DELETION, NOT AN INSERTION
IONS was already in the archive TWICE for the one approval: IONS-2026-06-24 (correct) and
IONS-2026-06-30 (keyed to the PDUFA goal date). The 06-30 page states "FDA decision date
2026-06-30" while its own headline says the approval happened "(Jun 24 2026)" -- it contradicts
itself, and no FDA decision happened on 06-30.

That false row is also exactly what kept the phantom alive. already_decided() refuses to act
when a drug matches MORE THAN ONE archive entry (the KEYTRUDA platform-drug guard). Both IONS
rows contain "olezarsen", so the slate row matched two entries, the guard called it ambiguous,
and stood down -- every single build. The duplicate was self-inflicted ambiguity.

Removing the false row leaves exactly one match and the sweep fires. A 301 preserves the URL.

Idempotent. Run with --dry-run first.
"""
import os, re, json, shutil, sys, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, 'pdufa_site_src')
DEC  = os.path.join(SITE, 'decisions', 'index.html')
SMAP = os.path.join(SITE, 'sitemap.xml')
VJSON= os.path.join(SITE, 'vercel.json')
TODAY = '2026-07-15'

# (ticker, decision date, archive label). The label must stay long enough that already_decided()
# scores sim > 0.80 against the slate's drug string: for a platform drug like KEYTRUDA the archive
# holds several matching rows, and the guard only breaks the tie for a near-exact textual match.
# A 30-char truncation here scores ~0.54 and would silently fail to sweep.
ADD = [
    ('BIIB', '2026-07-13', 'LEQEMBI IQLIK (lecanemab-irmb) (at-home injection)'),
    ('MRK',  '2026-07-10', 'KEYTRUDA (pembrolizumab) plus Padcev (enfortumab vedotin-ejfv) - (KEYNOTE-B15/EV-304)'),
    ('PFE',  '2026-07-10', 'KEYTRUDA (pembrolizumab) plus Padcev (enfortumab vedotin-ejfv) - (KEYNOTE-B15/EV-304)'),
]
DROP_ROW  = 'IONS-2026-06-30'      # false decision date; real decision is IONS-2026-06-24
REDIRECTS = [('/fda-decision/IONS-2026-06-30', '/fda-decision/IONS-2026-06-24')]


def row_html(tk, d, label):
    return (f'<a class="row" href="/fda-decision/{tk}-{d}"><div class="t">{tk} · {d} '
            f'<span class="ok">✓</span></div><div class="d"><span class="ok">Approved</span> '
            f': {label}</div></a>')


def fix_archive(dry):
    h = open(DEC, encoding='utf-8').read()
    orig = h

    # 1) drop the false IONS row
    if f'/fda-decision/{DROP_ROW}"' in h:
        h2 = re.sub(r'<a class="row" href="/fda-decision/' + DROP_ROW + r'">.*?</a>', '', h, flags=re.S)
        print(f'  - removed false archive row {DROP_ROW} ({len(h)-len(h2)} chars)')
        h = h2
    else:
        print(f'  - {DROP_ROW} row already absent (idempotent)')

    # 2) insert the new rows, newest-first inside the 2026 grid
    for tk, d, label in ADD:
        if f'/fda-decision/{tk}-{d}"' in h:
            print(f'  = {tk}-{d} already in archive (idempotent)')
            continue
        m = re.search(r'<div class="mhead">2026 · (\d+)</div><div class="grid">', h)
        if not m:
            sys.exit('  *** 2026 grid header not found')
        gs = m.end()
        pos = None
        for r in re.finditer(r'<a class="row" href="/fda-decision/[A-Z]+-(\d{4}-\d{2}-\d{2})"', h[gs:]):
            if r.group(1) < d:
                pos = gs + r.start(); break
        if pos is None:
            pos = gs
        h = h[:pos] + row_html(tk, d, label) + h[pos:]
        print(f'  + added archive row {tk}-{d}')

    # 3) recompute the 2026 count from the actual rows rather than incrementing blindly
    n2026 = len(re.findall(r'<a class="row" href="/fda-decision/[A-Z]+-2026-\d{2}-\d{2}"', h))
    h = re.sub(r'<div class="mhead">2026 · \d+</div>', f'<div class="mhead">2026 · {n2026}</div>', h, count=1)
    print(f'  = 2026 count set to {n2026} (recounted from rows, not incremented)')

    if h != orig and not dry:
        shutil.copy2(DEC, DEC + '.bak_' + TODAY)
        open(DEC, 'w', encoding='utf-8').write(h)
        print('  wrote decisions/index.html')


def fix_cort_breadcrumb(dry):
    """The CORT page's breadcrumb reads "Decisions > ARQT 2026-06-29" -- the same copy/paste that
    put ARQT in its og:title (fixed 2026-07-14). Wrong ticker on a page about being right."""
    p = os.path.join(SITE, 'fda-decision', 'CORT-2026-03-25', 'index.html')
    h = open(p, encoding='utf-8').read()
    if 'ARQT 2026-06-29' in h:
        h = h.replace('&rsaquo; ARQT 2026-06-29', '&rsaquo; CORT 2026-03-25')
        if not dry:
            shutil.copy2(p, p + '.bak_' + TODAY)
            open(p, 'w', encoding='utf-8').write(h)
        print('  + fixed CORT breadcrumb (was "ARQT 2026-06-29")')
    else:
        print('  = CORT breadcrumb already correct')


def fix_sitemap(dry):
    h = open(SMAP, encoding='utf-8').read(); orig = h
    h = re.sub(r'<url><loc>https://www\.pdufa\.bio/fda-decision/' + DROP_ROW + r'</loc>.*?</url>\s*', '', h, flags=re.S)
    if h != orig: print(f'  - removed {DROP_ROW} from sitemap')
    for tk, d, _ in ADD:
        loc = f'https://www.pdufa.bio/fda-decision/{tk}-{d}'
        if loc + '</loc>' in h:
            print(f'  = {tk}-{d} already in sitemap'); continue
        entry = f'<url><loc>{loc}</loc><lastmod>{TODAY}</lastmod><changefreq>weekly</changefreq></url>\n'
        anchor = re.search(r'<url><loc>https://www\.pdufa\.bio/fda-decision/[^<]*</loc>.*?</url>\n', h, re.S)
        h = h[:anchor.start()] + entry + h[anchor.start():]
        print(f'  + added {tk}-{d} to sitemap')
    if h != orig and not dry:
        shutil.copy2(SMAP, SMAP + '.bak_' + TODAY)
        open(SMAP, 'w', encoding='utf-8').write(h)
        print('  wrote sitemap.xml')


def fix_redirects(dry):
    j = json.load(open(VJSON, encoding='utf-8'))
    have = {r['source'] for r in j.get('redirects', [])}
    ch = False
    for src, dst in REDIRECTS:
        if src in have:
            print(f'  = redirect {src} already present'); continue
        j.setdefault('redirects', []).append({'source': src, 'destination': dst, 'permanent': True})
        print(f'  + redirect {src} -> {dst} (301)'); ch = True
    if ch and not dry:
        shutil.copy2(VJSON, VJSON + '.bak_' + TODAY)
        open(VJSON, 'w', encoding='utf-8').write(json.dumps(j, indent=1) + '\n')
        print('  wrote vercel.json')


def drop_page(dry):
    p = os.path.join(SITE, 'fda-decision', DROP_ROW)
    if os.path.isdir(p):
        if not dry:
            shutil.move(p, os.path.join(HERE, '_retired_' + DROP_ROW))
        print(f'  - retired page /fda-decision/{DROP_ROW} (301 -> IONS-2026-06-24)')
    else:
        print(f'  = page {DROP_ROW} already retired')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if a.dry_run: print('*** DRY RUN — nothing will be written ***')
    print('1) decisions archive');      fix_archive(a.dry_run)
    print('2) CORT breadcrumb');        fix_cort_breadcrumb(a.dry_run)
    print('3) sitemap');                fix_sitemap(a.dry_run)
    print('4) vercel redirects');       fix_redirects(a.dry_run)
    print('5) retire the false page');  drop_page(a.dry_run)
    print('\nNext: build_slate_from_crawl.py --dry-run  (the sweep should now drop all four)')
