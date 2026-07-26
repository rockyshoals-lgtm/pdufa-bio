"""CI guard #11: no filing-artefact drug names may reach the published data.

WHY THIS EXISTS
The catalyst crawler's raw SEC parser occasionally grabs an exhibit label instead of a drug —
Axsome's real AXS-12 PDUFA came through with drug "EX-99" (that's EX-99.1, the 8-K exhibit
number), and a Dyne filing came through as the garbled "zeleciment basivarsen". The crawler now
rejects these at extraction time, but this guard is the backstop: if a junk name ever lands in the
published surfaces — via a crawler regression, a bad merge, or a manual slip — the build fails
instead of shipping "EX-99" as a drug on a public FDA calendar.

Checks the drug/name fields in both published data surfaces.

    python tests/test_no_junk_drug_names.py
"""
import json, os, re, sys

SITE = 'pdufa_site_src'
API = os.path.join(SITE, 'api', 'data.js')
DATASET = os.path.join(SITE, 'api', 'v1', 'dataset.mjs')

# Mirrors the crawler's _is_junk_drug: exhibit labels, SEC form types, bare numbers. NO letter-count
# rule -- single-letter dev codes (A-101, S095035) are real drugs and must pass.
JUNK = re.compile(r'^\s*(ex[\s\-]?\d|exhibit\b|form\s|item\s|8-?k\b|10-?[kq]\b|424b|\d+(\.\d+)?\s*$)', re.I)


def is_junk(name):
    n = str(name or '').strip()
    if not n:
        return False  # blank is handled by the null-drug policy, not this guard
    return bool(JUNK.match(n))


def slate_names():
    if not os.path.exists(API):
        return []
    src = open(API, encoding='utf-8').read()
    i = src.find('const SLATE=')
    slate, _ = json.JSONDecoder().raw_decode(src[i + len('const SLATE='):])
    return [(c.get('ticker'), c.get('drug')) for c in slate['catalysts']]


def dataset_names():
    if not os.path.exists(DATASET):
        return []
    txt = open(DATASET, encoding='utf-8').read()
    arr = json.loads(txt[txt.index('['):txt.rindex(']') + 1])
    return [(r.get('t'), r.get('name')) for r in arr]


def main():
    bad = []
    for surface, rows in (('api/data.js', slate_names()), ('api/v1/dataset.mjs', dataset_names())):
        for tk, name in rows:
            if is_junk(name):
                bad.append((surface, tk, name))
    if bad:
        for surface, tk, name in bad:
            print(f'  FAIL {surface}: {tk} has a filing-artefact drug name: "{name}"')
        print(f'\n{len(bad)} junk drug name(s) in published data (exhibit/form labels are not drugs). '
              f'DO NOT PUBLISH.')
        return 1
    print(f'OK -- no junk drug names in either surface '
          f'({len(slate_names())} slate + {len(dataset_names())} dataset rows checked).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
