#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  GUNGNIR v4.0 — 2026 READOUT BACKTEST (T-1 Validated)                  ║
║  Period: January 1 – February 16, 2026                                  ║
║  49 events from historical_readouts_2000.csv                            ║
║  All prices: Yahoo Finance T-1 close (last trading day before readout) ║
║  Zero forward leakage.                                                  ║
╚══════════════════════════════════════════════════════════════════════════╝

USAGE:
    cd C:\\Users\\dcmoo\\Documents\\Python
    python gungnir_readout_backtest_2026.py
"""

import csv
import sys
import os
import json
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gungnir import GungnirScorer

try:
    import yfinance as yf
    _HAS_YF = True
except ImportError:
    _HAS_YF = False
    print("WARNING: yfinance not installed. No price data will be pulled.")

import numpy as np

DATA_FILE = "historical_readouts_2000.csv"


def load_events():
    events = []
    with open(DATA_FILE, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("year", "") != "2026":
                continue
            events.append(r)
    events.sort(key=lambda x: x["Catalyst Date"], reverse=True)
    return events


def get_t1_price(ticker, catalyst_date_str):
    """Get T-1 close, T+0 open, and post-decision close from Yahoo Finance."""
    if not _HAS_YF:
        return None, None, None, None, None

    cat_date = datetime.strptime(catalyst_date_str, "%Y-%m-%d")
    start = cat_date - timedelta(days=10)
    end = cat_date + timedelta(days=5)

    try:
        df = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                         end=end.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
        if df.empty:
            return None, None, None, None, None

        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)

        pre_dates = [d for d in df.index if d.date() < cat_date.date()]
        if not pre_dates:
            return None, None, None, None, None
        t1_date = max(pre_dates)
        t1_close = float(df.loc[t1_date, "Close"])

        t0_dates = [d for d in df.index if d.date() == cat_date.date()]
        t0_open = float(df.loc[t0_dates[0], "Open"]) if t0_dates else None

        post_dates = [d for d in df.index if d.date() >= cat_date.date()]
        if post_dates:
            post_date = min(post_dates)
            post_close = float(df.loc[post_date, "Close"])
        else:
            post_close = None

        return t1_date.strftime("%Y-%m-%d"), t1_close, t0_open, post_close, None

    except Exception as e:
        return None, None, None, None, str(e)


def run_backtest():
    events = load_events()
    print(f"\nLoaded {len(events)} readout events for 2026\n")

    scorer = GungnirScorer()
    results = []

    for i, ev in enumerate(events):
        ticker = ev["Ticker"]
        drug = ev["Drug"]
        indication = ev["Indication"]
        stage = ev["Stage"]
        cat_date = ev["Catalyst Date"]
        catalyst_text = ev["Catalyst"]
        outcome = ev["outcome"]

        print(f"[{i+1:2d}/{len(events)}] {cat_date} | {ticker:8s} | {stage:12s} | {outcome:8s} | {drug[:45]}")

        result = scorer.score(
            catalyst_text,
            ticker=ticker,
            drug=drug,
            indication=indication,
            stage=stage,
            date=cat_date
        )

        tier = result.get("tier", "UNKNOWN")
        final_score = result.get("final_score", 0.0)
        ml_score = result.get("ml_score", 0.0)
        hard_cap = result.get("hard_cap_applied")
        risk_flags_raw = result.get("risk_flags", [])
        rules_fired_raw = result.get("rules_fired", [])
        # Normalize: may be list of dicts, strings, or mixed
        def flatten_list(lst):
            out = []
            for item in lst:
                if isinstance(item, dict):
                    out.append(item.get("rule", item.get("flag", item.get("name", str(item)))))
                elif isinstance(item, (list, tuple)):
                    out.extend(str(x) for x in item)
                else:
                    out.append(str(item))
            return out
        rules_fired = flatten_list(rules_fired_raw)
        risk_flags = flatten_list(risk_flags_raw)

        if outcome == "positive":
            correct = tier in ("TIER_1", "TIER_2")
        elif outcome == "negative":
            correct = tier in ("TIER_3", "TIER_4")
        else:
            correct = None

        t1_date, t1_close, t0_open, post_close, price_err = get_t1_price(ticker, cat_date)

        pct_move = None
        if t1_close and post_close:
            pct_move = ((post_close - t1_close) / t1_close) * 100

        row = {
            "ticker": ticker,
            "company": ev.get("Name", ""),
            "drug": drug,
            "indication": indication,
            "stage": stage,
            "catalyst_date": cat_date,
            "outcome": outcome,
            "tier": tier,
            "final_score": final_score,
            "ml_score": ml_score,
            "hard_cap": hard_cap or "",
            "risk_flags": " | ".join(risk_flags) if risk_flags else "",
            "rules_fired": ", ".join(rules_fired) if rules_fired else "",
            "t1_date": t1_date or "",
            "t1_close": t1_close or "",
            "t0_open": t0_open or "",
            "post_close": post_close or "",
            "pct_move": f"{pct_move:.4f}" if pct_move is not None else "",
            "correct": correct if correct is not None else "",
            "catalyst_text": catalyst_text[:200],
        }
        results.append(row)

        tag = "OK" if correct else ("XX" if correct is False else "??")
        cap_str = f" [CAP={hard_cap}]" if hard_cap else ""
        move_str = f" | Move: {pct_move:+.1f}%" if pct_move is not None else ""
        print(f"      -> {tier} ({final_score:.1%}){cap_str}{move_str} [{tag}]")

    # ─── Write CSV ───
    outfile = "gungnir_readout_backtest_2026_results.csv"
    fieldnames = list(results[0].keys())
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)
    print(f"\n{'='*80}")
    print(f"  Results written to {outfile}")

    # ═══════════════════════════════════════════════════════════════
    # ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*80}")
    print("  GUNGNIR v4.0 — 2026 READOUT BACKTEST SUMMARY")
    print(f"{'='*80}")

    scoreable = [r for r in results if r["correct"] != ""]
    correct_n = sum(1 for r in scoreable if r["correct"] is True)
    wrong_n = sum(1 for r in scoreable if r["correct"] is False)

    print(f"\n  Total events:        {len(results)}")
    print(f"  Scoreable:           {len(scoreable)}")
    print(f"  Overall accuracy:    {correct_n}/{len(scoreable)} = {correct_n/len(scoreable):.1%}")

    positives = [r for r in scoreable if r["outcome"] == "positive"]
    negatives = [r for r in scoreable if r["outcome"] == "negative"]
    pos_correct = sum(1 for r in positives if r["correct"] is True)
    neg_correct = sum(1 for r in negatives if r["correct"] is True)

    print(f"\n  POSITIVE detection:  {pos_correct}/{len(positives)} ({pos_correct/len(positives):.1%})")
    print(f"  NEGATIVE detection:  {neg_correct}/{len(negatives)} ({neg_correct/len(negatives):.1%})")

    tiers = Counter(r["tier"] for r in results)
    print(f"\n  Tier distribution:")
    for t in ["TIER_1", "TIER_2", "TIER_3", "TIER_4"]:
        n = tiers.get(t, 0)
        print(f"    {t}: {n:3d} ({n/len(results):.0%})")

    # False positives
    fps = [r for r in scoreable if r["outcome"] == "negative" and r["correct"] is False]
    if fps:
        print(f"\n  FALSE POSITIVES ({len(fps)}) — negative events scored TIER_1/2:")
        for r in fps:
            move_str = f"{float(r['pct_move']):+.1f}%" if r['pct_move'] else "N/A"
            print(f"    {r['ticker']:8s} {r['tier']} ({float(r['final_score']):.1%}) | {r['stage']:12s} | Move: {move_str}")
            print(f"      {r['drug'][:60]}")
            if r['rules_fired']:
                print(f"      Rules: {r['rules_fired']}")

    # False negatives
    fns = [r for r in scoreable if r["outcome"] == "positive" and r["correct"] is False]
    if fns:
        print(f"\n  FALSE NEGATIVES ({len(fns)}) — positive events scored TIER_3/4:")
        for r in fns:
            move_str = f"{float(r['pct_move']):+.1f}%" if r['pct_move'] else "N/A"
            print(f"    {r['ticker']:8s} {r['tier']} ({float(r['final_score']):.1%}) | {r['stage']:12s} | Move: {move_str}")
            print(f"      {r['drug'][:60]}")
            if r['rules_fired']:
                print(f"      Rules: {r['rules_fired']}")

    # P&L
    print(f"\n  HYPOTHETICAL P&L (equal-weight, T-1 close -> post close):")
    total_pnl = 0.0
    trades = 0
    wins = 0
    losses = 0
    for r in results:
        if not r["pct_move"]:
            continue
        move = float(r["pct_move"])
        tier = r["tier"]
        if tier == "TIER_1":
            pnl = move
            action = "LONG"
        elif tier == "TIER_2":
            pnl = move * 0.5
            action = "HALF"
        else:
            pnl = 0.0
            action = "FLAT"

        if action != "FLAT":
            trades += 1
            if pnl > 0:
                wins += 1
            else:
                losses += 1
        total_pnl += pnl

    print(f"    Total trades: {trades}")
    if trades > 0:
        print(f"    Win/Loss: {wins}/{losses} ({wins/trades:.0%} win rate)")
    print(f"    Net P&L: {total_pnl:+.1f}%")
    print(f"\n{'='*80}")

    return results


if __name__ == "__main__":
    run_backtest()
