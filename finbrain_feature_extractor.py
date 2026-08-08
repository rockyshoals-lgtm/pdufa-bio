"""
FinBrain Market Signal Feature Extractor for Gungnir v35
=========================================================

PURPOSE:
Extract pre-readout market signals from FinBrain for 1,752 historical phase readout events.
All features are T-1 compliant (knowable before readout date).

STATUS: STUB/BLOCKED
The FinBrain MCP tools (finbrain-python 0.1.8) have Pydantic serialization bugs that prevent
data extraction. The tools exist and the server is healthy (health check passed), but the
request parameter validation fails with:
  - "Input should be a valid dictionary or instance of TickersReq"
  - "Input should be a valid dictionary or instance of SentimentsReq"
  - etc.

This script is a TEMPLATE that will work once the FinBrain MCP is fixed.

FEATURES TO EXTRACT (all T-1 compliant):

1. News Sentiment (FinBrain news sentiment API, T-30 to T-1 pre-readout)
   - finbrain_sentiment_avg_30d: Average sentiment score T-30 to T-1
   - finbrain_sentiment_avg_7d: Average sentiment score T-7 to T-1
   - finbrain_sentiment_trend: sentiment_7d - sentiment_30d (improving vs declining)

2. Analyst Ratings (FinBrain analyst ratings API, 90 days pre-readout)
   - finbrain_analyst_upgrades_90d: Count of upgrades in 90 days pre-readout
   - finbrain_analyst_downgrades_90d: Count of downgrades
   - finbrain_analyst_net_signal: upgrades - downgrades

3. Insider Transactions (FinBrain insider API, 90 days pre-readout)
   - finbrain_insider_net_90d: Net insider buys - sells (count)
   - finbrain_insider_value_90d: Net dollar value of insider transactions

4. Options Put/Call (FinBrain options API, T-30 to T-1 pre-readout)
   - finbrain_pcr_avg_30d: Average put/call ratio T-30 to T-1
   - finbrain_pcr_avg_7d: Average put/call ratio T-7 to T-1
   - finbrain_pcr_trend: pcr_7d - pcr_30d (put/call ratio changing)

OUTPUT:
finbrain_features.json: Dict keyed by "ticker|date" with feature values
  Example: {
    "MRK|2022-06-28": {
      "finbrain_sentiment_avg_30d": -0.15,
      "finbrain_sentiment_avg_7d": 0.05,
      "finbrain_sentiment_trend": 0.20,
      ...
    },
    ...
  }

COVERAGE EXPECTATION:
- Not all tickers will have FinBrain data
- Use phase-average imputation for missing values (same as CT.gov in v33)
- Current training set has 1,752 events across 89 unique tickers
- Top tickers: MRK (67), AZN (64), PFE (41), BMY (41), RHHBY (36), NVS (31), LLY (31)
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# SECTION 1: DATA LOADING
# ============================================================================

def load_training_data(csv_path: str) -> pd.DataFrame:
    """
    Load the 1,752 phase readout events with stock returns.

    Args:
        csv_path: Path to gungnir_readout_analysis.csv

    Returns:
        DataFrame with columns: ticker, date, drug, indication, stage, outcome, etc.
    """
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    logger.info(f"Loaded {len(df)} events from {csv_path}")
    logger.info(f"Unique tickers: {df['ticker'].nunique()}")
    logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
    return df


# ============================================================================
# SECTION 2: FINBRAIN API CALLS (BLOCKED - PYDANTIC ISSUES)
# ============================================================================

def get_news_sentiment(ticker: str, start_date: datetime, end_date: datetime) -> Optional[Dict]:
    """
    Fetch news sentiment from FinBrain for ticker during date range.

    BLOCKED: FinBrain MCP returns "Input should be a valid dictionary or instance of SentimentsReq"

    Args:
        ticker: Stock ticker (e.g., 'MRK')
        start_date: Start of sentiment lookback period
        end_date: End of sentiment lookback period

    Returns:
        Dict with date -> sentiment_score mapping, or None if API fails

    Once FinBrain MCP is fixed, this should:
    1. Call mcp__finbrain__news_sentiment_by_ticker with proper SentimentsReq
    2. Filter results to [start_date, end_date]
    3. Return {date: score, ...}
    """
    # TODO: Once FinBrain MCP Pydantic issues are fixed
    # from mcp_integration import call_finbrain_sentiment
    # data = call_finbrain_sentiment(ticker)
    # return {d: s for d, s in data.items() if start_date <= d <= end_date}
    return None


def get_analyst_ratings(ticker: str, lookback_days: int = 90) -> Optional[Dict]:
    """
    Fetch analyst rating changes from FinBrain.

    BLOCKED: FinBrain MCP returns "Input should be a valid dictionary or instance of AnalystRatingsReq"

    Args:
        ticker: Stock ticker
        lookback_days: Number of days to look back (default 90)

    Returns:
        Dict with 'upgrades' and 'downgrades' counts

    Once FinBrain MCP is fixed, this should:
    1. Call mcp__finbrain__analyst_ratings_by_ticker with proper AnalystRatingsReq
    2. Filter to [T-90, T-1]
    3. Count upgrades and downgrades
    """
    # TODO: Once FinBrain MCP Pydantic issues are fixed
    # from mcp_integration import call_finbrain_analyst_ratings
    # data = call_finbrain_analyst_ratings(ticker)
    # return {'upgrades': count_upgrades(data), 'downgrades': count_downgrades(data)}
    return None


def get_insider_transactions(ticker: str, lookback_days: int = 90) -> Optional[Dict]:
    """
    Fetch insider transaction data from FinBrain.

    BLOCKED: FinBrain MCP returns "Input should be a valid dictionary or instance of InsiderReq"

    Args:
        ticker: Stock ticker
        lookback_days: Number of days to look back (default 90)

    Returns:
        Dict with 'net_buys' (count) and 'net_value' (USD)

    Once FinBrain MCP is fixed, this should:
    1. Call mcp__finbrain__insider_transactions_by_ticker with proper InsiderReq
    2. Filter to [T-90, T-1]
    3. Calculate net buys (buy transactions - sell transactions)
    4. Sum dollar values
    """
    # TODO: Once FinBrain MCP Pydantic issues are fixed
    # from mcp_integration import call_finbrain_insider
    # data = call_finbrain_insider(ticker)
    # return {
    #     'net_buys': count_buys(data) - count_sells(data),
    #     'net_value': sum_buy_values(data) - sum_sell_values(data)
    # }
    return None


def get_put_call_ratio(ticker: str, start_date: datetime, end_date: datetime) -> Optional[Dict]:
    """
    Fetch put/call ratio from FinBrain.

    BLOCKED: FinBrain MCP returns "Input should be a valid dictionary or instance of PutCallReq"

    Args:
        ticker: Stock ticker
        start_date: Start of lookback period
        end_date: End of lookback period

    Returns:
        Dict with date -> put_call_ratio mapping

    Once FinBrain MCP is fixed, this should:
    1. Call mcp__finbrain__options_put_call with proper PutCallReq
    2. Filter to [start_date, end_date]
    3. Return {date: pcr, ...}
    """
    # TODO: Once FinBrain MCP Pydantic issues are fixed
    # from mcp_integration import call_finbrain_options
    # data = call_finbrain_options(ticker)
    # return {d: r for d, r in data.items() if start_date <= d <= end_date}
    return None


# ============================================================================
# SECTION 3: FEATURE COMPUTATION
# ============================================================================

def compute_sentiment_features(
    sentiment_data: Optional[Dict],
    event_date: datetime
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Compute sentiment features from time series data.

    Args:
        sentiment_data: Dict of date -> sentiment_score from API
        event_date: Readout event date

    Returns:
        (avg_30d, avg_7d, trend)
    """
    if not sentiment_data:
        return None, None, None

    t1 = event_date - timedelta(days=1)
    t7 = event_date - timedelta(days=7)
    t30 = event_date - timedelta(days=30)

    sentiment_30d = [v for d, v in sentiment_data.items() if t30 <= d <= t1]
    sentiment_7d = [v for d, v in sentiment_data.items() if t7 <= d <= t1]

    avg_30d = sum(sentiment_30d) / len(sentiment_30d) if sentiment_30d else None
    avg_7d = sum(sentiment_7d) / len(sentiment_7d) if sentiment_7d else None
    trend = (avg_7d - avg_30d) if (avg_7d and avg_30d) else None

    return avg_30d, avg_7d, trend


def compute_put_call_features(
    pcr_data: Optional[Dict],
    event_date: datetime
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Compute put/call ratio features from time series data.

    Args:
        pcr_data: Dict of date -> put_call_ratio from API
        event_date: Readout event date

    Returns:
        (avg_30d, avg_7d, trend)
    """
    if not pcr_data:
        return None, None, None

    t1 = event_date - timedelta(days=1)
    t7 = event_date - timedelta(days=7)
    t30 = event_date - timedelta(days=30)

    pcr_30d = [v for d, v in pcr_data.items() if t30 <= d <= t1]
    pcr_7d = [v for d, v in pcr_data.items() if t7 <= d <= t1]

    avg_30d = sum(pcr_30d) / len(pcr_30d) if pcr_30d else None
    avg_7d = sum(pcr_7d) / len(pcr_7d) if pcr_7d else None
    trend = (avg_7d - avg_30d) if (avg_7d and avg_30d) else None

    return avg_30d, avg_7d, trend


# ============================================================================
# SECTION 4: CACHING & BATCH PROCESSING
# ============================================================================

def extract_features_for_event(
    ticker: str,
    event_date: datetime,
    ticker_cache: Dict
) -> Dict:
    """
    Extract all FinBrain features for a single event.

    Uses cached API data to avoid redundant calls.

    Args:
        ticker: Stock ticker
        event_date: Readout date (T0)
        ticker_cache: Cached data for this ticker

    Returns:
        Dict with feature_name -> value (or None if missing)
    """
    t1 = event_date - timedelta(days=1)
    t7 = event_date - timedelta(days=7)
    t30 = event_date - timedelta(days=30)

    # Get cached data (or fetch if not cached)
    # For now, all returns None due to FinBrain MCP block
    sentiment_data = ticker_cache.get('sentiment')  # None
    analyst_data = ticker_cache.get('analyst')      # None
    insider_data = ticker_cache.get('insider')      # None
    pcr_data = ticker_cache.get('pcr')              # None

    # Compute features
    sent_30d, sent_7d, sent_trend = compute_sentiment_features(sentiment_data, event_date)
    pcr_30d, pcr_7d, pcr_trend = compute_put_call_features(pcr_data, event_date)

    analyst_dict = analyst_data or {}
    analyst_upgrades = analyst_dict.get('upgrades', None)
    analyst_downgrades = analyst_dict.get('downgrades', None)
    analyst_net = None
    if analyst_upgrades is not None and analyst_downgrades is not None:
        analyst_net = analyst_upgrades - analyst_downgrades

    insider_dict = insider_data or {}
    insider_net = insider_dict.get('net_buys', None)
    insider_value = insider_dict.get('net_value', None)

    return {
        'finbrain_sentiment_avg_30d': sent_30d,
        'finbrain_sentiment_avg_7d': sent_7d,
        'finbrain_sentiment_trend': sent_trend,
        'finbrain_analyst_upgrades_90d': analyst_upgrades,
        'finbrain_analyst_downgrades_90d': analyst_downgrades,
        'finbrain_analyst_net_signal': analyst_net,
        'finbrain_insider_net_90d': insider_net,
        'finbrain_insider_value_90d': insider_value,
        'finbrain_pcr_avg_30d': pcr_30d,
        'finbrain_pcr_avg_7d': pcr_7d,
        'finbrain_pcr_trend': pcr_trend,
    }


def extract_all_features(
    df: pd.DataFrame,
    output_path: str = 'finbrain_features.json'
) -> Dict:
    """
    Extract FinBrain features for all 1,752 events.

    CURRENTLY BLOCKED: All feature extraction will return None values because
    the FinBrain MCP has Pydantic serialization bugs.

    Args:
        df: DataFrame with events
        output_path: Where to save results

    Returns:
        Dict keyed by "ticker|date" with feature dicts
    """
    logger.warning("FinBrain MCP tools are BLOCKED due to Pydantic serialization issues.")
    logger.warning("All extracted features will be None until the MCP is fixed.")

    features = {}
    ticker_cache = {}

    for idx, row in df.iterrows():
        ticker = row['ticker']
        event_date = row['date']
        key = f"{ticker}|{event_date.strftime('%Y-%m-%d')}"

        # Initialize ticker cache if needed
        if ticker not in ticker_cache:
            ticker_cache[ticker] = {
                'sentiment': None,      # Would call get_news_sentiment()
                'analyst': None,        # Would call get_analyst_ratings()
                'insider': None,        # Would call get_insider_transactions()
                'pcr': None,            # Would call get_put_call_ratio()
            }

        features[key] = extract_features_for_event(ticker, event_date, ticker_cache[ticker])

        if (idx + 1) % 100 == 0:
            logger.info(f"Processed {idx + 1} / {len(df)} events")

    # Save results
    with open(output_path, 'w') as f:
        json.dump(features, f, indent=2, default=str)

    logger.info(f"Saved {len(features)} feature sets to {output_path}")
    return features


# ============================================================================
# SECTION 5: PHASE-AVERAGE IMPUTATION (v33 style)
# ============================================================================

def compute_phase_averages(features: Dict, df: pd.DataFrame) -> Dict:
    """
    Compute phase-average values for imputation (missing data handling).

    Same approach as CT.gov features in GUNGNIR v33:
    For each phase, compute mean of non-null feature values,
    then use those means to fill missing data.

    Args:
        features: Dict keyed by "ticker|date"
        df: Original event dataframe

    Returns:
        Dict of phase -> feature_name -> average_value
    """
    df['key'] = df['ticker'] + '|' + df['date'].astype(str)
    phase_avgs = {}

    feature_names = [
        'finbrain_sentiment_avg_30d',
        'finbrain_sentiment_avg_7d',
        'finbrain_sentiment_trend',
        'finbrain_analyst_upgrades_90d',
        'finbrain_analyst_downgrades_90d',
        'finbrain_analyst_net_signal',
        'finbrain_insider_net_90d',
        'finbrain_insider_value_90d',
        'finbrain_pcr_avg_30d',
        'finbrain_pcr_avg_7d',
        'finbrain_pcr_trend',
    ]

    for phase in df['phase'].unique():
        phase_df = df[df['phase'] == phase]
        phase_features = {fname: [] for fname in feature_names}

        for _, row in phase_df.iterrows():
            key = row['key']
            if key in features:
                for fname in feature_names:
                    val = features[key].get(fname)
                    if val is not None:
                        phase_features[fname].append(val)

        phase_avgs[phase] = {}
        for fname in feature_names:
            if phase_features[fname]:
                phase_avgs[phase][fname] = sum(phase_features[fname]) / len(phase_features[fname])
            else:
                phase_avgs[phase][fname] = None

        logger.info(f"Phase {phase}: computed averages for {len([f for f in phase_features.values() if f])} features")

    return phase_avgs


def impute_missing_features(
    features: Dict,
    df: pd.DataFrame,
    phase_avgs: Dict
) -> Dict:
    """
    Fill missing feature values using phase averages.

    Args:
        features: Dict keyed by "ticker|date"
        df: Original event dataframe
        phase_avgs: Phase-level average values

    Returns:
        Features dict with imputed values
    """
    df['key'] = df['ticker'] + '|' + df['date'].astype(str)

    for _, row in df.iterrows():
        key = row['key']
        phase = row['phase']

        if key not in features:
            features[key] = {}

        feature_names = [
            'finbrain_sentiment_avg_30d',
            'finbrain_sentiment_avg_7d',
            'finbrain_sentiment_trend',
            'finbrain_analyst_upgrades_90d',
            'finbrain_analyst_downgrades_90d',
            'finbrain_analyst_net_signal',
            'finbrain_insider_net_90d',
            'finbrain_insider_value_90d',
            'finbrain_pcr_avg_30d',
            'finbrain_pcr_avg_7d',
            'finbrain_pcr_trend',
        ]

        for fname in feature_names:
            if features[key].get(fname) is None:
                phase_avg = phase_avgs.get(phase, {}).get(fname)
                features[key][fname] = phase_avg

    logger.info("Imputation complete")
    return features


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main execution: extract FinBrain features for all 1,752 events.

    STATUS: BLOCKED
    This will run but will return None for all features until FinBrain MCP is fixed.
    """
    csv_path = '/sessions/loving-nifty-dirac/mnt/Python/9realms/gungnir_readout_analysis.csv'
    output_path = '/sessions/loving-nifty-dirac/mnt/Python/9realms/finbrain_features.json'

    logger.info("=" * 80)
    logger.info("GUNGNIR v35 - FinBrain Feature Extraction")
    logger.info("=" * 80)
    logger.info("")
    logger.warning("STATUS: BLOCKED")
    logger.warning("The FinBrain MCP tools have Pydantic serialization bugs.")
    logger.warning("Request validation fails with: Input should be a valid dictionary or instance of SentimentsReq")
    logger.warning("All features will be extracted as None until the MCP is fixed.")
    logger.info("")

    # Load training data
    df = load_training_data(csv_path)

    # Extract features (currently blocked)
    features = extract_all_features(df, output_path)

    # Compute phase averages for imputation
    phase_avgs = compute_phase_averages(features, df)

    # Impute missing values
    features = impute_missing_features(features, df, phase_avgs)

    # Save final results
    with open(output_path, 'w') as f:
        json.dump(features, f, indent=2, default=str)

    logger.info(f"Complete. Features saved to {output_path}")
    logger.info(f"Total events: {len(features)}")
    logger.info("")
    logger.warning("Note: All feature values are None due to FinBrain MCP block.")
    logger.warning("Once FinBrain Pydantic issues are fixed, re-run this script to populate.")


if __name__ == '__main__':
    main()
