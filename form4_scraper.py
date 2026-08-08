#!/usr/bin/env python3
"""
SEC EDGAR Form 4 Scraper - Phase 1.2
Pulls Form 4 insider transaction filings for all tickers in backfill_event_index.csv
from 2015-01-01 through today.

Stage 1: Build per-CIK index of Form 4 filings (1 request per CIK)
Stage 2: Download + parse each Form 4 filing XML

Resumable. Rate-limited to 10 req/sec (SEC policy).
Output: form4_index.json (stage 1), form4_transactions.json (stage 2)
"""

import json
import os
import re
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

BASE = Path('/sessions/confident-serene-ptolemy/mnt/9realms')
TICKER_CIK_MAP = BASE / 'ticker_cik_map.json'
INDEX_OUT = BASE / 'form4_index.json'
TXN_OUT = BASE / 'form4_transactions.json'
LOG_OUT = BASE / 'form4_scraper.log'

HEADERS = {'User-Agent': '9Realms Research rockyshoals@gmail.com'}
BACKFILL_START = '2015-01-01'
SLEEP_BETWEEN = 0.11  # ~9 req/sec (safety margin under 10 req/sec SEC limit)


def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    with open(LOG_OUT, 'a') as f:
        f.write(line + '\n')


def http_get_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return None


def http_get_text(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return None


# =====================================================================
# STAGE 1: Build Form 4 filing index per CIK
# =====================================================================

def stage1_build_index(tc_map, existing=None):
    """
    For each CIK in ticker_cik_map, hit submissions API and collect
    every Form 4 filing with filingDate >= BACKFILL_START.

    Also follows `files` array (older filings) if present.
    Saves incrementally every 25 tickers.
    """
    if existing is None:
        existing = {}

    tickers = sorted(tc_map.get('matched', {}).keys())
    total = len(tickers)
    done_set = set(existing.keys())

    log(f'Stage 1: {total} tickers total, {len(done_set)} already done, {total - len(done_set)} remaining')

    for i, ticker in enumerate(tickers):
        if ticker in done_set:
            continue

        cik = tc_map['matched'][ticker]
        cik_p = str(cik).zfill(10)

        url = f'https://data.sec.gov/submissions/CIK{cik_p}.json'
        try:
            data = http_get_json(url)
        except Exception as e:
            log(f'  [{i+1}/{total}] {ticker} cik={cik_p} ERROR fetching submissions: {e}')
            existing[ticker] = {'cik': cik, 'error': str(e), 'filings': []}
            time.sleep(SLEEP_BETWEEN)
            continue

        if not data:
            log(f'  [{i+1}/{total}] {ticker} cik={cik_p} 404 or empty')
            existing[ticker] = {'cik': cik, 'error': 'not_found', 'filings': []}
            time.sleep(SLEEP_BETWEEN)
            continue

        recent = data.get('filings', {}).get('recent', {})
        form4_list = []
        forms = recent.get('form', [])
        accs = recent.get('accessionNumber', [])
        dates = recent.get('filingDate', [])
        prims = recent.get('primaryDocument', [])

        for idx, f in enumerate(forms):
            if f == '4' and dates[idx] >= BACKFILL_START:
                form4_list.append({
                    'acc': accs[idx],
                    'filingDate': dates[idx],
                    'primaryDoc': prims[idx],
                })

        # Check older filings archives
        older_files = data.get('filings', {}).get('files', [])
        for older in older_files:
            older_url = f"https://data.sec.gov/submissions/{older.get('name')}"
            try:
                older_data = http_get_json(older_url)
                time.sleep(SLEEP_BETWEEN)
            except Exception as e:
                log(f'    {ticker} older archive error: {e}')
                continue

            if not older_data:
                continue

            for idx in range(len(older_data.get('form', []))):
                form = older_data['form'][idx]
                fd = older_data['filingDate'][idx]
                if form == '4' and fd >= BACKFILL_START:
                    form4_list.append({
                        'acc': older_data['accessionNumber'][idx],
                        'filingDate': fd,
                        'primaryDoc': older_data['primaryDocument'][idx],
                    })

        existing[ticker] = {
            'cik': cik,
            'entity_name': data.get('name', ''),
            'filings': form4_list,
        }

        if (i + 1) % 25 == 0 or len(form4_list) > 0:
            log(f'  [{i+1}/{total}] {ticker} cik={cik_p} → {len(form4_list)} Form 4s')

        # checkpoint every 25
        if (i + 1) % 25 == 0:
            with open(INDEX_OUT, 'w') as fh:
                json.dump(existing, fh)

        time.sleep(SLEEP_BETWEEN)

    with open(INDEX_OUT, 'w') as fh:
        json.dump(existing, fh)

    total_filings = sum(len(v.get('filings', [])) for v in existing.values())
    log(f'Stage 1 DONE: {len(existing)} tickers, {total_filings} Form 4 filings indexed')
    return existing


# =====================================================================
# STAGE 2: Download + parse Form 4 XML
# =====================================================================

def parse_form4_xml(xml_text, acc, ticker, cik, filing_date):
    """
    Parse a Form 4 XML and return a list of transactions.
    Each transaction dict: {owner_name, is_director, is_officer, officer_title,
      is_ten_percent, is_other, transaction_code, transaction_date,
      shares, price_per_share, total_dollars, derivative (bool)}
    """
    # Form 4 XML often has no namespace or trivial ones. Try parsing raw.
    if not xml_text or '<ownershipDocument' not in xml_text:
        return []

    try:
        # strip any leading whitespace / BOM
        xml_text = xml_text.lstrip('\ufeff \n\r\t')
        # Clip to <ownershipDocument...</ownershipDocument>
        start = xml_text.find('<ownershipDocument')
        end = xml_text.find('</ownershipDocument>')
        if start == -1 or end == -1:
            return []
        xml_clip = xml_text[start:end + len('</ownershipDocument>')]
        root = ET.fromstring(xml_clip)
    except ET.ParseError:
        return []
    except Exception:
        return []

    # Reporting owner
    owner = root.find('reportingOwner')
    owner_name = ''
    is_director = False
    is_officer = False
    is_ten_percent = False
    is_other = False
    officer_title = ''

    if owner is not None:
        n = owner.find('reportingOwnerId/rptOwnerName')
        if n is not None and n.text:
            owner_name = n.text.strip()

        rel = owner.find('reportingOwnerRelationship')
        if rel is not None:
            d = rel.find('isDirector')
            if d is not None and d.text and d.text.strip() in ('1', 'true'):
                is_director = True
            o = rel.find('isOfficer')
            if o is not None and o.text and o.text.strip() in ('1', 'true'):
                is_officer = True
            t = rel.find('isTenPercentOwner')
            if t is not None and t.text and t.text.strip() in ('1', 'true'):
                is_ten_percent = True
            oth = rel.find('isOther')
            if oth is not None and oth.text and oth.text.strip() in ('1', 'true'):
                is_other = True
            ot = rel.find('officerTitle')
            if ot is not None and ot.text:
                officer_title = ot.text.strip()

    transactions = []

    # Non-derivative transactions
    nd_table = root.find('nonDerivativeTable')
    if nd_table is not None:
        for txn in nd_table.findall('nonDerivativeTransaction'):
            t = parse_txn(txn, derivative=False)
            if t:
                t.update({
                    'owner_name': owner_name,
                    'is_director': is_director,
                    'is_officer': is_officer,
                    'officer_title': officer_title,
                    'is_ten_percent': is_ten_percent,
                    'is_other': is_other,
                    'acc': acc,
                    'ticker': ticker,
                    'cik': cik,
                    'filing_date': filing_date,
                })
                transactions.append(t)

    # Derivative transactions (optional — skip for now, focus on common stock)
    # Including them for completeness
    d_table = root.find('derivativeTable')
    if d_table is not None:
        for txn in d_table.findall('derivativeTransaction'):
            t = parse_txn(txn, derivative=True)
            if t:
                t.update({
                    'owner_name': owner_name,
                    'is_director': is_director,
                    'is_officer': is_officer,
                    'officer_title': officer_title,
                    'is_ten_percent': is_ten_percent,
                    'is_other': is_other,
                    'acc': acc,
                    'ticker': ticker,
                    'cik': cik,
                    'filing_date': filing_date,
                })
                transactions.append(t)

    return transactions


def parse_txn(txn_elem, derivative=False):
    out = {'derivative': derivative}

    code_elem = txn_elem.find('transactionCoding/transactionCode')
    if code_elem is not None and code_elem.text:
        out['transaction_code'] = code_elem.text.strip()
    else:
        out['transaction_code'] = ''

    date_elem = txn_elem.find('transactionDate/value')
    if date_elem is not None and date_elem.text:
        out['transaction_date'] = date_elem.text.strip()
    else:
        out['transaction_date'] = ''

    sh_elem = txn_elem.find('transactionAmounts/transactionShares/value')
    if sh_elem is not None and sh_elem.text:
        try:
            out['shares'] = float(sh_elem.text.strip())
        except ValueError:
            out['shares'] = 0.0
    else:
        out['shares'] = 0.0

    price_elem = txn_elem.find('transactionAmounts/transactionPricePerShare/value')
    if price_elem is not None and price_elem.text:
        try:
            out['price_per_share'] = float(price_elem.text.strip())
        except ValueError:
            out['price_per_share'] = 0.0
    else:
        out['price_per_share'] = 0.0

    ad_elem = txn_elem.find('transactionAmounts/transactionAcquiredDisposedCode/value')
    if ad_elem is not None and ad_elem.text:
        out['acquired_disposed'] = ad_elem.text.strip()  # 'A' or 'D'
    else:
        out['acquired_disposed'] = ''

    out['total_dollars'] = out['shares'] * out['price_per_share']

    return out


def stage2_download_parse(index, existing_txns=None):
    """
    For each filing in the index, download the XML and parse transactions.
    Group by ticker. Save incrementally.
    """
    if existing_txns is None:
        existing_txns = {}

    all_tickers = sorted(index.keys())
    total_tickers = len(all_tickers)

    # Count total filings
    total_filings = sum(len(v.get('filings', [])) for v in index.values())
    done_tickers = set(existing_txns.keys())

    log(f'Stage 2: {total_tickers} tickers, {total_filings} total Form 4 filings')
    log(f'  {len(done_tickers)} tickers already processed')

    filings_done = 0
    for i, ticker in enumerate(all_tickers):
        if ticker in done_tickers:
            filings_done += len(index[ticker].get('filings', []))
            continue

        entry = index[ticker]
        cik = entry.get('cik', 0)
        filings = entry.get('filings', [])

        if not filings:
            existing_txns[ticker] = []
            continue

        txns_for_ticker = []
        for filing in filings:
            acc = filing['acc']
            acc_nodash = acc.replace('-', '')
            prim = filing['primaryDoc']
            fd = filing['filingDate']

            # The actual Form 4 XML is typically .xml; the primaryDoc may be xslF345X05/form4.xml
            # The raw XML sits next to it without the xsl/ prefix
            # Example: https://www.sec.gov/Archives/edgar/data/1444192/000114036126000969/xslF345X05/form4.xml
            # But the parseable XML might just be: wk-form4_XXXXXX.xml or form4.xml without the xsl prefix
            # Best approach: strip the "xslF345X05/" prefix if present
            if prim.startswith('xslF345X05/'):
                raw_prim = prim.replace('xslF345X05/', '')
            elif prim.startswith('xsl'):
                raw_prim = re.sub(r'^xsl[A-Za-z0-9]+/', '', prim)
            else:
                raw_prim = prim

            url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{raw_prim}'

            try:
                xml_text = http_get_text(url)
            except Exception as e:
                log(f'  {ticker} {acc} fetch error: {e}')
                xml_text = None

            time.sleep(SLEEP_BETWEEN)

            if not xml_text:
                continue

            # If we got back HTML (xsl styled page), try the direct form4.xml
            if '<ownershipDocument' not in xml_text:
                # Try looking for the document file listing
                # Fallback: look for .xml in the accession dir
                dir_url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&dateb=&owner=include&count=10'
                # skip fallback for speed — if no ownershipDocument, move on
                continue

            txns = parse_form4_xml(xml_text, acc, ticker, cik, fd)
            txns_for_ticker.extend(txns)
            filings_done += 1

        existing_txns[ticker] = txns_for_ticker

        if (i + 1) % 10 == 0 or len(txns_for_ticker) > 0:
            log(f'  [{i+1}/{total_tickers}] {ticker} cik={cik} → {len(txns_for_ticker)} txns from {len(filings)} filings ({filings_done}/{total_filings} filings done)')

        if (i + 1) % 10 == 0:
            with open(TXN_OUT, 'w') as fh:
                json.dump(existing_txns, fh)

    with open(TXN_OUT, 'w') as fh:
        json.dump(existing_txns, fh)

    total_txns = sum(len(v) for v in existing_txns.values())
    log(f'Stage 2 DONE: {len(existing_txns)} tickers, {total_txns} transactions parsed')


# =====================================================================
# MAIN
# =====================================================================

def main():
    if len(sys.argv) < 2:
        print('Usage: form4_scraper.py <stage1|stage2|all>')
        sys.exit(1)

    stage = sys.argv[1]

    with open(TICKER_CIK_MAP) as f:
        tc_map = json.load(f)
    log(f'Loaded ticker_cik_map: {len(tc_map.get("matched", {}))} matched tickers')

    if stage in ('stage1', 'all'):
        existing = {}
        if INDEX_OUT.exists():
            with open(INDEX_OUT) as f:
                existing = json.load(f)
            log(f'Resuming stage 1 with {len(existing)} tickers already indexed')
        stage1_build_index(tc_map, existing)

    if stage in ('stage2', 'all'):
        with open(INDEX_OUT) as f:
            index = json.load(f)
        log(f'Loaded form4_index: {len(index)} tickers')

        existing_txns = {}
        if TXN_OUT.exists():
            with open(TXN_OUT) as f:
                existing_txns = json.load(f)
            log(f'Resuming stage 2 with {len(existing_txns)} tickers already parsed')

        stage2_download_parse(index, existing_txns)


if __name__ == '__main__':
    main()
