#!/usr/bin/env python3
"""
ODIN API ENRICHMENT MODULE — T-1 Compliant Signal Generation
==============================================================
Fetches external data to create new predictive signals for ODIN.

SETUP:
1. Create a .env file in the same directory with your API keys:
   FINBRAIN_API_KEY=your_key
   FMP_API_KEY=your_key
   LUNARCRUSH_API_KEY=your_key
   OPENFDA_API_KEY=your_key

2. Install dependencies:
   pip install requests python-dotenv tqdm pandas

3. Run:
   python ODIN_API_ENRICHMENT_MODULE.py --check-apis
   python ODIN_API_ENRICHMENT_MODULE.py -i ODIN_PDUFA_1349_GPU_READY.csv -o ODIN_PDUFA_ENRICHED.csv -v

Author: ODIN Team
Last Updated: 2026-01-21
"""

from __future__ import annotations

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import requests

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables only.")
    print("   Install with: pip install python-dotenv")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class APIConfig:
    """API configuration loaded from environment variables."""
    
    # Paid APIs
    finbrain_key: str = field(default_factory=lambda: os.getenv("FINBRAIN_API_KEY", ""))
    fmp_key: str = field(default_factory=lambda: os.getenv("FMP_API_KEY", ""))
    lunarcrush_key: str = field(default_factory=lambda: os.getenv("LUNARCRUSH_API_KEY", ""))
    
    # Free Government APIs (optional keys for higher rate limits)
    openfda_key: str = field(default_factory=lambda: os.getenv("OPENFDA_API_KEY", ""))
    patentsview_key: str = field(default_factory=lambda: os.getenv("PATENTSVIEW_API_KEY", ""))
    
    # Base URLs
    finbrain_base: str = "https://api.finbrain.tech/v1"
    fmp_base: str = "https://financialmodelingprep.com/api/v3"
    openfda_base: str = "https://api.fda.gov"
    clinicaltrials_base: str = "https://clinicaltrials.gov/api/v2"
    pubmed_base: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    lunarcrush_base: str = "https://lunarcrush.com/api4/public"
    
    # Cache settings
    cache_dir: Path = field(default_factory=lambda: Path("./odin_api_cache"))
    cache_ttl_hours: int = 24 * 7  # 1 week cache
    
    def __post_init__(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def validate(self) -> Dict[str, bool]:
        """Check which APIs are configured."""
        return {
            "finbrain": bool(self.finbrain_key),
            "fmp": bool(self.fmp_key),
            "lunarcrush": bool(self.lunarcrush_key),
            "openfda": True,  # Works without key
            "clinicaltrials": True,  # Free, no key
            "pubmed": True,  # Free, no key
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CACHING LAYER
# ═══════════════════════════════════════════════════════════════════════════════

class APICache:
    """File-based cache for API responses to avoid repeated calls."""
    
    def __init__(self, cache_dir: Path, ttl_hours: int = 168):
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _hash_key(self, key: str) -> str:
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve from cache if not expired."""
        path = self.cache_dir / f"{self._hash_key(key)}.json"
        if not path.exists():
            return None
        
        try:
            with open(path, "r") as f:
                data = json.load(f)
            
            cached_at = datetime.fromisoformat(data["_cached_at"])
            if datetime.now() - cached_at > self.ttl:
                return None  # Expired
            
            return data["payload"]
        except Exception:
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Store in cache with timestamp."""
        path = self.cache_dir / f"{self._hash_key(key)}.json"
        data = {
            "_cached_at": datetime.now().isoformat(),
            "_key": key,
            "payload": value
        }
        with open(path, "w") as f:
            json.dump(data, f)


# ═══════════════════════════════════════════════════════════════════════════════
# BASE API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class BaseAPIClient:
    """Base class with retry logic and rate limiting."""
    
    def __init__(self, config: APIConfig, cache: APICache):
        self.config = config
        self.cache = cache
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _request(
        self, 
        url: str, 
        headers: Optional[Dict] = None, 
        params: Optional[Dict] = None,
        max_retries: int = 3,
        cache_key: Optional[str] = None
    ) -> Optional[Dict]:
        """Make HTTP request with caching and retry."""
        
        # Check cache first
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self.logger.debug(f"Cache hit: {cache_key}")
                return cached
        
        # Make request with retries
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                
                if resp.status_code == 429:  # Rate limited
                    wait = 2 ** attempt
                    self.logger.warning(f"Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                
                if resp.status_code == 404:
                    return None
                    
                resp.raise_for_status()
                data = resp.json()
                
                # Cache successful response
                if cache_key:
                    self.cache.set(cache_key, data)
                
                return data
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt+1}): {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2 ** attempt)
        
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# FINBRAIN CLIENT — Sentiment, Insider Trading, Analyst Ratings
# ═══════════════════════════════════════════════════════════════════════════════

class FinBrainClient(BaseAPIClient):
    """FinBrain API client for sentiment, insider trading, analyst ratings."""
    
    def get_sentiment(self, ticker: str, before_date: str) -> Optional[float]:
        """Get average sentiment score in the 30 days before the date."""
        if not self.config.finbrain_key:
            return None
            
        cache_key = f"finbrain_sentiment_{ticker}_{before_date}"
        url = f"{self.config.finbrain_base}/sentiments/US/{ticker}"
        headers = {"Authorization": f"Bearer {self.config.finbrain_key}"}
        
        data = self._request(url, headers=headers, cache_key=cache_key)
        if not data or "sentimentData" not in data:
            return None
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        lookback = cutoff - timedelta(days=30)
        
        scores = []
        for entry in data.get("sentimentData", []):
            try:
                entry_date = datetime.strptime(entry["date"], "%Y-%m-%d")
                if lookback <= entry_date < cutoff:
                    scores.append(float(entry["score"]))
            except (KeyError, ValueError):
                continue
        
        return sum(scores) / len(scores) if scores else None
    
    def get_insider_net_activity(self, ticker: str, before_date: str) -> Optional[float]:
        """Get net insider buying/selling in past 90 days."""
        if not self.config.finbrain_key:
            return None
            
        cache_key = f"finbrain_insider_{ticker}_{before_date}"
        url = f"{self.config.finbrain_base}/insider-transactions/{ticker}"
        headers = {"Authorization": f"Bearer {self.config.finbrain_key}"}
        
        data = self._request(url, headers=headers, cache_key=cache_key)
        if not data:
            return None
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        lookback = cutoff - timedelta(days=90)
        
        net_shares = 0
        for txn in data.get("transactions", []):
            try:
                txn_date = datetime.strptime(txn["date"], "%Y-%m-%d")
                if lookback <= txn_date < cutoff:
                    shares = float(txn.get("shares", 0))
                    if txn.get("type", "").lower() in ("buy", "purchase"):
                        net_shares += shares
                    elif txn.get("type", "").lower() in ("sell", "sale"):
                        net_shares -= shares
            except (KeyError, ValueError):
                continue
        
        return net_shares
    
    def get_analyst_consensus(self, ticker: str, before_date: str) -> Optional[float]:
        """Get analyst rating consensus score (0-1 scale)."""
        if not self.config.finbrain_key:
            return None
            
        cache_key = f"finbrain_analyst_{ticker}_{before_date}"
        url = f"{self.config.finbrain_base}/analyst-ratings/US/{ticker}"
        headers = {"Authorization": f"Bearer {self.config.finbrain_key}"}
        
        data = self._request(url, headers=headers, cache_key=cache_key)
        if not data:
            return None
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        lookback = cutoff - timedelta(days=180)
        
        signal_map = {
            "strong buy": 1.0, "buy": 0.8, "outperform": 0.7,
            "hold": 0.5, "neutral": 0.5,
            "underperform": 0.3, "sell": 0.2, "strong sell": 0.0
        }
        
        scores = []
        for rating in data.get("ratings", []):
            try:
                rating_date = datetime.strptime(rating["date"], "%Y-%m-%d")
                if lookback <= rating_date < cutoff:
                    signal = rating.get("signal", "").lower()
                    if signal in signal_map:
                        scores.append(signal_map[signal])
            except (KeyError, ValueError):
                continue
        
        return sum(scores) / len(scores) if scores else None
    
    def get_linkedin_growth(self, ticker: str, before_date: str) -> Optional[float]:
        """Get LinkedIn employee growth rate (3-month)."""
        if not self.config.finbrain_key:
            return None
            
        cache_key = f"finbrain_linkedin_{ticker}_{before_date}"
        url = f"{self.config.finbrain_base}/linkedindata/US/{ticker}"
        headers = {"Authorization": f"Bearer {self.config.finbrain_key}"}
        
        data = self._request(url, headers=headers, cache_key=cache_key)
        if not data or "data" not in data:
            return None
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        lookback_6m = cutoff - timedelta(days=180)
        
        counts = []
        for entry in data.get("data", []):
            try:
                entry_date = datetime.strptime(entry["date"], "%Y-%m-%d")
                if lookback_6m <= entry_date < cutoff:
                    counts.append((entry_date, float(entry.get("employee_count", 0))))
            except (KeyError, ValueError):
                continue
        
        if len(counts) < 2:
            return None
        
        counts.sort(key=lambda x: x[0])
        recent = counts[-1][1]
        older = counts[0][1]
        
        if older > 0:
            return (recent - older) / older
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# OPENFDA CLIENT — Drug Safety Signals
# ═══════════════════════════════════════════════════════════════════════════════

class OpenFDAClient(BaseAPIClient):
    """OpenFDA API client for adverse events and warning letters."""
    
    def get_adverse_event_count(
        self, 
        drug_name: str, 
        before_date: str, 
        lookback_days: int = 365
    ) -> Optional[int]:
        """Get count of adverse events reported in past year."""
        cache_key = f"openfda_ae_{drug_name}_{before_date}"
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        start = cutoff - timedelta(days=lookback_days)
        
        start_str = start.strftime("%Y%m%d")
        end_str = cutoff.strftime("%Y%m%d")
        
        url = f"{self.config.openfda_base}/drug/event.json"
        params = {
            "search": f'patient.drug.medicinalproduct:"{drug_name}" AND receivedate:[{start_str} TO {end_str}]',
            "count": "receivedate"
        }
        
        if self.config.openfda_key:
            params["api_key"] = self.config.openfda_key
        
        data = self._request(url, params=params, cache_key=cache_key)
        if not data or "results" not in data:
            return None
        
        total = sum(r.get("count", 0) for r in data["results"])
        return total
    
    def get_warning_letter_count(
        self, 
        company_name: str, 
        before_date: str,
        lookback_days: int = 730
    ) -> Optional[int]:
        """Get count of FDA warning letters to company."""
        cache_key = f"openfda_warning_{company_name}_{before_date}"
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        start = cutoff - timedelta(days=lookback_days)
        
        url = f"{self.config.openfda_base}/device/enforcement.json"
        params = {
            "search": f'firm_name:"{company_name}"',
            "limit": 100
        }
        
        if self.config.openfda_key:
            params["api_key"] = self.config.openfda_key
        
        data = self._request(url, params=params, cache_key=cache_key)
        if not data or "results" not in data:
            return 0
        
        count = 0
        for result in data.get("results", []):
            try:
                report_date = result.get("report_date", "")
                if report_date:
                    rd = datetime.strptime(report_date, "%Y%m%d")
                    if start <= rd < cutoff:
                        count += 1
            except (ValueError, KeyError):
                continue
        
        return count


# ═══════════════════════════════════════════════════════════════════════════════
# CLINICALTRIALS.GOV CLIENT — Trial Pipeline Signals
# ═══════════════════════════════════════════════════════════════════════════════

class ClinicalTrialsClient(BaseAPIClient):
    """ClinicalTrials.gov API client for trial counts."""
    
    def get_sponsor_trial_count(
        self, 
        sponsor: str, 
        before_date: str,
        status: str = "RECRUITING"
    ) -> Optional[int]:
        """Get count of sponsor's active trials."""
        cache_key = f"ct_sponsor_{sponsor}_{status}_{before_date}"
        
        url = f"{self.config.clinicaltrials_base}/studies"
        params = {
            "query.spons": sponsor,
            "filter.overallStatus": status,
            "pageSize": 1,
            "countTotal": "true"
        }
        
        data = self._request(url, params=params, cache_key=cache_key)
        if not data:
            return None
        
        return data.get("totalCount", 0)
    
    def get_drug_trial_count(
        self, 
        drug_name: str, 
        before_date: str
    ) -> Optional[Dict[str, int]]:
        """Get trial counts by phase for a specific drug."""
        cache_key = f"ct_drug_{drug_name}_{before_date}"
        
        url = f"{self.config.clinicaltrials_base}/studies"
        params = {
            "query.intr": drug_name,
            "pageSize": 100,
        }
        
        data = self._request(url, params=params, cache_key=cache_key)
        if not data or "studies" not in data:
            return None
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        
        phase_counts = {"1": 0, "2": 0, "3": 0, "4": 0}
        for study in data.get("studies", []):
            try:
                start_str = study.get("protocolSection", {}).get(
                    "statusModule", {}
                ).get("startDateStruct", {}).get("date", "")
                
                if start_str:
                    try:
                        start_date = datetime.strptime(start_str[:10], "%Y-%m-%d")
                    except ValueError:
                        try:
                            start_date = datetime.strptime(start_str[:7], "%Y-%m")
                        except ValueError:
                            continue
                    
                    if start_date >= cutoff:
                        continue
                
                phases = study.get("protocolSection", {}).get(
                    "designModule", {}
                ).get("phases", [])
                
                for phase in phases:
                    if "1" in phase:
                        phase_counts["1"] += 1
                    if "2" in phase:
                        phase_counts["2"] += 1
                    if "3" in phase:
                        phase_counts["3"] += 1
                    if "4" in phase:
                        phase_counts["4"] += 1
                        
            except (KeyError, ValueError):
                continue
        
        return phase_counts


# ═══════════════════════════════════════════════════════════════════════════════
# PUBMED CLIENT — Publication Signal
# ═══════════════════════════════════════════════════════════════════════════════

class PubMedClient(BaseAPIClient):
    """PubMed API client for publication counts."""
    
    def get_publication_count(
        self, 
        drug_name: str, 
        before_date: str,
        lookback_months: int = 12
    ) -> Optional[int]:
        """Get count of publications mentioning the drug."""
        cache_key = f"pubmed_{drug_name}_{before_date}"
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        start = cutoff - timedelta(days=lookback_months * 30)
        
        start_str = start.strftime("%Y/%m/%d")
        end_str = cutoff.strftime("%Y/%m/%d")
        
        url = f"{self.config.pubmed_base}/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": f'"{drug_name}"[Title/Abstract]',
            "datetype": "pdat",
            "mindate": start_str,
            "maxdate": end_str,
            "retmode": "json",
            "rettype": "count"
        }
        
        data = self._request(url, params=params, cache_key=cache_key)
        if not data or "esearchresult" not in data:
            return None
        
        return int(data["esearchresult"].get("count", 0))


# ═══════════════════════════════════════════════════════════════════════════════
# FMP CLIENT — Financial Health Signals
# ═══════════════════════════════════════════════════════════════════════════════

class FMPClient(BaseAPIClient):
    """Financial Modeling Prep API client for financial health signals."""
    
    def get_cash_runway_months(self, ticker: str, before_date: str) -> Optional[float]:
        """Estimate cash runway in months based on burn rate."""
        if not self.config.fmp_key:
            return None
            
        cache_key = f"fmp_runway_{ticker}_{before_date}"
        
        url = f"{self.config.fmp_base}/cash-flow-statement/{ticker}"
        params = {"apikey": self.config.fmp_key, "limit": 8}
        
        data = self._request(url, params=params, cache_key=cache_key)
        if not data or not isinstance(data, list) or len(data) < 1:
            return None
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        
        for report in data:
            try:
                report_date = datetime.strptime(report["date"], "%Y-%m-%d")
                if report_date < cutoff:
                    recent_cash = float(report.get("cashAtEndOfPeriod", 0))
                    recent_burn = float(report.get("netCashUsedForOperatingActivites", 0))
                    
                    if recent_cash and recent_burn and recent_burn < 0:
                        monthly_burn = abs(recent_burn) / 3
                        if monthly_burn > 0:
                            return recent_cash / monthly_burn
                    break
            except (KeyError, ValueError):
                continue
        
        return None
    
    def get_institutional_change(self, ticker: str, before_date: str) -> Optional[float]:
        """Get institutional ownership share count."""
        if not self.config.fmp_key:
            return None
            
        cache_key = f"fmp_inst_{ticker}_{before_date}"
        
        url = f"{self.config.fmp_base}/institutional-holder/{ticker}"
        params = {"apikey": self.config.fmp_key}
        
        data = self._request(url, params=params, cache_key=cache_key)
        if not data or not isinstance(data, list):
            return None
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        
        total_shares = 0
        for holder in data:
            try:
                if "dateReported" in holder:
                    report_date = datetime.strptime(holder["dateReported"], "%Y-%m-%d")
                    if report_date < cutoff:
                        total_shares += float(holder.get("shares", 0))
            except (KeyError, ValueError):
                continue
        
        return total_shares if total_shares > 0 else None


# ═══════════════════════════════════════════════════════════════════════════════
# LUNARCRUSH CLIENT — Social Sentiment & Mentions
# ═══════════════════════════════════════════════════════════════════════════════

class LunarCrushClient(BaseAPIClient):
    """LunarCrush API client for social media intelligence."""
    
    def _lc_request(
        self, 
        endpoint: str, 
        params: Optional[Dict] = None,
        cache_key: Optional[str] = None
    ) -> Optional[Dict]:
        """Make LunarCrush API request."""
        if not self.config.lunarcrush_key:
            return None
            
        url = f"{self.config.lunarcrush_base}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.config.lunarcrush_key}"}
        
        return self._request(url, headers=headers, params=params, cache_key=cache_key)
    
    def get_social_sentiment(
        self, 
        ticker: str, 
        before_date: str,
        lookback_days: int = 30
    ) -> Optional[Dict[str, float]]:
        """Get social sentiment metrics for a stock."""
        cache_key = f"lc_sentiment_{ticker}_{before_date}"
        
        # Try topic endpoint for stocks
        data = self._lc_request(
            f"topic/{ticker}/time-series",
            params={"interval": "1w"},
            cache_key=cache_key
        )
        
        if not data or "data" not in data:
            return None
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        lookback = cutoff - timedelta(days=lookback_days)
        
        sentiments = []
        bullish_counts = []
        bearish_counts = []
        
        for entry in data.get("data", []):
            try:
                ts = entry.get("time") or entry.get("timestamp") or entry.get("date")
                if isinstance(ts, (int, float)):
                    entry_date = datetime.fromtimestamp(ts)
                else:
                    entry_date = datetime.strptime(str(ts)[:10], "%Y-%m-%d")
                
                if lookback <= entry_date < cutoff:
                    sent = entry.get("sentiment") or entry.get("sentiment_score")
                    if sent is not None:
                        sentiments.append(float(sent))
                    
                    bullish = entry.get("bullish") or entry.get("sentiment_bullish") or 0
                    bearish = entry.get("bearish") or entry.get("sentiment_bearish") or 0
                    bullish_counts.append(float(bullish))
                    bearish_counts.append(float(bearish))
                    
            except (KeyError, ValueError, TypeError):
                continue
        
        if not sentiments:
            return None
        
        total_bullish = sum(bullish_counts)
        total_bearish = sum(bearish_counts)
        total_sentiment_posts = total_bullish + total_bearish
        
        return {
            "sentiment_avg": sum(sentiments) / len(sentiments),
            "bullish_pct": total_bullish / total_sentiment_posts if total_sentiment_posts > 0 else 0.5,
            "sentiment_samples": len(sentiments)
        }
    
    def get_social_volume(
        self, 
        ticker: str, 
        before_date: str,
        lookback_days: int = 30
    ) -> Optional[Dict[str, float]]:
        """Get social volume/engagement metrics."""
        cache_key = f"lc_volume_{ticker}_{before_date}"
        
        data = self._lc_request(
            f"topic/{ticker}/time-series",
            params={"interval": "1m"},
            cache_key=cache_key
        )
        
        if not data or "data" not in data:
            return None
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        lookback = cutoff - timedelta(days=lookback_days)
        
        posts = []
        interactions = []
        
        for entry in data.get("data", []):
            try:
                ts = entry.get("time") or entry.get("timestamp") or entry.get("date")
                if isinstance(ts, (int, float)):
                    entry_date = datetime.fromtimestamp(ts)
                else:
                    entry_date = datetime.strptime(str(ts)[:10], "%Y-%m-%d")
                
                if lookback <= entry_date < cutoff:
                    post_count = (
                        entry.get("posts") or 
                        entry.get("posts_active") or 
                        entry.get("social_volume") or 0
                    )
                    posts.append(float(post_count))
                    
                    interact = (
                        entry.get("interactions") or 
                        entry.get("social_engagements") or
                        entry.get("engagements") or 0
                    )
                    interactions.append(float(interact))
                        
            except (KeyError, ValueError, TypeError):
                continue
        
        if not posts:
            return None
        
        return {
            "posts_avg": sum(posts) / len(posts),
            "posts_total": sum(posts),
            "interactions_avg": sum(interactions) / len(interactions) if interactions else 0,
            "social_days_tracked": len(posts)
        }
    
    def get_galaxy_score(self, ticker: str, before_date: str) -> Optional[float]:
        """Get LunarCrush Galaxy Score (0-100 composite)."""
        cache_key = f"lc_galaxy_{ticker}_{before_date}"
        
        data = self._lc_request(f"topic/{ticker}", cache_key=cache_key)
        
        if not data or "data" not in data:
            return None
        
        # Try to get from main response
        galaxy = data.get("data", {}).get("galaxy_score")
        if galaxy:
            return float(galaxy)
        
        return None
    
    def get_social_dominance(
        self, 
        ticker: str, 
        before_date: str,
        lookback_days: int = 7
    ) -> Optional[float]:
        """Get social dominance - share of voice vs market."""
        cache_key = f"lc_dominance_{ticker}_{before_date}"
        
        data = self._lc_request(
            f"topic/{ticker}/time-series",
            params={"interval": "1w"},
            cache_key=cache_key
        )
        
        if not data or "data" not in data:
            return None
        
        cutoff = datetime.strptime(before_date, "%Y-%m-%d")
        lookback = cutoff - timedelta(days=lookback_days)
        
        dominance_values = []
        
        for entry in data.get("data", []):
            try:
                ts = entry.get("time") or entry.get("timestamp")
                if isinstance(ts, (int, float)):
                    entry_date = datetime.fromtimestamp(ts)
                else:
                    continue
                
                if lookback <= entry_date < cutoff:
                    dom = entry.get("social_dominance") or entry.get("dominance")
                    if dom is not None:
                        dominance_values.append(float(dom))
            except (ValueError, TypeError):
                continue
        
        return sum(dominance_values) / len(dominance_values) if dominance_values else None


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER ENRICHMENT ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ODINEnrichmentEngine:
    """Master orchestrator that enriches ODIN dataset with API signals."""
    
    def __init__(self, config: Optional[APIConfig] = None):
        self.config = config or APIConfig()
        self.cache = APICache(self.config.cache_dir, self.config.cache_ttl_hours)
        
        # Initialize clients
        self.finbrain = FinBrainClient(self.config, self.cache)
        self.openfda = OpenFDAClient(self.config, self.cache)
        self.clinicaltrials = ClinicalTrialsClient(self.config, self.cache)
        self.pubmed = PubMedClient(self.config, self.cache)
        self.fmp = FMPClient(self.config, self.cache)
        self.lunarcrush = LunarCrushClient(self.config, self.cache)
        
        self.logger = logging.getLogger("ODINEnrichment")
    
    def enrich_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single PDUFA event row with API signals."""
        ticker = row.get("ticker", "")
        asset = row.get("asset", "")
        company = row.get("company", ticker)
        cutoff = row.get("data_cutoff_date", "")
        
        if not cutoff:
            return {}
        
        signals = {}
        
        # Extract drug name from asset
        drug_name = asset.split("(")[0].strip() if "(" in asset else asset
        
        # ═══════════════════════════════════════════════════════════════════
        # FINBRAIN SIGNALS
        # ═══════════════════════════════════════════════════════════════════
        if self.config.finbrain_key:
            signals["sentiment_30d"] = self.finbrain.get_sentiment(ticker, cutoff)
            signals["insider_net_90d"] = self.finbrain.get_insider_net_activity(ticker, cutoff)
            signals["analyst_consensus"] = self.finbrain.get_analyst_consensus(ticker, cutoff)
            signals["linkedin_growth_3m"] = self.finbrain.get_linkedin_growth(ticker, cutoff)
        
        # ═══════════════════════════════════════════════════════════════════
        # FDA SIGNALS
        # ═══════════════════════════════════════════════════════════════════
        signals["ae_count_12m"] = self.openfda.get_adverse_event_count(drug_name, cutoff)
        signals["warning_letters_2y"] = self.openfda.get_warning_letter_count(company, cutoff)
        
        # ═══════════════════════════════════════════════════════════════════
        # CLINICAL TRIALS SIGNALS
        # ═══════════════════════════════════════════════════════════════════
        signals["sponsor_active_trials"] = self.clinicaltrials.get_sponsor_trial_count(
            company, cutoff, "RECRUITING"
        )
        
        trial_phases = self.clinicaltrials.get_drug_trial_count(drug_name, cutoff)
        if trial_phases:
            signals["drug_trials_p1"] = trial_phases.get("1", 0)
            signals["drug_trials_p2"] = trial_phases.get("2", 0)
            signals["drug_trials_p3"] = trial_phases.get("3", 0)
        
        # ═══════════════════════════════════════════════════════════════════
        # PUBMED SIGNALS
        # ═══════════════════════════════════════════════════════════════════
        signals["publications_12m"] = self.pubmed.get_publication_count(drug_name, cutoff)
        
        # ═══════════════════════════════════════════════════════════════════
        # FMP FINANCIAL SIGNALS
        # ═══════════════════════════════════════════════════════════════════
        if self.config.fmp_key:
            signals["cash_runway_months"] = self.fmp.get_cash_runway_months(ticker, cutoff)
            signals["institutional_shares"] = self.fmp.get_institutional_change(ticker, cutoff)
        
        # ═══════════════════════════════════════════════════════════════════
        # LUNARCRUSH SOCIAL SIGNALS
        # ═══════════════════════════════════════════════════════════════════
        if self.config.lunarcrush_key:
            social_sentiment = self.lunarcrush.get_social_sentiment(ticker, cutoff)
            if social_sentiment:
                signals["social_sentiment_avg"] = social_sentiment.get("sentiment_avg")
                signals["social_bullish_pct"] = social_sentiment.get("bullish_pct")
            
            social_volume = self.lunarcrush.get_social_volume(ticker, cutoff)
            if social_volume:
                signals["social_posts_avg"] = social_volume.get("posts_avg")
                signals["social_posts_total"] = social_volume.get("posts_total")
                signals["social_interactions_avg"] = social_volume.get("interactions_avg")
            
            signals["galaxy_score"] = self.lunarcrush.get_galaxy_score(ticker, cutoff)
            signals["social_dominance"] = self.lunarcrush.get_social_dominance(ticker, cutoff)
        
        return signals
    
    def enrich_dataframe(self, df, progress: bool = True):
        """Enrich entire DataFrame with API signals."""
        try:
            from tqdm import tqdm
            has_tqdm = True
        except ImportError:
            has_tqdm = False
            print("⚠️  tqdm not installed. Install with: pip install tqdm")
        
        # Define new columns
        new_cols = [
            # FinBrain signals
            "sentiment_30d", "insider_net_90d", "analyst_consensus", "linkedin_growth_3m",
            # FDA signals
            "ae_count_12m", "warning_letters_2y",
            # Clinical trials signals
            "sponsor_active_trials", "drug_trials_p1", "drug_trials_p2", "drug_trials_p3",
            # PubMed signals
            "publications_12m",
            # FMP financial signals
            "cash_runway_months", "institutional_shares",
            # LunarCrush social signals
            "social_sentiment_avg", "social_bullish_pct",
            "social_posts_avg", "social_posts_total", "social_interactions_avg",
            "galaxy_score", "social_dominance"
        ]
        
        for col in new_cols:
            df[col] = None
        
        if progress and has_tqdm:
            iterator = tqdm(df.iterrows(), total=len(df), desc="Enriching")
        else:
            iterator = df.iterrows()
            if progress:
                print(f"Processing {len(df)} rows...")
        
        for idx, row in iterator:
            signals = self.enrich_row(row.to_dict())
            for col, val in signals.items():
                if col in df.columns:
                    df.at[idx, col] = val
        
        return df


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Command-line interface for enrichment."""
    import argparse
    import pandas as pd
    
    parser = argparse.ArgumentParser(
        description="ODIN API Enrichment Module - Add external signals to PDUFA dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ODIN_API_ENRICHMENT_MODULE.py --check-apis
  python ODIN_API_ENRICHMENT_MODULE.py -i ODIN_PDUFA_1349_GPU_READY.csv -o ODIN_ENRICHED.csv -v
        """
    )
    parser.add_argument("--input", "-i", help="Input CSV path")
    parser.add_argument("--output", "-o", help="Output CSV path")
    parser.add_argument("--check-apis", action="store_true", help="Check API configuration")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level, 
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Initialize config
    config = APIConfig()
    
    if args.check_apis:
        print("\n" + "="*50)
        print("🔑 ODIN API CONFIGURATION STATUS")
        print("="*50)
        
        status = config.validate()
        for api, is_configured in status.items():
            emoji = "✅" if is_configured else "❌"
            key_status = "configured" if is_configured else "NOT SET"
            print(f"  {emoji} {api.upper():15} {key_status}")
        
        print("="*50)
        
        # Show specific guidance
        missing = [k for k, v in status.items() if not v]
        if missing:
            print("\n⚠️  Missing API keys. Add them to your .env file:")
            print("   FINBRAIN_API_KEY=your_key")
            print("   FMP_API_KEY=your_key")
            print("   LUNARCRUSH_API_KEY=your_key")
        else:
            print("\n✅ All APIs configured! Ready to enrich.")
        
        print(f"\n📁 Cache directory: {config.cache_dir.absolute()}")
        return
    
    # Require input/output for enrichment
    if not args.input or not args.output:
        parser.print_help()
        print("\n❌ Error: --input and --output required for enrichment")
        return
    
    # Load data
    print(f"\n📥 Loading: {args.input}")
    df = pd.read_csv(args.input)
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {len(df.columns)}")
    
    # Show API status
    print("\n🔑 API Status:")
    for api, status in config.validate().items():
        emoji = "✅" if status else "⬜"
        print(f"   {emoji} {api}")
    
    # Enrich
    print("\n🚀 Starting enrichment...")
    engine = ODINEnrichmentEngine(config)
    df = engine.enrich_dataframe(df, progress=True)
    
    # Save
    df.to_csv(args.output, index=False)
    print(f"\n💾 Saved: {args.output}")
    
    # Summary
    new_cols = [c for c in df.columns if c.startswith(("sentiment", "insider", "analyst", 
                "linkedin", "ae_", "warning", "sponsor", "drug_trials", "publications",
                "cash_", "institutional", "social_", "galaxy"))]
    
    print(f"\n📊 Enrichment Summary:")
    print(f"   New columns added: {len(new_cols)}")
    for col in new_cols:
        non_null = df[col].notna().sum()
        pct = 100 * non_null / len(df)
        print(f"   {col:25} {non_null:4} values ({pct:5.1f}%)")


if __name__ == "__main__":
    main()
