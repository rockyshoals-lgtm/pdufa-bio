#!/usr/bin/env python3
"""
Smart Money Backfill Pipeline v1.0
===================================

Phase 1: Fetch 13F-HR filings for 10 god tier biotech funds (2020-2026)
Phase 2: Parse infotable.xml → (issuer_name, value, shares)
Phase 3: Match issuer_name → ticker via fuzzy name match against ODIN company universe

Output: smart_money_13f_cache.json
Structure:
{
  "funds": { cik: {name, weight, filings: [{date, period, n_holdings, total_value}]} },
  "holdings": [ {cik, date, period, ticker, issuer_name, value_usd, shares} ],
  "methodology": {...}
}

Rate limited to 10 req/sec with User-Agent (SEC EDGAR requirement).
Caches all raw XML so reruns don't re-hit EDGAR.
"""

import json
import os
import re
import time
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
import requests
import pandas as pd
from datetime import datetime

# ---------- Configuration ----------

WORKDIR = Path("/sessions/confident-serene-ptolemy/mnt/9realms")
CACHE_DIR = WORKDIR / "smart_money_cache"
CACHE_DIR.mkdir(exist_ok=True)

UA = "9realms-research rockyshoals@gmail.com"
HEADERS = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
SEC_RATE_DELAY = 0.11  # ~9 req/sec, safe margin under 10/sec limit

# 10 God Tier funds (CIKs VERIFIED Apr 20 2026 via EDGAR submissions API)
# Prior CLAUDE.md CIKs for Avoro/RTW/EcoR1/BVF/Redmile/Cormorant were WRONG (matched to
# unrelated Armbrust Inc., Regional Index, UNSOCIAL, Fairholme, Matthew DeVries,
# and RTW-as-Cormorant respectively). All 10 now verified.
GOD_TIER_FUNDS = {
    "0001346824": {"name": "RA Capital Management",          "weight": 1.00},
    "0001263508": {"name": "Baker Bros. Advisors",            "weight": 1.00},
    "0001224962": {"name": "Perceptive Advisors",             "weight": 0.90},
    "0001055951": {"name": "OrbiMed Advisors",                "weight": 0.85},
    "0001633313": {"name": "Avoro Capital Advisors",          "weight": 0.85},  # was 0001826050 (Armbrust)
    "0001493215": {"name": "RTW Investments",                 "weight": 0.85},  # was 0001739608 (Regional Index) — also was mislabeled "Cormorant"
    "0001587114": {"name": "EcoR1 Capital",                   "weight": 0.75},  # was 0001503183 (UNSOCIAL)
    "0001056807": {"name": "BVF Inc",                         "weight": 0.75},  # was 0001056831 (Fairholme)
    "0001425738": {"name": "Redmile Group",                   "weight": 0.65},  # was 0001378666 (DeVries)
    "0001583977": {"name": "Cormorant Asset Management",      "weight": 0.65},  # was 0001493215 (which is actually RTW)
}

START_DATE = "2019-10-01"  # Need Q3 2019 13F (filed Nov 2019) to cover Jan 2020 events
END_DATE = "2026-04-30"

# ---------- HTTP helpers ----------

_last_req = [0.0]
def polite_get(url, timeout=20):
    """Rate-limited GET against SEC EDGAR."""
    elapsed = time.time() - _last_req[0]
    if elapsed < SEC_RATE_DELAY:
        time.sleep(SEC_RATE_DELAY - elapsed)
    _last_req[0] = time.time()
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    return r

# ---------- Submissions API ----------

def get_submissions(cik):
    """Get all filings for a CIK (recent + older archives)."""
    cik_padded = cik.lstrip("0").zfill(10)
    cache_file = CACHE_DIR / f"submissions_CIK{cik_padded}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)
    url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    r = polite_get(url)
    if r.status_code != 200:
        print(f"  ERR: submissions {cik} -> {r.status_code}")
        return None
    j = r.json()
    with open(cache_file, "w") as f:
        json.dump(j, f)
    return j

def get_older_submissions(cik, archive_name):
    """Fetch older submissions archive (pre-1000-filings)."""
    cik_padded = cik.lstrip("0").zfill(10)
    cache_file = CACHE_DIR / f"submissions_CIK{cik_padded}_{archive_name}"
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)
    url = f"https://data.sec.gov/submissions/{archive_name}"
    r = polite_get(url)
    if r.status_code != 200:
        return None
    j = r.json()
    with open(cache_file, "w") as f:
        json.dump(j, f)
    return j

def collect_13f_filings(cik, start_date, end_date):
    """Return list of {accession, date, period} for 13F-HR within window."""
    sub = get_submissions(cik)
    if not sub:
        return []
    rows = []
    def extract(rec):
        forms = rec.get("form", [])
        dates = rec.get("filingDate", [])
        accs = rec.get("accessionNumber", [])
        periods = rec.get("reportDate", [])
        for i, f in enumerate(forms):
            if f == "13F-HR":
                if start_date <= dates[i] <= end_date:
                    rows.append({
                        "accession": accs[i],
                        "filing_date": dates[i],
                        "period": periods[i] if i < len(periods) else "",
                    })
    # Recent
    extract(sub.get("filings", {}).get("recent", {}))
    # Older archives
    for older_file in sub.get("filings", {}).get("files", []):
        j = get_older_submissions(cik, older_file["name"])
        if j:
            # Older files have flat structure
            extract(j)
    return rows

# ---------- 13F Infotable parsing ----------

NS = "{http://www.sec.gov/edgar/document/thirteenf/informationtable}"

def fetch_infotable(cik, accession):
    """Fetch infotable.xml for a filing (with disk cache)."""
    cik_stripped = cik.lstrip("0")
    acc_nodash = accession.replace("-", "")
    cache_file = CACHE_DIR / f"infotable_{cik_stripped}_{acc_nodash}.xml"
    if cache_file.exists():
        return cache_file.read_text()
    # Try standard path
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_stripped}/{acc_nodash}/infotable.xml"
    r = polite_get(url)
    if r.status_code == 200 and len(r.text) > 500:
        cache_file.write_text(r.text)
        return r.text
    # Fallback: list the index and hunt for an XML containing "infoTable"
    idx_url = f"https://www.sec.gov/Archives/edgar/data/{cik_stripped}/{acc_nodash}/index.json"
    r = polite_get(idx_url)
    if r.status_code != 200:
        return None
    idx = r.json()
    for item in idx.get("directory", {}).get("item", []):
        name = item["name"]
        if name.endswith(".xml") and "primary_doc" not in name.lower():
            # Try this XML
            url2 = f"https://www.sec.gov/Archives/edgar/data/{cik_stripped}/{acc_nodash}/{name}"
            r2 = polite_get(url2)
            # Match infoTable with OR without namespace prefix (case-insensitive)
            if r2.status_code == 200 and ("infotable" in r2.text.lower() or "informationtable" in r2.text.lower()):
                cache_file.write_text(r2.text)
                return r2.text
    return None

def parse_infotable(xml_text):
    """Parse 13F infotable.xml -> list of {issuer, cusip, value, shares}."""
    holdings = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return holdings
    for info in root.findall(f"{NS}infoTable"):
        issuer = info.findtext(f"{NS}nameOfIssuer", "")
        cusip = info.findtext(f"{NS}cusip", "")
        value = info.findtext(f"{NS}value", "0")
        shrs_node = info.find(f"{NS}shrsOrPrnAmt")
        shares = shrs_node.findtext(f"{NS}sshPrnamt", "0") if shrs_node is not None else "0"
        shrs_type = shrs_node.findtext(f"{NS}sshPrnamtType", "") if shrs_node is not None else ""
        try:
            value_usd = float(value)
            # 13F value field convention: amounts may be in $000 (pre-2023) or whole $ (post-2023).
            # Per SEC: reports after ~2023-01 use whole dollars. Before that, thousands.
            # We'll normalize on write based on period date.
            shares_n = float(shares)
        except ValueError:
            continue
        holdings.append({
            "issuer_name": issuer,
            "cusip": cusip,
            "value_raw": value_usd,
            "shares": shares_n,
            "shares_type": shrs_type,
        })
    return holdings

# ---------- Issuer name -> ticker matching ----------

def normalize_name(name):
    """Normalize company name for fuzzy matching."""
    n = name.lower()
    # Remove punctuation
    n = re.sub(r"[,./\\&']", " ", n)
    # Remove common suffixes
    suffixes = [
        "pharmaceuticals", "pharmaceutical", "therapeutics", "therapeutic",
        "biosciences", "bioscience", "biotechnology", "biotech",
        "incorporated", "inc", "corp", "corporation",
        "limited", "ltd", "co", "company", "holdings", "holding",
        "plc", "sa", "nv", "ag", "ab", "bv", "pte",
        "class a", "class b", "class c",
        "common stock", "ordinary shares", "common shares",
        "sponsored ads", "ads", "adr", "adrs",
        "com",
    ]
    tokens = n.split()
    # Drop suffix tokens from the end
    while tokens and tokens[-1] in suffixes:
        tokens.pop()
    # Remove generic words anywhere
    filler = {"inc", "corp", "ltd", "co", "corporation", "incorporated", "holdings", "holding"}
    tokens = [t for t in tokens if t not in filler]
    return " ".join(tokens).strip()

def build_name_map(odin_csv):
    """Build normalized_name -> ticker map from ODIN CSV."""
    df = pd.read_csv(odin_csv)
    pairs = df[["ticker", "company"]].drop_duplicates()
    name_to_ticker = {}
    for _, row in pairs.iterrows():
        if pd.isna(row["company"]) or pd.isna(row["ticker"]):
            continue
        norm = normalize_name(row["company"])
        if norm:
            # Prefer shorter ticker (common stock) on collision
            if norm not in name_to_ticker or len(row["ticker"]) < len(name_to_ticker[norm]):
                name_to_ticker[norm] = row["ticker"]
    return name_to_ticker

def match_issuer(issuer_name, name_to_ticker):
    """Return matching ticker or None."""
    norm = normalize_name(issuer_name)
    if norm in name_to_ticker:
        return name_to_ticker[norm]
    # Try first-2-tokens match
    tokens = norm.split()
    if len(tokens) >= 2:
        key2 = " ".join(tokens[:2])
        if key2 in name_to_ticker:
            return name_to_ticker[key2]
    # Try first-token match (dangerous but biotech names are distinctive)
    if len(tokens) >= 1:
        key1 = tokens[0]
        if len(key1) >= 5 and key1 in name_to_ticker:
            return name_to_ticker[key1]
    return None

# ---------- Main pipeline ----------

def main():
    print("=" * 70)
    print("SMART MONEY BACKFILL v1.0 — Phase 1: 13F-HR for 10 God Tier Funds")
    print("=" * 70)
    print(f"Window: {START_DATE} to {END_DATE}")
    print(f"Funds: {len(GOD_TIER_FUNDS)}")
    print()

    # Build ticker matching table
    print("Building ticker match table from ODIN CSV...")
    name_to_ticker = build_name_map(WORKDIR / "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv")
    print(f"  {len(name_to_ticker)} normalized company names mapped to tickers")
    print()

    # Discover filings
    all_filings = {}  # cik -> [filings]
    total_f = 0
    for cik, info in GOD_TIER_FUNDS.items():
        filings = collect_13f_filings(cik, START_DATE, END_DATE)
        all_filings[cik] = filings
        total_f += len(filings)
        print(f"  {info['name']:40s} ({cik}): {len(filings):3d} 13F-HR filings")
    print(f"\n  Total filings to fetch: {total_f}")
    print()

    # Fetch + parse infotables
    print("Fetching and parsing infotables...")
    holdings_rows = []
    fund_summaries = {}
    matched_count = 0
    unmatched_issuers = {}  # issuer_name -> count
    for cik, info in GOD_TIER_FUNDS.items():
        filings = all_filings[cik]
        fund_summaries[cik] = {
            "name": info["name"],
            "weight": info["weight"],
            "filings": [],
        }
        print(f"\n  {info['name']}: {len(filings)} filings")
        for i, f in enumerate(filings):
            xml = fetch_infotable(cik, f["accession"])
            if xml is None:
                print(f"    [{i+1:2d}/{len(filings)}] {f['filing_date']} — FAILED fetch")
                continue
            holdings = parse_infotable(xml)
            if not holdings:
                print(f"    [{i+1:2d}/{len(filings)}] {f['filing_date']} — no holdings parsed")
                continue
            # Determine units: SEC amended Rule 13f-1 — filings made on/after 2023-01-03
            # use whole dollars; prior filings (including Q4 2022 period) in $000.
            # Use FILING date, not period date. Some filers kept $000 past the rule
            # change — auto-detect via median position size.
            period = f.get("period") or f["filing_date"]
            multiplier = 1000.0 if f["filing_date"] < "2023-01-03" else 1.0
            if multiplier == 1.0 and holdings:
                vals = sorted(h["value_raw"] for h in holdings if h["value_raw"] > 0)
                if vals:
                    median_val = vals[len(vals) // 2]
                    # Median position < $100K across 30+ holdings for a god tier
                    # fund is implausible; re-interpret as $000.
                    if median_val < 100_000 and len(vals) >= 20:
                        multiplier = 1000.0
            total_value_file = 0.0
            matched_this_file = 0
            for h in holdings:
                value_usd = h["value_raw"] * multiplier
                total_value_file += value_usd
                ticker = match_issuer(h["issuer_name"], name_to_ticker)
                if ticker:
                    matched_this_file += 1
                    matched_count += 1
                    holdings_rows.append({
                        "cik": cik,
                        "fund_name": info["name"],
                        "filing_date": f["filing_date"],
                        "period": period,
                        "ticker": ticker,
                        "issuer_name": h["issuer_name"],
                        "value_usd": value_usd,
                        "shares": h["shares"],
                    })
                else:
                    unmatched_issuers[h["issuer_name"]] = unmatched_issuers.get(h["issuer_name"], 0) + 1
            fund_summaries[cik]["filings"].append({
                "filing_date": f["filing_date"],
                "period": period,
                "accession": f["accession"],
                "n_holdings": len(holdings),
                "total_value_usd": total_value_file,
                "matched_biotechs": matched_this_file,
            })
            sys.stdout.write(f"    [{i+1:2d}/{len(filings)}] {f['filing_date']} period={period}: "
                             f"{len(holdings):4d} holdings, ${total_value_file/1e9:6.2f}B, "
                             f"{matched_this_file:3d} biotech matches\n")

    # Save results
    out_cache = {
        "methodology": {
            "version": "smart_money_backfill_v1.0",
            "date_window": [START_DATE, END_DATE],
            "god_tier_funds": GOD_TIER_FUNDS,
            "total_filings_fetched": sum(len(f["filings"]) for f in fund_summaries.values()),
            "total_holdings_rows": len(holdings_rows),
            "matched_biotech_holdings": matched_count,
            "unmatched_issuers_sampled": sorted(unmatched_issuers.items(), key=lambda x: -x[1])[:30],
            "units_convention": "pre-2023 13F values in $000; post-2023 in whole $; normalized to whole $ here",
        },
        "funds": fund_summaries,
        "holdings": holdings_rows,
    }
    out_path = WORKDIR / "smart_money_13f_cache.json"
    with open(out_path, "w") as f:
        json.dump(out_cache, f, default=str)
    print()
    print("=" * 70)
    print(f"DONE. Saved {out_path}")
    print(f"  {out_cache['methodology']['total_filings_fetched']} filings fetched")
    print(f"  {len(holdings_rows)} biotech holdings matched")
    print(f"  {len(unmatched_issuers)} unique unmatched issuers")
    print(f"  File size: {out_path.stat().st_size / 1e6:.1f} MB")
    print("=" * 70)

if __name__ == "__main__":
    main()
