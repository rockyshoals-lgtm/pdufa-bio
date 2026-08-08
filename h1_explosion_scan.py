#!/usr/bin/env python3
"""
H1 2026 EXPLOSION SCAN — Score ALL catalysts through BIFROST v5.1
=================================================================
Loads 366 H1 catalysts, fetches live yfinance SI, scores through
explosion detector, ranks by P(explosion).
"""

import json, sys, time, math, warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings('ignore')
DIR = Path(__file__).parent
sys.path.insert(0, str(DIR))

from mcp_9realms_vnext import tool_explosion_score

# ── Phase 1: Load catalysts ──────────────────────────────────────────────
print("=" * 80)
print("  H1 2026 EXPLOSION SCAN — BIFROST v5.1")
print("=" * 80)

with open(DIR / "catalyst_scores_v33.json") as f:
    all_cats = json.load(f)

# H1 2026: Jan–Jun 2026, and also include April's current portfolio dates
h1 = [c for c in all_cats
      if c.get("catalyst_date", "") >= "2026-01-01"
      and c.get("catalyst_date", "") <= "2026-06-30"]

print(f"\n  Total H1 2026 catalysts: {len(h1)}")

# Get unique tickers
tickers = list(set(c["ticker"] for c in h1 if c.get("ticker")))
print(f"  Unique tickers: {len(tickers)}")

# ── Phase 2: Fetch yfinance SI for all tickers ──────────────────────────
print(f"\n  Fetching yfinance data for {len(tickers)} tickers...")

si_cache_path = DIR / "short_interest_snapshot.json"
with open(si_cache_path) as f:
    si_cache = json.load(f)

# Find tickers we don't have yet
missing = [t for t in tickers if t not in si_cache or "error" in si_cache.get(t, {})]
print(f"  Already cached: {len(tickers) - len(missing)}, need to fetch: {len(missing)}")

if missing:
    import yfinance as yf
    for i, ticker in enumerate(missing):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            si_cache[ticker] = {
                "ticker": ticker,
                "shares_short": info.get("sharesShort", 0) or 0,
                "short_pct_float": info.get("shortPercentOfFloat", 0) or 0,
                "short_ratio": info.get("shortRatio", 0) or 0,
                "float_shares": info.get("floatShares", 0) or 0,
                "shares_outstanding": info.get("sharesOutstanding", 0) or 0,
                "avg_volume": info.get("averageVolume", 0) or 0,
                "market_cap": info.get("marketCap", 0) or 0,
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0) or 0,
                "current_price": info.get("currentPrice", 0) or info.get("regularMarketPrice", 0) or 0,
                "fetch_date": datetime.now().strftime("%Y-%m-%d"),
            }
        except Exception as e:
            si_cache[ticker] = {"ticker": ticker, "error": str(e)[:100]}
        if (i + 1) % 25 == 0:
            print(f"    [{i+1}/{len(missing)}] {ticker}")
        time.sleep(0.3)

    # Save updated cache
    with open(si_cache_path, "w") as f:
        json.dump(si_cache, f, indent=2, default=str)
    print(f"  SI cache updated: {len(si_cache)} total tickers")

# ── Phase 3: Score ALL catalysts through v5.1 ───────────────────────────
print(f"\n  Scoring {len(h1)} catalysts through v5.1 Explosion Detector...")

results = []
for cat in h1:
    ticker = cat.get("ticker", "")
    si = si_cache.get(ticker, {})
    if "error" in si:
        si = {}

    # Get price — use yfinance current price if available, else catalog price
    price = float(si.get("current_price", 0) or 0)
    if price <= 0:
        price = float(cat.get("price", 0) or 0)
    if price <= 0:
        continue  # Skip if no price

    mcap = float(si.get("market_cap", 0) or cat.get("market_cap", 0) or 0)
    if mcap <= 0:
        mcap = price * 50e6  # rough estimate

    high_52w = float(si.get("fifty_two_week_high", 0) or 0)

    # Determine ODIN-equivalent score
    # For PDUFA events, use a rough proxy based on stage
    # For phase readouts, use gungnir_probability as the "expected" prob
    is_pdufa = cat.get("is_pdufa", False)
    stage = cat.get("stage", "")

    if is_pdufa or "PDUFA" in stage:
        # Use a rough ODIN proxy: NDA/BLA filings have ~68% base rate
        if "priority" in stage.lower():
            odin_proxy = 0.80
        else:
            odin_proxy = 0.68
    else:
        # Use gungnir_probability for phase readouts
        odin_proxy = float(cat.get("gungnir_probability", 0.5) or 0.5)

    # SI data
    pct_si = float(si.get("short_pct_float", 0) or 0)
    dtc = float(si.get("short_ratio", 0) or 0)
    flt = float(si.get("float_shares", 0) or 0)

    try:
        e = tool_explosion_score(
            ticker=ticker, odin_score=odin_proxy, eve_price=price,
            market_cap=mcap, high_52w=high_52w, volume_ratio=1.0,
            runup_30d=0.0,  # don't have real-time runup, use 0
            float_shares=flt, pct_float_short=pct_si, days_to_cover=dtc,
        )
    except Exception as ex:
        continue

    results.append({
        "ticker": ticker,
        "name": cat.get("name", ""),
        "drug": cat.get("drug", ""),
        "indication": cat.get("indication", ""),
        "stage": stage,
        "catalyst_date": cat.get("catalyst_date", ""),
        "conference": cat.get("conference", ""),
        "is_pdufa": is_pdufa,
        "price": round(price, 2),
        "mcap_m": round(mcap / 1e6, 1),
        "mcap_label": e.get("market_cap_label", ""),
        "odin_proxy": round(odin_proxy, 3),
        "gungnir_prob": round(float(cat.get("gungnir_probability", 0) or 0), 3),
        "gungnir_tier": cat.get("gungnir_tier", ""),
        "investment_score": float(cat.get("investment_score", 0) or 0),
        "investment_tier": cat.get("investment_tier", ""),
        "explosion_prob": e["explosion_probability"],
        "explosion_tier": e["explosion_tier"],
        "position_mult": e["position_multiplier"],
        "pct_float_short": round(pct_si * 100, 1),
        "days_to_cover": round(dtc, 1),
        "float_m": round(flt / 1e6, 1) if flt > 0 else 0,
        "high_52w": round(high_52w, 2),
        "price_compression": round(price / high_52w, 3) if high_52w > 0 else 1.0,
        "interpretation": e.get("interpretation", ""),
    })

print(f"  Scored: {len(results)} catalysts")

# ── Phase 4: Rank and display ────────────────────────────────────────────
results.sort(key=lambda x: x["explosion_prob"], reverse=True)

# Tier counts
from collections import Counter
tier_counts = Counter(r["explosion_tier"] for r in results)
print(f"\n  Tier Distribution:")
for tier in ["SNIPER", "ELEVATED", "NORMAL", "QUIET"]:
    print(f"    {tier}: {tier_counts.get(tier, 0)}")

# Top results
print(f"\n{'='*120}")
print(f"  TOP EXPLOSION CANDIDATES — H1 2026 (ranked by P(explosion))")
print(f"{'='*120}")
print(f"  {'#':>3s} {'Ticker':<7s} {'P(exp)':>7s} {'Tier':<9s} {'Mult':>4s} {'Price':>7s} {'Mcap':>8s} "
      f"{'SI%':>5s} {'DTC':>5s} {'Float':>7s} {'Compress':>8s} {'Stage':<18s} {'Date':<11s} {'Drug/Indication'}")
print(f"  {'-'*118}")

for i, r in enumerate(results[:60], 1):
    drug_ind = f"{r['drug'][:20]} / {r['indication'][:25]}" if r['drug'] else r['indication'][:45]
    compress = f"{r['price_compression']:.2f}" if r['price_compression'] < 1.0 else "—"
    flt = f"{r['float_m']:.0f}M" if r['float_m'] > 0 else "—"
    si = f"{r['pct_float_short']:.1f}" if r['pct_float_short'] > 0 else "—"
    dtc = f"{r['days_to_cover']:.1f}" if r['days_to_cover'] > 0 else "—"

    marker = "🎯" if r["explosion_tier"] == "SNIPER" else "⚡" if r["explosion_tier"] == "ELEVATED" else "  "

    print(f"{marker}{i:>3d} {r['ticker']:<7s} {r['explosion_prob']:>6.1%} {r['explosion_tier']:<9s} {r['position_mult']:>3.1f}x "
          f"${r['price']:>6.2f} {r['mcap_label']:>8s} {si:>5s} {dtc:>5s} {flt:>7s} {compress:>8s} "
          f"{r['stage']:<18s} {r['catalyst_date']:<11s} {drug_ind}")

# SNIPER deep dives
snipers = [r for r in results if r["explosion_tier"] == "SNIPER"]
elevated = [r for r in results if r["explosion_tier"] == "ELEVATED"]

print(f"\n{'='*120}")
print(f"  SNIPER DEEP DIVES ({len(snipers)} setups)")
print(f"{'='*120}")

for r in snipers:
    print(f"""
  🎯 {r['ticker']} — P(explosion) = {r['explosion_prob']:.1%}
     {r['name']} | {r['drug']} | {r['indication']}
     Stage: {r['stage']} | Date: {r['catalyst_date']} | Conference: {r['conference'] or 'N/A'}
     Price: ${r['price']:.2f} | Mcap: {r['mcap_label']} | 52wH: ${r['high_52w']:.2f} | Compression: {r['price_compression']:.2f}
     SI: {r['pct_float_short']:.1f}% | DTC: {r['days_to_cover']:.1f} | Float: {r['float_m']:.1f}M shares
     Gungnir: {r['gungnir_prob']:.3f} ({r['gungnir_tier']}) | Inv Score: {r['investment_score']:.1f} ({r['investment_tier']})
     {r['interpretation']}""")

# Save full results
output_path = DIR / "h1_2026_explosion_scan.json"
with open(output_path, "w") as f:
    json.dump({"scan_date": datetime.now().isoformat(), "n_scored": len(results),
               "snipers": len(snipers), "elevated": len(elevated),
               "results": results}, f, indent=2)
print(f"\n  Full results saved: {output_path}")

