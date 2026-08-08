#!/usr/bin/env python3
"""
FinBrain Live Data Module — Direct SDK Wrapper
===============================================
Bypasses the broken MCP connector (req serialization bug) and calls
the FinBrain Python SDK directly.

Usage (CLI):
    python finbrain_live.py --ticker CABA --all
    python finbrain_live.py --ticker TVTX --putcall
    python finbrain_live.py --ticker GRCE --insider --analyst
    python finbrain_live.py --tickers CABA,ALXO,WHWK,GRCE,CRDF,TVTX --all
    python finbrain_live.py --tickers CABA,ALXO --putcall --json

Usage (Python import):
    from finbrain_live import FinBrainLive
    fb = FinBrainLive()
    data = fb.put_call("CABA", limit=10)
    data = fb.insider("CABA", limit=10)
    data = fb.analyst("ALXO", limit=10)
    data = fb.sentiment("GRCE", limit=30)
    data = fb.portfolio_scan(["CABA", "ALXO", "GRCE"])

9 Realms / pdufa.bio — April 2026
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

# ---------------------------------------------------------------------------
# API Key — fallback hardcoded from existing collector scripts
# ---------------------------------------------------------------------------
API_KEY = os.environ.get("FINBRAIN_API_KEY", "5813fe19-a03c-4873-a7be-354315c39b80")


class FinBrainLive:
    """Direct FinBrain SDK wrapper for live market data."""

    def __init__(self, api_key: Optional[str] = None):
        try:
            from finbrain import FinBrainClient
        except ImportError:
            raise ImportError(
                "finbrain-python not installed. Run: pip install finbrain-python --break-system-packages"
            )
        self.client = FinBrainClient(api_key=api_key or API_KEY)

    # ------------------------------------------------------------------
    # Core endpoints
    # ------------------------------------------------------------------

    def put_call(self, ticker: str, limit: int = 30,
                 date_from: Optional[str] = None,
                 date_to: Optional[str] = None) -> List[Dict]:
        """Get put/call ratio time series. Returns list of dicts with
        date, ratio, callVolume, putVolume, totalVolume, price."""
        kwargs = {"limit": limit}
        if date_from:
            kwargs["date_from"] = date_from
        if date_to:
            kwargs["date_to"] = date_to
        data = self.client.options.put_call(ticker, **kwargs)
        return data.get("data", [])

    def insider(self, ticker: str, limit: int = 20) -> List[Dict]:
        """Get insider transactions. Returns list of dicts with
        date, insider, relationship, transactionType, shares, pricePerShare,
        totalValue, sharesOwned, filingUrl."""
        data = self.client.insider_transactions.ticker(ticker, limit=limit)
        return data.get("transactions", [])

    def analyst(self, ticker: str, limit: int = 20) -> List[Dict]:
        """Get analyst ratings. Returns list of dicts with
        date, institution, action, rating, targetPrice."""
        data = self.client.analyst_ratings.ticker(ticker, limit=limit)
        return data.get("ratings", [])

    def sentiment(self, ticker: str, limit: int = 30,
                  date_from: Optional[str] = None) -> List[Dict]:
        """Get news sentiment scores. Returns list of dicts with date, score."""
        kwargs = {"limit": limit}
        if date_from:
            kwargs["date_from"] = date_from
        data = self.client.sentiments.ticker(ticker, **kwargs)
        return data.get("data", data.get("sentiments", []))

    def predictions(self, ticker: str) -> Dict:
        """Get AI price predictions. Returns dict with expected_short/mid/long,
        technical_analysis, series, sentiment."""
        data = self.client.predictions.ticker(ticker)
        return data

    def house_trades(self, ticker: str, limit: int = 10) -> List[Dict]:
        """Get US House member trades."""
        data = self.client.house_trades.ticker(ticker, limit=limit)
        return data.get("trades", data.get("data", []))

    def senate_trades(self, ticker: str, limit: int = 10) -> List[Dict]:
        """Get US Senate member trades."""
        data = self.client.senate_trades.ticker(ticker, limit=limit)
        return data.get("trades", data.get("data", []))

    # ------------------------------------------------------------------
    # Composite / portfolio-level
    # ------------------------------------------------------------------

    def put_call_summary(self, ticker: str) -> Dict:
        """Single-ticker P/C summary with bias classification."""
        rows = self.put_call(ticker, limit=5)
        if not rows:
            return {"ticker": ticker, "status": "NO_DATA"}
        latest = rows[0]
        ratio = latest.get("ratio", 0)
        calls = latest.get("callVolume", 0)
        puts = latest.get("putVolume", 0)
        total = latest.get("totalVolume", 0)

        if ratio == 0 or ratio < 0.30:
            bias = "BULLISH"
        elif ratio < 0.70:
            bias = "MIXED_BULLISH"
        elif ratio < 1.50:
            bias = "MIXED"
        elif ratio < 3.0:
            bias = "BEARISH"
        else:
            bias = "EXTREME_BEARISH"

        # UOA-style volume tier
        if total >= 5000:
            vol_tier = "SCREAMING"
        elif total >= 1000:
            vol_tier = "ELEVATED"
        elif total >= 200:
            vol_tier = "NORMAL"
        else:
            vol_tier = "QUIET"

        return {
            "ticker": ticker,
            "date": latest.get("date"),
            "ratio": ratio,
            "calls": calls,
            "puts": puts,
            "total_volume": total,
            "bias": bias,
            "volume_tier": vol_tier,
            "trend_5d": [
                {"date": r.get("date"), "ratio": r.get("ratio"),
                 "calls": r.get("callVolume", 0), "puts": r.get("putVolume", 0)}
                for r in rows[:5]
            ]
        }

    def insider_summary(self, ticker: str) -> Dict:
        """Single-ticker insider summary with net buy/sell classification."""
        txns = self.insider(ticker, limit=20)
        if not txns:
            return {"ticker": ticker, "status": "NO_DATA"}

        buys = [t for t in txns if t.get("transactionType", "").lower() in
                ("buy", "purchase", "derivative_purchase")]
        sells = [t for t in txns if t.get("transactionType", "").lower() in
                 ("sale", "sell")]

        buy_value = sum(t.get("totalValue", 0) or 0 for t in buys)
        sell_value = sum(t.get("totalValue", 0) or 0 for t in sells)

        if buy_value > sell_value * 2:
            direction = "NET_BUYING"
        elif sell_value > buy_value * 2:
            direction = "NET_SELLING"
        else:
            direction = "MIXED"

        return {
            "ticker": ticker,
            "n_transactions": len(txns),
            "n_buys": len(buys),
            "n_sells": len(sells),
            "buy_value": buy_value,
            "sell_value": sell_value,
            "direction": direction,
            "recent": txns[:5]
        }

    def portfolio_scan(self, tickers: List[str]) -> Dict[str, Dict]:
        """Full portfolio scan — P/C + insider + analyst for all tickers."""
        results = {}
        for t in tickers:
            results[t] = {
                "put_call": safe_call(lambda: self.put_call_summary(t)),
                "insider": safe_call(lambda: self.insider_summary(t)),
                "analyst": safe_call(lambda: self.analyst(t, limit=5)),
            }
        return results


def safe_call(fn):
    """Wrap API call with error handling."""
    try:
        return fn()
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_portfolio_report(results: Dict[str, Dict]):
    """Pretty-print portfolio scan results."""
    print("=" * 70)
    print(f"  FINBRAIN PORTFOLIO INTEL — {datetime.now().strftime('%B %d, %Y')}")
    print("=" * 70)

    for ticker, data in results.items():
        print(f"\n{'─' * 50}")
        print(f"  {ticker}")
        print(f"{'─' * 50}")

        # Put/Call
        pc = data.get("put_call", {})
        if isinstance(pc, dict) and pc.get("status") != "NO_DATA" and "error" not in pc:
            bias = pc.get("bias", "?")
            vol = pc.get("volume_tier", "?")
            print(f"  OPTIONS: P/C={pc.get('ratio', '?')} | "
                  f"C={pc.get('calls', 0)} P={pc.get('puts', 0)} | "
                  f"Vol={pc.get('total_volume', 0)} | {bias} | {vol}")
            trend = pc.get("trend_5d", [])
            if len(trend) > 1:
                print(f"  5d trend: " + " → ".join(
                    [f"{r['ratio']}" for r in trend]))
        else:
            print(f"  OPTIONS: No data")

        # Insider
        ins = data.get("insider", {})
        if isinstance(ins, dict) and ins.get("status") != "NO_DATA" and "error" not in ins:
            print(f"  INSIDER: {ins.get('direction', '?')} | "
                  f"Buys=${ins.get('buy_value', 0):,.0f} "
                  f"Sells=${ins.get('sell_value', 0):,.0f} | "
                  f"{ins.get('n_transactions', 0)} txns")
            for t in ins.get("recent", [])[:3]:
                name = (t.get("insider") or "?")[:25]
                ttype = t.get("transactionType", "?")
                val = t.get("totalValue", 0) or 0
                print(f"    {t.get('date', '')} | {name} | {ttype} | "
                      f"${val:,.0f}" if isinstance(val, (int, float)) else
                      f"    {t.get('date', '')} | {name} | {ttype} | ${val}")
        else:
            print(f"  INSIDER: No data")

        # Analyst
        an = data.get("analyst", [])
        if isinstance(an, list) and an:
            print(f"  ANALYST:")
            for r in an[:3]:
                inst = (r.get("institution") or "?")[:20]
                print(f"    {r.get('date', '')} | {inst} | "
                      f"{r.get('action', '')} {r.get('rating', '')} | "
                      f"PT: {r.get('targetPrice', '?')}")
        else:
            print(f"  ANALYST: No data")


def main():
    parser = argparse.ArgumentParser(description="FinBrain Live Data — 9 Realms")
    parser.add_argument("--ticker", "-t", help="Single ticker")
    parser.add_argument("--tickers", "-T", help="Comma-separated tickers")
    parser.add_argument("--putcall", action="store_true", help="Put/call ratios")
    parser.add_argument("--insider", action="store_true", help="Insider transactions")
    parser.add_argument("--analyst", action="store_true", help="Analyst ratings")
    parser.add_argument("--sentiment", action="store_true", help="News sentiment")
    parser.add_argument("--all", action="store_true", help="All endpoints")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--limit", type=int, default=10, help="Record limit")
    args = parser.parse_args()

    if not args.ticker and not args.tickers:
        # Default portfolio
        args.tickers = "CABA,ALXO,WHWK,GRCE,CRDF,TVTX"
        args.all = True

    fb = FinBrainLive()
    tickers = (args.tickers.split(",") if args.tickers
               else [args.ticker])

    if args.all or (not args.putcall and not args.insider
                    and not args.analyst and not args.sentiment):
        results = fb.portfolio_scan(tickers)
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print_portfolio_report(results)
        return

    # Individual endpoints
    for t in tickers:
        print(f"\n=== {t} ===")
        if args.putcall:
            data = fb.put_call(t, limit=args.limit)
            if args.json:
                print(json.dumps(data, indent=2, default=str))
            else:
                for row in data[:args.limit]:
                    print(f"  {row.get('date')} | P/C={row.get('ratio')} | "
                          f"C={row.get('callVolume', 0)} P={row.get('putVolume', 0)}")

        if args.insider:
            data = fb.insider(t, limit=args.limit)
            if args.json:
                print(json.dumps(data, indent=2, default=str))
            else:
                for row in data[:args.limit]:
                    name = (row.get("insider") or "?")[:25]
                    print(f"  {row.get('date')} | {name} | "
                          f"{row.get('transactionType')} | ${row.get('totalValue', 0):,}")

        if args.analyst:
            data = fb.analyst(t, limit=args.limit)
            if args.json:
                print(json.dumps(data, indent=2, default=str))
            else:
                for row in data[:args.limit]:
                    print(f"  {row.get('date')} | {row.get('institution', '?')[:20]} | "
                          f"{row.get('action', '')} {row.get('rating', '')} | "
                          f"PT: {row.get('targetPrice', '?')}")

        if args.sentiment:
            data = fb.sentiment(t, limit=args.limit)
            if args.json:
                print(json.dumps(data, indent=2, default=str))
            else:
                for row in data[:args.limit]:
                    print(f"  {row.get('date')} | score={row.get('score', '?')}")


if __name__ == "__main__":
    main()
