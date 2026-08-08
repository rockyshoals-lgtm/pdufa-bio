"""
ODIN Live Scoring Pipeline v1.0
================================
Phase 1: Wire up MCP queries + market data + revenue estimation + full pipeline.

Usage (in Claude conversation):
    from odin_live_scorer import score_live
    result = score_live("IRON", catalyst_date="2026-02-15", ...)

Usage (CLI):
    python odin_live_scorer.py IRON --catalyst-date 2026-02-15

This module fetches LIVE data from:
  - yfinance: market cap, stock price, shares outstanding, price history
  - FinBrain MCP: insider trades, options P/C, sentiment, analyst ratings
  - LunarCrush MCP: social sentiment
  - ClinicalTrials MCP: trial info
  - PubMed MCP: publication count
  - ChEMBL MCP: drug/target data

Then runs the full ODIN pipeline:
  1. POA scoring (canonical v10.66 config)
  2. S24 revenue impact estimation
  3. Runup Module (alpha score, window, position sizing, exit protocol)

ENGINEER'S NOTE:
  This is the production "Score TICKER" command implementation.
  All MCP calls are optional — the pipeline degrades gracefully to neutral
  defaults if any data source is unavailable.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import numpy as np

# ODIN modules (from previous sessions)
from odin_orchestrator import score_poa, score_revenue_impact, load_canonical_config
from odin_runup_module import (
    score_runup_event, runup_to_dict, RunupResult,
    classify_revenue_tier, classify_mcap_cohort, classify_price_cohort,
    COMPARABLE_DRUGS, REVENUE_MULTIPLIERS,
)
from odin_regime import fetch_regime_live


# ============================================================
# MARKET DATA (yfinance)
# ============================================================

def fetch_market_data(ticker: str) -> Dict[str, Any]:
    """
    Pull live market data from Yahoo Finance.
    Returns: market_cap, price, shares_outstanding, price history for technicals.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("[WARN] yfinance not installed — market data unavailable")
        return {}

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        market_cap = info.get('marketCap', None)
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        shares = info.get('sharesOutstanding')

        # Get 90 days of price history for technicals
        hist = stock.history(period="3mo", auto_adjust=True)
        price_t30 = None
        price_t60 = None
        spy_return_30d = 0.0

        if hist is not None and len(hist) > 0:
            closes = hist['Close']
            if isinstance(closes, type(None)) or len(closes) == 0:
                closes = None
            else:
                if len(closes) >= 22:
                    price_t30 = float(closes.iloc[-22])  # ~30 calendar days ago
                if len(closes) >= 44:
                    price_t60 = float(closes.iloc[-44])

            # SPY for relative strength
            try:
                spy = yf.download("SPY", period="3mo", progress=False, auto_adjust=True)
                if spy is not None and len(spy) > 0:
                    spy_close = spy['Close']
                    if hasattr(spy_close, 'iloc') and len(spy_close) >= 22:
                        spy_now = float(spy_close.iloc[-1])
                        spy_30 = float(spy_close.iloc[-22])
                        if spy_30 > 0:
                            spy_return_30d = (spy_now / spy_30) - 1.0
            except Exception:
                pass

        result = {
            'market_cap': market_cap,
            'price_current': price,
            'shares_outstanding': shares,
            'price_t30': price_t30,
            'price_t60': price_t60,
            'spy_return_30d': spy_return_30d,
        }

        # Filter None values
        return {k: v for k, v in result.items() if v is not None}

    except Exception as e:
        print(f"[WARN] yfinance error for {ticker}: {e}")
        return {}


# ============================================================
# S24 REVENUE ESTIMATION (Spec §4)
# ============================================================

# Indication → comparable drug mapping
# Maps common indication keywords to COMPARABLE_DRUGS keys
INDICATION_COMPARABLE_MAP = {
    # Oncology
    'nsclc': 'NSCLC_1L', 'non-small cell lung': 'NSCLC_1L', 'lung cancer': 'NSCLC_1L',
    'her2': 'HER2_BREAST', 'breast cancer': 'HER2_BREAST',
    'aml': 'AML', 'acute myeloid leukemia': 'AML',

    # CNS
    'alzheimer': 'ALZHEIMERS',
    'depression': 'DEPRESSION_TRD', 'treatment-resistant depression': 'DEPRESSION_TRD',
    'parkinson': 'PARKINSONS',

    # Rare Disease
    'duchenne': 'DMD', 'dmd': 'DMD',
    'spinal muscular atrophy': 'SMA', 'sma': 'SMA',
    'danon': 'DANON',
    'erythropoietic protoporphyria': 'EPP', 'epp': 'EPP',
    'hunter syndrome': 'HUNTER_MPS2', 'mps ii': 'HUNTER_MPS2', 'mps2': 'HUNTER_MPS2',

    # GI
    'gastroparesis': 'GASTROPARESIS',
    'ulcerative colitis': 'IBD_UC', 'crohn': 'IBD_UC',

    # Cardiovascular
    'heart failure': 'HEART_FAILURE',
    'hypertrophic cardiomyopathy': 'HOCM', 'hocm': 'HOCM', 'hcm': 'HOCM',

    # Hematology
    'sickle cell': 'SICKLE_CELL',
    'hemophilia': 'HEMOPHILIA_A',
}

# Peak sales heuristic by therapeutic area (when no comparable match)
TA_PEAK_SALES_HEURISTIC = {
    'Oncology':          2_000_000_000,
    'Rare Disease':        500_000_000,
    'CNS/Neurology':     1_500_000_000,
    'Cardiovascular':    2_000_000_000,
    'Immunology':        3_000_000_000,
    'Infectious Disease':  800_000_000,
    'Metabolic/Endocrine':1_000_000_000,
    'Ophthalmology':       600_000_000,
    'GI/Hepatology':     1_000_000_000,
    'Dermatology':         800_000_000,
    'Hematology':        1_500_000_000,
    'Pain Management':     500_000_000,
    'Other':               500_000_000,
}


def estimate_peak_sales(
    event: dict,
    analyst_estimate: Optional[float] = None,
    company_guidance: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Estimate peak annual sales for a drug using Spec §4.3 priority:
      1. Analyst consensus (confidence 0.9)
      2. Company guidance (confidence 0.75)
      3. Comparable drug (confidence 0.6)
      4. TA heuristic / epidemiology (confidence 0.5)

    Also applies revenue adjustment multipliers (Spec §4.4).
    """
    indication = str(event.get('indication', '')).lower()
    ta = str(event.get('therapeutic_area', 'Other'))
    is_orphan = bool(event.get('orphan', False))
    is_btd = bool(event.get('btd', False))
    prior_approvals = float(event.get('sponsor_prior_approvals', 0) or 0)

    # Priority 1: Analyst consensus
    if analyst_estimate and analyst_estimate > 0:
        return {
            'peak_sales': analyst_estimate,
            'method': 'ANALYST_CONSENSUS',
            'confidence': 0.9,
            'comparable': None,
        }

    # Priority 2: Company guidance
    if company_guidance and company_guidance > 0:
        return {
            'peak_sales': company_guidance,
            'method': 'COMPANY_GUIDANCE',
            'confidence': 0.75,
            'comparable': None,
        }

    # Priority 3: Comparable drug match
    matched_comp = None
    for keyword, comp_key in INDICATION_COMPARABLE_MAP.items():
        if keyword in indication:
            matched_comp = comp_key
            break

    if matched_comp and matched_comp in COMPARABLE_DRUGS:
        base_sales = COMPARABLE_DRUGS[matched_comp]

        # Apply multipliers
        multiplier = 1.0
        adjustments = []

        if is_orphan:
            multiplier *= REVENUE_MULTIPLIERS['orphan_pricing']
            adjustments.append('orphan_pricing')
        if is_btd:
            multiplier *= 1.1  # BTD implies unmet need
            adjustments.append('btd_unmet_need')
        if prior_approvals == 0:
            multiplier *= 0.85  # First-time sponsor risk
            adjustments.append('first_time_sponsor_discount')

        # Market share discount — new entrant in established class
        if base_sales > 3_000_000_000:
            multiplier *= 0.15  # New entrant gets ~15% of blockbuster market
            adjustments.append('market_share_discount')
        elif base_sales > 1_000_000_000:
            multiplier *= 0.30
            adjustments.append('market_share_discount')

        adjusted = base_sales * multiplier

        return {
            'peak_sales': adjusted,
            'method': 'COMPARABLE_DRUG',
            'confidence': 0.6,
            'comparable': matched_comp,
            'base_peak_sales': base_sales,
            'multiplier': multiplier,
            'adjustments': adjustments,
        }

    # Priority 4: TA heuristic fallback
    base = TA_PEAK_SALES_HEURISTIC.get(ta, 500_000_000)

    # Apply rough multipliers
    multiplier = 1.0
    adjustments = []
    if is_orphan:
        multiplier *= 0.5  # Orphan drugs are smaller markets but higher pricing
        adjustments.append('orphan_small_market')
    if is_btd:
        multiplier *= 1.2
        adjustments.append('btd_premium')
    if prior_approvals == 0:
        multiplier *= 0.8
        adjustments.append('first_time_sponsor')

    adjusted = base * multiplier

    return {
        'peak_sales': adjusted,
        'method': 'TA_HEURISTIC',
        'confidence': 0.5,
        'comparable': None,
        'base_peak_sales': base,
        'multiplier': multiplier,
        'adjustments': adjustments,
    }


# ============================================================
# MCP DATA COLLECTORS
# ============================================================
# These are stub functions that document what data to pull.
# In the Claude conversation, the MCPs are called directly via tool use.
# When running standalone, these return empty/neutral data.

def collect_finbrain_data(ticker: str) -> Dict[str, Any]:
    """
    Collect FinBrain MCP data. In a Claude conversation, this data comes
    from direct MCP tool calls. This function is for CLI/standalone mode.

    FinBrain endpoints to query:
      - insider_transactions_by_ticker → insider buys/sells
      - options_put_call → P/C ratio time series
      - news_sentiment_by_ticker → sentiment score
      - analyst_ratings_by_ticker → price targets
      - house_trades_by_ticker → congressional trades
      - senate_trades_by_ticker → congressional trades
      - linkedin_metrics_by_ticker → employee count (hiring signal)
    """
    # In standalone mode, return empty. In Claude, MCPs are called directly.
    return {
        'insider_transactions': [],
        'put_call_ratio_10d': None,
        'news_sentiment': None,
        'analyst_ratings': [],
        'congressional_trades': [],
        'linkedin_employees': None,
        'source': 'STUB_NO_MCP',
    }


def collect_lunarcrush_data(ticker: str) -> Dict[str, Any]:
    """LunarCrush social sentiment. Called via MCP in Claude."""
    return {
        'social_sentiment': None,
        'social_volume': None,
        'source': 'STUB_NO_MCP',
    }


def collect_clinical_data(drug_name: str, indication: str) -> Dict[str, Any]:
    """ClinicalTrials + PubMed + ChEMBL. Called via MCPs in Claude."""
    return {
        'active_trials': [],
        'publication_count': None,
        'mechanism': None,
        'source': 'STUB_NO_MCP',
    }


# ============================================================
# MCP RESULT INTEGRATION
# ============================================================

def integrate_mcp_data(
    finbrain: Dict,
    lunarcrush: Dict,
    clinical: Dict,
    market: Dict,
) -> Dict[str, Any]:
    """
    Convert raw MCP data into the format expected by score_runup_event().

    Returns: market_data, options_data, smart_money_data dicts
    """
    # Market data for technicals
    market_data = None
    if market.get('price_current') and market.get('price_t30'):
        market_data = {
            'price_current': market['price_current'],
            'price_t30': market['price_t30'],
            'price_t60': market.get('price_t60', market['price_t30']),
            'spy_return_30d': market.get('spy_return_30d', 0.0),
        }

    # Options data
    options_data = None
    pc_ratio = finbrain.get('put_call_ratio_10d')
    if pc_ratio is not None:
        options_data = {
            'front_month_iv': None,  # Not available from FinBrain
            'back_month_iv': None,
            'put_call_ratio_10d': pc_ratio,
        }

    # Smart money
    smart_money_data = None
    insider_txns = finbrain.get('insider_transactions', [])
    cong_trades = finbrain.get('congressional_trades', [])
    if insider_txns or cong_trades:
        smart_money_data = {
            'insider_transactions': insider_txns,
            'congressional_trades': cong_trades,
        }

    return {
        'market_data': market_data,
        'options_data': options_data,
        'smart_money_data': smart_money_data,
    }


# ============================================================
# MAIN: score_live()
# ============================================================

def score_live(
    ticker: str,
    catalyst_date: str,
    event_data: Optional[Dict] = None,
    peak_sales_override: Optional[float] = None,
    market_cap_override: Optional[float] = None,
    base_position: float = 10000.0,
    regime: str = 'NORMAL',
    # MCP data (pass in when calling from Claude conversation)
    mcp_finbrain: Optional[Dict] = None,
    mcp_lunarcrush: Optional[Dict] = None,
    mcp_clinical: Optional[Dict] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    MAIN ENTRY POINT: Score a live PDUFA catalyst end-to-end.

    This is what runs when David says "Score TICKER".

    Args:
        ticker:              Stock ticker (e.g., "IRON")
        catalyst_date:       PDUFA date (e.g., "2026-02-15")
        event_data:          Pre-populated event dict (if from dataset).
                             If None, builds from MCP data + defaults.
        peak_sales_override: Manual peak sales estimate (bypasses estimation)
        market_cap_override: Manual market cap (bypasses yfinance)
        base_position:       Base $ per trade
        regime:              Market regime (BULL/NORMAL/BEAR/CRISIS)
        mcp_finbrain:        FinBrain MCP results (from Claude tool calls)
        mcp_lunarcrush:      LunarCrush MCP results
        mcp_clinical:        ClinicalTrials/PubMed/ChEMBL results
        verbose:             Print progress

    Returns:
        Full ODIN output dict per Spec §10.2
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"ODIN LIVE SCORER — {ticker} (PDUFA: {catalyst_date})")
        print(f"{'='*60}")

    # -------------------------------------------------------
    # STEP 0: Build event dict
    # -------------------------------------------------------
    if event_data is None:
        event_data = {'ticker': ticker, 'catalyst_date': catalyst_date}

    event = dict(event_data)
    event['ticker'] = ticker
    event['catalyst_date'] = catalyst_date

    # -------------------------------------------------------
    # STEP 0.5: Auto-detect regime if not specified
    # -------------------------------------------------------
    if regime == 'AUTO':
        if verbose:
            print(f"\n[0/6] Detecting biotech regime...")
        regime_result = fetch_regime_live()
        regime = regime_result.get('regime', 'NORMAL')
        if verbose:
            print(f"  Regime: {regime} (confidence: {regime_result.get('confidence', 'N/A')})")
            print(f"  XBI: ${regime_result.get('xbi_price', 'N/A'):.2f}, 50MA: ${regime_result.get('xbi_50ma', 'N/A')}")
    else:
        regime_result = {'regime': regime, 'confidence': 1.0, 'multiplier': {'BULL':1.2,'NORMAL':1.0,'BEAR':0.5,'CRISIS':0.0}.get(regime,1.0)}

    # -------------------------------------------------------
    # STEP 1: Fetch market data
    # -------------------------------------------------------
    if verbose:
        print(f"\n[1/6] Fetching market data...")

    market = fetch_market_data(ticker)
    market_cap = market_cap_override or market.get('market_cap')
    price = market.get('price_current')

    if verbose:
        print(f"  Market Cap: ${market_cap:,.0f}" if market_cap else "  Market Cap: UNAVAILABLE")
        print(f"  Price: ${price:.2f}" if price else "  Price: UNAVAILABLE")

    # -------------------------------------------------------
    # STEP 2: Collect MCP data (use provided or stub)
    # -------------------------------------------------------
    if verbose:
        print(f"\n[2/6] Collecting MCP signals...")

    finbrain = mcp_finbrain or collect_finbrain_data(ticker)
    lunarcrush = mcp_lunarcrush or collect_lunarcrush_data(ticker)
    clinical = mcp_clinical or collect_clinical_data(
        event.get('asset', ''), event.get('indication', '')
    )

    # Integrate into runup module format
    integrated = integrate_mcp_data(finbrain, lunarcrush, clinical, market)

    fb_source = finbrain.get('source', 'LIVE')
    if verbose:
        print(f"  FinBrain: {fb_source}")
        if finbrain.get('put_call_ratio_10d') is not None:
            print(f"    P/C Ratio (10d): {finbrain['put_call_ratio_10d']:.2f}")
        n_insider = len(finbrain.get('insider_transactions', []))
        if n_insider > 0:
            print(f"    Insider Txns: {n_insider}")

    # -------------------------------------------------------
    # STEP 3: Estimate peak sales (S24)
    # -------------------------------------------------------
    if verbose:
        print(f"\n[3/6] Estimating peak sales (S24)...")

    if peak_sales_override:
        peak_sales_result = {
            'peak_sales': peak_sales_override,
            'method': 'MANUAL_OVERRIDE',
            'confidence': 1.0,
            'comparable': None,
        }
    else:
        # Check if analyst estimate came from FinBrain
        analyst_est = None
        for rating in finbrain.get('analyst_ratings', []):
            tp = rating.get('target_price_to') or rating.get('target_price_raw')
            if tp and market.get('shares_outstanding'):
                # Very rough: target price × shares = implied market cap post-approval
                # Revenue estimate = (implied mcap - current mcap) * some factor
                # This is a heuristic — real implementation should use EvaluatePharma
                pass

        peak_sales_result = estimate_peak_sales(
            event=event,
            analyst_estimate=analyst_est,
        )

    peak_sales = peak_sales_result['peak_sales']

    if verbose:
        print(f"  Peak Sales Est: ${peak_sales:,.0f}")
        print(f"  Method: {peak_sales_result['method']}")
        if peak_sales_result.get('comparable'):
            print(f"  Comparable: {peak_sales_result['comparable']}")

    # -------------------------------------------------------
    # STEP 4: Run ODIN POA
    # -------------------------------------------------------
    if verbose:
        print(f"\n[4/6] Running ODIN POA (canonical v10.66)...")

    poa = score_poa(event)

    if verbose:
        print(f"  Probability: {poa['probability']:.1%}")
        print(f"  Tier: {poa['tier']}")
        print(f"  Logit: {poa['logit']:.4f}")

    # -------------------------------------------------------
    # STEP 5: Run S24 Revenue Impact
    # -------------------------------------------------------
    if verbose:
        print(f"\n[5/6] Computing revenue impact...")

    revenue = score_revenue_impact(event, peak_sales=peak_sales, market_cap=market_cap)

    if verbose:
        print(f"  Revenue Tier: {revenue['tier']}")
        print(f"  Impact Ratio: {revenue['ratio']:.2f}")
        print(f"  Position Mult: {revenue['multiplier']:.1f}x")

    # -------------------------------------------------------
    # STEP 6: Run Runup Module
    # -------------------------------------------------------
    if verbose:
        print(f"\n[6/6] Running Runup Module (alpha + window + sizing)...")

    runup = score_runup_event(
        event=event,
        poa_result=poa,
        revenue_result=revenue,
        market_data=integrated['market_data'],
        options_data=integrated['options_data'],
        smart_money_data=integrated['smart_money_data'],
        base_position=base_position,
        regime=regime,
    )

    if verbose:
        print(f"  Alpha Score: {runup.alpha_score:.1f}")
        print(f"  Alpha Tier: {runup.alpha_tier}")
        print(f"  Window: T{runup.entry_day} → T{runup.exit_day} ({runup.window_name})")
        print(f"  Expected Return: {runup.expected_return_low:.1%} to {runup.expected_return_high:.1%}")
        print(f"  Position: ${runup.final_position:,.0f} ({runup.position_multiplier:.2f}x)")
        print(f"  Confidence: {runup.confidence}")
        if runup.risk_flags:
            print(f"  Risk Flags: {runup.risk_flags}")

    # -------------------------------------------------------
    # BUILD OUTPUT (Spec §10.2)
    # -------------------------------------------------------
    output = {
        'ticker': ticker,
        'catalyst_date': catalyst_date,
        'scored_at': datetime.now().isoformat(),

        'odin_score': poa['probability'],
        'odin_tier': poa['tier'],
        'odin_logit': poa['logit'],

        'revenue_analysis': {
            'peak_sales_estimate': peak_sales,
            'market_cap': market_cap,
            'revenue_impact_ratio': revenue['ratio'],
            'revenue_tier': revenue['tier'],
            'estimation_method': peak_sales_result['method'],
            'comparable': peak_sales_result.get('comparable'),
            'confidence': peak_sales_result.get('confidence', 0.5),
        },

        'alpha_score': {
            'total': runup.alpha_score,
            'tier': runup.alpha_tier,
            'components': runup.alpha_components,
        },

        'window': {
            'name': runup.window_name,
            'entry': f'T{runup.entry_day}',
            'exit': f'T{runup.exit_day}',
            'calendar_days': runup.calendar_days,
        },
        'expected_return': {
            'low': round(runup.expected_return_low, 4),
            'high': round(runup.expected_return_high, 4),
        },
        'position': {
            'base': base_position,
            'final': runup.final_position,
            'multiplier': runup.position_multiplier,
        },
        'exit_protocol': runup.exit_protocol,

        'specialist_interest': runup.specialist_interest,
        'smart_money': runup.smart_money,
        'options_recommendation': runup.options_recommendation,
        'risk_flags': runup.risk_flags,
        'confidence': runup.confidence,

        'market_data': {
            'price': price,
            'market_cap': market_cap,
            'price_t30': market.get('price_t30'),
        },

        'data_sources': {
            'market': 'yfinance' if market else 'UNAVAILABLE',
            'finbrain': fb_source,
            'lunarcrush': lunarcrush.get('source', 'UNAVAILABLE'),
            'clinical': clinical.get('source', 'UNAVAILABLE'),
        },

        'regime': {
            'current': regime,
            'details': regime_result if isinstance(regime_result, dict) else {'regime': regime},
        },
    }

    if verbose:
        print(f"\n{'='*60}")
        print("SCORING COMPLETE")
        print(f"{'='*60}")

    return output


# ============================================================
# MCP HELPER: Process raw MCP results into finbrain format
# ============================================================

def process_finbrain_insider(raw_insider_data: list) -> list:
    """
    Convert raw FinBrain insider_transactions_by_ticker response
    into the format expected by insider_signal().
    """
    if not raw_insider_data:
        return []

    transactions = []
    for item in raw_insider_data:
        # Handle both FinBrain formats
        txn_type = item.get('transaction_type', '')
        # FinBrain uses 'P - Purchase' or 'S - Sale' or 'S - Sale+OE'
        if 'Purchase' in str(txn_type) or txn_type == 'P':
            clean_type = 'Purchase'
        elif 'Sale' in str(txn_type) or txn_type == 'S':
            clean_type = 'Sale'
        else:
            clean_type = txn_type

        usd_val = item.get('usd_value', 0)
        if usd_val is None:
            usd_val = 0
        # Sometimes comes as string
        try:
            usd_val = float(usd_val)
        except (ValueError, TypeError):
            usd_val = 0

        transactions.append({
            'date': item.get('date', ''),
            'insider_name': item.get('insider_name', ''),
            'transaction_type': clean_type,
            'usd_value': abs(usd_val),
            'shares': item.get('shares', 0),
        })

    return transactions


def process_finbrain_options(raw_pc_data: list) -> Optional[float]:
    """
    Convert raw FinBrain options_put_call response into 10-day avg P/C ratio.
    """
    if not raw_pc_data:
        return None

    # Take last 10 entries
    recent = raw_pc_data[-10:] if len(raw_pc_data) >= 10 else raw_pc_data
    ratios = []
    for item in recent:
        pc = item.get('put_call_ratio')
        if pc is not None:
            try:
                ratios.append(float(pc))
            except (ValueError, TypeError):
                continue

    if not ratios:
        return None

    return sum(ratios) / len(ratios)


def process_finbrain_sentiment(raw_sentiment: list) -> Optional[float]:
    """Convert raw FinBrain news_sentiment_by_ticker into a score."""
    if not raw_sentiment:
        return None

    recent = raw_sentiment[-10:] if len(raw_sentiment) >= 10 else raw_sentiment
    scores = []
    for item in recent:
        s = item.get('score')
        if s is not None:
            try:
                scores.append(float(s))
            except (ValueError, TypeError):
                continue

    if not scores:
        return None

    return sum(scores) / len(scores)


def build_mcp_finbrain(
    insider_raw: Optional[list] = None,
    options_raw: Optional[list] = None,
    sentiment_raw: Optional[list] = None,
    analyst_raw: Optional[list] = None,
    house_raw: Optional[list] = None,
    senate_raw: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Build the finbrain data dict from raw MCP responses.
    Use this in a Claude conversation after calling FinBrain MCPs.

    Example:
        insider = finbrain:insider_transactions_by_ticker(market="S&P 500", ticker="IRON")
        options = finbrain:options_put_call(market="S&P 500", ticker="IRON")
        ...
        fb_data = build_mcp_finbrain(
            insider_raw=insider['series'],
            options_raw=options['series'],
            ...
        )
        result = score_live("IRON", ..., mcp_finbrain=fb_data)
    """
    congressional = []
    for trade in (house_raw or []):
        congressional.append({**trade, 'source': 'house'})
    for trade in (senate_raw or []):
        congressional.append({**trade, 'source': 'senate'})

    return {
        'insider_transactions': process_finbrain_insider(insider_raw or []),
        'put_call_ratio_10d': process_finbrain_options(options_raw),
        'news_sentiment': process_finbrain_sentiment(sentiment_raw),
        'analyst_ratings': analyst_raw or [],
        'congressional_trades': congressional,
        'source': 'FINBRAIN_MCP',
    }


# ============================================================
# CLI
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ODIN Live Scorer")
    parser.add_argument('ticker', help="Stock ticker (e.g., IRON)")
    parser.add_argument('--catalyst-date', required=True, help="PDUFA date (YYYY-MM-DD)")
    parser.add_argument('--ta', default='Other', help="Therapeutic area")
    parser.add_argument('--indication', default='', help="Disease indication")
    parser.add_argument('--asset', default='', help="Drug name")
    parser.add_argument('--peak-sales', type=float, default=None, help="Manual peak sales estimate")
    parser.add_argument('--market-cap', type=float, default=None, help="Manual market cap")
    parser.add_argument('--base-position', type=float, default=10000, help="Base $ per trade")
    parser.add_argument('--regime', default='AUTO', choices=['BULL','NORMAL','BEAR','CRISIS','AUTO'])

    # Boolean flags
    parser.add_argument('--btd', action='store_true')
    parser.add_argument('--orphan', action='store_true')
    parser.add_argument('--priority-review', action='store_true')
    parser.add_argument('--fast-track', action='store_true')
    parser.add_argument('--prior-crl', action='store_true')
    parser.add_argument('--no-fetch', action='store_true', help="Skip yfinance (offline mode)")
    parser.add_argument('--output', default=None, help="Save JSON output to file")

    args = parser.parse_args()

    event = {
        'ticker': args.ticker,
        'catalyst_date': args.catalyst_date,
        'therapeutic_area': args.ta,
        'indication': args.indication,
        'asset': args.asset,
        'btd': args.btd,
        'orphan': args.orphan,
        'priority_review': args.priority_review,
        'fast_track': args.fast_track,
        'prior_crl': args.prior_crl,
        'application_type': 'NDA',
        'sponsor_prior_approvals': 0,
    }

    result = score_live(
        ticker=args.ticker,
        catalyst_date=args.catalyst_date,
        event_data=event,
        peak_sales_override=args.peak_sales,
        market_cap_override=args.market_cap,
        base_position=args.base_position,
        regime=args.regime,
    )

    # Print final JSON
    print(f"\n{'='*60}")
    print("FULL OUTPUT:")
    print(f"{'='*60}")
    print(json.dumps(result, indent=2, default=str))

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nSaved to {args.output}")


if __name__ == '__main__':
    main()
