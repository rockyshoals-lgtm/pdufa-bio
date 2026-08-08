#!/usr/bin/env python3
"""
ODIN API ENRICHMENT MODULE V4
=============================
FIXES:
- OpenFDA: Use brand_name search (not generic_name)
- ClinicalTrials.gov: Use query.term instead of query.intr
- Simplified error handling

Usage:
    python ODIN_API_ENRICHMENT_V4.py -i ODIN_PDUFA_1349_GPU_READY.csv -o ODIN_ENRICHED.csv -v
"""

import os
import re
import sys
import json
import time
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import requests
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

# ============================================================================
# LOGGING SETUP
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('ODIN')

# ============================================================================
# CONFIGURATION
# ============================================================================
CACHE_DIR = Path('.odin_cache_v4')
CACHE_DIR.mkdir(exist_ok=True)
load_dotenv()


def clean_name(name: str) -> str:
    """Clean drug/company names - remove parentheses, special chars."""
    if not name:
        return ""
    cleaned = re.sub(r'\s*\([^)]*\)', '', name)  # Remove (...)
    cleaned = re.sub(r'[^\w\s\-]', '', cleaned)   # Keep alphanumeric, space, hyphen
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


# ============================================================================
# BASE API CLIENT
# ============================================================================
class BaseAPIClient:
    def __init__(self, name: str, base_url: str, api_key: Optional[str] = None):
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'ODIN/4.0'
        
    def _cache_key(self, url: str, params: dict) -> str:
        safe_params = {k: v for k, v in params.items() if 'key' not in k.lower()}
        return hashlib.md5(f"{url}:{json.dumps(safe_params, sort_keys=True)}".encode()).hexdigest()
    
    def _get_cached(self, cache_key: str) -> Optional[dict]:
        cache_file = CACHE_DIR / f"{cache_key}.json"
        if cache_file.exists():
            if datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime) < timedelta(hours=24):
                try:
                    return json.loads(cache_file.read_text())
                except:
                    pass
        return None
    
    def _set_cached(self, cache_key: str, data: dict):
        try:
            (CACHE_DIR / f"{cache_key}.json").write_text(json.dumps(data))
        except:
            pass
    
    def _request(self, url: str, params: dict = None, cache_key: str = None) -> Optional[dict]:
        params = params or {}
        
        if cache_key:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
        
        try:
            resp = self.session.get(url, params=params, timeout=30)
            
            # Don't retry on any error - just return None
            if resp.status_code != 200:
                logger.debug(f"{self.name}: HTTP {resp.status_code}")
                return None
            
            data = resp.json()
            
            if isinstance(data, dict) and 'Error Message' in data:
                return None
            
            if cache_key and data:
                self._set_cached(cache_key, data)
            
            return data
            
        except Exception as e:
            logger.debug(f"{self.name}: {str(e)[:50]}")
            return None


# ============================================================================
# FMP CLIENT (STABLE API)
# ============================================================================
class FMPClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__('FMP', 'https://financialmodelingprep.com/stable', api_key)
        
    def get_cash_runway(self, ticker: str, cutoff_date: datetime) -> Optional[float]:
        url = f"{self.base_url}/cash-flow-statement"
        params = {'symbol': ticker, 'apikey': self.api_key, 'limit': 8}
        data = self._request(url, params, self._cache_key(url, {'symbol': ticker}))
        
        if not data or not isinstance(data, list):
            return None
        
        try:
            valid = [s for s in data if datetime.strptime(s.get('date', ''), '%Y-%m-%d') < cutoff_date]
            if not valid:
                return None
            
            latest = valid[0]
            ocf = latest.get('operatingCashFlow', 0) or 0
            cash = latest.get('cashAtEndOfPeriod', 0) or 0
            
            if ocf >= 0:
                return 120.0
            
            burn = abs(ocf) / 12
            return min(cash / burn, 120.0) if burn > 0 else None
        except:
            return None
    
    def get_key_metrics(self, ticker: str) -> Optional[dict]:
        url = f"{self.base_url}/key-metrics"
        params = {'symbol': ticker, 'apikey': self.api_key, 'limit': 1}
        data = self._request(url, params, self._cache_key(url, {'symbol': ticker}))
        return data[0] if data and isinstance(data, list) and len(data) > 0 else None


# ============================================================================
# OPENFDA CLIENT - FIXED
# ============================================================================
class OpenFDAClient(BaseAPIClient):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__('OpenFDA', 'https://api.fda.gov', api_key)
    
    def get_adverse_events_count(self, drug_name: str, months: int = 12, 
                                  cutoff_date: datetime = None) -> Optional[int]:
        """Count adverse events using medicinalproduct field (most reliable)."""
        drug_clean = clean_name(drug_name)
        if not drug_clean or len(drug_clean) < 2:
            return None
        
        if cutoff_date is None:
            cutoff_date = datetime.now()
        end_date = min(cutoff_date, datetime.now())
        start_date = end_date - timedelta(days=months * 30)
        
        url = f"{self.base_url}/drug/event.json"
        
        # Use medicinalproduct field - this is what's actually reported
        # Don't use date filter initially - it causes 500 errors
        params = {
            'search': f'patient.drug.medicinalproduct:"{drug_clean}"',
            'count': 'receivedate',
            'limit': 1000
        }
        if self.api_key:
            params['api_key'] = self.api_key
        
        cache_key = self._cache_key(url, {'drug': drug_clean, 'months': months})
        data = self._request(url, params, cache_key)
        
        if data and 'results' in data:
            # Filter by date in post-processing
            count = 0
            for r in data['results']:
                try:
                    rdate = datetime.strptime(str(r.get('time', '')), '%Y%m%d')
                    if start_date <= rdate <= end_date:
                        count += r.get('count', 0)
                except:
                    continue
            return count if count > 0 else None
        
        return None
    
    def get_warning_letters(self, company: str, years: int = 2) -> Optional[int]:
        company_clean = clean_name(company)
        if not company_clean:
            return None
            
        url = f"{self.base_url}/drug/enforcement.json"
        params = {'search': f'recalling_firm:"{company_clean}"', 'limit': 100}
        if self.api_key:
            params['api_key'] = self.api_key
        
        data = self._request(url, params, self._cache_key(url, {'company': company_clean}))
        
        if data and 'results' in data:
            cutoff = datetime.now() - timedelta(days=years * 365)
            count = sum(1 for r in data['results'] 
                       if datetime.strptime(r.get('report_date', '19000101'), '%Y%m%d') >= cutoff)
            return count
        return None


# ============================================================================
# CLINICALTRIALS.GOV CLIENT - FIXED
# ============================================================================
class ClinicalTrialsClient(BaseAPIClient):
    def __init__(self):
        super().__init__('ClinicalTrials', 'https://clinicaltrials.gov/api/v2', None)
    
    def get_trial_counts_by_phase(self, drug_name: str) -> Dict[str, int]:
        """Get trial counts by phase using filter.advanced."""
        drug_clean = clean_name(drug_name)
        if not drug_clean or len(drug_clean) < 2:
            return {'phase1': 0, 'phase2': 0, 'phase3': 0}
        
        counts = {}
        
        # Use AREA[Phase] syntax with filter.advanced
        phase_map = {
            'phase1': 'PHASE1',
            'phase2': 'PHASE2', 
            'phase3': 'PHASE3'
        }
        
        for key, api_phase in phase_map.items():
            url = f"{self.base_url}/studies"
            
            params = {
                'query.term': drug_clean,
                'filter.advanced': f'AREA[Phase]{api_phase}',
                'countTotal': 'true',
                'pageSize': 1
            }
            
            cache_key = self._cache_key(url, {'drug': drug_clean, 'phase': api_phase})
            data = self._request(url, params, cache_key)
            
            counts[key] = data.get('totalCount', 0) if data else 0
        
        return counts
    
    def count_sponsor_trials(self, sponsor: str) -> Optional[int]:
        sponsor_clean = clean_name(sponsor)
        if not sponsor_clean:
            return None
            
        url = f"{self.base_url}/studies"
        params = {
            'query.term': sponsor_clean,
            'filter.advanced': 'AREA[OverallStatus]RECRUITING',
            'countTotal': 'true',
            'pageSize': 1
        }
        
        data = self._request(url, params, self._cache_key(url, {'sponsor': sponsor_clean}))
        return data.get('totalCount', 0) if data else None


# ============================================================================
# PUBMED CLIENT
# ============================================================================
class PubMedClient(BaseAPIClient):
    def __init__(self):
        super().__init__('PubMed', 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils', None)
    
    def count_publications(self, query: str, months: int = 12, 
                           cutoff_date: datetime = None) -> Optional[int]:
        query_clean = clean_name(query)
        if not query_clean or len(query_clean) < 2:
            return None
        
        if cutoff_date is None:
            cutoff_date = datetime.now()
        end_date = min(cutoff_date, datetime.now())
        start_date = end_date - timedelta(days=months * 30)
        
        url = f"{self.base_url}/esearch.fcgi"
        params = {
            'db': 'pubmed',
            'term': query_clean,
            'datetype': 'pdat',
            'mindate': start_date.strftime('%Y/%m/%d'),
            'maxdate': end_date.strftime('%Y/%m/%d'),
            'retmode': 'json',
            'rettype': 'count'
        }
        
        data = self._request(url, params, self._cache_key(url, {'q': query_clean, 's': start_date.strftime('%Y%m%d')}))
        
        if data and 'esearchresult' in data:
            return int(data['esearchresult'].get('count', 0))
        return None


# ============================================================================
# LUNARCRUSH CLIENT
# ============================================================================
class LunarCrushClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__('LunarCrush', 'https://lunarcrush.com/api4/public', api_key)
    
    def get_social_metrics(self, ticker: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/stocks/{ticker}/v1"
        params = {'key': self.api_key}
        data = self._request(url, params, self._cache_key(url, {'ticker': ticker}))
        
        if data and 'data' in data:
            m = data['data']
            return {
                'sentiment_avg': m.get('sentiment'),
                'bullish_pct': m.get('sentiment_bullish_percent'),
                'posts_total': m.get('posts'),
                'galaxy_score': m.get('galaxy_score'),
            }
        return None


# ============================================================================
# FINBRAIN CLIENT
# ============================================================================
class FinBrainClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__('FinBrain', 'https://api.finbrain.tech/v1', api_key)
        self.session.headers['Authorization'] = f'Bearer {api_key}'
    
    def get_sentiment(self, ticker: str, days: int = 30) -> Optional[float]:
        """Get average sentiment score over N days."""
        url = f"{self.base_url}/sentiment/{ticker}"
        data = self._request(url, cache_key=self._cache_key(url, {'days': days}))
        
        if data and 'sentimentData' in data:
            scores = [d.get('score', 0) for d in data['sentimentData'][-days:]]
            return sum(scores) / len(scores) if scores else None
        return None
    
    def get_insider_activity(self, ticker: str, days: int = 90) -> Optional[float]:
        """Get net insider buy/sell activity."""
        url = f"{self.base_url}/insider/{ticker}"
        data = self._request(url, cache_key=self._cache_key(url, {'days': days}))
        
        if data and 'transactions' in data:
            net = 0
            cutoff = datetime.now() - timedelta(days=days)
            for txn in data['transactions']:
                try:
                    txn_date = datetime.strptime(txn.get('date', ''), '%Y-%m-%d')
                    if txn_date >= cutoff:
                        if txn.get('type') == 'buy':
                            net += txn.get('shares', 0)
                        elif txn.get('type') == 'sell':
                            net -= txn.get('shares', 0)
                except:
                    continue
            return net
        return None
    
    def get_analyst_consensus(self, ticker: str) -> Optional[float]:
        """Get analyst consensus rating (1-5 scale)."""
        url = f"{self.base_url}/analyst/{ticker}"
        data = self._request(url, cache_key=self._cache_key(url, {}))
        
        if data and 'consensus' in data:
            rating_map = {
                'strong_buy': 5.0, 'buy': 4.0, 'hold': 3.0,
                'sell': 2.0, 'strong_sell': 1.0
            }
            return rating_map.get(data['consensus'].lower(), 3.0)
        return None


# ============================================================================
# MAIN ENRICHMENT ENGINE
# ============================================================================
class ODINEnrichmentEngine:
    def __init__(self, verbose: bool = False):
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        self.fmp = FMPClient(os.getenv('FMP_API_KEY')) if os.getenv('FMP_API_KEY') else None
        self.finbrain = FinBrainClient(os.getenv('FINBRAIN_API_KEY')) if os.getenv('FINBRAIN_API_KEY') else None
        self.openfda = OpenFDAClient(os.getenv('OPENFDA_API_KEY'))
        self.clinicaltrials = ClinicalTrialsClient()
        self.pubmed = PubMedClient()
        self.lunarcrush = LunarCrushClient(os.getenv('LUNARCRUSH_API_KEY')) if os.getenv('LUNARCRUSH_API_KEY') else None
        
        logger.info("✅ All clients initialized")
    
    def enrich_row(self, row: dict) -> Dict[str, Any]:
        signals = {}
        
        ticker = row.get('ticker', '')
        company = row.get('company', '')
        asset = row.get('asset', '')
        
        # Parse cutoff date
        cutoff_str = row.get('data_cutoff_date') or row.get('catalyst_date', '')
        try:
            cutoff = datetime.strptime(cutoff_str, '%Y-%m-%d')
        except:
            cutoff = datetime.now() - timedelta(days=365)
        
        # FMP
        if self.fmp and ticker:
            signals['cash_runway_months'] = self.fmp.get_cash_runway(ticker, cutoff)
            metrics = self.fmp.get_key_metrics(ticker)
            if metrics:
                signals['pe_ratio'] = metrics.get('peRatio')
                signals['price_to_book'] = metrics.get('priceToBook')
        
        # FinBrain
        if self.finbrain and ticker:
            signals['sentiment_30d'] = self.finbrain.get_sentiment(ticker, 30)
            signals['insider_net_90d'] = self.finbrain.get_insider_activity(ticker, 90)
            signals['analyst_consensus'] = self.finbrain.get_analyst_consensus(ticker)
        
        # OpenFDA
        if asset:
            signals['ae_count_12m'] = self.openfda.get_adverse_events_count(asset, 12, cutoff)
            signals['warning_letters_2y'] = self.openfda.get_warning_letters(company, 2)
        
        # ClinicalTrials
        if asset:
            trials = self.clinicaltrials.get_trial_counts_by_phase(asset)
            signals['trials_phase1'] = trials.get('phase1', 0)
            signals['trials_phase2'] = trials.get('phase2', 0)
            signals['trials_phase3'] = trials.get('phase3', 0)
            if company:
                signals['sponsor_active_trials'] = self.clinicaltrials.count_sponsor_trials(company)
        
        # PubMed
        if asset:
            signals['publications_12m'] = self.pubmed.count_publications(asset, 12, cutoff)
        
        # LunarCrush
        if self.lunarcrush and ticker:
            social = self.lunarcrush.get_social_metrics(ticker)
            if social:
                signals['social_sentiment_avg'] = social.get('sentiment_avg')
                signals['social_bullish_pct'] = social.get('bullish_pct')
                signals['galaxy_score'] = social.get('galaxy_score')
        
        return signals
    
    def enrich_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        new_cols = [
            'cash_runway_months', 'pe_ratio', 'price_to_book',
            'sentiment_30d', 'insider_net_90d', 'analyst_consensus',
            'ae_count_12m', 'warning_letters_2y',
            'trials_phase1', 'trials_phase2', 'trials_phase3', 'sponsor_active_trials',
            'publications_12m',
            'social_sentiment_avg', 'social_bullish_pct', 'galaxy_score'
        ]
        
        for col in new_cols:
            if col not in df.columns:
                df[col] = None
        
        for idx, row in tqdm(df.iterrows(), total=len(df), desc='Enriching'):
            try:
                signals = self.enrich_row(row.to_dict())
                for key, value in signals.items():
                    if key in df.columns:
                        df.at[idx, key] = value
            except Exception as e:
                logger.debug(f"Row {idx}: {e}")
            
            time.sleep(0.25)
        
        return df


# ============================================================================
# CLI
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description='ODIN API Enrichment V4')
    parser.add_argument('-i', '--input', help='Input CSV')
    parser.add_argument('-o', '--output', help='Output CSV')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--check', action='store_true', help='Check APIs')
    parser.add_argument('--clear-cache', action='store_true')
    
    args = parser.parse_args()
    
    if args.clear_cache:
        import shutil
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
        CACHE_DIR.mkdir(exist_ok=True)
        print(f"✅ Cache cleared")
        return
    
    if args.check:
        print("\n🔑 API Status:")
        for name, key in [('FMP', 'FMP_API_KEY'), ('FINBRAIN', 'FINBRAIN_API_KEY'),
                          ('OPENFDA', 'OPENFDA_API_KEY'), ('LUNARCRUSH', 'LUNARCRUSH_API_KEY')]:
            status = "✅" if os.getenv(key) else "❌"
            print(f"  {status} {name}")
        print("  ✅ ClinicalTrials (no key needed)")
        print("  ✅ PubMed (no key needed)")
        
        print("\n🧪 Testing APIs...")
        
        # Test OpenFDA
        print("\n  OpenFDA test (KEYTRUDA):")
        client = OpenFDAClient(os.getenv('OPENFDA_API_KEY'))
        result = client.get_adverse_events_count('KEYTRUDA', 12, datetime.now())
        print(f"    Adverse events: {result}")
        
        # Test ClinicalTrials via client
        print("\n  ClinicalTrials test (pembrolizumab):")
        ct_client = ClinicalTrialsClient()
        result = ct_client.get_trial_counts_by_phase('pembrolizumab')
        print(f"    Phase 1: {result.get('phase1', 0)}")
        print(f"    Phase 2: {result.get('phase2', 0)}")
        print(f"    Phase 3: {result.get('phase3', 0)}")
        
        # Test sponsor trials
        print("\n  ClinicalTrials sponsor test (Merck):")
        sponsor_result = ct_client.count_sponsor_trials('Merck')
        print(f"    Recruiting trials: {sponsor_result}")
        
        return
    
    if not args.input:
        parser.print_help()
        return
    
    print(f"\n📥 Loading: {args.input}")
    df = pd.read_csv(args.input)
    print(f"   Rows: {len(df)}")
    
    engine = ODINEnrichmentEngine(verbose=args.verbose)
    df = engine.enrich_dataframe(df)
    
    output = args.output or args.input.replace('.csv', '_enriched.csv')
    df.to_csv(output, index=False)
    print(f"\n💾 Saved: {output}")
    
    print("\n📊 Summary:")
    for col in ['cash_runway_months', 'sentiment_30d', 'ae_count_12m', 'trials_phase3', 'publications_12m', 'galaxy_score']:
        if col in df.columns:
            n = df[col].notna().sum()
            print(f"   {col}: {n}/{len(df)} ({100*n/len(df):.1f}%)")


if __name__ == '__main__':
    main()
