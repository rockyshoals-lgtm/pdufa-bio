#!/usr/bin/env python3
"""
Momentum Scanner v2.0 (FAST) — 9 Realms
=======================================
Broad-market momentum scanner powered by FMP + Unusual Whales APIs.
~10-20x faster than the yfinance version: whole-market snapshot in 3 calls,
then parallel history pulls for a shortlist only.

Pipeline (3-stage funnel):
  Stage 1  FMP exchange quotes (2 calls: NASDAQ + NYSE) + ETF list (1 call)
           -> full-market snapshot: price, volume, yearHigh, SMA50/200, mcap
           -> filter (price/liquidity/ETF) + preliminary momentum rank
  Stage 2  FMP historical EOD (parallel, shortlist only, default 400 names)
           -> exact 5/10/20/60d returns + volume surge (5d vs 20d avg)
           -> final composite z-score
  Stage 3  UW options-volume overlay (parallel, top N)
           -> call/put ratio + bullish-flow flag

Keys (env vars or --keys keys.json with {"FMP_API_KEY": ..., "UW_API_TOKEN": ...}):
  FMP_API_KEY   required
  UW_API_TOKEN  optional (Stage 3 skipped if absent)

Usage:
  python momentum_scanner_fast.py
  python momentum_scanner_fast.py --top 50 --shortlist 600 --workers 10
  python momentum_scanner_fast.py --tickers my_list.txt      # skip Stage 1 universe
  python momentum_scanner_fast.py --no-uw

Requires: pip install pandas numpy requests
Disclaimer: Informational/educational only. Not investment advice.
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests

FMP_STABLE = "https://financialmodelingprep.com/stable"
FMP_V3 = "https://financialmodelingprep.com/api/v3"
UW_BASE = "https://api.unusualwhales.com/api"

DEFAULTS = {
    "min_price": 2.0,
    "min_dollar_vol": 5e6,     # day volume x price floor at Stage 1
    "shortlist": 400,          # names promoted to Stage 2 history pull
    "top": 25,
    "uw_top_n": 25,
    "workers": 8,              # parallel FMP history workers (respect your rate limit)
    "exchanges": ["NASDAQ", "NYSE"],
}

# Final composite weights (Stage 2)
WEIGHTS = {
    "ret_5d": 0.10,
    "ret_10d": 0.15,
    "ret_20d": 0.25,
    "ret_60d": 0.20,
    "pct_of_52w_high": 0.15,
    "vol_surge": 0.15,
}


# ----------------------------------------------------------------------------
# HTTP helpers
# ----------------------------------------------------------------------------
def fmp_get(path_stable: str, path_v3: str | None, params: dict, key: str,
            retries: int = 3):
    """GET against FMP stable, falling back to legacy v3 path. Retries on 429."""
    urls = [f"{FMP_STABLE}/{path_stable}"] + ([f"{FMP_V3}/{path_v3}"] if path_v3 else [])
    last_err = None
    for url in urls:
        for attempt in range(retries):
            try:
                r = requests.get(url, params={**params, "apikey": key}, timeout=30)
                if r.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                if r.status_code in (401, 403, 404):
                    last_err = f"{r.status_code} on {url.split('?')[0]}"
                    break  # try next url form
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                last_err = str(e)
                time.sleep(1)
    raise RuntimeError(f"FMP request failed: {path_stable} ({last_err})")


def uw_get(path: str, token: str, params: dict | None = None):
    r = requests.get(f"{UW_BASE}/{path}",
                     headers={"Authorization": f"Bearer {token}",
                              "Accept": "application/json"},
                     params=params or {}, timeout=20)
    r.raise_for_status()
    return r.json()


def load_keys(args) -> tuple[str, str]:
    fmp = os.environ.get("FMP_API_KEY", "")
    uw = os.environ.get("UW_API_TOKEN", "")
    if args.keys and os.path.exists(args.keys):
        with open(args.keys) as f:
            kj = json.load(f)
        fmp = fmp or kj.get("FMP_API_KEY", "")
        uw = uw or kj.get("UW_API_TOKEN", "")
    if not fmp:
        sys.exit("FMP_API_KEY not set (env var or --keys keys.json). Aborting.")
    return fmp, uw


# ----------------------------------------------------------------------------
# Stage 1 — full-market snapshot via FMP exchange quotes
# ----------------------------------------------------------------------------
def fetch_etf_symbols(key: str) -> set[str]:
    try:
        data = fmp_get("etf-list", "etf/list", {}, key)
        return {d.get("symbol", "") for d in data}
    except Exception as e:
        print(f"  WARN: ETF list unavailable ({e}) — using name-based ETF filter only")
        return set()


def fetch_exchange_snapshot(key: str, exchanges: list[str]) -> pd.DataFrame:
    frames = []
    for ex in exchanges:
        print(f"  pulling {ex} quotes...")
        data = fmp_get("batch-exchange-quote", f"quotes/{ex}",
                       {"exchange": ex, "short": "false"}, key)
        df = pd.DataFrame(data)
        if not df.empty:
            frames.append(df)
    if not frames:
        sys.exit("No exchange quote data returned — check FMP plan/endpoint access.")
    q = pd.concat(frames, ignore_index=True).drop_duplicates(subset="symbol")
    return q


def stage1_filter_and_rank(q: pd.DataFrame, etfs: set[str],
                           min_price: float, min_dollar_vol: float) -> pd.DataFrame:
    q = q.copy()
    for c in ["price", "volume", "yearHigh", "priceAvg50", "priceAvg200",
              "marketCap", "changePercentage"]:
        if c not in q.columns:
            q[c] = np.nan
        q[c] = pd.to_numeric(q[c], errors="coerce")

    # Common-stock filters
    q = q[~q["symbol"].isin(etfs)]
    q = q[~q["symbol"].str.contains(r"[\.\-\$\^=]", regex=True, na=True)]
    name = q.get("name", pd.Series("", index=q.index)).fillna("")
    q = q[~name.str.contains(r"\bETF\b|\bETN\b|Fund\b|Trust\b|Index\b", regex=True)]

    # Liquidity / price floors
    q["dollar_vol"] = q["price"] * q["volume"]
    q = q[(q["price"] >= min_price) & (q["dollar_vol"] >= min_dollar_vol)]
    q = q.dropna(subset=["price", "yearHigh", "priceAvg50", "priceAvg200"])
    q = q[(q["yearHigh"] > 0) & (q["priceAvg50"] > 0) & (q["priceAvg200"] > 0)]

    # Preliminary momentum rank (quote-only proxies; recall-oriented)
    q["pct_of_52w_high"] = q["price"] / q["yearHigh"]
    q["px_vs_sma50"] = q["price"] / q["priceAvg50"] - 1
    q["px_vs_sma200"] = q["price"] / q["priceAvg200"] - 1
    q["prelim_score"] = (zscore(q["pct_of_52w_high"])
                         + zscore(q["px_vs_sma50"])
                         + zscore(q["px_vs_sma200"])
                         + 0.5 * zscore(q["changePercentage"]))
    return q.set_index("symbol").sort_values("prelim_score", ascending=False)


# ----------------------------------------------------------------------------
# Stage 2 — exact momentum from parallel EOD history pulls
# ----------------------------------------------------------------------------
def fetch_history(symbol: str, key: str) -> dict | None:
    """~70 trading days of close+volume -> exact windows + volume surge."""
    frm = (datetime.now() - timedelta(days=110)).strftime("%Y-%m-%d")
    try:
        data = fmp_get("historical-price-eod/light",
                       f"historical-price-full/{symbol}",
                       {"symbol": symbol, "from": frm}, key)
    except Exception:
        return None
    rows = data.get("historical", data) if isinstance(data, dict) else data
    if not rows:
        return None
    df = pd.DataFrame(rows)
    price_col = "price" if "price" in df.columns else "close"
    if price_col not in df.columns or "volume" not in df.columns:
        return None
    df = df.sort_values("date")
    px = pd.to_numeric(df[price_col], errors="coerce").dropna()
    vol = pd.to_numeric(df["volume"], errors="coerce").reindex(px.index)
    if len(px) < 61:
        return None
    last = px.iloc[-1]
    v20 = vol.iloc[-20:].mean()
    out = {
        "symbol": symbol,
        "ret_5d": last / px.iloc[-6] - 1,
        "ret_10d": last / px.iloc[-11] - 1,
        "ret_20d": last / px.iloc[-21] - 1,
        "ret_60d": last / px.iloc[-61] - 1,
        "vol_surge": (vol.iloc[-5:].mean() / v20) if v20 else np.nan,
    }
    return out


def stage2_exact_momentum(shortlist: list[str], key: str, workers: int) -> pd.DataFrame:
    rows = []
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_history, s, key): s for s in shortlist}
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                rows.append(res)
            done += 1
            if done % 100 == 0:
                print(f"  history: {done}/{len(shortlist)}")
    return pd.DataFrame(rows).set_index("symbol") if rows else pd.DataFrame()


# ----------------------------------------------------------------------------
# Stage 3 — Unusual Whales flow overlay
# ----------------------------------------------------------------------------
def uw_flow_one(t: str, token: str) -> dict | None:
    try:
        data = uw_get(f"stock/{t}/options-volume", token).get("data") or [{}]
        d = data[0] if isinstance(data, list) else data
        cv = float(d.get("call_volume") or 0)
        pv = float(d.get("put_volume") or 0)
        cprem = float(d.get("call_premium") or 0)
        pprem = float(d.get("put_premium") or 0)
        total = cv + pv
        return {
            "symbol": t,
            "uw_call_put_ratio": round(cv / pv, 2) if pv else np.nan,
            "uw_options_volume": int(total),
            "uw_net_call_premium": round(cprem - pprem, 0),
            "uw_bullish_flow": bool(total > 0 and cv / max(total, 1) >= 0.65),
        }
    except Exception:
        return None


def stage3_uw_overlay(tickers: list[str], token: str) -> pd.DataFrame:
    rows = []
    with ThreadPoolExecutor(max_workers=4) as ex:  # UW rate limit friendly
        for fut in as_completed({ex.submit(uw_flow_one, t, token): t for t in tickers}):
            res = fut.result()
            if res:
                rows.append(res)
    return pd.DataFrame(rows).set_index("symbol") if rows else pd.DataFrame()


# ----------------------------------------------------------------------------
# Scoring
# ----------------------------------------------------------------------------
def zscore(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan)
    sd = s.std()
    if not sd or np.isnan(sd):
        return pd.Series(0.0, index=s.index)
    return ((s - s.mean()) / sd).clip(-4, 4).fillna(0.0)


def final_score(m: pd.DataFrame) -> pd.DataFrame:
    m = m.copy()
    m["momentum_score"] = sum(w * zscore(m[c]) for c, w in WEIGHTS.items())
    m["momentum_score"] += 0.10 * (m["px_vs_sma50"] > 0).astype(float)
    m["momentum_score"] += 0.10 * (m["px_vs_sma200"] > 0).astype(float)
    return m.sort_values("momentum_score", ascending=False)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="9 Realms momentum scanner v2 (FMP+UW)")
    ap.add_argument("--tickers", help="custom ticker file — skips Stage 1 universe")
    ap.add_argument("--top", type=int, default=DEFAULTS["top"])
    ap.add_argument("--shortlist", type=int, default=DEFAULTS["shortlist"])
    ap.add_argument("--workers", type=int, default=DEFAULTS["workers"])
    ap.add_argument("--min-price", type=float, default=DEFAULTS["min_price"])
    ap.add_argument("--min-dollar-vol", type=float, default=DEFAULTS["min_dollar_vol"])
    ap.add_argument("--no-uw", action="store_true")
    ap.add_argument("--keys", default="keys.json", help="optional JSON key file")
    ap.add_argument("--out", help="output CSV path")
    args = ap.parse_args()

    fmp_key, uw_token = load_keys(args)
    t0 = time.time()
    print("=== 9 Realms Momentum Scanner v2 (FMP + UW) ===")

    # Stage 1
    if args.tickers:
        with open(args.tickers) as f:
            shortlist = sorted({ln.strip().upper() for ln in f
                                if ln.strip() and not ln.startswith("#")})
        print(f"Stage 1: custom watchlist — {len(shortlist)} tickers")
        snap = pd.DataFrame(index=shortlist)
        snap[["pct_of_52w_high", "px_vs_sma50", "px_vs_sma200", "price",
              "marketCap", "dollar_vol"]] = np.nan
        # Pull quotes for watchlist so final table still has snapshot columns
        try:
            data = fmp_get("batch-quote", None,
                           {"symbols": ",".join(shortlist)}, fmp_key)
            qq = pd.DataFrame(data).set_index("symbol")
            snap = stage1_filter_and_rank(qq.reset_index(), set(), 0, 0)
            shortlist = snap.index.tolist()
        except Exception as e:
            print(f"  WARN: watchlist quote pull failed ({e})")
    else:
        print("Stage 1: full-market snapshot...")
        etfs = fetch_etf_symbols(fmp_key)
        q = fetch_exchange_snapshot(fmp_key, DEFAULTS["exchanges"])
        print(f"  {len(q)} raw quotes")
        snap = stage1_filter_and_rank(q, etfs, args.min_price, args.min_dollar_vol)
        print(f"  {len(snap)} pass filters -> shortlisting top {args.shortlist} by prelim rank")
        shortlist = snap.head(args.shortlist).index.tolist()

    # Stage 2
    print(f"Stage 2: exact momentum for {len(shortlist)} names "
          f"({args.workers} workers)...")
    hist = stage2_exact_momentum(shortlist, fmp_key, args.workers)
    if hist.empty:
        sys.exit("Stage 2 returned no history — check FMP key/plan.")
    m = hist.join(snap[["price", "marketCap", "dollar_vol", "pct_of_52w_high",
                        "px_vs_sma50", "px_vs_sma200"]], how="left")
    ranked = final_score(m)

    # Stage 3
    if not args.no_uw and uw_token:
        topn = ranked.head(DEFAULTS["uw_top_n"]).index.tolist()
        print(f"Stage 3: UW flow overlay on top {len(topn)}...")
        uw = stage3_uw_overlay(topn, uw_token)
        if not uw.empty:
            ranked = ranked.join(uw)
    elif not args.no_uw:
        print("Stage 3: UW_API_TOKEN not set — skipping flow overlay")

    # Output
    today = datetime.now().strftime("%Y-%m-%d")
    out_path = args.out or f"momentum_scan_{today}.csv"
    ranked.round(4).to_csv(out_path, index_label="ticker")
    elapsed = time.time() - t0
    print(f"\nSaved: {out_path}  ({len(ranked)} names, {elapsed:.0f}s total)")

    show = ["momentum_score", "price", "ret_5d", "ret_20d", "ret_60d",
            "pct_of_52w_high", "vol_surge"]
    show += [c for c in ["uw_call_put_ratio", "uw_net_call_premium",
                         "uw_bullish_flow"] if c in ranked.columns]
    with pd.option_context("display.width", 180, "display.float_format", "{:.3f}".format):
        print(f"\nTop {args.top} momentum names:\n")
        print(ranked[show].head(args.top).to_string())

    print("\nDisclaimer: informational/educational only — not investment advice.")


if __name__ == "__main__":
    main()
