#!/usr/bin/env python3
"""
Stage 2 concurrent downloader for Form 4 filings.
Uses thread pool with shared token-bucket rate limiter at SEC's 10 req/sec ceiling.

Loads: form4_index_pruned.json
Saves: form4_transactions.json (ticker → list of transactions)
"""

import json
import os
import re
import sys
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

BASE = Path('/sessions/confident-serene-ptolemy/mnt/9realms')
INDEX_IN = BASE / 'form4_index_pruned.json'
TXN_OUT = BASE / 'form4_transactions.json'
LOG_OUT = BASE / 'form4_stage2.log'

HEADERS = {'User-Agent': '9Realms Research rockyshoals@gmail.com'}
MAX_WORKERS = 8
RATE_LIMIT_PER_SEC = 9.0  # stay under SEC's 10/s ceiling

_rate_lock = threading.Lock()
_last_request_time = [0.0]
_min_interval = 1.0 / RATE_LIMIT_PER_SEC

_log_lock = threading.Lock()

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    with _log_lock:
        print(line, flush=True)
        with open(LOG_OUT, 'a') as f:
            f.write(line + '\n')


def rate_limited_wait():
    with _rate_lock:
        now = time.time()
        elapsed = now - _last_request_time[0]
        if elapsed < _min_interval:
            sleep_for = _min_interval - elapsed
            time.sleep(sleep_for)
        _last_request_time[0] = time.time()


def http_get_text(url, retries=3):
    for attempt in range(retries):
        rate_limited_wait()
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == retries - 1:
                return None
            time.sleep(2 ** attempt)
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(2 ** attempt)
    return None


def parse_txn(txn_elem, derivative=False):
    out = {'derivative': derivative}

    code_elem = txn_elem.find('transactionCoding/transactionCode')
    out['transaction_code'] = code_elem.text.strip() if (code_elem is not None and code_elem.text) else ''

    date_elem = txn_elem.find('transactionDate/value')
    out['transaction_date'] = date_elem.text.strip() if (date_elem is not None and date_elem.text) else ''

    sh_elem = txn_elem.find('transactionAmounts/transactionShares/value')
    try:
        out['shares'] = float(sh_elem.text.strip()) if (sh_elem is not None and sh_elem.text) else 0.0
    except (ValueError, AttributeError):
        out['shares'] = 0.0

    price_elem = txn_elem.find('transactionAmounts/transactionPricePerShare/value')
    try:
        out['price_per_share'] = float(price_elem.text.strip()) if (price_elem is not None and price_elem.text) else 0.0
    except (ValueError, AttributeError):
        out['price_per_share'] = 0.0

    ad_elem = txn_elem.find('transactionAmounts/transactionAcquiredDisposedCode/value')
    out['acquired_disposed'] = ad_elem.text.strip() if (ad_elem is not None and ad_elem.text) else ''

    out['total_dollars'] = out['shares'] * out['price_per_share']
    return out


def parse_form4_xml(xml_text, acc, ticker, cik, filing_date):
    if not xml_text or '<ownershipDocument' not in xml_text:
        return []
    try:
        xml_text = xml_text.lstrip('\ufeff \n\r\t')
        start = xml_text.find('<ownershipDocument')
        end = xml_text.find('</ownershipDocument>')
        if start == -1 or end == -1:
            return []
        xml_clip = xml_text[start:end + len('</ownershipDocument>')]
        root = ET.fromstring(xml_clip)
    except Exception:
        return []

    owner = root.find('reportingOwner')
    owner_name = ''
    is_director = is_officer = is_ten_percent = is_other = False
    officer_title = ''

    if owner is not None:
        n = owner.find('reportingOwnerId/rptOwnerName')
        if n is not None and n.text:
            owner_name = n.text.strip()

        rel = owner.find('reportingOwnerRelationship')
        if rel is not None:
            for field, setter in [
                ('isDirector', lambda: 'is_director'),
                ('isOfficer', lambda: 'is_officer'),
                ('isTenPercentOwner', lambda: 'is_ten_percent'),
                ('isOther', lambda: 'is_other'),
            ]:
                el = rel.find(field)
                if el is not None and el.text and el.text.strip() in ('1', 'true'):
                    if field == 'isDirector':
                        is_director = True
                    elif field == 'isOfficer':
                        is_officer = True
                    elif field == 'isTenPercentOwner':
                        is_ten_percent = True
                    else:
                        is_other = True

            ot = rel.find('officerTitle')
            if ot is not None and ot.text:
                officer_title = ot.text.strip()

    txns = []
    base_meta = {
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
    }

    nd = root.find('nonDerivativeTable')
    if nd is not None:
        for t_elem in nd.findall('nonDerivativeTransaction'):
            t = parse_txn(t_elem, derivative=False)
            t.update(base_meta)
            txns.append(t)

    d = root.find('derivativeTable')
    if d is not None:
        for t_elem in d.findall('derivativeTransaction'):
            t = parse_txn(t_elem, derivative=True)
            t.update(base_meta)
            txns.append(t)

    return txns


def download_one_filing(task):
    """task = (ticker, cik, filing_dict)"""
    ticker, cik, filing = task
    acc = filing['acc']
    acc_nodash = acc.replace('-', '')
    prim = filing['primaryDoc']
    fd = filing['filingDate']

    raw_prim = prim
    if prim.startswith('xslF345X05/'):
        raw_prim = prim.replace('xslF345X05/', '')
    elif re.match(r'^xsl[A-Za-z0-9]+/', prim):
        raw_prim = re.sub(r'^xsl[A-Za-z0-9]+/', '', prim)

    url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{raw_prim}'

    xml_text = http_get_text(url)
    if not xml_text or '<ownershipDocument' not in xml_text:
        return (ticker, [])

    txns = parse_form4_xml(xml_text, acc, ticker, cik, fd)
    return (ticker, txns)


def main():
    with open(INDEX_IN) as f:
        index = json.load(f)
    log(f'Loaded pruned index: {len(index)} tickers')

    # Resume support
    existing_txns = {}
    completed_tickers = set()
    if TXN_OUT.exists():
        try:
            with open(TXN_OUT) as f:
                existing_txns = json.load(f)
            # Only treat a ticker as completed if it has an explicit 'done' sentinel or
            # we see all its filings matched. Simplest: check if we saved at all.
            completed_tickers = set(existing_txns.keys())
            log(f'Resuming: {len(completed_tickers)} tickers already saved')
        except json.JSONDecodeError:
            log('Corrupted checkpoint, starting fresh')
            existing_txns = {}

    # Build task list
    tasks = []
    total_filings = 0
    for tk, entry in index.items():
        if tk in completed_tickers:
            continue
        cik = entry.get('cik', 0)
        filings = entry.get('filings', [])
        total_filings += len(filings)
        for fg in filings:
            tasks.append((tk, cik, fg))

    log(f'Total filings to download: {total_filings:,} across {len(index) - len(completed_tickers)} pending tickers')
    log(f'Starting thread pool: {MAX_WORKERS} workers, rate limit {RATE_LIMIT_PER_SEC} req/s')

    # Group results by ticker
    ticker_txns = {tk: [] for tk in index.keys() if tk not in completed_tickers}
    completed = 0
    start_time = time.time()
    last_save = start_time

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(download_one_filing, t): t for t in tasks}
        for fut in as_completed(futures):
            try:
                ticker, txns = fut.result()
                ticker_txns[ticker].extend(txns)
                completed += 1
            except Exception as e:
                completed += 1
                continue

            # progress log every 500
            if completed % 500 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta_s = (total_filings - completed) / rate if rate > 0 else 0
                log(f'  {completed:,}/{total_filings:,} filings ({100*completed/total_filings:.1f}%) rate={rate:.1f}/s ETA={eta_s/60:.1f}min')

            # checkpoint every 60 seconds
            if time.time() - last_save > 60:
                # Merge ticker_txns into existing_txns, save
                save_data = {**existing_txns, **{tk: v for tk, v in ticker_txns.items() if v or (ticker_txns[tk] is not None and len(index.get(tk, {}).get('filings', [])) == 0)}}
                with open(TXN_OUT, 'w') as f:
                    json.dump(save_data, f)
                last_save = time.time()

    # Final save
    save_data = {**existing_txns, **ticker_txns}
    with open(TXN_OUT, 'w') as f:
        json.dump(save_data, f)

    total_txns = sum(len(v) for v in save_data.values())
    log(f'Stage 2 COMPLETE: {len(save_data)} tickers, {total_txns:,} transactions saved')


if __name__ == '__main__':
    main()
