#!/usr/bin/env python3
"""
Momentum Scanner v1.0 — 9 Realms
================================
Broad-market stock momentum scanner.

Pipeline:
  1. Universe    — NASDAQ Trader symbol directory (NASDAQ + NYSE/AMEX), ETFs/tests excluded
  2. Prices      — yfinance batch download (1 year daily)
  3. Momentum    — multi-window returns (5/10/20/60d), 52w-high proximity, SMA position
  4. Volume      — 5d avg volume vs 20d avg (surge ratio), dollar-volume liquidity floor
  5. Score       — composite z-score rank
  6. UW overlay  — optional Unusual Whales flow confirmation on top names
                   (set UW_API_TOKEN env var; skipped gracefully if absent)

Usage:
  python momentum_scanner.py                        # full broad-market scan
  python momentum_scanner.py --top 50               # show top 50
  python momentum_scanner.py --tickers my_list.txt  # custom watchlist (one ticker/line)
  python momentum_scanner.py --min-price 5 --min-dollar-vol 10e6
  python momentum_scanner.py --no-uw                # skip Unusual Whales overlay

Output:
  momentum_scan_YYYY-MM-DD.csv (full ranked results) + console top table

Requires: pip install yfinance pandas numpy requests
Disclaimer: Informational/educational only. Not investment advice.
"""

import argparse
import io
import os
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd
import requests

try:
    import yfinance as yf
except ImportError:
    sys.exit("yfinance not installed. Run: pip install yfinance")

# ----------------------------------------------------------------------------
# Config defaults
# ----------------------------------------------------------------------------
DEFAULTS = {
    "min_price": 2.0,            # skip sub-$2 names
    "min_dollar_vol": 5e6,       # min 20d avg dollar volume ($)
    "top": 25,                   # rows shown in console
    "uw_top_n": 25,              # how many top names get UW flow check
    "batch_size": 200,           # yfinance download batch
    "history_period": "1y",
}

# Composite score weights (must sum to 1.0)
WEIGHTS = {
    "ret_5d": 0.10,
    "ret_10d": 0.15,
    "ret_20d": 0.25,
    "ret_60d": 0.20,
    "pct_of_52w_high": 0.15,     # closeness to 52w high (breakout proximity)
    "vol_surge": 0.15,           # 5d avg vol / 20d avg vol
}

UW_BASE = "https://api.unusualwhales.com/api"


# ----------------------------------------------------------------------------
# 1. Universe
# ----------------------------------------------------------------------------
def fetch_universe() -> list[str]:
    """NASDAQ Trader symbol directory: NASDAQ + NYSE/AMEX/ARCA common stocks."""
    urls = {
        "nasdaq": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
        "other": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
    }
    tickers: set[str] = set()
    for name, url in urls.items():
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"  WARN: could not fetch {name} listing ({e})")
            continue
        df = pd.read_csv(io.StringIO(r.text), sep="|")
        df = df[:-1]  # drop file-timestamp footer row
        sym_col = "Symbol" if "Symbol" in df.columns else "ACT Symbol"
        # Exclude test issues and ETFs
        if "Test Issue" in df.columns:
            df = df[df["Test Issue"] == "N"]
        if "ETF" in df.columns:
            df = df[df["ETF"] == "N"]
        syms = df[sym_col].dropna().astype(str)
        # Drop units/warrants/rights/preferreds ($, ., ^, multi-class junk)
        syms = syms[~syms.str.contains(r"[\$\.\^\+=]", regex=True)]
        syms = syms[syms.str.len() <= 5]
        tickers.update(syms.str.strip())
    return sorted(tickers)


def load_ticker_file(path: str) -> list[str]:
    with open(path) as f:
        return sorted({ln.strip().upper() for ln in f if ln.strip() and not ln.startswith("#")})


# ----------------------------------------------------------------------------
# 2-4. Prices + metrics
# ----------------------------------------------------------------------------
def compute_metrics(close: pd.DataFrame, volume: pd.DataFrame,
                    min_price: float, min_dollar_vol: float) -> pd.DataFrame:
    """Vectorized momentum/volume metrics from wide close/volume frames."""
    close = close.dropna(axis=1, how="all")
    volume = volume.reindex(columns=close.columns)

    last = close.ffill().iloc[-1]

    def ret(n: int) -> pd.Series:
        if len(close) <= n:
            return pd.Series(np.nan, index=close.columns)
        return last / close.ffill().iloc[-(n + 1)] - 1.0

    vol20 = volume.rolling(20).mean().iloc[-1]
    vol5 = volume.rolling(5).mean().iloc[-1]
    dollar_vol = vol20 * last

    m = pd.DataFrame({
        "price": last,
        "ret_5d": ret(5),
        "ret_10d": ret(10),
        "ret_20d": ret(20),
        "ret_60d": ret(60),
        "pct_of_52w_high": last / close.max(),
        "vol_surge": vol5 / vol20,
        "dollar_vol_20d": dollar_vol,
        "above_sma20": last > close.rolling(20).mean().iloc[-1],
        "above_sma50": last > close.rolling(50).mean().iloc[-1],
    })

    # Filters: price floor, liquidity floor, enough history for 60d return
    m = m[(m["price"] >= min_price) & (m["dollar_vol_20d"] >= min_dollar_vol)]
    m = m.dropna(subset=["ret_20d", "vol_surge"])
    return m


def zscore(s: pd.Series) -> pd.Series:
    s = s.replace([np.inf, -np.inf], np.nan)
    sd = s.std()
    if not sd or np.isnan(sd):
        return pd.Series(0.0, index=s.index)
    return ((s - s.mean()) / sd).clip(-4, 4).fillna(0.0)


def score(m: pd.DataFrame) -> pd.DataFrame:
    m = m.copy()
    m["momentum_score"] = sum(w * zscore(m[c]) for c, w in WEIGHTS.items())
    # Small bonus for trend confirmation
    m["momentum_score"] += 0.10 * m["above_sma20"].astype(float)
    m["momentum_score"] += 0.10 * m["above_sma50"].astype(float)
    return m.sort_values("momentum_score", ascending=False)


def download_prices(tickers: list[str], period: str, batch_size: int):
    """Batch download; returns (close, volume) wide DataFrames."""
    closes, volumes = [], []
    n_batches = (len(tickers) + batch_size - 1) // batch_size
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        print(f"  downloading batch {i // batch_size + 1}/{n_batches} ({len(batch)} tickers)...")
        try:
            data = yf.download(batch, period=period, interval="1d",
                               group_by="column", auto_adjust=True,
                               threads=True, progress=False)
        except Exception as e:
            print(f"  WARN: batch failed ({e}), skipping")
            continue
        if data.empty:
            continue
        if isinstance(data.columns, pd.MultiIndex):
            closes.append(data["Close"])
            volumes.append(data["Volume"])
        else:  # single ticker fallback
            closes.append(data[["Close"]].rename(columns={"Close": batch[0]}))
            volumes.append(data[["Volume"]].rename(columns={"Volume": batch[0]}))
        time.sleep(0.5)
    if not closes:
        sys.exit("No price data downloaded.")
    return pd.concat(closes, axis=1), pd.concat(volumes, axis=1)


# ----------------------------------------------------------------------------
# 6. Unusual Whales flow overlay (optional)
# ----------------------------------------------------------------------------
def uw_flow_check(tickers: list[str], token: str) -> pd.DataFrame:
    """Options-volume snapshot per ticker: call/put ratio + volume vs OI."""
    rows = []
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    for t in tickers:
        try:
            r = requests.get(f"{UW_BASE}/stock/{t}/options-volume",
                             headers=headers, timeout=15)
            if r.status_code != 200:
                continue
            data = (r.json().get("data") or [{}])
            d = data[0] if isinstance(data, list) else data
            cv = float(d.get("call_volume") or 0)
            pv = float(d.get("put_volume") or 0)
            total = cv + pv
            rows.append({
                "ticker": t,
                "uw_call_put_ratio": round(cv / pv, 2) if pv else np.nan,
                "uw_options_volume": int(total),
                "uw_bullish_flow": bool(total > 0 and cv / max(total, 1) >= 0.65),
            })
        except Exception:
            continue
        time.sleep(0.35)  # stay under rate limits
    return pd.DataFrame(rows).set_index("ticker") if rows else pd.DataFrame()


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="9 Realms momentum scanner")
    ap.add_argument("--tickers", help="path to custom ticker file (one per line)")
    ap.add_argument("--top", type=int, default=DEFAULTS["top"])
    ap.add_argument("--min-price", type=float, default=DEFAULTS["min_price"])
    ap.add_argument("--min-dollar-vol", type=float, default=DEFAULTS["min_dollar_vol"])
    ap.add_argument("--period", default=DEFAULTS["history_period"])
    ap.add_argument("--no-uw", action="store_true", help="skip Unusual Whales overlay")
    ap.add_argument("--out", help="output CSV path (default momentum_scan_<date>.csv)")
    args = ap.parse_args()

    print("=== 9 Realms Momentum Scanner ===")
    if args.tickers:
        universe = load_ticker_file(args.tickers)
        print(f"Universe: {len(universe)} tickers from {args.tickers}")
    else:
        print("Fetching broad-market universe (NASDAQ Trader)...")
        universe = fetch_universe()
        print(f"Universe: {len(universe)} tickers")

    print("Downloading price history...")
    close, volume = download_prices(universe, args.period, DEFAULTS["batch_size"])
    print(f"Got data for {close.shape[1]} tickers over {close.shape[0]} sessions")

    print("Computing momentum metrics...")
    m = compute_metrics(close, volume, args.min_price, args.min_dollar_vol)
    print(f"{len(m)} tickers pass price/liquidity filters")
    ranked = score(m)

    # UW overlay
    token = os.environ.get("UW_API_TOKEN", "")
    if not args.no_uw and token:
        top_names = ranked.head(DEFAULTS["uw_top_n"]).index.tolist()
        print(f"Unusual Whales flow check on top {len(top_names)}...")
        uw = uw_flow_check(top_names, token)
        if not uw.empty:
            ranked = ranked.join(uw)
    elif not args.no_uw:
        print("UW_API_TOKEN not set — skipping Unusual Whales overlay (use --no-uw to silence)")

    # Output
    today = datetime.now().strftime("%Y-%m-%d")
    out_path = args.out or f"momentum_scan_{today}.csv"
    ranked.round(4).to_csv(out_path, index_label="ticker")
    print(f"\nSaved full results: {out_path}")

    show_cols = ["momentum_score", "price", "ret_5d", "ret_20d", "ret_60d",
                 "pct_of_52w_high", "vol_surge"]
    if "uw_call_put_ratio" in ranked.columns:
        show_cols += ["uw_call_put_ratio", "uw_bullish_flow"]
    with pd.option_context("display.width", 160, "display.float_format", "{:.3f}".format):
        print(f"\nTop {args.top} momentum names:\n")
        print(ranked[show_cols].head(args.top).to_string())

    print("\nDisclaimer: informational/educational only — not investment advice.")


if __name__ == "__main__":
    main()
