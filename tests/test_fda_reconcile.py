"""FDA reconciliation (#13) — every recent FDA drug approval should be in our decided archive.

WHY THIS EXISTS (audit 2026-07-25)
Merck's Lipfendra (enlicitide) — the first oral PCSK9 inhibitor, the biggest cardiology approval of
the year — was FDA-approved 2026-07-16 and the site missed it entirely, because it entered and
resolved after the last full crawl and wasn't pre-loaded. This check reads the FDA's own
press-release RSS for the trailing window and confirms each drug-approval item has a matching row in
the decided archive. Anything present in the FDA feed but absent from our archive is surfaced for
review — that is exactly the signal that would have flagged Lipfendra the next morning.

DESIGN — this is a RECONCILIATION REPORT, run by the scheduled job (it needs network), not a blocking
offline guard. The FDA feed contains many approvals we don't track (generics, devices, non-catalyst
sponsors), so hard-failing every deploy on them would be wrong. It exits 0 and prints a loud
"NOT IN ARCHIVE" list; the daily task reads that list and a human/agent verifies + backfills real
misses. If the feed can't be fetched, it SKIPs (never breaks the run).

    python tests/test_fda_reconcile.py [--days 30]
"""
import os, re, sys, argparse, urllib.request, datetime as dt

SITE = 'pdufa_site_src'
DECISIONS = os.path.join(SITE, 'decisions', 'index.html')
RSS = 'https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml'
STOP = {'FDA', 'THE', 'FOR', 'AND', 'FIRST', 'NEW', 'DRUG', 'ORAL', 'TREATMENT', 'ADULTS',
        'APPROVES', 'APPROVAL', 'APPROVED', 'INHIBITOR', 'THERAPY', 'PATIENTS', 'DISEASE',
        'CHILDREN', 'ADULT', 'WITH', 'HIGH', 'LOWER', 'REDUCE', 'CLASS', 'ONLY', 'ONCE'}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={'User-Agent': 'pdufa.bio reconcile contact@pdufa.bio'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=30)
    a = ap.parse_args()

    if not os.path.exists(DECISIONS):
        print('  SKIP decisions archive not found'); return 0
    archive = open(DECISIONS, encoding='utf-8').read().upper()
    # also match on the FDA article LINK: an approval whose FDA URL is already a source in our data
    # is covered even when the FDA headline never names the drug (e.g. Lipfendra's descriptive title).
    ds = os.path.join(SITE, 'api', 'v1', 'dataset.mjs')
    dataset_urls = open(ds, encoding='utf-8').read() if os.path.exists(ds) else ''

    try:
        xml = fetch(RSS)
    except Exception as e:
        print(f'  SKIP could not fetch FDA RSS ({e}) — reconciliation not run this cycle'); return 0

    items = re.findall(r'<item>(.*?)</item>', xml, re.S)
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=a.days)
    approvals, missing = [], []
    for it in items:
        title = re.sub(r'<[^>]+>', '', (re.search(r'<title>(.*?)</title>', it, re.S) or [None, ''])[1]).strip()
        if 'approv' not in title.lower():
            continue
        pub = re.search(r'<pubDate>(.*?)</pubDate>', it)
        try:
            when = dt.datetime.strptime(pub.group(1).strip()[:25], '%a, %d %b %Y %H:%M:%S') if pub else dt.datetime.utcnow()
        except Exception:
            when = dt.datetime.utcnow()
        if when < cutoff:
            continue
        approvals.append(title)
        link = (re.search(r'<link>(.*?)</link>', it, re.S) or [None, ''])[1].strip()
        desc = re.sub(r'<[^>]+>', ' ', (re.search(r'<description>(.*?)</description>', it, re.S) or [None, ''])[1])
        # covered if the FDA article URL is already a source in our dataset, OR a distinctive
        # word from the title/description appears in the decided archive
        by_link = bool(link) and link.split('?')[0] in dataset_urls
        toks = [w for w in re.findall(r'[A-Za-z][A-Za-z\-]{4,}', title + ' ' + desc) if w.upper() not in STOP]
        by_text = any(w.upper() in archive for w in toks)
        if not (by_link or by_text):
            missing.append((when.date().isoformat(), title))

    print(f'FDA press-release approvals in last {a.days}d: {len(approvals)}  |  not found in archive: {len(missing)}')
    if missing:
        print('  NOT IN ARCHIVE — verify against the FDA item and backfill if it is a tracked catalyst:')
        for d, t in missing:
            print(f'    [{d}] {t[:110]}')
        print('  (Reconciliation is advisory: many FDA approvals are generics/devices/untracked sponsors.)')
    else:
        print('OK -- every recent FDA approval headline maps to something in the decided archive.')
    return 0   # advisory: never blocks the deploy; the daily task surfaces the list


if __name__ == '__main__':
    sys.exit(main())
