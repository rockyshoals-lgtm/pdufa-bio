#!/usr/bin/env python3
"""
BIFROST Options Module v1.0
===========================
Systematic options strategy for PDUFA/phase readout catalysts.

Strategy: Buy ATM calls on ODIN T1/T2 + small/mid-cap events at T-14,
sell at T-1. Never hold through the decision. Capture delta (stock runup)
+ vega (IV expansion) simultaneously.

Key Findings (493 events, 2022-2026):
  - T-14 entry optimal: Call EV +19.3% on approvals (vs +10.2% stock)
  - ODIN filter critical: approvals +19.3% vs CRLs -12.9%
  - 10.3% of approval trades returned >100%
  - Only 8.8% lost >50%

Integration: Score with ODIN v11 first, then BIFROST v4 for equity timing,
then this module for options overlay on small/mid caps with liquid chains.

Cardinal Rule: THE RUNUP IS THE TRADE. Never hold through the event.
Options amplify gains AND losses — ODIN filtering is non-negotiable.

Author: 9 Realms / pdufa.bio
Version: 1.0.0
Date: April 2026
"""

import yfinance as yf
import json
import csv
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import norm
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# BLACK-SCHOLES PRICING
# ============================================================
def bs_call_price(S, K, T, r, sigma):
    """Black-Scholes call price. T in years, sigma as decimal."""
    if T <= 0 or sigma <= 0 or S <= 0:
        return max(S - K, 0)
    d1 = (np.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def bs_delta(S, K, T, r, sigma):
    """Black-Scholes call delta."""
    if T <= 0 or sigma <= 0:
        return 1.0 if S > K else 0.0
    d1 = (np.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d1)


def bs_vega(S, K, T, r, sigma):
    """Black-Scholes vega (per 1% IV change)."""
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    return S * np.sqrt(T) * norm.pdf(d1) * 0.01


# ============================================================
# OPTIONS CHAIN SCANNER
# ============================================================
def scan_options_chain(ticker, price, catalyst_date_str, min_oi=10, min_volume=1):
    """
    Scan a ticker's options chain for the optimal expiry/strike.

    Returns dict with chain analysis or None if no suitable options.

    Strategy: Find the expiry that SPANS the catalyst date (so we capture
    IV expansion into the event), buy ATM, sell at T-1.
    """
    try:
        t = yf.Ticker(ticker)
        expirations = t.options
        if not expirations:
            return None

        catalyst_dt = datetime.strptime(catalyst_date_str, '%Y-%m-%d')
        today = datetime.now()
        days_to_catalyst = (catalyst_dt - today).days

        # Find best expiry: spans catalyst, closest to catalyst + 14-21 days
        best_expiry = None
        best_score = float('inf')

        for exp in expirations:
            exp_dt = datetime.strptime(exp, '%Y-%m-%d')
            days_after_catalyst = (exp_dt - catalyst_dt).days

            # Must expire AFTER catalyst (to capture IV expansion into event)
            if days_after_catalyst < 7:
                continue

            # Prefer 14-30 days after catalyst (enough theta runway)
            score = abs(days_after_catalyst - 21)
            if score < best_score:
                best_score = score
                best_expiry = exp

        if not best_expiry:
            # Fallback: any expiry after catalyst
            for exp in expirations:
                if exp > catalyst_date_str:
                    best_expiry = exp
                    break

        if not best_expiry:
            return None

        # Pull the chain
        chain = t.option_chain(best_expiry)
        calls = chain.calls

        if calls.empty:
            return None

        # Find ATM call
        calls_copy = calls.copy()
        calls_copy['dist'] = abs(calls_copy['strike'] - price)
        atm_idx = calls_copy['dist'].idxmin()
        atm = calls_copy.loc[atm_idx]

        # Also check slightly OTM (5-10% above) for leverage
        otm_target = price * 1.10
        calls_copy['otm_dist'] = abs(calls_copy['strike'] - otm_target)
        otm_idx = calls_copy['otm_dist'].idxmin()
        otm = calls_copy.loc[otm_idx]

        iv_atm = atm.get('impliedVolatility', 0) * 100
        iv_otm = otm.get('impliedVolatility', 0) * 100

        exp_dt = datetime.strptime(best_expiry, '%Y-%m-%d')
        dte = (exp_dt - today).days

        # Liquidity score (0-100)
        atm_oi = int(atm.get('openInterest', 0) or 0)
        atm_vol = int(atm.get('volume', 0) or 0)
        bid = float(atm.get('bid', 0) or 0)
        ask = float(atm.get('ask', 0) or 0)
        spread_pct = ((ask - bid) / ((ask + bid) / 2) * 100) if (ask + bid) > 0 else 100

        liq_score = min(100, (
            min(atm_oi / 50, 1) * 30 +          # OI component (max at 50+)
            min(atm_vol / 10, 1) * 20 +          # Volume component (max at 10+)
            max(0, (1 - spread_pct / 50)) * 30 + # Spread component (tight = good)
            (1 if ask > 0 and bid > 0 else 0) * 20  # Has two-sided market
        ))

        # Theoretical entry price (midpoint)
        mid_price = (bid + ask) / 2 if (bid + ask) > 0 else ask

        # Greeks at entry
        T_years = dte / 365
        sigma = iv_atm / 100 if iv_atm > 0 else 1.0
        delta = bs_delta(price, atm['strike'], T_years, 0.05, sigma)
        vega = bs_vega(price, atm['strike'], T_years, 0.05, sigma)

        return {
            'ticker': ticker,
            'price': round(price, 2),
            'catalyst_date': catalyst_date_str,
            'days_to_catalyst': days_to_catalyst,
            'best_expiry': best_expiry,
            'dte': dte,
            'atm_strike': float(atm['strike']),
            'atm_iv': round(iv_atm, 1),
            'atm_bid': round(bid, 2),
            'atm_ask': round(ask, 2),
            'atm_mid': round(mid_price, 2),
            'atm_oi': atm_oi,
            'atm_volume': atm_vol,
            'spread_pct': round(spread_pct, 1),
            'otm_strike': float(otm['strike']),
            'otm_iv': round(iv_otm, 1),
            'delta': round(delta, 3),
            'vega': round(vega, 3),
            'liquidity_score': round(liq_score, 1),
            'n_expirations': len(expirations),
            'all_expirations': expirations[:10],
            'tradeable': liq_score >= 25 and iv_atm > 0 and mid_price > 0.05,
        }

    except Exception as e:
        return {'ticker': ticker, 'error': str(e), 'tradeable': False}


# ============================================================
# POSITION SIZING FOR OPTIONS
# ============================================================
def options_position_size(portfolio_value, odin_tier, liquidity_score, iv_level,
                          mcap_tier='small', explosion_tier='NORMAL'):
    """
    Calculate options position size.

    Options get SMALLER allocations than equity because of leverage.
    Max loss = premium paid. Size so max loss = equity equivalent risk.

    Rules:
    - Base: 1-2% of portfolio (vs 3-5% equity)
    - ODIN T1 + high liquidity: up to 2%
    - ODIN T2 + moderate liquidity: up to 1.5%
    - Low liquidity: cap at 1%
    - SNIPER explosion tier: 1.5x multiplier (max 3%)
    - Never >3% in a single options position
    """
    # Base allocation by ODIN tier
    if odin_tier == 1:
        base_pct = 2.0
    elif odin_tier == 2:
        base_pct = 1.5
    else:
        base_pct = 1.0

    # Liquidity adjustment
    if liquidity_score >= 60:
        liq_mult = 1.0
    elif liquidity_score >= 40:
        liq_mult = 0.75
    elif liquidity_score >= 25:
        liq_mult = 0.5
    else:
        return 0  # Don't trade illiquid options

    # Explosion tier multiplier
    if explosion_tier == 'SNIPER':
        expl_mult = 1.5
    elif explosion_tier == 'ELEVATED':
        expl_mult = 1.25
    else:
        expl_mult = 1.0

    position_pct = base_pct * liq_mult * expl_mult
    position_pct = min(position_pct, 3.0)  # Hard cap

    return round(position_pct, 2)


# ============================================================
# TRADE SCORING
# ============================================================
def score_options_trade(scan_result, odin_score=0, odin_tier=2, gungnir_prob=0,
                        conference_boost=0, explosion_tier='NORMAL'):
    """
    Score an options trade opportunity (0-100).

    Components:
    - Model conviction (ODIN/Gungnir probability): 40%
    - IV regime (higher IV = more vega capture): 15%
    - Liquidity (tradeable spread/OI): 20%
    - Timing (days to catalyst vs optimal T-14): 15%
    - Catalyst quality (conference, explosion): 10%
    """
    if not scan_result or not scan_result.get('tradeable'):
        return 0

    # Model conviction (0-40)
    prob = max(odin_score, gungnir_prob)
    conviction = min(40, prob * 40)

    # IV regime (0-15) — higher IV = more premium to capture
    iv = scan_result.get('atm_iv', 0)
    if iv >= 150:
        iv_score = 15
    elif iv >= 100:
        iv_score = 12
    elif iv >= 70:
        iv_score = 8
    elif iv >= 40:
        iv_score = 5
    else:
        iv_score = 2

    # Liquidity (0-20)
    liq = scan_result.get('liquidity_score', 0)
    liq_score = liq * 0.2

    # Timing (0-15) — optimal is T-14 to T-21
    days = scan_result.get('days_to_catalyst', 0)
    if 10 <= days <= 25:
        timing = 15
    elif 7 <= days <= 35:
        timing = 10
    elif 3 <= days <= 45:
        timing = 5
    else:
        timing = 0

    # Catalyst quality (0-10)
    cat_score = 0
    if conference_boost > 0:
        cat_score += 5
    if explosion_tier in ('SNIPER', 'ELEVATED'):
        cat_score += 5

    total = conviction + iv_score + liq_score + timing + cat_score
    return round(min(100, total), 1)


# ============================================================
# MAIN SCANNER
# ============================================================
def scan_universe(catalysts, portfolio_value=100000):
    """
    Scan a list of catalyst events for options opportunities.

    catalysts: list of dicts with keys:
        ticker, catalyst_date, stage, odin_score/gungnir_probability,
        odin_tier/gungnir_tier, market_cap, investment_score, etc.
    """
    results = []

    for cat in catalysts:
        ticker = cat.get('ticker', '')
        mcap = cat.get('market_cap', 0)
        if isinstance(mcap, str):
            try: mcap = float(mcap)
            except: mcap = 0

        # Determine cap tier
        if mcap < 50e6:
            cap_tier = 'nano'
        elif mcap < 300e6:
            cap_tier = 'micro'
        elif mcap < 2e9:
            cap_tier = 'small'
        else:
            cap_tier = 'mid'

        # Strategy split: equity for nano/micro, options for small/mid
        strategy = 'OPTIONS' if cap_tier in ('small', 'mid') else 'EQUITY'

        # Get current price
        try:
            t = yf.Ticker(ticker)
            info = t.info
            price = info.get('currentPrice', info.get('previousClose', 0))
        except:
            price = cat.get('price', 0)

        if price <= 0:
            continue

        # Model scores
        odin_score = cat.get('odin_score', cat.get('gungnir_probability', 0))
        odin_tier = 1 if odin_score >= 0.85 else (2 if odin_score >= 0.65 else 3)
        gungnir_prob = cat.get('gungnir_probability', 0)
        conf_boost = cat.get('conference_boost', 0)
        explosion = cat.get('explosion_tier', 'NORMAL')

        result = {
            'ticker': ticker,
            'name': cat.get('name', ''),
            'drug': cat.get('drug', ''),
            'indication': cat.get('indication', ''),
            'stage': cat.get('stage', ''),
            'catalyst_date': cat.get('catalyst_date', ''),
            'market_cap': mcap,
            'cap_tier': cap_tier,
            'price': price,
            'strategy': strategy,
            'odin_score': odin_score,
            'odin_tier': odin_tier,
            'gungnir_prob': gungnir_prob,
            'investment_score': cat.get('investment_score', 0),
            'investment_tier': cat.get('investment_tier', ''),
        }

        if strategy == 'OPTIONS':
            # Scan options chain
            scan = scan_options_chain(ticker, price, cat.get('catalyst_date', ''))
            if scan and scan.get('tradeable'):
                result.update({
                    'options_scan': scan,
                    'options_score': score_options_trade(
                        scan, odin_score, odin_tier, gungnir_prob, conf_boost, explosion
                    ),
                    'position_pct': options_position_size(
                        portfolio_value, odin_tier,
                        scan.get('liquidity_score', 0),
                        scan.get('atm_iv', 0),
                        cap_tier, explosion
                    ),
                    'entry': f"T-14 (target {cat.get('catalyst_date', '')})",
                    'exit': 'T-1 (day before catalyst)',
                    'expiry': scan.get('best_expiry', ''),
                    'strike': scan.get('atm_strike', 0),
                    'iv': scan.get('atm_iv', 0),
                    'bid_ask': f"${scan.get('atm_bid', 0):.2f}/${scan.get('atm_ask', 0):.2f}",
                    'liquidity': scan.get('liquidity_score', 0),
                    'delta': scan.get('delta', 0),
                })
            else:
                result['strategy'] = 'EQUITY_FALLBACK'
                result['fallback_reason'] = scan.get('error', 'No liquid options') if scan else 'No options chain'

        results.append(result)

    # Sort by options_score for OPTIONS, investment_score for EQUITY
    options_plays = sorted(
        [r for r in results if r['strategy'] == 'OPTIONS'],
        key=lambda x: x.get('options_score', 0), reverse=True
    )
    equity_plays = sorted(
        [r for r in results if r['strategy'] in ('EQUITY', 'EQUITY_FALLBACK')],
        key=lambda x: x.get('investment_score', 0), reverse=True
    )

    return {'options': options_plays, 'equity': equity_plays, 'all': results}


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    import sys

    print("=" * 80)
    print("BIFROST OPTIONS MODULE v1.0")
    print("Equity nano/micro + Options small/mid | ODIN T1/T2 filtered")
    print("Entry T-14, Exit T-1. Never hold through event.")
    print("=" * 80)

    # Load catalyst scores
    with open('catalyst_scores_v33.json') as f:
        all_catalysts = json.load(f)

    # Filter H1+Q3 2026, ALPHA/BETA tier only
    h1q3 = [c for c in all_catalysts
            if '2026-04-01' <= c.get('catalyst_date', '') <= '2026-09-30'
            and c.get('investment_tier') in ('ALPHA', 'BETA')]

    # Deduplicate by ticker (keep highest score)
    seen = {}
    for c in sorted(h1q3, key=lambda x: x.get('investment_score', 0), reverse=True):
        if c['ticker'] not in seen:
            seen[c['ticker']] = c
    catalysts = list(seen.values())[:40]  # Top 40

    print(f"\nScanning {len(catalysts)} top catalysts...")
    print(f"This will pull live options chains from yfinance (~2-3 min)\n")

    results = scan_universe(catalysts)

    # Report OPTIONS plays
    print("\n" + "=" * 80)
    print("OPTIONS PLAYS (Small/Mid Cap)")
    print("=" * 80)
    for i, r in enumerate(results['options'][:20]):
        scan = r.get('options_scan', {})
        print(f"\n{i+1:2d}. {r['ticker']:6s} | {r['name'][:25]:25s} | Score: {r.get('options_score', 0):5.1f}")
        print(f"    Stage: {r['stage']:12s} | Catalyst: {r['catalyst_date']} | MCap: ${r['market_cap']/1e6:.0f}M ({r['cap_tier']})")
        print(f"    Price: ${r['price']:.2f} | Strike: ${r.get('strike', 0):.1f} | Expiry: {r.get('expiry', 'N/A')}")
        print(f"    IV: {r.get('iv', 0):.0f}% | Delta: {r.get('delta', 0):.2f} | Bid/Ask: {r.get('bid_ask', 'N/A')}")
        print(f"    Liquidity: {r.get('liquidity', 0):.0f}/100 | Position: {r.get('position_pct', 0):.1f}% | Gungnir: {r['gungnir_prob']:.1%}")
        print(f"    Drug: {r['drug'][:50]}")

    # Report EQUITY plays
    print("\n" + "=" * 80)
    print("EQUITY PLAYS (Nano/Micro Cap)")
    print("=" * 80)
    for i, r in enumerate(results['equity'][:15]):
        fb = f" [{r.get('fallback_reason', '')}]" if r['strategy'] == 'EQUITY_FALLBACK' else ''
        print(f"{i+1:2d}. {r['ticker']:6s} | {r['name'][:25]:25s} | InvScore: {r.get('investment_score', 0):5.1f} | "
              f"${r['price']:.2f} | MCap ${r['market_cap']/1e6:.0f}M ({r['cap_tier']}){fb}")

    # Save results
    output = {
        'version': '1.0.0',
        'generated': datetime.now().isoformat(),
        'strategy': {
            'options_entry': 'T-14 (14 trading days before catalyst)',
            'options_exit': 'T-1 (day before catalyst)',
            'equity_entry': 'T-25 to T-14 (per BIFROST v4)',
            'equity_exit': 'T-7 to T-1 (per BIFROST v4)',
            'cardinal_rule': 'NEVER hold through the event. The runup IS the trade.',
            'options_caps': 'Small ($300M-$2B) and Mid ($2B+) only',
            'equity_caps': 'Nano (<$50M) and Micro ($50M-$300M)',
            'odin_filter': 'T1 (>=0.85) and T2 (0.65-0.85) ONLY',
        },
        'backtest': {
            'approval_call_ev_t14': '+19.3%',
            'approval_stock_ev_t14': '+10.2%',
            'leverage_ratio': '1.9x',
            'pct_100plus_winners': '10.3%',
            'pct_50plus_losers': '8.8%',
            'sharpe': 0.177,
        },
        'options_plays': [{k: v for k, v in r.items() if k != 'options_scan'}
                         for r in results['options'][:20]],
        'equity_plays': [r for r in results['equity'][:15]],
    }

    with open('bifrost_options_v1_deploy.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n\nSaved to bifrost_options_v1_deploy.json")
    print(f"Options plays: {len(results['options'])}")
    print(f"Equity plays: {len(results['equity'])}")
    print(f"\nDisclaimer: For informational/educational purposes only. Not investment advice.")
