#!/usr/bin/env python3
"""
Q2 2026 Options Scan v3 — Direct BIFROST v1.3 scoring from existing ORATS cache.
Reads orats_q2_apr19_cache/TICKER_strikes.json, scores each Q2 catalyst under v1.3 rules.
"""
import json, os, sys, time
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request
import urllib.parse

BASE = Path("/sessions/confident-serene-ptolemy/mnt/9realms")
CACHE_DIR = BASE / "orats_q2_apr19_cache"
TODAY = datetime(2026, 4, 19)
Q2_END = datetime(2026, 6, 30)
ORATS_TOKEN = "cc1aa61c-ebfa-42e9-8fc0-6bc8f23aaa3d"

def load_catalysts():
    with open(BASE / "catalyst_scores_v44.json") as f:
        data = json.load(f)
    q2 = []
    for c in data:
        try:
            cd = datetime.strptime(c['catalyst_date'], '%Y-%m-%d')
        except Exception:
            continue
        if TODAY <= cd <= Q2_END:
            c['_days_to_cat'] = (cd - TODAY).days
            q2.append(c)
    return q2

def fetch_orats(ticker, force=False):
    """Pull ORATS /strikes for ticker, cache locally. Returns dict or None."""
    cache_path = CACHE_DIR / f"{ticker}_strikes.json"
    if cache_path.exists() and not force:
        try:
            with open(cache_path) as f:
                return json.load(f)
        except Exception:
            pass
    # API call
    url = f"https://api.orats.io/datav2/strikes?ticker={ticker}&token={ORATS_TOKEN}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
        data = json.loads(raw)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'w') as f:
            json.dump(data, f)
        time.sleep(0.65)  # throttle
        return data
    except Exception as e:
        return {"error": str(e)}

def find_atm_call(strikes_data, catalyst_date):
    """Find ATM call with expiration AFTER catalyst_date, closest DTE in [7, 45]."""
    if not strikes_data or 'data' not in strikes_data or not strikes_data['data']:
        return None
    rows = strikes_data['data']
    spot = rows[0].get('spotPrice') or rows[0].get('stockPrice')
    if not spot or spot <= 0:
        return None
    today_str = rows[0].get('tradeDate', '2026-04-17')
    try:
        trade_date = datetime.strptime(today_str, '%Y-%m-%d')
    except Exception:
        trade_date = TODAY - timedelta(days=2)
    # Filter strikes expiring after catalyst (or if catalyst already, pick future expiry)
    cat_dt = datetime.strptime(catalyst_date, '%Y-%m-%d') if isinstance(catalyst_date, str) else catalyst_date
    valid = []
    for r in rows:
        try:
            exp = datetime.strptime(r['expirDate'], '%Y-%m-%d')
        except Exception:
            continue
        dte = (exp - trade_date).days
        if dte < 7 or dte > 45:
            continue
        # Expiration must be after or equal to catalyst date
        if exp < cat_dt:
            continue
        valid.append((r, dte, exp))
    if not valid:
        return None
    # For each expiry, find ATM (smallest |strike-spot|); then among them pick the smallest DTE >= catalyst
    # Group by expiry
    from collections import defaultdict
    by_expiry = defaultdict(list)
    for r, dte, exp in valid:
        by_expiry[exp].append((r, dte))
    # Pick the nearest expiry >= catalyst
    expiries = sorted(by_expiry.keys())
    target_expiry = expiries[0]
    target_rows = by_expiry[target_expiry]
    # Find ATM strike
    atm_row, atm_dte = min(target_rows, key=lambda x: abs(x[0]['strike'] - spot))
    atm_row['_spot'] = spot
    atm_row['_dte'] = atm_dte
    atm_row['_expiry'] = target_expiry.strftime('%Y-%m-%d')
    atm_row['_trade_date'] = trade_date.strftime('%Y-%m-%d')
    return atm_row

def score_ticker(cat):
    """Score a single Q2 catalyst under BIFROST v1.3 rules."""
    ticker = cat['ticker']
    days = cat['_days_to_cat']
    out = {
        'ticker': ticker,
        'name': cat.get('name'),
        'drug': cat.get('drug'),
        'catalyst': cat.get('next_catalyst'),
        'catalyst_date': cat['catalyst_date'],
        'days_to_catalyst': days,
        'is_pdufa': cat.get('is_pdufa'),
        'phase': cat.get('phase'),
        'stage': cat.get('stage'),
        'size_tier': cat.get('size_tier'),
        'mcap_usd': cat.get('market_cap'),
        'spot_ref': cat.get('price'),
        'gungnir_prob': cat.get('gungnir_probability'),
        'gungnir_tier': cat.get('gungnir_tier'),
        'investment_tier': cat.get('investment_tier'),
        'investment_score': cat.get('investment_score'),
        'ta': cat.get('ta'),
        'edge': None, 'scorable': False, 'entry_score': 0, 'flags': [],
    }
    # Skip if days out of useful window
    if days < 1 or days > 45:
        out['edge'] = 'AVOID'
        out['flags'].append(f'days_to_catalyst={days} out of [1,45]')
        return out
    # Load ORATS
    data = fetch_orats(ticker)
    if not data or 'error' in (data or {}) or 'data' not in (data or {}):
        out['edge'] = 'NO_CHAIN'
        out['flags'].append(f'no ORATS chain')
        return out
    atm = find_atm_call(data, cat['catalyst_date'])
    if atm is None:
        out['edge'] = 'NO_ATM'
        out['flags'].append('no ATM call with expiry >= catalyst in DTE[7,45]')
        return out
    # Pull option fields
    spot = atm['_spot']
    strike = atm['strike']
    dte = atm['_dte']
    expiry = atm['_expiry']
    bid = atm.get('callBidPrice') or 0
    ask = atm.get('callAskPrice') or 0
    oi = atm.get('callOpenInterest') or 0
    vol = atm.get('callVolume') or 0
    mid_iv = atm.get('callMidIv') or atm.get('smvVol') or 0
    call_val = atm.get('callValue') or 0
    mid = (bid + ask) / 2 if (bid and ask) else max(bid, ask, call_val)
    if mid <= 0:
        out['edge'] = 'STALE'
        out['flags'].append('bid=ask=0 or stale')
        return out
    real_40 = bid * 0.6 + ask * 0.4
    spread_pct = ((ask - bid) / mid * 100) if mid > 0 else 999
    out.update({
        'spot': round(spot, 2),
        'atm_strike': round(strike, 2),
        'expiry': expiry,
        'dte': dte,
        'call_bid': round(bid, 2),
        'call_ask': round(ask, 2),
        'call_mid': round(mid, 2),
        'call_real_40': round(real_40, 2),
        'call_oi': oi,
        'call_vol': vol,
        'call_iv_pct': round(mid_iv * 100 if mid_iv < 10 else mid_iv, 1),
        'spread_pct': round(spread_pct, 1),
    })
    # Determine edge
    inv_tier = cat.get('investment_tier', '')
    g_prob = cat.get('gungnir_probability', 0) or 0
    phase = cat.get('phase', 0)
    stage = (cat.get('stage') or '').lower()
    is_phase12 = (phase in (1, 2)) or ('phase 1' in stage) or ('phase 2' in stage)
    size = (cat.get('size_tier') or '').lower()
    is_small_cap = size in ('nano', 'micro')
    is_pdufa = bool(cat.get('is_pdufa'))

    edge = 'AVOID'
    if is_phase12 and not is_pdufa and (inv_tier in ('ALPHA', 'BETA') or g_prob >= 0.65):
        edge = 'CORE'
    elif is_pdufa and is_small_cap and oi >= 50 and spread_pct <= 30:
        edge = 'LOTTO'
    elif is_pdufa and is_small_cap and oi >= 20:
        edge = 'LOTTO_LOW_LIQ'
    out['edge'] = edge
    out['scorable'] = True

    # Entry score
    score = 50
    if edge == 'CORE':
        score += 30
    elif edge == 'LOTTO':
        score += 25
    elif edge == 'LOTTO_LOW_LIQ':
        score += 10
    else:
        score -= 30
    # OI
    if 100 <= oi <= 499:
        score += 10
    elif oi < 20:
        score -= 15
    elif oi >= 500:
        score -= 5
    # Spread
    if spread_pct < 15:
        score += 5
    elif spread_pct > 50:
        score -= 25
    elif spread_pct > 30:
        score -= 10
    # Vol
    if vol >= 100:
        score += 5
    # DTE sweet spot
    if 5 <= days <= 14:
        score += 5
    elif 1 <= days <= 4:
        score += 2
    # IV position — don't have IV rank cheaply; mild bonus if IV reasonable
    iv_pct = out['call_iv_pct']
    if 60 <= iv_pct <= 200:
        score += 3  # catalyst priced in but not saturated
    elif iv_pct < 40:
        score -= 5  # IV may be too cheap — trap
    out['entry_score'] = score
    if edge == 'CORE' and g_prob:
        out['flags'].append(f'phase12_readout_gp={g_prob:.2f}')
    if edge in ('LOTTO','LOTTO_LOW_LIQ'):
        out['flags'].append(f'PDUFA_{size}')
    if oi < 50:
        out['flags'].append(f'low_oi={oi}')
    if spread_pct > 30:
        out['flags'].append(f'wide_spread={spread_pct:.0f}pct')
    return out

def main():
    cats = load_catalysts()
    print(f"[Q2] {len(cats)} catalysts in window {TODAY.date()} → {Q2_END.date()}")
    results = []
    misses = 0
    for i, c in enumerate(cats):
        try:
            r = score_ticker(c)
        except Exception as e:
            r = {'ticker': c['ticker'], 'edge': 'ERROR', 'error': str(e),
                 'catalyst_date': c['catalyst_date'], 'days_to_catalyst': c['_days_to_cat']}
        results.append(r)
        if not r.get('scorable'):
            misses += 1
        if (i+1) % 25 == 0:
            print(f"  {i+1}/{len(cats)} scored ({misses} unscorable so far)")
    # Write raw
    with open(BASE / "q2_options_scan_v3_raw.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    # Split by edge
    core = [r for r in results if r.get('edge') == 'CORE']
    lotto = [r for r in results if r.get('edge') == 'LOTTO']
    lotto_low = [r for r in results if r.get('edge') == 'LOTTO_LOW_LIQ']
    avoid = [r for r in results if r.get('edge') == 'AVOID']
    no_chain = [r for r in results if r.get('edge') in ('NO_CHAIN','NO_ATM','STALE','ERROR')]
    core.sort(key=lambda x: -x.get('entry_score', 0))
    lotto.sort(key=lambda x: -x.get('entry_score', 0))
    lotto_low.sort(key=lambda x: -x.get('entry_score', 0))
    ranked = {
        'top_core': core[:20],
        'all_core': core,
        'top_lotto': lotto[:20],
        'all_lotto': lotto,
        'lotto_low_liq': lotto_low,
        'counts': {
            'total': len(results),
            'core': len(core),
            'lotto': len(lotto),
            'lotto_low_liq': len(lotto_low),
            'avoid': len(avoid),
            'no_chain_or_stale': len(no_chain),
        }
    }
    with open(BASE / "q2_options_scan_v3_ranked.json", 'w') as f:
        json.dump(ranked, f, indent=2, default=str)
    print(f"\n=== COUNTS ===")
    for k, v in ranked['counts'].items():
        print(f"  {k}: {v}")
    print(f"\n=== TOP 5 CORE ===")
    for r in core[:5]:
        print(f"  {r['ticker']:6s} {r['catalyst_date']} DTE={r.get('dte'):>3} strike=${r.get('atm_strike'):>5.2f} mid=${r.get('call_mid'):>5.2f} OI={r.get('call_oi'):>4} spread={r.get('spread_pct'):>4.1f}% score={r.get('entry_score')}")
    print(f"\n=== TOP 5 LOTTO ===")
    for r in lotto[:5]:
        print(f"  {r['ticker']:6s} {r['catalyst_date']} DTE={r.get('dte'):>3} strike=${r.get('atm_strike'):>5.2f} mid=${r.get('call_mid'):>5.2f} OI={r.get('call_oi'):>4} spread={r.get('spread_pct'):>4.1f}% score={r.get('entry_score')}")
    print(f"\n=== PORTFOLIO ===")
    for t in ['GRCE','WHWK','CRDF','CABA','ALXO']:
        r = next((x for x in results if x['ticker']==t), None)
        if r:
            print(f"  {t}: edge={r.get('edge')} score={r.get('entry_score')} flags={r.get('flags')}")
    return ranked

if __name__ == '__main__':
    main()
