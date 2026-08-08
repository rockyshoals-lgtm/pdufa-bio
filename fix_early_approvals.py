# -*- coding: utf-8 -*-
"""Resolve two EARLY FDA approvals that pdufa.bio still shows as pending.

THE BUG (root cause, not the symptom):
build_slate_from_crawl.load_decided() reads ONLY pdufa_site_src/decisions/index.html to learn
which events are already decided. Its own docstring names CORT as the motivating example:

    "An FDA approval can land EARLY (CORT/relacorilant approved 2026-03-25 vs a 2026-07-11
     PDUFA), so a forward-dated PDUFA is NOT proof the decision is still pending."

The guard is correct. It just never fired, because CORT's approval was NEVER ADDED to the
archive index it reads. The /fda-decision/CORT-2026-03-25 page was even built — it just was
not listed. A safety net that reads an incomplete list is not a safety net.

VERIFIED AGAINST PRIMARY SOURCES:
  CORT — "FDA Approves Corcept's ... Lifyorli(TM) (relacorilant) Plus Nab-Paclitaxel for
         Treatment of Patients with Platinum-Resistant Ovarian Cancer", Corcept IR, 2026-03-25.
         (Corcept then uses the BRAND name Lifyorli in its Apr-10 SGO and May-29 ASCO releases —
         a drug only gets a brand name once approved. Independent corroboration.)
  CELC — "Celcuity Announces FDA Approval of REVTORPYK(TM) (gedatolisib) ...", 2026-07-14,
         approved 3 days ahead of the 2026-07-17 goal date.

This script is idempotent: it will not double-insert.
"""
import os, re, shutil, sys, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, 'pdufa_site_src')
DEC_INDEX = os.path.join(SITE, 'decisions', 'index.html')

# (ticker, date, banner_drug, archive_drug_label, source_url)
FIX = [
    ('CELC', '2026-07-14', 'Gedatolisib with Fulvestrant - (VIKTORIA-1)',
     'REVTORPYK (gedatolisib) + fulvestrant',
     'https://ir.celcuity.com/news-releases'),
    ('CORT', '2026-03-25', 'Relacorilant + nab-paclitaxel - (ROSELLA)',
     'Lifyorli (relacorilant) + nab-paclitaxel',
     'https://ir.corcept.com/news-releases/news-release-details/fda-approves-corcepts-selective-glucocorticoid-receptor'),
]

def row_html(tk, d, label):
    return (f'<a class="row" href="/fda-decision/{tk}-{d}"><div class="t">{tk} · {d} '
            f'<span class="ok">✓</span></div><div class="d"><span class="ok">Approved</span> '
            f': {label}</div></a>')

def add_rows():
    h = open(DEC_INDEX, encoding='utf-8').read()
    shutil.copy(DEC_INDEX, DEC_INDEX + '.bak')
    added = []
    for tk, d, _bd, label, _u in FIX:
        if f'/fda-decision/{tk}-{d}' in h:
            print(f'  {tk}-{d} already in archive — skipping (idempotent)')
            continue
        # insert into the 2026 grid, keeping the newest-first date order the archive uses
        m = re.search(r'(<div class="mhead">2026 · (\d+)</div><div class="grid">)', h)
        if not m:
            print('  *** could not find the 2026 grid header — aborting'); return None, []
        grid_start = m.end()
        # find each existing row's date inside the 2026 grid, insert before the first older one
        rows = list(re.finditer(r'<a class="row" href="/fda-decision/[A-Z]+-(\d{4}-\d{2}-\d{2})"', h[grid_start:]))
        pos = grid_start
        for r in rows:
            if r.group(1) < d:           # first row older than ours -> insert here
                pos = grid_start + r.start()
                break
        else:
            pos = grid_start + (rows[-1].start() if rows else 0)
        h = h[:pos] + row_html(tk, d, label) + h[pos:]
        added.append(f'{tk}-{d}')
        # bump the 2026 count
        m2 = re.search(r'<div class="mhead">2026 · (\d+)</div>', h)
        if m2:
            h = h[:m2.start()] + f'<div class="mhead">2026 · {int(m2.group(1)) + 1}</div>' + h[m2.end():]
    open(DEC_INDEX, 'w', encoding='utf-8').write(h)
    return h, added

def make_page(tk, d, drug, label, url):
    """Build /fda-decision/{tk}-{d} from the VERA page as a template."""
    out_dir = os.path.join(SITE, 'fda-decision', f'{tk}-{d}')
    if os.path.exists(os.path.join(out_dir, 'index.html')):
        print(f'  page {tk}-{d} exists — skipping')
        return False
    tpl_p = os.path.join(SITE, 'fda-decision', 'VERA-2026-07-07', 'index.html')
    t = open(tpl_p, encoding='utf-8').read()
    pretty = dt.date.fromisoformat(d).strftime('%b %-d, %Y') if os.name != 'nt' \
        else dt.date.fromisoformat(d).strftime('%b %d, %Y').replace(' 0', ' ')
    t = t.replace('VERA-2026-07-07', f'{tk}-{d}')
    t = t.replace('2026-07-07', d)
    t = t.replace('Jul 7, 2026', pretty)
    t = t.replace('Atacicept - (ORIGIN 3)', drug)
    t = t.replace('Trutakna (atacicept)', label)
    t = t.replace('Atacicept', drug.split(' - ')[0])
    t = re.sub(r'\bVERA\b', tk, t)
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8').write(t)
    print(f'  built page /fda-decision/{tk}-{d}')
    return True

def fix_ogtitle():
    """The CORT decision page carries ARQT's og:title — a copy/paste bug in whatever generated
    it. Wrong ticker in the social card of a page whose whole job is being right about tickers."""
    p = os.path.join(SITE, 'fda-decision', 'CORT-2026-03-25', 'index.html')
    if not os.path.exists(p):
        return
    h = open(p, encoding='utf-8').read()
    if 'content="ARQT FDA Dec' in h:
        shutil.copy(p, p + '.bak')
        h = h.replace('content="ARQT FDA Dec', 'content="CORT FDA Dec')
        h = re.sub(r'(og:title[^>]*content=")ARQT', r'\1CORT', h)
        open(p, 'w', encoding='utf-8').write(h)
        print('  fixed CORT page og:title (was ARQT)')
    else:
        print('  CORT og:title already correct')

if __name__ == '__main__':
    print('1) building any missing decision pages')
    for tk, d, drug, label, url in FIX:
        make_page(tk, d, drug, label, url)
    print('2) adding rows to the decisions archive (what load_decided actually reads)')
    h, added = add_rows()
    print('   added:', added or 'nothing (already present)')
    print('3) fixing the CORT og:title bug')
    fix_ogtitle()
    print('\nNext: re-run build_slate_from_crawl.py — already_decided() can now see these '
          'and will drop them from the forward calendar.')
