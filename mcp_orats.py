#!/usr/bin/env python3
"""
MCP ORATS — IV Intelligence Module for 9 Realms
=================================================
Connects to ORATS Delayed Data API ($99/mo tier) to provide:
  - IV Rank & Percentile (current + historical)
  - IV Cheapness Scoring for catalyst tickers
  - IV Term Structure analysis
  - Historical Volatility time series
  - SMV Summaries (interpolated IV at various DTEs)
  - Options chain snapshots with Greeks

Integration: Companion MCP to mcp_9realms_vnext.py.
  Score with ODIN/Gungnir first, then use orats_iv_scan to find cheap options.

Base URL: https://api.orats.io/datav2
Auth: Token via query parameter
Rate Limit: 100 requests/minute, 20,000/month (delayed tier)

Author: 9 Realms / pdufa.bio
Version: 1.0.0
Date: April 2026
"""

import json
import os
import sys
import math
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ORATS_BASE_URL = "https://api.orats.io/datav2"
ORATS_TOKEN = os.environ.get("ORATS_API_TOKEN", "")
VERSION = "1.0.0"
CACHE_DIR = Path(__file__).parent / "orats_cache"
CACHE_TTL_SECONDS = 900  # 15 min cache for delayed data (already 15min delayed)

# Rate limiting
_request_timestamps: List[float] = []
MAX_REQUESTS_PER_MINUTE = 95  # leave headroom under 100

# ---------------------------------------------------------------------------
# HTTP Client (stdlib — no external deps required)
# ---------------------------------------------------------------------------
import urllib.request
import urllib.parse
import urllib.error
import ssl

# Disable SSL verification warnings for some environments
_ssl_ctx = ssl.create_default_context()

def _rate_limit():
    """Enforce 100 req/min rate limit."""
    now = time.time()
    # Remove timestamps older than 60 seconds
    while _request_timestamps and _request_timestamps[0] < now - 60:
        _request_timestamps.pop(0)
    if len(_request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        sleep_time = 60 - (now - _request_timestamps[0]) + 0.1
        if sleep_time > 0:
            time.sleep(sleep_time)
    _request_timestamps.append(time.time())

def _cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

def _get_cached(url: str) -> Optional[dict]:
    """Check file cache for recent response."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{_cache_key(url)}.json"
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            try:
                return json.loads(cache_file.read_text())
            except:
                pass
    return None

def _set_cache(url: str, data: dict):
    """Write response to file cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{_cache_key(url)}.json"
    try:
        cache_file.write_text(json.dumps(data))
    except:
        pass

def orats_get(endpoint: str, params: dict = None) -> dict:
    """
    Make authenticated GET request to ORATS API.
    Returns parsed JSON response.
    """
    if not ORATS_TOKEN:
        return {"error": "ORATS_API_TOKEN environment variable not set. Get your API key at https://orats.com/data-api"}

    params = params or {}
    params["token"] = ORATS_TOKEN

    url = f"{ORATS_BASE_URL}{endpoint}?{urllib.parse.urlencode(params)}"

    # Check cache
    cached = _get_cached(url)
    if cached:
        cached["_cached"] = True
        return cached

    # Rate limit
    _rate_limit()

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            _set_cache(url, data)
            return data
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}: {body[:500]}"}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Core Data Functions
# ---------------------------------------------------------------------------

def get_iv_rank(tickers: str) -> dict:
    """
    Get current IV rank and percentile for up to 10 tickers.

    Returns: iv, ivRank1m, ivPct1m, ivRank1y, ivPct1y
    - ivRank1y: (Current IV - 1yr Low) / (1yr High - 1yr Low). 0 = at yearly low, 100 = at yearly high.
    - ivPct1y: Percentile — what % of past year's IV readings are below current. 15 = cheaper than 85% of the year.
    NOTE: ORATS returns iv as absolute % (e.g., 111.35 = 111.35%), ranks/pcts as 0-100 range.
    """
    return orats_get("/ivrank", {"ticker": tickers})

def get_iv_rank_history(tickers: str, trade_date: str = None) -> dict:
    """
    Get historical IV rank data.
    trade_date: specific date or range like "2026-01-01,2026-04-04".
    If omitted, returns full history (can be 1000+ rows).
    """
    params = {"ticker": tickers}
    if trade_date:
        params["tradeDate"] = trade_date
    return orats_get("/hist/ivrank", params)

def get_summaries(tickers: str) -> dict:
    """
    Get SMV summary data — interpolated IV at various DTEs.
    Includes: iv10d, iv20d, iv30d, iv60d, iv90d, iv6m, iv1y, slope, deriv, etc.
    """
    return orats_get("/summaries", {"ticker": tickers})

def get_summaries_history(tickers: str, trade_date: str = None) -> dict:
    """Get historical SMV summaries."""
    params = {"ticker": tickers}
    if trade_date:
        params["tradeDate"] = trade_date
    return orats_get("/hist/summaries", params)

def get_historical_volatility(tickers: str, trade_date: str = None) -> dict:
    """
    Get historical realized volatility across multiple windows.
    Includes: orHv5d through orHv1000d, clsHv5d through clsHv1000d.
    """
    params = {"ticker": tickers}
    if trade_date:
        params["tradeDate"] = trade_date
    return orats_get("/hist/hvs", params)

def get_core_data(tickers: str) -> dict:
    """
    Get core analytics — IV percentiles, correlation, beta, earnings data.
    Includes: ivPctile1m, ivPctile1y, ivPctileSpy, orHvXd, clsHvXd, etc.
    """
    return orats_get("/cores", {"ticker": tickers})

def get_strikes(tickers: str, dte: str = None, delta: str = None) -> dict:
    """
    Get current options chain with Greeks and IV per strike.
    dte: filter like "14,60" for 14-60 DTE range
    delta: filter like "0.3,0.7" for delta range
    """
    params = {"ticker": tickers}
    if dte:
        params["dte"] = dte
    if delta:
        params["delta"] = delta
    return orats_get("/strikes", params)

def get_daily_prices(tickers: str, trade_date: str = None) -> dict:
    """Get daily OHLCV price data."""
    params = {"ticker": tickers}
    if trade_date:
        params["tradeDate"] = trade_date
    return orats_get("/hist/dailies", params)


# ---------------------------------------------------------------------------
# IV Cheapness Scoring Engine
# ---------------------------------------------------------------------------

def compute_iv_cheapness(iv_rank_data: dict, summary_data: dict, hv_data: dict,
                         days_to_catalyst: int) -> dict:
    """
    Compute IV Cheapness Score (0-100) using REAL ORATS data.

    Components:
    1. IV Percentile 1Y (35 pts): ivPct1y — where current IV sits in 52-week range
    2. IV/RV Ratio (25 pts): current IV vs 30d realized vol
    3. Timing Sweet Spot (25 pts): days to catalyst relative to optimal T-14 entry
    4. Term Structure (15 pts): short-dated IV vs long-dated IV ratio
    """
    score = 0
    details = {}

    # --- Component 1: IV Percentile 1Y (35 pts) ---
    iv_pct_1y = iv_rank_data.get("ivPct1y")
    iv_rank_1y = iv_rank_data.get("ivRank1y")
    current_iv = iv_rank_data.get("iv")

    if iv_pct_1y is not None:
        pct = float(iv_pct_1y)  # already 0-100 from ORATS
        details["iv_pct_1y"] = round(pct, 1)

        if pct < 15:
            score += 35
            details["pct_verdict"] = "VERY CHEAP"
        elif pct < 30:
            score += 28
            details["pct_verdict"] = "CHEAP"
        elif pct < 50:
            score += 18
            details["pct_verdict"] = "FAIR"
        elif pct < 75:
            score += 8
            details["pct_verdict"] = "EXPENSIVE"
        else:
            score += 0
            details["pct_verdict"] = "VERY EXPENSIVE"

    if iv_rank_1y is not None:
        details["iv_rank_1y"] = round(float(iv_rank_1y), 1)  # already 0-100
    if current_iv is not None:
        details["current_iv"] = round(float(current_iv), 1)  # already in % (e.g. 111.35)

    # --- Component 2: IV/RV Ratio (25 pts) ---
    rv_30d = None
    if hv_data:
        rv_30d = hv_data.get("clsHv30d") or hv_data.get("orHv30d")

    if current_iv and rv_30d:
        try:
            iv_val = float(current_iv)   # already in % (e.g., 111.35)
            rv_val = float(rv_30d)       # already in % from ORATS
            if rv_val > 0:
                ratio = iv_val / rv_val
                details["iv_rv_ratio"] = round(ratio, 2)

                if ratio < 1.2:
                    score += 25
                    details["iv_rv_verdict"] = "VERY CHEAP"
                elif ratio < 1.5:
                    score += 20
                    details["iv_rv_verdict"] = "CHEAP"
                elif ratio < 2.0:
                    score += 12
                    details["iv_rv_verdict"] = "FAIR"
                elif ratio < 3.0:
                    score += 5
                    details["iv_rv_verdict"] = "EXPENSIVE"
                else:
                    score += 0
                    details["iv_rv_verdict"] = "VERY EXPENSIVE"
        except (ValueError, TypeError):
            pass

    # --- Component 3: Timing (25 pts) ---
    dtc = days_to_catalyst
    details["days_to_catalyst"] = dtc

    if 14 <= dtc <= 35:
        score += 25
        details["timing_verdict"] = "SWEET SPOT"
    elif 10 <= dtc < 14:
        score += 20
        details["timing_verdict"] = "GOOD"
    elif 35 < dtc <= 60:
        score += 18
        details["timing_verdict"] = "EARLY"
    elif 7 <= dtc < 10:
        score += 10
        details["timing_verdict"] = "LATE"
    elif dtc > 60:
        score += 12
        details["timing_verdict"] = "TOO EARLY (watch)"
    else:
        score += 0
        details["timing_verdict"] = "TOO LATE (<7d)"

    # --- Component 4: Term Structure (15 pts) ---
    # Summaries IV fields are decimal (1.4197 = 141.97%) but ratio is unitless
    if summary_data:
        iv_30d = summary_data.get("iv30d")
        iv_90d = summary_data.get("iv90d")
        if iv_30d and iv_90d:
            try:
                tilt = float(iv_30d) / float(iv_90d) if float(iv_90d) > 0 else 1.0
                details["term_structure_tilt"] = round(tilt, 2)

                if tilt < 1.1:
                    score += 15
                    details["tilt_verdict"] = "FLAT (no expansion)"
                elif tilt < 1.3:
                    score += 10
                    details["tilt_verdict"] = "MILD expansion"
                elif tilt < 1.8:
                    score += 5
                    details["tilt_verdict"] = "MODERATE expansion"
                else:
                    score += 0
                    details["tilt_verdict"] = "HEAVY expansion"
            except (ValueError, TypeError):
                score += 8
                details["tilt_verdict"] = "N/A"
    else:
        score += 8
        details["tilt_verdict"] = "N/A"

    details["cheapness_score"] = score

    if score >= 80:
        details["overall"] = "DIRT CHEAP"
    elif score >= 65:
        details["overall"] = "CHEAP"
    elif score >= 45:
        details["overall"] = "FAIR VALUE"
    elif score >= 30:
        details["overall"] = "EXPENSIVE"
    else:
        details["overall"] = "OVERPRICED"

    return details


# ---------------------------------------------------------------------------
# MCP Tool Functions (callable from MCP server or directly)
# ---------------------------------------------------------------------------

def tool_orats_iv_rank(tickers: str) -> str:
    """
    Get current IV rank and percentile for biotech catalyst tickers.

    Returns IV, IV Rank (1m/1y), and IV Percentile (1m/1y) for each ticker.
    Use to determine if options are cheap (low percentile) or expensive (high percentile).

    Args:
        tickers: Comma-separated ticker symbols (max 10). E.g., "CABA,GRCE,NTLA"
    """
    data = get_iv_rank(tickers)
    if "error" in data:
        return json.dumps(data)

    results = data.get("data", [])
    output = []
    for row in results:
        ticker = row.get("ticker", "?")
        iv = row.get("iv", 0)           # already in % (e.g., 111.35)
        rank_1m = row.get("ivRank1m", 0) # already 0-100
        pct_1m = row.get("ivPct1m", 0)   # already 0-100
        rank_1y = row.get("ivRank1y", 0) # already 0-100
        pct_1y = row.get("ivPct1y", 0)   # already 0-100

        output.append({
            "ticker": ticker,
            "current_iv": f"{float(iv):.1f}%" if iv else "N/A",
            "iv_rank_1m": f"{float(rank_1m):.1f}%" if rank_1m else "N/A",
            "iv_pct_1m": f"{float(pct_1m):.1f}%" if pct_1m else "N/A",
            "iv_rank_1y": f"{float(rank_1y):.1f}%" if rank_1y else "N/A",
            "iv_pct_1y": f"{float(pct_1y):.1f}%" if pct_1y else "N/A",
            "cheap_signal": "CHEAP" if pct_1y and float(pct_1y) < 30 else
                           "EXPENSIVE" if pct_1y and float(pct_1y) > 70 else "FAIR",
        })

    return json.dumps({"tickers": output, "note": "IV Rank 1Y < 30% = cheap options, > 70% = expensive"}, indent=2)


def tool_orats_iv_scan(tickers: str, catalyst_dates: str) -> str:
    """
    IV Cheapness Scanner — find the cheapest options before catalyst events.

    Pulls IV rank, term structure, and historical vol for each ticker,
    computes a cheapness score (0-100), and ranks from cheapest to most expensive.

    Args:
        tickers: Comma-separated ticker symbols (max 10). E.g., "CABA,GRCE,NTLA"
        catalyst_dates: Matching comma-separated catalyst dates (YYYY-MM-DD). E.g., "2026-04-20,2026-04-23,2026-08-31"
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    date_list = [d.strip() for d in catalyst_dates.split(",")]

    if len(ticker_list) != len(date_list):
        return json.dumps({"error": "Number of tickers must match number of catalyst_dates"})

    today = datetime.now()
    results = []

    # Batch fetch IV rank (up to 10 at once)
    batch_tickers = ",".join(ticker_list[:10])
    iv_rank_resp = get_iv_rank(batch_tickers)
    iv_rank_map = {}
    for row in iv_rank_resp.get("data", []):
        iv_rank_map[row.get("ticker", "").upper()] = row

    # Batch fetch summaries
    summary_resp = get_summaries(batch_tickers)
    summary_map = {}
    for row in summary_resp.get("data", []):
        summary_map[row.get("ticker", "").upper()] = row

    # Batch fetch historical vol
    hv_resp = get_historical_volatility(batch_tickers)
    hv_map = {}
    for row in hv_resp.get("data", []):
        hv_map[row.get("ticker", "").upper()] = row

    for ticker, cat_date_str in zip(ticker_list, date_list):
        try:
            cat_date = datetime.strptime(cat_date_str, "%Y-%m-%d")
            dtc = (cat_date - today).days
        except:
            dtc = 30

        iv_data = iv_rank_map.get(ticker, {})
        smv_data = summary_map.get(ticker, {})
        hv_data = hv_map.get(ticker, {})

        if not iv_data:
            results.append({
                "ticker": ticker,
                "catalyst_date": cat_date_str,
                "days_to_catalyst": dtc,
                "cheapness_score": -1,
                "overall": "NO DATA",
                "error": "No IV rank data available"
            })
            continue

        cheapness = compute_iv_cheapness(iv_data, smv_data, hv_data, dtc)

        results.append({
            "ticker": ticker,
            "catalyst_date": cat_date_str,
            "days_to_catalyst": dtc,
            **cheapness
        })

    # Sort by cheapness score descending (cheapest first)
    results.sort(key=lambda x: x.get("cheapness_score", -1), reverse=True)

    return json.dumps({
        "scan_date": today.strftime("%Y-%m-%d"),
        "n_scanned": len(results),
        "rankings": results,
        "interpretation": {
            "80-100": "DIRT CHEAP — IV hasn't expanded, buy now",
            "65-79": "CHEAP — good entry, IV starting to move",
            "45-64": "FAIR VALUE — reasonable but not a steal",
            "30-44": "EXPENSIVE — IV already elevated",
            "0-29": "OVERPRICED — IV fully expanded, don't chase"
        }
    }, indent=2)


def tool_orats_iv_history(ticker: str, days: int = 90) -> str:
    """
    Get IV rank history for a single ticker over the past N days.

    Use to see how IV has evolved approaching a catalyst — detect expansion in progress.

    Args:
        ticker: Single ticker symbol. E.g., "CABA"
        days: Number of days of history (default 90, max 365)
    """
    days = min(days, 365)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    date_range = f"{start_date.strftime('%Y-%m-%d')},{end_date.strftime('%Y-%m-%d')}"

    data = get_iv_rank_history(ticker.upper(), date_range)
    if "error" in data:
        return json.dumps(data)

    rows = data.get("data", [])

    # Summarize the trajectory
    if rows:
        ivs = [float(r.get("iv", 0)) for r in rows if r.get("iv")]
        ranks = [float(r.get("ivRank1y", 0)) for r in rows if r.get("ivRank1y")]
        pcts = [float(r.get("ivPct1y", 0)) for r in rows if r.get("ivPct1y")]

        summary = {
            "ticker": ticker.upper(),
            "period": f"{days} days",
            "data_points": len(rows),
            "iv_current": f"{ivs[-1]:.1f}%" if ivs else "N/A",
            "iv_min": f"{min(ivs):.1f}%" if ivs else "N/A",
            "iv_max": f"{max(ivs):.1f}%" if ivs else "N/A",
            "iv_rank_1y_current": f"{ranks[-1]:.1f}%" if ranks else "N/A",
            "iv_pct_1y_current": f"{pcts[-1]:.1f}%" if pcts else "N/A",
            "expanding": pcts[-1] > pcts[0] if len(pcts) >= 2 else None,
            "expansion_magnitude": f"{(pcts[-1] - pcts[0]):+.1f}pp" if len(pcts) >= 2 else "N/A",
        }

        # Include last 10 data points for trend
        recent = rows[-10:] if len(rows) >= 10 else rows
        trend = []
        for r in recent:
            trend.append({
                "date": r.get("tradeDate", ""),
                "iv": f"{float(r.get('iv', 0)):.1f}%",
                "ivRank1y": f"{float(r.get('ivRank1y', 0)):.1f}%",
                "ivPct1y": f"{float(r.get('ivPct1y', 0)):.1f}%",
            })

        return json.dumps({"summary": summary, "recent_trend": trend}, indent=2)

    return json.dumps({"ticker": ticker, "error": "No historical data returned", "raw": data})


def tool_orats_term_structure(ticker: str) -> str:
    """
    Get IV term structure — implied volatility at different expirations.

    Shows iv10d, iv20d, iv30d, iv60d, iv90d, iv6m, iv1y.
    Rising front-month IV vs back-month = catalyst being priced in.

    Args:
        ticker: Single ticker symbol. E.g., "CABA"
    """
    data = get_summaries(ticker.upper())
    if "error" in data:
        return json.dumps(data)

    rows = data.get("data", [])
    if not rows:
        return json.dumps({"ticker": ticker, "error": "No summary data"})

    row = rows[0]

    # Extract term structure — Summaries IV fields are DECIMAL (1.4197 = 141.97%)
    ts = {}
    for field in ["iv10d", "iv20d", "iv30d", "iv60d", "iv90d", "iv6m", "iv1y"]:
        val = row.get(field)
        if val:
            ts[field] = f"{float(val) * 100:.1f}%"

    # Also show ex-earnings IV (removes earnings component)
    exErn = {}
    for field in ["exErnIv30d", "exErnIv90d", "exErnIv6m"]:
        val = row.get(field)
        if val:
            exErn[field] = f"{float(val) * 100:.1f}%"

    # Detect front-loading (expansion) — values are decimal
    iv30 = float(row.get("iv30d", 0))
    iv90 = float(row.get("iv90d", 0))
    tilt = iv30 / iv90 if iv90 > 0 else 1.0

    # Implied move is also decimal (0.38 = 38%)
    impl_move = row.get("impliedMove")
    impl_earn = row.get("impliedEarningsMove")

    return json.dumps({
        "ticker": ticker.upper(),
        "stock_price": row.get("stockPrice"),
        "term_structure": ts,
        "ex_earnings_iv": exErn,
        "tilt_30d_vs_90d": round(tilt, 3),
        "interpretation": "FRONT-LOADED (catalyst priced in)" if tilt > 1.3
                         else "FLAT (no expansion yet)" if tilt < 1.1
                         else "MILD TILT (early expansion)",
        "implied_move": f"{float(impl_move) * 100:.1f}%" if impl_move else None,
        "implied_earnings_move": f"{float(impl_earn) * 100:.1f}%" if impl_earn else None,
        "contango": row.get("contango"),
        "confidence": row.get("confidence"),
    }, indent=2)


def tool_orats_strikes(ticker: str, dte_min: int = 14, dte_max: int = 60,
                        delta_min: float = 0.3, delta_max: float = 0.7) -> str:
    """
    Get options chain snapshot — ATM calls with Greeks and IV.

    Args:
        ticker: Single ticker symbol
        dte_min: Minimum days to expiration (default 14)
        dte_max: Maximum days to expiration (default 60)
        delta_min: Minimum delta filter (default 0.3)
        delta_max: Maximum delta filter (default 0.7)
    """
    data = get_strikes(
        ticker.upper(),
        dte=f"{dte_min},{dte_max}",
        delta=f"{delta_min},{delta_max}"
    )
    if "error" in data:
        return json.dumps(data)

    rows = data.get("data", [])

    # Filter to calls only and format
    calls = [r for r in rows if r.get("callPut") == "C" or r.get("delta", 0) > 0]

    output = []
    for r in calls[:20]:  # limit output
        output.append({
            "expiry": r.get("expirDate"),
            "strike": r.get("strike"),
            "dte": r.get("dte"),
            "iv": f"{float(r.get('iv', 0)):.1f}%" if r.get("iv") else None,
            "delta": round(float(r.get("delta", 0)), 3),
            "gamma": round(float(r.get("gamma", 0)), 4),
            "theta": round(float(r.get("theta", 0)), 4),
            "vega": round(float(r.get("vega", 0)), 4),
            "bid": r.get("bid"),
            "ask": r.get("ask"),
            "volume": r.get("volume"),
            "open_interest": r.get("openInterest"),
        })

    return json.dumps({
        "ticker": ticker.upper(),
        "n_strikes": len(output),
        "filter": f"DTE {dte_min}-{dte_max}, Delta {delta_min}-{delta_max}",
        "strikes": output
    }, indent=2)


def tool_orats_status() -> str:
    """Check ORATS API connectivity and token validity."""
    if not ORATS_TOKEN:
        return json.dumps({
            "status": "NOT CONFIGURED",
            "error": "Set ORATS_API_TOKEN environment variable",
            "signup": "https://orats.com/data-api",
            "tier": "Delayed Data API ($99/month)",
        })

    # Test with a simple ticker request
    data = get_iv_rank("SPY")
    if "error" in data:
        return json.dumps({"status": "ERROR", "detail": data["error"]})

    rows = data.get("data", [])
    if rows:
        return json.dumps({
            "status": "CONNECTED",
            "version": VERSION,
            "tier": "Delayed Data API",
            "test_ticker": "SPY",
            "spy_iv": f"{float(rows[0].get('iv', 0)):.1f}%",
            "spy_iv_rank_1y": f"{float(rows[0].get('ivRank1y', 0)):.1f}%",
            "cache_ttl": f"{CACHE_TTL_SECONDS}s",
        })

    return json.dumps({"status": "CONNECTED (no data)", "version": VERSION})


# ---------------------------------------------------------------------------
# MCP Server (FastMCP) — only loaded when run as MCP server
# ---------------------------------------------------------------------------

def start_mcp_server():
    """Start the MCP server using FastMCP."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        print("ERROR: mcp package not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    mcp = FastMCP("orats_mcp")

    @mcp.tool(
        name="orats_iv_rank",
        annotations={
            "title": "IV Rank & Percentile",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def mcp_iv_rank(tickers: str) -> str:
        """Get current IV rank and percentile for catalyst tickers. Use to determine if options are cheap (ivPct1y < 30%) or expensive (> 70%). Max 10 comma-separated tickers."""
        return tool_orats_iv_rank(tickers)

    @mcp.tool(
        name="orats_iv_scan",
        annotations={
            "title": "IV Cheapness Scanner",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def mcp_iv_scan(tickers: str, catalyst_dates: str) -> str:
        """Scan catalyst tickers for cheap options. Computes cheapness score (0-100) using IV percentile, IV/RV ratio, timing, and term structure. Higher = cheaper. Tickers and catalyst_dates are comma-separated and must match."""
        return tool_orats_iv_scan(tickers, catalyst_dates)

    @mcp.tool(
        name="orats_iv_history",
        annotations={
            "title": "IV History & Expansion Tracker",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def mcp_iv_history(ticker: str, days: int = 90) -> str:
        """Get IV rank history for a ticker to track expansion into a catalyst. Shows if IV is expanding or still cheap."""
        return tool_orats_iv_history(ticker, days)

    @mcp.tool(
        name="orats_term_structure",
        annotations={
            "title": "IV Term Structure",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def mcp_term_structure(ticker: str) -> str:
        """Get IV term structure (iv10d through iv1y). Rising front-month IV vs back-month = catalyst being priced in. Tilt > 1.3 = expansion, < 1.1 = flat/cheap."""
        return tool_orats_term_structure(ticker)

    @mcp.tool(
        name="orats_strikes",
        annotations={
            "title": "Options Chain Snapshot",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def mcp_strikes(ticker: str, dte_min: int = 14, dte_max: int = 60,
                           delta_min: float = 0.3, delta_max: float = 0.7) -> str:
        """Get options chain with IV and Greeks for a ticker. Filter by DTE range and delta range. Returns ATM-ish calls."""
        return tool_orats_strikes(ticker, dte_min, dte_max, delta_min, delta_max)

    @mcp.tool(
        name="orats_status",
        annotations={
            "title": "ORATS Connection Status",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False
        }
    )
    async def mcp_status() -> str:
        """Check ORATS API connectivity, token validity, and current SPY IV."""
        return tool_orats_status()

    mcp.run(transport="stdio")


# ---------------------------------------------------------------------------
# CLI Mode (for direct testing without MCP)
# ---------------------------------------------------------------------------

def cli_demo():
    """Run a demo scan from command line."""
    print(f"ORATS IV Intelligence Module v{VERSION}")
    print(f"Token configured: {'YES' if ORATS_TOKEN else 'NO'}")
    print()

    if not ORATS_TOKEN:
        print("Set ORATS_API_TOKEN environment variable to use.")
        print("Get your API key at: https://orats.com/data-api")
        print()
        print("Example:")
        print("  export ORATS_API_TOKEN=your-token-here")
        print("  python mcp_orats.py")
        print()
        print("Or run as MCP server:")
        print("  python mcp_orats.py --mcp")
        return

    # Demo: scan current portfolio + watchlist
    print("=" * 60)
    print("  IV CHEAPNESS SCAN — Current Portfolio + Watchlist")
    print("=" * 60)
    print()

    tickers = "CABA,GRCE,NTLA,MNKD,BHVN,NVCR"
    dates = "2026-04-20,2026-04-23,2026-08-31,2026-07-26,2026-06-30,2026-06-30"

    result = tool_orats_iv_scan(tickers, dates)
    data = json.loads(result)

    if "error" in data:
        print(f"Error: {data['error']}")
        return

    for r in data.get("rankings", []):
        ticker = r.get("ticker", "?")
        score = r.get("cheapness_score", -1)
        overall = r.get("overall", "?")
        iv = r.get("current_iv", "?")
        pct = r.get("iv_pct_1y", "?")
        dtc = r.get("days_to_catalyst", "?")

        print(f"  {ticker:6s} | Cheapness: {score:3d}/100 | {overall:15s} | IV: {iv:>6s} | IVPct1Y: {pct}% | Catalyst: {dtc}d")

    print()
    print("Done. Full results in JSON above.")


if __name__ == "__main__":
    if "--mcp" in sys.argv:
        start_mcp_server()
    else:
        cli_demo()
