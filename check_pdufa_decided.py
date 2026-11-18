# -*- coding: utf-8 -*-
"""Detect FDA decisions that ALREADY HAPPENED for PDUFAs still listed as pending.

WHY THIS EXISTS
The slate sweep in build_slate_from_crawl.already_decided() can only remove a phantom if the
decision is IN the decisions archive. If the FDA acts and nobody has logged it yet, the archive
is silent and the phantom stays. That is the last hole:

    CORT  approved 2026-03-25, listed as pending until 2026-07-15  (archive HAD it; the drug-name
          match failed because the brand name "Lifyorli" shares nothing with "relacorilant")
    CELC  approved 2026-07-14, listed as pending the next morning  (archive did NOT have it yet)

The company announces its own approval within minutes. So: for every forward PDUFA, read the
sponsor's recent press releases and look for the FDA acting. Same idea as the readout miner's
enrich_from_filings(), aimed at PDUFAs.

THIS DOES NOT MUTATE THE SITE. It reports. A wrong auto-delete on a public calendar is worse
than a stale row, and an "approval" headline can be for a different drug from the same sponsor.
A human (or a follow-up curation step) adds the verified row to the decisions archive; the
sweep then removes the phantom on the next build.

    python check_pdufa_decided.py            # every forward PDUFA
    python check_pdufa_decided.py --days 120 # only ones inside 120 days
"""
import os, re, sys, json, argparse
import concurrent.futures as cf
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))

def load_env():
    for p in (os.path.join(HERE, 'Odin Perfection', '.env_master'), os.path.join(HERE, '.env')):
        if os.path.exists(p):
            for line in open(p, encoding='utf-8', errors='ignore'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
load_env()

FMP_PR = 'https://financialmodelingprep.com/stable/news/press-releases'
PR_CAP = 3000

# The FDA acted. Company PRs are formulaic about this.
APPROVED = re.compile(
    r'\bFDA\s+Approves\b|\bU\.?S\.?\s+FDA\s+Approves\b|Announces?\s+(?:the\s+)?FDA\s+Approval|'
    r'Receives?\s+FDA\s+Approval|\bApproved\s+by\s+the\s+(?:U\.?S\.?\s+)?FDA\b|'
    r'Announces?\s+(?:U\.?S\.?\s+)?Approval\s+of', re.I)
CRL = re.compile(
    r'Complete\s+Response\s+Letter|\bCRL\b|Receives?\s+(?:a\s+)?Complete\s+Response', re.I)
# forward-looking noise: "if approved", "seeking approval", "submits for approval"
FUTURE = re.compile(r'\bif\s+approved\b|\bseek\w*\s+approval|submit\w*|\bfiles?\b|acceptance\s+of', re.I)

def norm(s):
    s = (s or '').lower()
    s = re.sub(r'[()]', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    stop = {'the','and','with','plus','in','for','a','of','combination','tablet','tablets',
            'capsule','capsules','injection','solution','cream','foam','placebo','oral',
            # 2026-11-18: generic words matched other drugs' approvals. 'treatment' in the MRK
            # IDVYNSO row's name matched Merck KGaA's PIMJETMI release ("...for Patients with").
            'treatment','naive','patients','children','adults','pediatric','lower','doses',
            'weekly','daily','sndas','supplemental','formulation','first','second','resubmission',
            'relapsed','refractory','disease','syndrome','cancer','tumor','tumors','chronic',
            'advanced','full','approval','label','expansion','season','study','trial','phase'}
    return [w for w in s.split() if w not in stop and len(w) > 4]


def row_source_dates(path):
    """(ticker, date) -> the date of the document each open PDUFA row is sourced to. A release older
    than the row's own source cannot have decided it: that source already says the goal is pending
    (PHAR's Sep 25 sNDA acceptance came two weeks after the Sep 11 Joenja approval)."""
    out = {}
    try:
        src = open(path, encoding='utf-8').read()
        rows = json.loads(src[src.index('['):src.rindex(']') + 1])
    except Exception:
        return out
    for r in rows:
        if r.get('type') != 'PDUFA':
            continue
        d = r.get('_d') or {}
        m = re.search(r'(20\d\d-\d\d-\d\d)', str(d.get('source') or ''))
        if m:
            out[(r.get('t'), r.get('d'))] = m.group(1)
    return out


def load_acks(path):
    """Headlines checked by hand and found to be about a DIFFERENT application than the row."""
    try:
        return json.load(open(path, encoding='utf-8')).get('acks', [])
    except Exception:
        return []


def acked(acks, ticker, date, url, title):
    for a in acks:
        if a.get('ticker') == ticker and a.get('date') == date and (
                (a.get('url_prefix') and str(url).startswith(a['url_prefix'])) or
                (a.get('title_prefix') and str(title).startswith(a['title_prefix']))):
            return True
    return False


def match(c, releases, src_date=None, acks=()):
    """The first release that looks like the FDA acting on this row's drug, or None."""
    toks = norm(c.get('drug'))
    if not toks:
        return None
    for title, blob, pub, url in releases:
        if FUTURE.search(title):
            continue
        act = 'Approved' if APPROVED.search(title) else ('CRL' if CRL.search(title) else None)
        if not act:
            continue
        # the PR must actually be about THIS drug
        if not any(re.search(r'\b' + re.escape(t) + r'\b', blob, re.I) for t in toks):
            continue
        if src_date and pub and pub[:10] < src_date:
            continue
        if acked(acks, c.get('ticker'), c.get('date'), url, title):
            continue
        return (c['ticker'], c.get('date'), act, pub, title, url)
    return None


def self_test():
    idv = {'ticker': 'MRK', 'date': '2027-04-22', 'drug': 'IDVYNSO - treatment-naive HIV-1 (P053) and 96-week data (sNDAs)'}
    pim = ('FDA Approves PIMJETMI (pimicotinib) for Patients with Tenosynovial Giant Cell Tumor',
           'FDA Approves PIMJETMI . the first treatment for adults with TGCT', '2026-11-10', 'https://x/pim')
    joe = {'ticker': 'PHAR', 'date': '2027-01-30', 'drug': 'Joenja (leniolisib) lower doses (sNDA)'}
    old = ("FDA approves Pharming's Joenja as first treatment for children with APDS",
           "FDA approves Pharming's Joenja . leniolisib children", '2026-09-11', 'https://x/joe')
    new = ("FDA approves Pharming's Joenja lower doses for children from 13 kg",
           "FDA approves Joenja . leniolisib lower doses", '2026-12-20', 'https://x/joe2')
    gil = {'ticker': 'GILD', 'date': '2027-02-02', 'drug': 'Yeztugo (lenacapavir) once-weekly oral'}
    bix = ("U.S. FDA Approves Gilead's Bixlenvo", 'Bixlenvo bictegravir lenacapavir', '2026-08-27',
           'https://x/bix')
    ack = [{'ticker': 'GILD', 'date': '2027-02-02', 'url_prefix': 'https://x/bix'}]
    cases = [
        (match(idv, [pim]) is None, 'a generic word never ties another drug\'s approval to a row'),
        (match(joe, [old], '2026-09-25') is None, 'an approval older than the row\'s own source is skipped'),
        (match(joe, [new], '2026-09-25') is not None, 'a newer approval of the same drug is still flagged'),
        (match(gil, [bix], '2026-08-06', ack) is None, 'a hand-checked different product is skipped'),
        (match(gil, [bix], '2026-08-06') is not None, 'without the ack the same headline is flagged'),
    ]
    bad = [why for ok, why in cases if not ok]
    for why in bad:
        print('SELF-TEST FAILED:', why)
    return not bad

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=0, help='only PDUFAs within N days (0 = all)')
    ap.add_argument('--api', default=os.path.join(HERE, 'pdufa_site_src', 'api', 'data.js'))
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if not self_test():
        return 1
    if a.self_test:
        print('OK -- decided-PDUFA matcher: generic words, older releases and hand-checked other '
              'products are skipped; a newer approval of the row\'s drug is flagged.')
        return 0
    key = os.environ.get('FMP_API_KEY')
    if not key:
        print('FMP_API_KEY not set — cannot read company PRs. Nothing to do.'); return 1
    import requests

    src = open(a.api, encoding='utf-8').read()
    i = src.find('const SLATE=')
    slate, _ = json.JSONDecoder().raw_decode(src[i + len('const SLATE='):])
    cats = slate['catalysts']
    today = dt.date.today()

    def within(c):
        if not a.days:
            return True
        try:
            return (dt.date.fromisoformat(str(c.get('date'))[:10]) - today).days <= a.days
        except Exception:
            return True
    cats = [c for c in cats if c.get('ticker') and within(c)]
    tickers = sorted({c['ticker'] for c in cats})
    print(f'checking {len(cats)} forward PDUFAs across {len(tickers)} tickers against company PRs...\n')

    def fetch(tk):
        try:
            r = requests.get(FMP_PR, params={'symbols': tk, 'limit': 40, 'apikey': key}, timeout=20)
            rows = r.json() if r.status_code == 200 else []
        except Exception:
            return tk, []
        out = []
        for x in (rows if isinstance(rows, list) else []):
            if not isinstance(x, dict):
                continue
            title = str(x.get('title') or '')
            body = str(x.get('text') or x.get('content') or '')[:PR_CAP]
            out.append((title, re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', title + ' . ' + body)),
                        str(x.get('publishedDate') or x.get('date') or '')[:10],
                        x.get('url') or x.get('link') or ''))
        return tk, out

    prs = {}
    with cf.ThreadPoolExecutor(10) as ex:
        for tk, v in ex.map(fetch, tickers):
            prs[tk] = v

    srcd = row_source_dates(os.path.join(HERE, 'pdufa_site_src', 'api', 'v1', 'dataset.mjs'))
    acks = load_acks(os.path.join(HERE, '_pdufa_decided_ack.json'))
    found = []
    for c in cats:
        m = match(c, prs.get(c['ticker'], []), srcd.get((c['ticker'], c.get('date'))), acks)
        if m:
            found.append(m)

    if not found:
        print('No forward PDUFA appears to have been decided already. Calendar is clean.')
        return 0
    print('*** %d forward PDUFA(s) look ALREADY DECIDED — verify, then add to the decisions '
          'archive so the sweep removes them ***\n' % len(found))
    for tk, d, act, pub, title, url in sorted(found, key=lambda x: x[3], reverse=True):
        print(f'  {tk:6s} listed {d}  ->  {act} announced {pub}')
        print(f'         "{title[:104]}"')
        print(f'         {url[:104]}')
    print('\nNothing was changed. Verify each against the company IR/8-K, add a row to')
    print('pdufa_site_src/decisions/index.html, then re-run build_slate_from_crawl.py.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
