#!/usr/bin/env python3
"""
Q2 2026 ORATS Options Scan (Apr 19, 2026)
BIFROST v1.3 corrected rules — NO T-5 minimum, T+1 to T+21 windows
CORE edge: Phase 1/2 positive readout, ATM call, T-14→T-1
LOTTO edge: Micro/nano PDUFA, OI≥50, spread≤30%
"""

import json
import os
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Config
TODAY = datetime(2026, 4, 19)
ORATS_TOKEN = "cc1aa61c-ebfa-42e9-8fc0-6bc8f23aaa3d"
ORATS_BASE = "https://api.orats.io/datav2"
CACHE_DIR = Path("/sessions/confident-serene-ptolemy/mnt/9realms/orats_q2_apr19_cache")
CACHE_DIR.mkdir(exist_ok=True)

# Load catalyst scores
CATALYST_FILE = Path("/sessions/confident-serene-ptolemy/mnt/9realms/catalyst_scores_v44.json")
with open(CATALYST_FILE) as f:
    catalyst_list = json.load(f)

print(f"[{TODAY}] Loading {len(catalyst_list)} catalysts from v44...")

# Filter to Q2 2026 date range
q2_catalysts = {}
for data in catalyst_list:
    try:
        ticker = data.get("ticker")
        cat_date = datetime.fromisoformat(data.get("catalyst_date", ""))
        if TODAY <= cat_date <= datetime(2026, 6, 30):
            q2_catalysts[ticker] = data
    except (ValueError, TypeError):
        pass

print(f"[{TODAY}] {len(q2_catalysts)} catalysts in Q2 range (2026-04-19 to 2026-06-30)")

# Get spot prices via ORATS (or fallback)
def get_spot(ticker):
    """Fetch current spot price from ORATS ivrank endpoint."""
    url = f"{ORATS_BASE}/hist/ivrank"
    params = {"ticker": ticker, "token": ORATS_TOKEN}
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data and "data" in data and len(data["data"]) > 0:
                return float(data["data"][0].get("close", 0))
    except:
        pass
    return None

# Get options chain from ORATS
def get_strikes_cached(ticker):
    """Fetch options chain, use cache if available."""
    cache_file = CACHE_DIR / f"{ticker}_strikes.json"

    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)

    url = f"{ORATS_BASE}/strikes"
    params = {"ticker": ticker, "token": ORATS_TOKEN}
    try:
        resp = requests.get(url, params=params, timeout=10)
        time.sleep(0.65)  # Rate limit
        if resp.status_code == 200:
            data = resp.json()
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            return data
    except Exception as e:
        print(f"  ERROR fetching {ticker}: {e}")
    return None

# Get IV Rank
def get_ivrank(ticker):
    """Fetch IV percentile."""
    cache_file = CACHE_DIR / f"{ticker}_ivrank.json"

    if cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
            if data and "data" in data and len(data["data"]) > 0:
                return float(data["data"][0].get("iv_rank", 50))

    url = f"{ORATS_BASE}/hist/ivrank"
    params = {"ticker": ticker, "token": ORATS_TOKEN}
    try:
        resp = requests.get(url, params=params, timeout=5)
        time.sleep(0.65)
        if resp.status_code == 200:
            data = resp.json()
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            if data and "data" in data and len(data["data"]) > 0:
                return float(data["data"][0].get("iv_rank", 50))
    except:
        pass
    return 50.0

# Classify and score catalysts
results = {}
summary = {"CORE": [], "LOTTO": [], "LOTTO_LOW_LIQ": [], "EARLY": [], "AVOID": []}

for ticker, cdata in q2_catalysts.items():
    cat_date = datetime.fromisoformat(cdata.get("catalyst_date", ""))
    days_to = (cat_date - TODAY).days

    # Check eligibility window
    if days_to < 1 or days_to > 45:
        results[ticker] = {
            **cdata,
            "days_to_catalyst": days_to,
            "classification": "AVOID",
            "reason": f"days_to_catalyst {days_to} out of [1, 45] range",
            "entry_score": -30
        }
        summary["AVOID"].append(ticker)
        continue

    # Classify by edge type
    is_phase1_2 = cdata.get("is_phase1") or cdata.get("is_phase1b") or cdata.get("is_phase2") or cdata.get("is_phase2a")
    is_pdufa = cdata.get("catalyst_type") == "PDUFA"
    is_readout = not is_pdufa

    gungnir_tier = cdata.get("gungnir_tier", "GAMMA")
    gungnir_prob = cdata.get("gungnir_probability", 0.5)
    mcap = cdata.get("market_cap", 0)

    cap_category = "large"
    if mcap > 0:
        if mcap < 50e6:
            cap_category = "nano"
        elif mcap < 300e6:
            cap_category = "micro"
        elif mcap < 2e9:
            cap_category = "small"
        elif mcap < 10e9:
            cap_category = "mid"

    # Fetch ORATS data
    print(f"  Scanning {ticker}: {cdata.get('drug_name', 'N/A')} ({cat_date.date()}, {days_to}d)")

    spot = get_spot(ticker)
    if not spot:
        print(f"    [SKIP] No spot price available")
        results[ticker] = {**cdata, "days_to_catalyst": days_to, "classification": "AVOID",
                          "reason": "No spot price", "entry_score": -30}
        summary["AVOID"].append(ticker)
        continue

    chains = get_strikes_cached(ticker)
    if not chains or "data" not in chains or not chains["data"]:
        print(f"    [SKIP] No options chain")
        results[ticker] = {**cdata, "days_to_catalyst": days_to, "classification": "AVOID",
                          "reason": "No options chain", "entry_score": -30}
        summary["AVOID"].append(ticker)
        continue

    # Find target expiry (first expiry after catalyst)
    expiries = sorted(set(s["eod_date"] for s in chains["data"] if s.get("eod_date")))
    target_expiry = None
    for exp in expiries:
        exp_date = datetime.fromisoformat(exp.split("T")[0])
        if exp_date > cat_date:
            target_expiry = exp
            break

    if not target_expiry:
        print(f"    [SKIP] No expiry after catalyst")
        results[ticker] = {**cdata, "days_to_catalyst": days_to, "classification": "AVOID",
                          "reason": "No expiry after catalyst", "entry_score": -30}
        summary["AVOID"].append(ticker)
        continue

    dte = (datetime.fromisoformat(target_expiry.split("T")[0]) - TODAY).days

    # Filter to target expiry, call options
    target_strikes = [s for s in chains["data"] if s.get("eod_date") == target_expiry and s.get("callMid", 0) > 0.01]

    if not target_strikes:
        print(f"    [SKIP] No call options at target expiry")
        results[ticker] = {**cdata, "days_to_catalyst": days_to, "classification": "AVOID",
                          "reason": "No calls at target expiry", "entry_score": -30}
        summary["AVOID"].append(ticker)
        continue

    # Find ATM strike
    atm_strike = min(target_strikes, key=lambda s: abs(float(s.get("strike", 0)) - spot))

    call_bid = float(atm_strike.get("callBid", 0))
    call_ask = float(atm_strike.get("callAsk", 0))
    call_mid = float(atm_strike.get("callMid", 0))
    call_oi = int(atm_strike.get("callOpenInterest", 0))
    call_vol = int(atm_strike.get("callVolume", 0))
    call_iv = float(atm_strike.get("callIv", 0)) * 100  # Convert to percent

    if call_bid == 0 or call_ask == 0:
        print(f"    [SKIP] Stale ATM strike (bid={call_bid}, ask={call_ask})")
        results[ticker] = {**cdata, "days_to_catalyst": days_to, "classification": "AVOID",
                          "reason": "Stale ATM strike", "entry_score": -30}
        summary["AVOID"].append(ticker)
        continue

    # Compute metrics
    real_40 = call_bid * 0.6 + call_ask * 0.4
    spread_pct = (call_ask - call_bid) / call_mid * 100 if call_mid > 0 else 100

    iv_pct = get_ivrank(ticker)

    # CORE classification
    is_core = False
    if is_readout and is_phase1_2 and days_to >= 1 and days_to <= 21 and dte >= 7 and dte <= 45:
        if gungnir_tier in ["ALPHA", "BETA"] or gungnir_prob >= 0.60:
            is_core = True

    # LOTTO classification
    is_lotto = False
    is_lotto_low_liq = False
    if is_pdufa and cap_category in ["micro", "nano"] and days_to >= 1 and days_to <= 21 and dte >= 7 and dte <= 45:
        if call_oi >= 50 and spread_pct <= 30:
            is_lotto = True
        elif call_oi >= 20:
            is_lotto_low_liq = True

    # EARLY classification
    is_early = False
    if (is_readout and is_phase1_2 or is_pdufa) and days_to > 21 and days_to <= 45 and dte >= 7 and dte <= 45:
        is_early = True

    # Compute entry_score
    score = 50
    classification = "AVOID"

    if is_core:
        score += 30
        classification = "CORE"
    elif is_lotto:
        score += 25
        classification = "LOTTO"
    elif is_lotto_low_liq:
        score += 10
        classification = "LOTTO_LOW_LIQ"
    elif is_early:
        score += 5
        classification = "EARLY"
    else:
        score -= 30

    # OI adjustment
    if 100 <= call_oi <= 499:
        score += 10
    elif call_oi < 20:
        score -= 15
    elif call_oi >= 500:
        score -= 5

    # Spread adjustment
    if spread_pct < 15:
        score += 5
    elif 30 <= spread_pct <= 50:
        score -= 10
    elif spread_pct > 50:
        score -= 25

    # IV adjustment
    if 60 <= iv_pct <= 85:
        score += 5
    elif iv_pct < 20:
        score -= 10
    elif iv_pct > 90:
        score -= 5

    # Volume adjustment
    if call_vol >= 100:
        score += 5

    # Days to catalyst adjustment
    if 5 <= days_to <= 14:
        score += 5
    elif 1 <= days_to <= 4:
        score += 2

    results[ticker] = {
        **cdata,
        "days_to_catalyst": days_to,
        "dte": dte,
        "spot": spot,
        "atm_strike": float(atm_strike.get("strike", 0)),
        "call_bid": call_bid,
        "call_ask": call_ask,
        "call_mid": call_mid,
        "call_real_40": real_40,
        "call_oi": call_oi,
        "call_vol": call_vol,
        "call_iv": call_iv,
        "spread_pct": spread_pct,
        "iv_percentile": iv_pct,
        "cap_category": cap_category,
        "classification": classification,
        "entry_score": max(-50, min(100, score))  # Clamp [−50, 100]
    }
    summary[classification].append(ticker)
    print(f"    [{classification}] score={score}, OI={call_oi}, spread={spread_pct:.1f}%, DTE={dte}")

# Save raw results
raw_file = Path("/sessions/confident-serene-ptolemy/mnt/9realms/q2_options_scan_apr19_v2_raw.json")
with open(raw_file, 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nSaved raw results: {raw_file}")

# Save ranked results
ranked = {}
for cls in ["CORE", "LOTTO", "LOTTO_LOW_LIQ", "EARLY"]:
    tickers = summary[cls]
    ranked[cls] = sorted(
        [results[t] for t in tickers],
        key=lambda x: x["entry_score"],
        reverse=True
    )

ranked_file = Path("/sessions/confident-serene-ptolemy/mnt/9realms/q2_options_scan_apr19_v2_ranked.json")
with open(ranked_file, 'w') as f:
    json.dump(ranked, f, indent=2, default=str)
print(f"Saved ranked results: {ranked_file}")

# Build markdown report
markdown = f"""# Q2 2026 ORATS Options Scan (Apr 19, 2026)
**BIFROST v1.3 Corrected Rules**

## Summary
- **CORE** (Phase 1/2 positive readout): {len(summary['CORE'])} candidates
- **LOTTO** (Micro/nano PDUFA, liquid): {len(summary['LOTTO'])} candidates
- **LOTTO_LOW_LIQ** (Micro/nano PDUFA, marginal): {len(summary['LOTTO_LOW_LIQ'])} candidates
- **EARLY** (T+22 to T+45, monitor): {len(summary['EARLY'])} candidates
- **AVOID**: {len(summary['AVOID'])} catalysts (out of range, no chain, etc.)

---
## TOP 10 CORE CANDIDATES
"""

for i, result in enumerate(ranked["CORE"][:10], 1):
    markdown += f"""
### {i}. {result['ticker']} — {result.get('drug_name', 'N/A')}
- **Catalyst**: {result.get('catalyst_date', 'N/A')} ({result['days_to_catalyst']}d out)
- **Phase**: {result.get('catalyst_type', 'N/A')}
- **Gungnir Tier**: {result.get('gungnir_tier', 'N/A')} (prob={result.get('gungnir_probability', 0):.2f})
- **Market Cap**: ${result.get('market_cap', 0)/1e9:.2f}B ({result['cap_category']})
- **Options ATM**:
  - Strike: ${result['atm_strike']:.2f} (spot ${result['spot']:.2f})
  - DTE: {result['dte']} days
  - Call Bid/Ask/Mid: ${result['call_bid']:.2f} / ${result['call_ask']:.2f} / ${result['call_mid']:.2f}
  - Real 40 Fill: ${result['call_real_40']:.2f}
  - OI: {result['call_oi']} | Vol: {result['call_vol']} | IV: {result['call_iv']:.1f}%
  - Spread: {result['spread_pct']:.1f}% | IV Percentile: {result['iv_percentile']:.0f}
- **Entry Score**: {result['entry_score']}/100
"""

markdown += f"""

---
## TOP 10 LOTTO CANDIDATES
"""

for i, result in enumerate(ranked["LOTTO"][:10], 1):
    markdown += f"""
### {i}. {result['ticker']} — {result.get('drug_name', 'N/A')}
- **Catalyst**: {result.get('catalyst_date', 'N/A')} ({result['days_to_catalyst']}d out)
- **Market Cap**: ${result.get('market_cap', 0)/1e6:.0f}M ({result['cap_category']})
- **Options ATM**:
  - Strike: ${result['atm_strike']:.2f} (spot ${result['spot']:.2f})
  - DTE: {result['dte']} days
  - Call Bid/Ask/Mid: ${result['call_bid']:.2f} / ${result['call_ask']:.2f} / ${result['call_mid']:.2f}
  - Real 40 Fill: ${result['call_real_40']:.2f}
  - OI: {result['call_oi']} | Vol: {result['call_vol']} | IV: {result['call_iv']:.1f}%
  - Spread: {result['spread_pct']:.1f}% | IV Percentile: {result['iv_percentile']:.0f}
- **Entry Score**: {result['entry_score']}/100
"""

if len(ranked["EARLY"]) > 0:
    markdown += f"""

---
## EARLY MONITOR (T+22 to T+45, enter in 1-2 weeks)
"""
    for i, result in enumerate(ranked["EARLY"][:10], 1):
        markdown += f"""
### {i}. {result['ticker']} — {result.get('drug_name', 'N/A')}
- **Catalyst**: {result.get('catalyst_date', 'N/A')} ({result['days_to_catalyst']}d out)
- **Market Cap**: ${result.get('market_cap', 0)/1e6:.0f}M
- **Options**: DTE {result['dte']}d, OI {result['call_oi']}, Spread {result['spread_pct']:.1f}%
- **Entry Score**: {result['entry_score']}/100
"""

markdown += f"""

---
## PORTFOLIO CALLOUTS

### GRCE (GTX-104, PDUFA Apr 23)
"""
if "GRCE" in results:
    grce = results["GRCE"]
    markdown += f"- **Classification**: {grce.get('classification', 'N/A')} (score {grce.get('entry_score', 0)}/100)\n"
    markdown += f"- **Days to catalyst**: {grce.get('days_to_catalyst', 'N/A')}\n"
    markdown += f"- **Options**: ATM ${grce.get('atm_strike', 0):.2f}, Bid ${grce.get('call_bid', 0):.2f} / Ask ${grce.get('call_ask', 0):.2f}, OI {grce.get('call_oi', 0)}\n"
    markdown += f"- **Verdict**: {grce.get('classification', 'AVOID')} — {'Tradeable' if grce.get('classification') in ['CORE', 'LOTTO'] else 'Not a v1.3 edge'}\n"
else:
    markdown += "- Not in Q2 range or no data\n"

for ticker in ["WHWK", "CRDF", "CABA", "ALXO"]:
    if ticker in results:
        r = results[ticker]
        markdown += f"""
### {ticker} ({r.get('drug_name', 'N/A')}, {r.get('catalyst_date', 'N/A')})
- **Classification**: {r.get('classification', 'N/A')} (score {r.get('entry_score', 0)}/100)
- **Days to catalyst**: {r.get('days_to_catalyst', 'N/A')}
- **Options**: DTE {r.get('dte', 'N/A')}, OI {r.get('call_oi', 0)}, Spread {r.get('spread_pct', 0):.1f}%
- **Verdict**: {r.get('classification', 'AVOID')} — {'Tradeable' if r.get('classification') in ['CORE', 'LOTTO'] else 'Not a v1.3 edge'}
"""

markdown += f"""

---
## VERDICT: What to Buy Today (Apr 19)

**CORE EDGE (Phase 1/2 Positive Readout)**: {len([r for r in ranked['CORE'] if r['days_to_catalyst'] <= 21])} candidates in entry window.
- Target: ATM calls, T-14 → T-1 entry, hold through post_1d for ALPHA/BETA tiers
- Top pick: {ranked['CORE'][0]['ticker'] if ranked['CORE'] else 'N/A'}

**LOTTO EDGE (Micro/Nano PDUFA)**: {len([r for r in ranked['LOTTO'] if r['days_to_catalyst'] <= 21])} liquid candidates.
- Target: OI 100-499 sweet spot, spread <30%, size ≤1% per position
- Top pick: {ranked['LOTTO'][0]['ticker'] if ranked['LOTTO'] else 'N/A'}

**PORTFOLIO SNAPSHOT**:
- GRCE (PDUFA Apr 23, 4d): {results.get('GRCE', {}).get('classification', 'N/A')}
- WHWK (AACR Apr 17-22, Readout): {results.get('WHWK', {}).get('classification', 'N/A')}
- CRDF (AACR Apr 17-22, Readout): {results.get('CRDF', {}).get('classification', 'N/A')}
- CABA (AAN Apr 20, Readout): {results.get('CABA', {}).get('classification', 'N/A')}
- ALXO (ESMO May 7, Readout): {results.get('ALXO', {}).get('classification', 'N/A')}

---
## Honest Caveats

- **No T-5 floor**: Events 1-5 days out ARE included if they meet BIFROST v1.3 criteria
- **OI liquidity**: 20+ is tradeable; 50+ is preferred; 100-499 is the sweet spot
- **Spread capture**: 40% capture (bid × 0.6 + ask × 0.4) = realistic fill expectation
- **CI note**: Entry scores are point estimates; actual results have bootstrapped uncertainty
- **Sample sizes**: LOTTO sample is small (only micro/nano); CORE unlocks with Phase 1/2 readouts
- **Honest calibration**: Use for ranking, not as calibrated probabilities

---

Generated: {TODAY.date()} · ORATS Delayed Data API · BIFROST v1.3 rules · CORE/LOTTO edge definitions locked
"""

md_file = Path("/sessions/confident-serene-ptolemy/mnt/9realms/Q2_Options_Scan_Apr19_v2.md")
with open(md_file, 'w') as f:
    f.write(markdown)
print(f"Saved markdown report: {md_file}")

# Print summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"CORE candidates:        {len(summary['CORE']):3d}")
print(f"LOTTO candidates:       {len(summary['LOTTO']):3d}")
print(f"LOTTO (low liq):        {len(summary['LOTTO_LOW_LIQ']):3d}")
print(f"EARLY monitor:          {len(summary['EARLY']):3d}")
print(f"AVOID:                  {len(summary['AVOID']):3d}")
print(f"TOTAL Q2 catalysts:     {len(q2_catalysts):3d}")
print("="*70)

if ranked["CORE"]:
    print(f"\nTop 3 CORE by score:")
    for i, r in enumerate(ranked["CORE"][:3], 1):
        print(f"  {i}. {r['ticker']:6s} {r.get('drug_name', 'N/A'):20s} DTE{r['dte']:2d} OI{r['call_oi']:4d} score{r['entry_score']:3.0f}")

if ranked["LOTTO"]:
    print(f"\nTop 3 LOTTO by score:")
    for i, r in enumerate(ranked["LOTTO"][:3], 1):
        print(f"  {i}. {r['ticker']:6s} {r.get('drug_name', 'N/A'):20s} DTE{r['dte']:2d} OI{r['call_oi']:4d} score{r['entry_score']:3.0f}")

print("\nFiles saved:")
print(f"  - {raw_file}")
print(f"  - {ranked_file}")
print(f"  - {md_file}")
