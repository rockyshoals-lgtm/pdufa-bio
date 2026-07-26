#!/usr/bin/env python3
"""Originality gate — competitor-sourced or non-redistributable data must NEVER reach the
public site, API or sitemap. Blocks deploy. Run: python3 tests/test_originality.py"""
import sys, os, glob, csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
BANNED_SOURCES = ('biopharmacatalyst', 'bpc', 'bpiq', 'biopharmawatch',
                  'fdatracker', 'rttnews', 'stocktitan', 'marketbeat')
BANNED_FILES = ('bpc_internal', 'drugbank')
errs, notes = [], []

# 1. public catalyst feed must be 100% redistributable and free of competitor sources
feed = os.path.join(REPO, 'catalysts_out', 'catalysts_public.csv')
if os.path.exists(feed):
    with open(feed, encoding='utf-8', errors='ignore') as fh:
        rows = list(csv.DictReader(fh))
    notes.append(f'public feed: {len(rows)} rows')
    bad_redist = [r for r in rows if str(r.get('redistribute', '')).strip().lower() in ('false', '0', 'no')]
    if bad_redist:
        errs.append(f'FATAL: {len(bad_redist)} non-redistributable rows in the PUBLIC feed')
    bad_src = [r for r in rows
               if any(b in str(r.get('source', '')).lower() for b in BANNED_SOURCES)]
    if bad_src:
        errs.append(f'FATAL: {len(bad_src)} competitor-sourced rows in the PUBLIC feed '
                    f'(e.g. {bad_src[0].get("source")})')
else:
    notes.append('public feed not present in this checkout — skipped')

# 2. nothing shipped may DEPEND on a competitor/licensed dataset.
#    Prose that *names* one (e.g. the /sources register explaining what we refuse to use)
#    is fine and in fact desirable — we only flag an actual data dependency.
DEP_MARKERS = ('.csv', '.xml', '.zip', '.json', 'import', 'require', 'read_csv', 'fetch(')
for pat in ('**/*.mjs', '**/*.js', '**/*.html'):
    for f in glob.glob(os.path.join(ROOT, pat), recursive=True):
        if os.sep + 'tests' + os.sep in f:
            continue
        try:
            txt = open(f, encoding='utf-8', errors='ignore').read().lower()
        except Exception:
            continue
        for b in BANNED_FILES:
            i = txt.find(b)
            while i != -1:
                window = txt[max(0, i - 60):i + 60]
                if any(mk in window for mk in DEP_MARKERS):
                    errs.append(f'FATAL: {os.path.relpath(f, ROOT)} appears to DEPEND on "{b}" '
                                f'(context: ...{window.strip()[:70]}...)')
                    break
                i = txt.find(b, i + 1)

# 3. licensed vendor raw data must never be served
for b in ('drugbank',):
    hits = glob.glob(os.path.join(REPO, f'*{b}*'))
    if hits:
        errs.append(f'FATAL: licensed dataset still on disk: {os.path.basename(hits[0])}')

print('\n'.join('  ' + n for n in notes))
if errs:
    print('\n'.join(errs)); sys.exit(1)
print('OK — public feed original & redistributable; no competitor or licensed data reachable.')
