"""
ODIN Data Pipelines
Real-time data sources for options flow, insider transactions, FDA news, and market data

Integrates with:
- FinBrain API (insider transactions, options flow, sentiment, predictions)
- OpenFDA API (drug approvals, CRLs, announcements)
- LunarCrush API (social sentiment)
- SEC EDGAR (Form 4 filings)
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3


@dataclass
class OptionsData:
    """Options chain data for a ticker"""
    ticker: str
    timestamp: str
    current_price: float
    iv_current: float
    iv_historical_30d: float
    iv_percentile: float
    put_call_ratio: float
    call_volume: int
    put_volume: int
    unusual_activity: bool
    expected_move_1std: float
    expected_move_2std: float
    top_strikes: List[Dict]
    source: str = "finbrain"


@dataclass
class InsiderTransaction:
    """SEC Form 4 insider transaction"""
    ticker: str
    insider_name: str
    relationship: str  # CEO, CFO, Director, etc.
    transaction_type: str  # Buy, Sell, Option Exercise
    shares: int
    price: float
    total_value: float
    date: str
    total_shares_after: int
    source: str = "finbrain"


@dataclass
class FDAEvent:
    """FDA regulatory event"""
    ticker: str
    drug_name: str
    event_type: str  # PDUFA, AdCom, CRL, Approval
    event_date: str
    outcome: Optional[str]  # APPROVED, CRL, PENDING
    details: str
    source: str


@dataclass
class SocialSentiment:
    """Social media sentiment data"""
    ticker: str
    timestamp: str
    sentiment_score: float  # 0-100
    galaxy_score: Optional[float]
    engagements_24h: int
    mentions_24h: int
    sentiment_delta_7d: float
    key_themes: List[str]
    source: str = "lunarcrush"


class FinBrainPipeline:
    """
    FinBrain API integration for financial data
    
    Endpoints:
    - Insider transactions
    - Options put/call ratios
    - News sentiment
    - Price predictions
    - Analyst ratings
    """
    
    BASE_URL = "https://api.finbrain.tech/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FINBRAIN_API_KEY")
        self.cache_file = "finbrain_cache.json"
        self.cache = self._load_cache()
        
        if not self.api_key:
            print("⚠️  FINBRAIN_API_KEY not set - some features will be limited")
    
    def _load_cache(self) -> Dict:
        if Path(self.cache_file).exists():
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make authenticated request to FinBrain API"""
        if not self.api_key:
            return None
        
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"FinBrain API error: {response.status}")
                        return None
        except Exception as e:
            print(f"FinBrain request failed: {e}")
            return None
    
    async def get_insider_transactions(self, ticker: str, days: int = 90) -> List[InsiderTransaction]:
        """
        Get recent insider transactions for a ticker
        """
        # Check cache first
        cache_key = f"insider_{ticker}_{days}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.fromisoformat(cached['timestamp']) > datetime.now() - timedelta(hours=6):
                return [InsiderTransaction(**t) for t in cached['data']]
        
        # Call API
        data = await self._make_request(f"insider-transactions/{ticker}", {"days": days})
        
        if not data:
            return []
        
        transactions = []
        for item in data.get('transactions', []):
            tx = InsiderTransaction(
                ticker=ticker,
                insider_name=item.get('insider_name', 'Unknown'),
                relationship=item.get('relationship', 'Unknown'),
                transaction_type=item.get('transaction_type', 'Unknown'),
                shares=item.get('shares', 0),
                price=item.get('price', 0.0),
                total_value=item.get('total_value', 0.0),
                date=item.get('date', ''),
                total_shares_after=item.get('shares_after', 0)
            )
            transactions.append(tx)
        
        # Cache results
        self.cache[cache_key] = {
            'timestamp': datetime.now().isoformat(),
            'data': [asdict(t) for t in transactions]
        }
        self._save_cache()
        
        return transactions
    
    async def get_options_flow(self, ticker: str) -> Optional[OptionsData]:
        """
        Get options put/call ratio and flow data
        """
        cache_key = f"options_{ticker}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.fromisoformat(cached['timestamp']) > datetime.now() - timedelta(hours=1):
                return OptionsData(**cached['data'])
        
        data = await self._make_request(f"options-flow/{ticker}")
        
        if not data:
            return None
        
        options = OptionsData(
            ticker=ticker,
            timestamp=datetime.now().isoformat(),
            current_price=data.get('current_price', 0.0),
            iv_current=data.get('iv_current', 0.0),
            iv_historical_30d=data.get('iv_30d', 0.0),
            iv_percentile=data.get('iv_percentile', 0.0),
            put_call_ratio=data.get('put_call_ratio', 1.0),
            call_volume=data.get('call_volume', 0),
            put_volume=data.get('put_volume', 0),
            unusual_activity=data.get('unusual_activity', False),
            expected_move_1std=data.get('expected_move_1std', 0.0),
            expected_move_2std=data.get('expected_move_2std', 0.0),
            top_strikes=data.get('top_strikes', [])
        )
        
        self.cache[cache_key] = {
            'timestamp': datetime.now().isoformat(),
            'data': asdict(options)
        }
        self._save_cache()
        
        return options
    
    async def get_sentiment(self, ticker: str) -> Optional[Dict]:
        """Get news sentiment score"""
        data = await self._make_request(f"sentiment/{ticker}")
        return data
    
    async def get_predictions(self, ticker: str) -> Optional[Dict]:
        """Get AI price predictions"""
        data = await self._make_request(f"predictions/{ticker}")
        return data


class LunarCrushPipeline:
    """
    LunarCrush API integration for social sentiment
    """
    
    BASE_URL = "https://lunarcrush.com/api4/public"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LUNARCRUSH_API_KEY")
        self.cache_file = "lunarcrush_cache.json"
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        if Path(self.cache_file).exists():
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make request to LunarCrush API"""
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"LunarCrush API error: {response.status}")
                        return None
        except Exception as e:
            print(f"LunarCrush request failed: {e}")
            return None
    
    async def get_social_sentiment(self, ticker: str) -> Optional[SocialSentiment]:
        """
        Get social sentiment data for a stock ticker
        """
        # Check cache
        cache_key = ticker
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            cache_time = cached.get('query_timestamp', '')
            if cache_time:
                try:
                    if datetime.fromisoformat(cache_time.replace('+00:00', '')) > datetime.now() - timedelta(hours=4):
                        return SocialSentiment(
                            ticker=ticker,
                            timestamp=cache_time,
                            sentiment_score=cached.get('sentiment_score', 50),
                            galaxy_score=cached.get('galaxy_score'),
                            engagements_24h=cached.get('engagements_24h', 0),
                            mentions_24h=cached.get('mentions_24h', 0),
                            sentiment_delta_7d=cached.get('sentiment_delta_7d_pct', 0),
                            key_themes=[
                                cached.get('top_theme_bullish', ''),
                                cached.get('top_theme_bearish', '')
                            ]
                        )
                except:
                    pass
        
        # Call API
        data = await self._make_request(f"topic/{ticker}/v1")
        
        if not data or 'data' not in data:
            return None
        
        topic_data = data['data']
        
        sentiment = SocialSentiment(
            ticker=ticker,
            timestamp=datetime.now().isoformat(),
            sentiment_score=topic_data.get('sentiment', 50),
            galaxy_score=topic_data.get('galaxy_score'),
            engagements_24h=topic_data.get('interactions_24h', 0),
            mentions_24h=topic_data.get('social_volume', 0),
            sentiment_delta_7d=topic_data.get('sentiment_relative', 0),
            key_themes=[]
        )
        
        # Cache
        self.cache[cache_key] = {
            'query_timestamp': sentiment.timestamp,
            'sentiment_score': sentiment.sentiment_score,
            'galaxy_score': sentiment.galaxy_score,
            'engagements_24h': sentiment.engagements_24h,
            'mentions_24h': sentiment.mentions_24h,
            'sentiment_delta_7d_pct': sentiment.sentiment_delta_7d
        }
        self._save_cache()
        
        return sentiment


class OpenFDAPipeline:
    """
    OpenFDA API integration for drug approval data
    """
    
    BASE_URL = "https://api.fda.gov/drug"
    
    def __init__(self):
        self.cache = {}
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make request to OpenFDA API"""
        url = f"{self.BASE_URL}/{endpoint}.json"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
        except Exception as e:
            print(f"OpenFDA request failed: {e}")
            return None
    
    async def search_drug_approvals(self, drug_name: str = None, 
                                   sponsor: str = None,
                                   limit: int = 10) -> List[Dict]:
        """
        Search for drug approvals
        """
        search_parts = []
        if drug_name:
            search_parts.append(f'products.brand_name:"{drug_name}"')
        if sponsor:
            search_parts.append(f'sponsor_name:"{sponsor}"')
        
        search_query = " AND ".join(search_parts) if search_parts else "*"
        
        params = {
            "search": search_query,
            "limit": limit
        }
        
        data = await self._make_request("drugsfda", params)
        
        if not data or 'results' not in data:
            return []
        
        return data['results']
    
    async def get_recent_approvals(self, days: int = 30) -> List[FDAEvent]:
        """Get recent FDA drug approvals"""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            "search": f'submissions.submission_status_date:[{start_date.strftime("%Y%m%d")} TO {end_date.strftime("%Y%m%d")}]',
            "limit": 100
        }
        
        data = await self._make_request("drugsfda", params)
        
        if not data or 'results' not in data:
            return []
        
        events = []
        for item in data['results']:
            # Extract relevant info
            for submission in item.get('submissions', []):
                if submission.get('submission_type') == 'ORIG':
                    event = FDAEvent(
                        ticker='',  # Would need to map sponsor to ticker
                        drug_name=item.get('products', [{}])[0].get('brand_name', 'Unknown'),
                        event_type='APPROVAL' if submission.get('submission_status') == 'AP' else 'OTHER',
                        event_date=submission.get('submission_status_date', ''),
                        outcome=submission.get('submission_status'),
                        details=json.dumps(submission),
                        source='openfda'
                    )
                    events.append(event)
        
        return events


class OdinDataPipeline:
    """
    Master data pipeline that combines all data sources
    """
    
    def __init__(self):
        self.finbrain = FinBrainPipeline()
        self.lunarcrush = LunarCrushPipeline()
        self.openfda = OpenFDAPipeline()
        
        # Database for storing aggregated data
        self.db_file = "odin_market_data.db"
        self._init_database()
        
        print("✅ ODIN Data Pipeline initialized")
        print(f"   FinBrain API: {'✅' if self.finbrain.api_key else '⚠️  No API key'}")
        print(f"   LunarCrush API: {'✅' if self.lunarcrush.api_key else '⚠️  No API key'}")
        print(f"   OpenFDA API: ✅ (No key required)")
    
    def _init_database(self):
        """Initialize database for market data storage"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS options_data (
                id INTEGER PRIMARY KEY,
                ticker TEXT,
                timestamp TEXT,
                iv_current REAL,
                iv_historical REAL,
                put_call_ratio REAL,
                expected_move REAL,
                data_json TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS insider_data (
                id INTEGER PRIMARY KEY,
                ticker TEXT,
                insider_name TEXT,
                transaction_type TEXT,
                shares INTEGER,
                price REAL,
                date TEXT,
                data_json TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS sentiment_data (
                id INTEGER PRIMARY KEY,
                ticker TEXT,
                timestamp TEXT,
                sentiment_score REAL,
                galaxy_score REAL,
                engagements INTEGER,
                data_json TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def get_comprehensive_data(self, ticker: str) -> Dict[str, Any]:
        """
        Get all available data for a ticker from all sources
        """
        results = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'options': None,
            'insider_transactions': [],
            'social_sentiment': None,
            'fda_events': [],
            'errors': []
        }
        
        # Fetch all data concurrently
        try:
            options_task = self.finbrain.get_options_flow(ticker)
            insider_task = self.finbrain.get_insider_transactions(ticker)
            sentiment_task = self.lunarcrush.get_social_sentiment(ticker)
            
            options, insiders, sentiment = await asyncio.gather(
                options_task, insider_task, sentiment_task,
                return_exceptions=True
            )
            
            if isinstance(options, Exception):
                results['errors'].append(f"Options: {str(options)}")
            else:
                results['options'] = asdict(options) if options else None
            
            if isinstance(insiders, Exception):
                results['errors'].append(f"Insider: {str(insiders)}")
            else:
                results['insider_transactions'] = [asdict(i) for i in insiders]
            
            if isinstance(sentiment, Exception):
                results['errors'].append(f"Sentiment: {str(sentiment)}")
            else:
                results['social_sentiment'] = asdict(sentiment) if sentiment else None
                
        except Exception as e:
            results['errors'].append(f"General: {str(e)}")
        
        # Store in database
        self._store_data(results)
        
        return results
    
    def _store_data(self, data: Dict):
        """Store fetched data in database"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        ticker = data['ticker']
        timestamp = data['timestamp']
        
        if data.get('options'):
            opts = data['options']
            c.execute('''
                INSERT INTO options_data 
                (ticker, timestamp, iv_current, iv_historical, put_call_ratio, expected_move, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                ticker, timestamp,
                opts.get('iv_current', 0),
                opts.get('iv_historical_30d', 0),
                opts.get('put_call_ratio', 1.0),
                opts.get('expected_move_1std', 0),
                json.dumps(opts)
            ))
        
        for tx in data.get('insider_transactions', []):
            c.execute('''
                INSERT INTO insider_data 
                (ticker, insider_name, transaction_type, shares, price, date, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                ticker,
                tx.get('insider_name', ''),
                tx.get('transaction_type', ''),
                tx.get('shares', 0),
                tx.get('price', 0),
                tx.get('date', ''),
                json.dumps(tx)
            ))
        
        if data.get('social_sentiment'):
            sent = data['social_sentiment']
            c.execute('''
                INSERT INTO sentiment_data 
                (ticker, timestamp, sentiment_score, galaxy_score, engagements, data_json)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                ticker, timestamp,
                sent.get('sentiment_score', 50),
                sent.get('galaxy_score'),
                sent.get('engagements_24h', 0),
                json.dumps(sent)
            ))
        
        conn.commit()
        conn.close()
    
    def build_ai_context(self, ticker: str, data: Dict) -> str:
        """
        Build a context string from market data for AI consumption
        """
        parts = [
            f"=== MARKET DATA FOR {ticker} ===",
            f"Data as of: {data['timestamp']}",
            ""
        ]
        
        # Options data
        if data.get('options'):
            opts = data['options']
            parts.append("--- OPTIONS DATA ---")
            parts.append(f"Current IV: {opts.get('iv_current', 'N/A'):.1%}" if opts.get('iv_current') else "Current IV: N/A")
            parts.append(f"Historical IV (30d): {opts.get('iv_historical_30d', 'N/A'):.1%}" if opts.get('iv_historical_30d') else "Historical IV: N/A")
            parts.append(f"IV Percentile: {opts.get('iv_percentile', 'N/A'):.0%}" if opts.get('iv_percentile') else "IV Percentile: N/A")
            parts.append(f"Put/Call Ratio: {opts.get('put_call_ratio', 'N/A'):.2f}" if opts.get('put_call_ratio') else "P/C Ratio: N/A")
            parts.append(f"Expected Move (1σ): {opts.get('expected_move_1std', 'N/A'):.1%}" if opts.get('expected_move_1std') else "Expected Move: N/A")
            parts.append(f"Unusual Activity: {'YES' if opts.get('unusual_activity') else 'No'}")
            parts.append("")
        
        # Insider transactions
        if data.get('insider_transactions'):
            parts.append("--- INSIDER TRANSACTIONS (Last 90 Days) ---")
            buys = [t for t in data['insider_transactions'] if 'buy' in t.get('transaction_type', '').lower()]
            sells = [t for t in data['insider_transactions'] if 'sell' in t.get('transaction_type', '').lower()]
            
            total_buy_value = sum(t.get('total_value', 0) for t in buys)
            total_sell_value = sum(t.get('total_value', 0) for t in sells)
            
            parts.append(f"Total Buys: {len(buys)} transactions (${total_buy_value:,.0f})")
            parts.append(f"Total Sells: {len(sells)} transactions (${total_sell_value:,.0f})")
            
            # Most recent significant transaction
            if data['insider_transactions']:
                recent = data['insider_transactions'][0]
                parts.append(f"Most Recent: {recent.get('insider_name')} - {recent.get('transaction_type')} "
                           f"{recent.get('shares'):,} shares @ ${recent.get('price', 0):.2f}")
            parts.append("")
        
        # Social sentiment
        if data.get('social_sentiment'):
            sent = data['social_sentiment']
            parts.append("--- SOCIAL SENTIMENT ---")
            parts.append(f"Sentiment Score: {sent.get('sentiment_score', 50)}/100")
            if sent.get('galaxy_score'):
                parts.append(f"Galaxy Score: {sent.get('galaxy_score'):.1f}")
            parts.append(f"24h Engagements: {sent.get('engagements_24h', 0):,}")
            parts.append(f"24h Mentions: {sent.get('mentions_24h', 0):,}")
            parts.append(f"7-Day Sentiment Change: {sent.get('sentiment_delta_7d', 0):+.1f}%")
            parts.append("")
        
        if data.get('errors'):
            parts.append("--- DATA GAPS ---")
            for err in data['errors']:
                parts.append(f"⚠️  {err}")
        
        return "\n".join(parts)


# Singleton instance
_data_pipeline: Optional[OdinDataPipeline] = None

def get_data_pipeline() -> OdinDataPipeline:
    """Get singleton data pipeline instance"""
    global _data_pipeline
    if _data_pipeline is None:
        _data_pipeline = OdinDataPipeline()
    return _data_pipeline


if __name__ == "__main__":
    async def test_pipeline():
        pipeline = OdinDataPipeline()
        
        # Test with a ticker
        print("\n🔍 Fetching data for GUTS...")
        data = await pipeline.get_comprehensive_data("GUTS")
        
        print("\n--- Raw Data ---")
        print(json.dumps(data, indent=2, default=str))
        
        print("\n--- AI Context ---")
        context = pipeline.build_ai_context("GUTS", data)
        print(context)
    
    asyncio.run(test_pipeline())
