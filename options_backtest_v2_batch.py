#!/usr/bin/env python3
"""
Options Backtest v2 — BATCH RUNNER
Runs in configurable batches to avoid timeout.
Saves progress incrementally. Can resume from where it left off.

Usage:
  python3 options_backtest_v2_batch.py pdufa    # Run PDUFA batch
  python3 options_backtest_v2_batch.py readout  # Run readout batch
  python3 options_backtest_v2_batch.py analyze  # Analyze all results
"""

import json, os, sys, time, math, hashlib
import urllib.request, urllib.parse, urllib.error, ssl
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

ORATS_BASE_URL = "https://api.orats.io/datav2"
ORATS_TOKEN = os.environ.get("ORATS_API_TOKEN", "cc1aa61c-ebfa-42e9-8fc0-6bc8f23aaa3d")
_ssl_ctx = ssl.create_default_context()
CACHE_DIR = Path(__file__).parent / "orats_backtest_cache"
CACHE_DIR.mkdir(exist_ok=True)
PROGRESS_DIR = Path(__file__).parent / "backtest_progress"
PROGRESS_DIR.mkdir(exist_ok=True)

_req_times = []
_api_calls = 0

def _rate_limit():
    global _api_calls
    now = time.time()
    while _req_times and _req_times[0] < now - 60:
        _req_times.pop(0)
    if len(_req_times) >= 82:
        wait = 60 - (now - _req_times[0]) + 1.0
        if wait > 0:
            time.sleep(wait)
    _req_times.append(time.time())
    _api_calls += 1

def orats_get(endpoint, params=None):
    params = params or {}
    params["token"] = ORATS_TOKEN
    url = f"{ORATS_BASE_URL}{endpoint}?{urllib.parse.urlencode(params)}"
    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    _rate_limit()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            cache_file.write_text(json.dumps(data))
            return data
    except Exception as e:
        return {"error": str(e)}

def get_trading_date(target_date, offset_days):
    d = datetime.strptime(str(target_date)[:10], "%Y-%m-%d")
    if offset_days >= 14:
        cal_days = int(offset_days * 1.45)
    else:
        cal_days = offset_days + 1
    target = d - timedelta(days=cal_days)
    while target.weekday() >= 5:
        target -= timedelta(days=1)
    return target.strftime("%Y-%m-%d")

def find_atm_call(strikes_data, stock_price):
    if not strikes_data:
        return None
    best = None
    best_score = -1
    for s in strikes_data:
        strike = float(s.get("strike", 0))
        delta = float(s.get("delta", 0)) if s.get("delta") else 0
        bid = float(s.get("callBidPrice", 0)) if s.get("callBidPrice") else 0
        ask = float(s.get("callAskPrice", 0)) if s.get("callAskPrice") else 0
        dte = int(s.get("dte", 0)) if s.get("dte") else 0
        oi = int(float(s.get("callOpenInterest", 0))) if s.get("callOpenInterest") else 0
        vol = int(float(s.get("callVolume", 0))) if s.get("callVolume") else 0
        if bid <= 0 or ask <= 0: continue
        if dte < 7 or dte > 60: continue
        if delta < 0.20 or delta > 0.80: continue
        spread_pct = (ask - bid) / ask if ask > 0 else 1.0
        if spread_pct > 0.55: continue
        atm_score = 1.0 - abs(delta - 0.5) * 2
        spread_score = 1.0 - spread_pct
        liq_score = min((oi + vol) / 100, 1.0)
        total_score = atm_score * 0.5 + spread_score * 0.3 + liq_score * 0.2
        if total_score > best_score:
            best_score = total_score
            raw_iv = float(s.get("smvVol", 0)) if s.get("smvVol") else None
            iv_pct = raw_iv * 100 if raw_iv and raw_iv < 10 else raw_iv
            best = {
                "strike": strike, "delta": delta, "bid": bid, "ask": ask,
                "mid": round((bid + ask) / 2, 4), "dte": dte, "oi": oi, "vol": vol,
                "spread_pct": round(spread_pct * 100, 1),
                "iv_pct": round(iv_pct, 1) if iv_pct else None,
                "stock_price": float(s.get("stockPrice", stock_price)),
            }
    return best

def backtest_event(ticker, event_date, event_type, outcome, cap_tier, extra_info=None):
    t14_date = get_trading_date(event_date, 14)
    t1_date = get_trading_date(event_date, 1)

    entry_data = orats_get("/hist/strikes", {"ticker": ticker, "tradeDate": t14_date})
    if "error" in entry_data: return None
    entry_strikes = entry_data.get("data", [])
    if not entry_strikes: return None
    entry_stock = float(entry_strikes[0].get("stockPrice", 0))
    if entry_stock <= 0: return None
    entry_call = find_atm_call(entry_strikes, entry_stock)
    if not entry_call: return None

    exit_data = orats_get("/hist/strikes", {"ticker": ticker, "tradeDate": t1_date})
    if "error" in exit_data: return None
    exit_strikes = exit_data.get("data", [])
    if not exit_strikes: return None
    exit_stock = float(exit_strikes[0].get("stockPrice", 0))

    target_strike = entry_call["strike"]
    exit_call = None
    for s in exit_strikes:
        strike = float(s.get("strike", 0))
        bid = float(s.get("callBidPrice", 0)) if s.get("callBidPrice") else 0
        dte = int(s.get("dte", 0)) if s.get("dte") else 0
        if strike == target_strike and bid > 0 and 0 < dte < 50:
            ask = float(s.get("callAskPrice", 0)) if s.get("callAskPrice") else bid
            raw_iv = float(s.get("smvVol", 0)) if s.get("smvVol") else None
            iv_pct = raw_iv * 100 if raw_iv and raw_iv < 10 else raw_iv
            exit_call = {
                "strike": strike, "bid": bid, "ask": ask,
                "mid": round((bid + ask) / 2, 4), "dte": dte,
                "iv_pct": round(iv_pct, 1) if iv_pct else None,
                "stock_price": exit_stock,
                "delta": float(s.get("delta", 0)) if s.get("delta") else None,
            }
            break

    if not exit_call:
        exit_call = find_atm_call(exit_strikes, exit_stock)
        if not exit_call: return None

    buy_ask = entry_call["ask"]
    sell_bid = exit_call["bid"]
    if buy_ask <= 0: return None
    option_return_worst = (sell_bid - buy_ask) / buy_ask * 100

    buy_mid = entry_call["mid"]
    sell_mid = exit_call["mid"]
    option_return_mid = (sell_mid - buy_mid) / buy_mid * 100 if buy_mid > 0 else None

    stock_return = (exit_stock - entry_stock) / entry_stock * 100

    entry_iv = entry_call.get("iv_pct")
    exit_iv = exit_call.get("iv_pct")
    iv_change_pct = None
    if entry_iv and exit_iv and entry_iv > 0:
        iv_change_pct = (exit_iv - entry_iv) / entry_iv * 100
        if abs(iv_change_pct) > 500: iv_change_pct = None

    return {
        "ticker": ticker, "event_date": str(event_date)[:10],
        "event_type": event_type, "outcome": outcome, "cap_tier": cap_tier,
        "entry_date": t14_date, "exit_date": t1_date,
        "entry_stock": round(entry_stock, 2), "exit_stock": round(exit_stock, 2),
        "stock_return_pct": round(stock_return, 2),
        "entry_strike": entry_call["strike"],
        "entry_ask": entry_call["ask"], "entry_bid": entry_call["bid"],
        "entry_mid": entry_call["mid"], "entry_dte": entry_call["dte"],
        "entry_delta": entry_call["delta"], "entry_iv_pct": entry_iv,
        "entry_spread_pct": entry_call["spread_pct"], "entry_oi": entry_call["oi"],
        "exit_strike": exit_call["strike"],
        "exit_bid": exit_call["bid"], "exit_ask": exit_call.get("ask", exit_call["bid"]),
        "exit_mid": exit_call["mid"], "exit_dte": exit_call.get("dte"),
        "exit_iv_pct": exit_iv,
        "option_return_worst_pct": round(option_return_worst, 2),
        "option_return_mid_pct": round(option_return_mid, 2) if option_return_mid is not None else None,
        "iv_change_pct": round(iv_change_pct, 1) if iv_change_pct is not None else None,
        **(extra_info or {}),
    }


def run_pdufa_batch():
    df = pd.read_csv('pdufa_runup_bifrost.csv')
    df['year'] = pd.to_datetime(df['pdufa_date']).dt.year
    df = df[df['year'] >= 2022].copy()

    # Load progress
    progress_file = PROGRESS_DIR / "pdufa_done.json"
    done_keys = set()
    results = []
    if progress_file.exists():
        saved = json.loads(progress_file.read_text())
        results = saved.get("results", [])
        done_keys = set(saved.get("done_keys", []))
        print(f"Resuming: {len(results)} trades already completed")

    skipped = 0
    total = len(df)

    for i, (_, row) in enumerate(df.iterrows()):
        ticker = row['ticker']
        date = str(row['pdufa_date'])[:10]
        key = f"{ticker}_{date}"

        if key in done_keys:
            continue

        outcome = 'approve' if row['outcome_bin'] == 1 else 'crl'
        cap = row['mcap_tier']
        cap_short = 'large' if 'Large' in str(cap) else 'mid' if 'Mid' in str(cap) else 'small' if 'Small' in str(cap) else 'micro' if 'Micro' in str(cap) else 'nano'

        # Skip nano
        if cap_short == 'nano':
            done_keys.add(key)
            continue

        result = backtest_event(ticker, date, "PDUFA", outcome, cap_short,
                               extra_info={"odin_tier": str(row.get('v5_tier', '')),
                                          "odin_score": float(row['v5_score']) if pd.notna(row.get('v5_score')) else None})
        done_keys.add(key)

        if result:
            results.append(result)
        else:
            skipped += 1

        # Save progress every 50 events
        if len(done_keys) % 50 == 0:
            progress_file.write_text(json.dumps({"results": results, "done_keys": list(done_keys), "skipped": skipped}, default=str))
            print(f"  PDUFA progress: {len(done_keys)}/{total} done, {len(results)} trades, {skipped} skipped, API: {_api_calls}")

    # Final save
    progress_file.write_text(json.dumps({"results": results, "done_keys": list(done_keys), "skipped": skipped}, default=str))
    print(f"\nPDUFA COMPLETE: {len(results)} trades, {skipped} skipped out of {len(done_keys)} attempted")
    return results, skipped


def run_readout_batch():
    df = pd.read_csv('gungnir_readout_analysis.csv')
    df['year'] = pd.to_datetime(df['date']).dt.year
    df = df[df['year'] >= 2022].copy()

    progress_file = PROGRESS_DIR / "readout_done.json"
    done_keys = set()
    results = []
    if progress_file.exists():
        saved = json.loads(progress_file.read_text())
        results = saved.get("results", [])
        done_keys = set(saved.get("done_keys", []))
        print(f"Resuming: {len(results)} trades already completed")

    skipped = 0
    total = len(df)

    for i, (_, row) in enumerate(df.iterrows()):
        ticker = row['ticker']
        date = str(row['date'])[:10]
        key = f"{ticker}_{date}"

        if key in done_keys:
            continue

        outcome = 'positive' if row['is_positive_outcome'] == 1 else 'negative'
        stage = str(row.get('stage', ''))

        if row.get('is_large') == 1: cap = 'large'
        elif row.get('is_mid') == 1: cap = 'mid'
        elif row.get('is_small') == 1: cap = 'small'
        elif row.get('is_micro') == 1: cap = 'micro'
        else: cap = 'nano'

        if cap == 'nano':
            done_keys.add(key)
            continue

        result = backtest_event(ticker, date, "Readout", outcome, cap,
                               extra_info={"stage": stage})
        done_keys.add(key)

        if result:
            results.append(result)
        else:
            skipped += 1

        if len(done_keys) % 50 == 0:
            progress_file.write_text(json.dumps({"results": results, "done_keys": list(done_keys), "skipped": skipped}, default=str))
            print(f"  Readout progress: {len(done_keys)}/{total} done, {len(results)} trades, {skipped} skipped, API: {_api_calls}")

    progress_file.write_text(json.dumps({"results": results, "done_keys": list(done_keys), "skipped": skipped}, default=str))
    print(f"\nReadout COMPLETE: {len(results)} trades, {skipped} skipped out of {len(done_keys)} attempted")
    return results, skipped


def run_analysis():
    """Load saved progress and run full analysis."""
    pdufa_file = PROGRESS_DIR / "pdufa_done.json"
    readout_file = PROGRESS_DIR / "readout_done.json"

    pdufa_results = []
    readout_results = []
    pdufa_skipped = 0
    readout_skipped = 0

    if pdufa_file.exists():
        saved = json.loads(pdufa_file.read_text())
        pdufa_results = saved["results"]
        pdufa_skipped = saved.get("skipped", 0)
    if readout_file.exists():
        saved = json.loads(readout_file.read_text())
        readout_results = saved["results"]
        readout_skipped = saved.get("skipped", 0)

    all_results = pdufa_results + readout_results
    print(f"Loaded {len(pdufa_results)} PDUFA + {len(readout_results)} readout = {len(all_results)} total trades")

    def analyze(results, label, return_field='option_return_worst_pct'):
        if not results: return {}
        opts = [r[return_field] for r in results if r.get(return_field) is not None]
        if not opts: return {}
        stocks = [r['stock_return_pct'] for r in results]
        n = len(opts)
        avg_opt = np.mean(opts)
        med_opt = np.median(opts)
        avg_stk = np.mean(stocks)
        med_stk = np.median(stocks)
        win = sum(1 for x in opts if x > 0) / n * 100
        big_w = sum(1 for x in opts if x > 100) / n * 100
        big_l = sum(1 for x in opts if x < -50) / n * 100
        p25, p75 = np.percentile(opts, 25), np.percentile(opts, 75)
        iv_changes = [r['iv_change_pct'] for r in results if r.get('iv_change_pct') is not None]
        avg_iv = np.mean(iv_changes) if iv_changes else None
        leverage = avg_opt / avg_stk if abs(avg_stk) > 0.01 else 0
        return {"label": label, "n": n, "avg_opt": round(avg_opt, 2), "med_opt": round(med_opt, 2),
                "p25_opt": round(p25, 2), "p75_opt": round(p75, 2),
                "avg_stock": round(avg_stk, 2), "med_stock": round(med_stk, 2),
                "win_rate": round(win, 1), "big_winners_pct": round(big_w, 1), "big_losers_pct": round(big_l, 1),
                "leverage": round(leverage, 2), "avg_iv_change": round(avg_iv, 1) if avg_iv else None}

    def pa(stats):
        if not stats: return
        s = stats
        iv_str = f" | IV chg: {s['avg_iv_change']:+.1f}%" if s.get('avg_iv_change') is not None else ""
        print(f"  {s['label']} (n={s['n']}):")
        print(f"    Stock:  avg {s['avg_stock']:>+7.2f}%, med {s['med_stock']:>+7.2f}%")
        print(f"    Option: avg {s['avg_opt']:>+7.2f}%, med {s['med_opt']:>+7.2f}%, [P25 {s['p25_opt']:>+.1f}%, P75 {s['p75_opt']:>+.1f}%]")
        print(f"    Win: {s['win_rate']:.1f}% | >100%: {s['big_winners_pct']:.1f}% | <-50%: {s['big_losers_pct']:.1f}% | Lev: {s['leverage']:.2f}x{iv_str}")

    analysis = {}

    for price_type, field, tag in [("WORST CASE (Buy ASK, Sell BID)", "option_return_worst_pct", "worst"),
                                     ("MID PRICE (Limit Orders)", "option_return_mid_pct", "mid")]:
        print(f"\n\n{'='*70}")
        print(f"  {price_type}")
        print(f"{'='*70}")

        print(f"\n--- OVERALL ---")
        s = analyze(all_results, "ALL", field); pa(s); analysis[f'all_{tag}'] = s

        print(f"\n--- BY TYPE ---")
        for lbl, sub in [("PDUFAs", pdufa_results), ("Readouts", readout_results)]:
            s = analyze(sub, lbl, field); pa(s); analysis[f'{lbl.lower()}_{tag}'] = s

        print(f"\n--- PDUFA BY OUTCOME ---")
        for out, lbl in [("approve", "Approvals"), ("crl", "CRLs")]:
            s = analyze([r for r in pdufa_results if r['outcome']==out], f"PDUFA {lbl}", field)
            pa(s); analysis[f'pdufa_{out}_{tag}'] = s

        print(f"\n--- READOUT BY OUTCOME ---")
        for out, lbl in [("positive", "Positive"), ("negative", "Negative")]:
            s = analyze([r for r in readout_results if r['outcome']==out], f"Readout {lbl}", field)
            pa(s); analysis[f'readout_{out}_{tag}'] = s

        print(f"\n--- PDUFA BY CAP ---")
        for cap in ['micro', 'small', 'mid', 'large']:
            s = analyze([r for r in pdufa_results if r['cap_tier']==cap], f"PDUFA {cap.upper()}", field)
            pa(s); analysis[f'pdufa_{cap}_{tag}'] = s

        print(f"\n--- READOUT BY CAP ---")
        for cap in ['micro', 'small', 'mid', 'large']:
            s = analyze([r for r in readout_results if r['cap_tier']==cap], f"Readout {cap.upper()}", field)
            pa(s); analysis[f'readout_{cap}_{tag}'] = s

        print(f"\n--- READOUT BY STAGE ---")
        for stage in ['Phase 1', 'Phase 1/2', 'Phase 2', 'Phase 2b', 'Phase 3']:
            sub = [r for r in readout_results if r.get('stage') == stage]
            if len(sub) >= 3:
                s = analyze(sub, f"Readout {stage}", field); pa(s)
                analysis[f'readout_{stage.replace(" ","_").replace("/","_")}_{tag}'] = s

        print(f"\n--- OUR STRATEGY ---")
        strat = [r for r in pdufa_results if r['cap_tier'] in ['small','mid'] and r['outcome']=='approve']
        s = analyze(strat, "PDUFA Small/Mid Approvals", field); pa(s)
        analysis[f'our_strategy_{tag}'] = s

        strat2 = [r for r in pdufa_results if r['cap_tier'] in ['small'] and r['outcome']=='approve']
        s = analyze(strat2, "PDUFA Small Approvals ONLY", field); pa(s)
        analysis[f'our_strategy_small_{tag}'] = s

        # ODIN T1 filter
        t1 = [r for r in pdufa_results if r.get('odin_tier') == 'T1' and r['cap_tier'] in ['small','mid']]
        if t1:
            s = analyze(t1, "PDUFA T1 Small/Mid", field); pa(s)
            analysis[f'odin_t1_sm_{tag}'] = s

    # IV EXPANSION
    print(f"\n\n{'='*70}")
    print("IV EXPANSION (T-14 → T-1)")
    print(f"{'='*70}")
    for label, subset in [
        ("PDUFA Micro", [r for r in pdufa_results if r['cap_tier'] == 'micro']),
        ("PDUFA Small", [r for r in pdufa_results if r['cap_tier'] == 'small']),
        ("PDUFA Mid", [r for r in pdufa_results if r['cap_tier'] == 'mid']),
        ("PDUFA Large", [r for r in pdufa_results if r['cap_tier'] == 'large']),
        ("Readout Micro", [r for r in readout_results if r['cap_tier'] == 'micro']),
        ("Readout Small", [r for r in readout_results if r['cap_tier'] == 'small']),
        ("Readout Mid", [r for r in readout_results if r['cap_tier'] == 'mid']),
        ("Readout Large", [r for r in readout_results if r['cap_tier'] == 'large']),
    ]:
        ivs = [r['iv_change_pct'] for r in subset if r.get('iv_change_pct') is not None]
        entry_ivs = [r['entry_iv_pct'] for r in subset if r.get('entry_iv_pct') is not None]
        exit_ivs = [r['exit_iv_pct'] for r in subset if r.get('exit_iv_pct') is not None]
        if ivs:
            print(f"  {label:>22s}: entry {np.mean(entry_ivs):>5.0f}% → exit {np.mean(exit_ivs):>5.0f}% | Δ {np.mean(ivs):>+6.1f}% (med {np.median(ivs):>+6.1f}%) n={len(ivs)}")

    # SPREAD IMPACT
    print(f"\n\n{'='*70}")
    print("SPREAD IMPACT: Worst vs Mid")
    print(f"{'='*70}")
    for label, subset in [
        ("ALL", all_results), ("PDUFA", pdufa_results), ("Readout", readout_results),
        ("PDUFA SM Approve", [r for r in pdufa_results if r['cap_tier'] in ['small','mid'] and r['outcome']=='approve']),
    ]:
        worst = [r['option_return_worst_pct'] for r in subset if r.get('option_return_worst_pct') is not None]
        mid = [r['option_return_mid_pct'] for r in subset if r.get('option_return_mid_pct') is not None]
        spreads = [r['entry_spread_pct'] for r in subset if r.get('entry_spread_pct')]
        if worst and mid:
            print(f"  {label:>25s}: Worst {np.mean(worst):>+7.1f}% | Mid {np.mean(mid):>+7.1f}% | Spread cost {np.mean(worst)-np.mean(mid):>+5.1f}pp | Avg spread {np.mean(spreads):.1f}%")

    # TOP TRADES
    print(f"\n\n{'='*70}")
    print("TOP 20 BEST TRADES (Mid Price)")
    print(f"{'='*70}")
    sorted_trades = sorted(all_results, key=lambda x: x.get('option_return_mid_pct') or -999, reverse=True)
    for t in sorted_trades[:20]:
        print(f"  {t['ticker']:>6s} {t['event_date']} {t['event_type']:>7s} {t['outcome']:>8s} {t['cap_tier']:>6s} | Stock {t['stock_return_pct']:>+6.1f}% | Opt {t.get('option_return_mid_pct',0):>+7.1f}% | Entry IV {t.get('entry_iv_pct','?')}%")

    print(f"\n\nTOP 20 WORST TRADES (Mid Price)")
    for t in sorted_trades[-20:]:
        print(f"  {t['ticker']:>6s} {t['event_date']} {t['event_type']:>7s} {t['outcome']:>8s} {t['cap_tier']:>6s} | Stock {t['stock_return_pct']:>+6.1f}% | Opt {t.get('option_return_mid_pct',0):>+7.1f}% | Entry IV {t.get('entry_iv_pct','?')}%")

    # Save comprehensive results
    output = {
        "generated": datetime.now().isoformat(),
        "version": "v2_expanded_complete",
        "data_source": "REAL ORATS hist/strikes — actual bid/ask prices",
        "methodology": {
            "entry": "Buy ATM call at T-14 (14 trading days before catalyst)",
            "exit": "Sell ATM call at T-1 (1 trading day before catalyst)",
            "worst_case": "Buy at ASK, sell at BID",
            "mid_case": "Buy at MID, sell at MID (limit orders)",
            "iv_fix": "smvVol decimal → percentage, capped at ±500%",
        },
        "coverage": {
            "n_pdufa_trades": len(pdufa_results),
            "n_readout_trades": len(readout_results),
            "n_pdufa_skipped": pdufa_skipped,
            "n_readout_skipped": readout_skipped,
            "total_trades": len(all_results),
        },
        "analysis": analysis,
        "pdufa_trades": pdufa_results,
        "readout_trades": readout_results,
    }

    out_file = Path(__file__).parent / "options_backtest_v2_results.json"
    out_file.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nSaved to: {out_file}")
    return output


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "pdufa"

    if mode == "pdufa":
        run_pdufa_batch()
    elif mode == "readout":
        run_readout_batch()
    elif mode == "analyze":
        run_analysis()
    else:
        print(f"Usage: {sys.argv[0]} [pdufa|readout|analyze]")
