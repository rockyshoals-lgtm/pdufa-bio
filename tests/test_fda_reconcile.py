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
# 2026-08-22: the press-release feed is NOT where most drug approvals are announced. BMY's
# iberdomide (Zenbexus) was approved Aug 13 and this check reported "OK -- every recent FDA
# approval maps to the archive" for nine days, because oncology and haematology approvals are
# posted to the CDER approval-notification pages, never to the press feed. Only 3 approvals
# appeared in a 30-day window; the real number is many times that. Read the notification page too.
ONC = ('https://www.fda.gov/drugs/resources-information-approved-drugs/'
       'oncology-cancerhematologic-malignancies-approval-notifications')
STOP = {'FDA', 'THE', 'FOR', 'AND', 'FIRST', 'NEW', 'DRUG', 'ORAL', 'TREATMENT', 'ADULTS',
        'APPROVES', 'APPROVAL', 'APPROVED', 'INHIBITOR', 'THERAPY', 'PATIENTS', 'DISEASE',
        'CHILDREN', 'ADULT', 'WITH', 'HIGH', 'LOWER', 'REDUCE', 'CLASS', 'ONLY', 'ONCE'}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={'User-Agent': 'pdufa.bio reconcile contact@pdufa.bio'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def covered(title, desc, link, archive, dataset_urls):
    """Is this FDA approval already represented in our decided archive?

    2026-08-22 -- the old test was `any(token in archive)` over every 5+ letter word in the
    title AND description. Across a 450-row archive some word always matched ("COMBINATION",
    "MYELOMA", "PATIENTS"), so the check could effectively only pass. Now:
      * the FDA article URL being a source in our data still counts (exact, strong), and
      * the TEXT test uses only the drug names the FDA itself names -- the parenthesised brand
        and the INN preceding it -- and requires the whole name, not a fragment.

    Returns True (covered), False (a real gap), or None (UNVERIFIABLE -- the headline names no
    drug at all, e.g. "FDA Approves First Oral PCSK9 Inhibitor to Lower LDL Cholesterol"). None
    is reported separately: calling an unverifiable item "missing" is how a reconciliation report
    starts crying wolf, and Lipfendra IS in our archive under enlicitide.
    """
    if link and link.split('?')[0] in dataset_urls:
        return True
    names = set()
    # "...approval to iberdomide (Zenbexus, Bristol-Myers Squibb Company)" -> both names
    for m in re.finditer(r'\b(?:to|for|of)\s+([a-z][a-z\-]{5,})\s*\(([A-Z][A-Za-z\-]{3,})', title + ' ' + desc):
        names.add(m.group(1)); names.add(m.group(2))
    for m in re.finditer(r'\b([A-Z][A-Z\-]{4,})\b', title):     # ALL-CAPS brand in a headline
        if m.group(1) not in STOP:
            names.add(m.group(1))
    # generic-sounding INN tokens as a fallback (mab/nib/tide/gene/cel endings)
    for w in re.findall(r'\b([a-z][a-z\-]{6,}(?:mab|nib|tinib|ciclib|sertib|tide|parvovec|cel|gene))\b',
                        (title + ' ' + desc).lower()):
        names.add(w)
    names = {n for n in names if len(n) >= 5}
    if not names:
        return None                      # headline names no drug -> cannot verify either way
    return any(n.upper() in archive for n in names)


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
    approvals, missing, unverifiable = [], [], []
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
        cov = covered(title, desc, link, archive, dataset_urls)
        if cov is None:
            unverifiable.append((when.date().isoformat(), title))
        elif not cov:
            missing.append((when.date().isoformat(), title))

    # ---- CDER approval notifications (where oncology/haematology approvals actually land) ----
    try:
        page = fetch(ONC)
    except Exception as e:
        print(f'  note: could not fetch the FDA approval-notification page ({e})')
        page = ''
    # The page is a dated table sorted newest-first:
    #   <tr><td><a href="...">headline</a></td><td>description</td><td>08/13/2026</td></tr>
    # Parse the rows so the date filter is real -- scraping bare links returned the entire
    # historical index (2023 approvals included), which would drown the signal in noise.
    for row in re.findall(r'<tr>(.*?)</tr>', page, re.S):
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
        if len(cells) < 3:
            continue
        am = re.search(r'href="([^"]+)"', cells[0])
        title = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', cells[0])).strip()
        desc = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', cells[1])).strip()
        dm = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', cells[2])
        if not (am and dm and title):
            continue
        when = dt.datetime(int(dm.group(3)), int(dm.group(1)), int(dm.group(2)))
        if when < cutoff:
            continue
        href = am.group(1)
        url = href if href.startswith('http') else 'https://www.fda.gov' + href
        approvals.append(title)
        cov = covered(title, desc, url, archive, dataset_urls)
        if cov is None:
            unverifiable.append((when.date().isoformat(), title))
        elif not cov:
            missing.append((when.date().isoformat(), title))

    print(f'FDA press-release approvals in last {a.days}d: {len(approvals)}  |  not found in archive: {len(missing)}')
    if missing:
        print('  NOT IN ARCHIVE — verify against the FDA item and backfill if it is a tracked catalyst:')
        for d, t in missing:
            print(f'    [{d}] {t[:110]}')
        print('  (Reconciliation is advisory: many FDA approvals are generics/devices/untracked sponsors.)')
    if unverifiable:
        print(f'  UNVERIFIABLE BY NAME: {len(unverifiable)} headline(s) name no drug '
              f'(e.g. "First Oral PCSK9 Inhibitor") -- open the FDA item to check:')
        for d, t in unverifiable[:6]:
            print(f'    [{d}] {t[:110]}')
    if not missing:
        print('OK -- every recent FDA approval headline maps to something in the decided archive.')
    return 0   # advisory: never blocks the deploy; the daily task surfaces the list


if __name__ == '__main__':
    sys.exit(main())
