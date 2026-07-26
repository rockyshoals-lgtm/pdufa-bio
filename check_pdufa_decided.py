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
            'capsule','capsules','injection','solution','cream','foam','placebo','oral'}
    return [w for w in s.split() if w not in stop and len(w) > 4]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=0, help='only PDUFAs within N days (0 = all)')
    ap.add_argument('--api', default=os.path.join(HERE, 'pdufa_site_src', 'api', 'data.js'))
    a = ap.parse_args()
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

    found = []
    for c in cats:
        toks = norm(c.get('drug'))
        if not toks:
            continue
        for title, blob, pub, url in prs.get(c['ticker'], []):
            if FUTURE.search(title):
                continue
            act = 'Approved' if APPROVED.search(title) else ('CRL' if CRL.search(title) else None)
            if not act:
                continue
            # the PR must actually be about THIS drug
            if not any(re.search(r'\b' + re.escape(t) + r'\b', blob, re.I) for t in toks):
                continue
            found.append((c['ticker'], c.get('date'), act, pub, title, url))
            break

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
