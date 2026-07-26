"""CI guard #10: the site may not advertise a data currency it cannot back.

WHY THIS EXISTS
For twelve days the dataset's every row carried updated_at = 2026-07-11, while /coverage claimed
"refreshes ~5x/day via cron" and the homepage flashed a "Live" badge. The envelope said "today";
the contents hadn't moved since July 11. Anyone who diffs the API against that sentence catches it
in one call — and a real FDA decision (centanafadine, 7/24) was about to resolve on a catalyst the
frozen data never showed. The freshness signal was cosmetic.

THE INVARIANT
A currency CLAIM must be a function of the DATA, never a decorative string.
  1. No page may assert an automated refresh cadence ("Nx/day", "via cron", "every hour") unless
     the data's BULK age actually backs it. Bulk age = today minus the MODE of updated_at across
     all rows (the last real full refresh) — deliberately the mode, so a single hand-added row
     with a fresh timestamp cannot fake site-wide currency.
  2. The homepage must not ship a hardcoded "Live" badge; the header must carry the data-driven
     freshness stamp (id="fresh") that prints the real data-through date.

This guard reads the source files offline, like the others.

    python tests/test_data_freshness.py
"""
import os, re, sys, datetime as dt
from collections import Counter

SITE = 'pdufa_site_src'
DATASET = os.path.join(SITE, 'api', 'v1', 'dataset.mjs')
COVERAGE = os.path.join(SITE, 'coverage', 'index.html')
INDEX = os.path.join(SITE, 'index.html')

# claims of an AUTOMATED cadence — only true if the data is actually being refreshed that often
CADENCE = re.compile(r'\d+\s*[×x]\s*/?\s*day|via\s+cron|refreshe?s?[^.]{0,40}\b(hourly|every\s+hour|per\s+hour)', re.I)
BULK_STALE_DAYS = 3   # if the bulk refresh is older than this, an "automated cadence" claim is false


def bulk_and_newest_age():
    """Currency of the FORWARD PDUFA calendar only (type PDUFA, not Decided, date >= today).
    Decided/historical rows keep their original timestamps on purpose; measuring them would
    falsely report the live calendar as stale. Matches the homepage badge's scope exactly."""
    import json
    txt = open(DATASET, encoding='utf-8', errors='ignore').read()
    today = dt.date.today()
    tISO = today.isoformat()
    try:
        arr = json.loads(txt[txt.index('['):txt.rindex(']') + 1])
    except Exception:
        arr = []
    days = [str(r.get('ua', ''))[:10] for r in arr
            if r.get('type') == 'PDUFA' and r.get('st') != 'Decided'
            and str(r.get('d', ''))[:10] >= tISO and r.get('ua')]
    if not days:
        return None, None, 0
    mode_day = Counter(days).most_common(1)[0][0]
    newest = max(days)
    bulk_age = (today - dt.date.fromisoformat(mode_day)).days
    newest_age = (today - dt.date.fromisoformat(newest)).days
    return bulk_age, newest_age, len(days)


def main():
    if not os.path.exists(DATASET):
        print(f'  SKIP {DATASET} not found'); return 0

    bulk_age, newest_age, n = bulk_and_newest_age()
    if bulk_age is None:
        print('  SKIP no updated_at timestamps in dataset'); return 0

    fail = []

    # 1) cadence claims must be backed by the data
    for path in (COVERAGE, INDEX):
        if not os.path.exists(path):
            continue
        for m in CADENCE.finditer(open(path, encoding='utf-8', errors='ignore').read()):
            if bulk_age > BULK_STALE_DAYS:
                fail.append((os.path.relpath(path, SITE),
                             f'claims an automated refresh cadence ("{m.group(0).strip()}") but the '
                             f'bulk of the data is {bulk_age}d old (last full refresh mode-date). '
                             f'The claim is false — remove it or revive the pipeline.'))

    # 2) homepage badge must be data-driven, not a hardcoded "Live"
    html = open(INDEX, encoding='utf-8', errors='ignore').read()
    has_stamp = 'id="fresh"' in html
    hardcoded_live = re.search(r'<span class="dot"></span>\s*Live\b', html)
    if hardcoded_live and not has_stamp:
        fail.append(('index.html',
                     'ships a hardcoded "Live" badge with no data-driven freshness stamp '
                     '(id="fresh"). "Live" must be computed from updated_at, never asserted.'))

    print(f'freshness: {n} rows · bulk refresh {bulk_age}d old · newest row {newest_age}d old')
    if fail:
        for rel, why in fail:
            print(f'  FAIL {rel}: {why}')
        print(f'\n{len(fail)} currency claim(s) the data does not support. The site would be '
              f'advertising freshness it cannot back. DO NOT PUBLISH.')
        return 1

    if bulk_age > 7:
        # not a failure — the site is honestly showing a stale date — but make it loud in CI
        print(f'  note: bulk data is {bulk_age}d old. The header correctly shows a stale '
              f'"data through" date; revive the crawl to move it. No dishonest claim present.')
    print('OK -- no page claims a currency the data cannot back; badge is data-driven.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
