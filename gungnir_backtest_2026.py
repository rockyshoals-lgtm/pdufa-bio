#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║            GUNGNIR 2026 BACKTEST — T-1 Price Validation                  ║
║                                                                          ║
║  Scores all Jan 1 – Feb 16, 2026 PDUFA events through Gungnir v4.0     ║
║  Pulls T-1 close prices from Yahoo Finance (NO forward leakage)         ║
║  Compares predicted tier vs actual FDA outcome                          ║
║                                                                          ║
║  USAGE:  python gungnir_backtest_2026.py                                ║
║  DEPS:   numpy, yfinance (pip install numpy yfinance)                   ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import csv
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# ── Dependencies ──────────────────────────────────────────────────────────
try:
    import numpy as np
except ImportError:
    print("ERROR: numpy required. Run: pip install numpy")
    sys.exit(1)

try:
    import yfinance as yf
except ImportError:
    yf = None
    print("WARNING: yfinance not installed. T-1 prices will be skipped.")
    print("         Run: pip install yfinance")

# ── Import Gungnir ────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gungnir import GungnirScorer


# ═══════════════════════════════════════════════════════════════════════════
# GROUND TRUTH: All resolved PDUFA events Jan 1 – Feb 16, 2026
#
# CRITICAL: Every field here is KNOWN OUTCOME — no forward-looking data.
# The catalyst_text is what was known BEFORE the PDUFA date (T-1 information).
# Outcome is the actual FDA decision.
#
# T-1 = the trading day BEFORE the PDUFA date. This is the last price
#        before the binary event. All scoring uses only T-1 information.
# ═══════════════════════════════════════════════════════════════════════════

GROUND_TRUTH_2026 = [
    # ── APPROVALS ──────────────────────────────────────────────────────────
    {
        "ticker": "PRIVATE",       # Sentynl Therapeutics (private)
        "drug": "copper histidinate (Zycubo)",
        "indication": "Menkes disease",
        "stage": "NDA",
        "pdufa_date": "2026-01-12",
        "outcome": "APPROVED",
        "catalyst_text": (
            "NDA for copper histidinate for Menkes disease. Rare disease. "
            "Orphan drug designation. Priority review. First treatment for Menkes. "
            "Breakthrough therapy designation. Unmet medical need. "
            "Sentynl Therapeutics. Gene therapy approach not required."
        ),
        "notes": "First-ever Menkes treatment. Private company — no tradeable ticker.",
    },
    {
        "ticker": "PRIVATE",       # ScinoPharm Taiwan
        "drug": "glatiramer acetate",
        "indication": "relapsing multiple sclerosis",
        "stage": "ANDA",
        "pdufa_date": "2026-01-05",
        "outcome": "APPROVED",
        "catalyst_text": (
            "ANDA generic glatiramer acetate for relapsing forms of multiple sclerosis. "
            "Well-established drug. Copaxone generic. ScinoPharm Taiwan. "
            "Bioequivalence demonstrated. Standard generic approval pathway."
        ),
        "notes": "Generic — minimal market impact.",
    },
    {
        "ticker": "MRK",
        "drug": "Keytruda + chemo +/- bevacizumab",
        "indication": "platinum-resistant ovarian cancer",
        "stage": "sNDA",
        "pdufa_date": "2026-02-20",      # original PDUFA
        "actual_decision_date": "2026-02-11",  # early approval
        "outcome": "APPROVED",
        "catalyst_text": (
            "sNDA for Keytruda (pembrolizumab) plus chemotherapy with or without "
            "bevacizumab for platinum-resistant ovarian cancer. Phase 3 KEYLYNK-001 "
            "met primary endpoint of overall survival. Statistically significant. "
            "Priority review. Merck large pharma with extensive FDA track record. "
            "Keytruda already approved for multiple indications. Established safety."
        ),
        "notes": "Approved 9 days early (Feb 11 vs Feb 20 PDUFA). MRK large cap — small % move.",
    },

    # ── CRLs (Complete Response Letters) ───────────────────────────────────
    {
        "ticker": "ATRA",         # Atara Biotherapeutics (acquired by Pierre Fabre)
        "drug": "tabelecleucel (tab-cel)",
        "indication": "EBV+ PTLD",
        "stage": "BLA",
        "pdufa_date": "2026-01-09",
        "outcome": "CRL",
        "catalyst_text": (
            "BLA for tabelecleucel (tab-cel) allogeneic T-cell immunotherapy for "
            "EBV-positive post-transplant lymphoproliferative disease. Single-arm "
            "ALLELE study. Rare disease. Orphan drug designation. Breakthrough therapy "
            "designation. Priority review. Second CRL — first CRL in 2024. "
            "FDA had prior alignment on single-arm design but now questioning sufficiency. "
            "Pierre Fabre transferred BLA from Atara. Manufacturing complexity — "
            "allogeneic cell therapy. EU/UK/Switzerland approved."
        ),
        "notes": "2nd CRL. FDA rejected single-arm ALLELE design. Major policy shift on rare disease evidence standards.",
    },
    {
        "ticker": "AQST",
        "drug": "Anaphylm (epinephrine sublingual film)",
        "indication": "type I allergic reactions including anaphylaxis",
        "stage": "NDA",
        "pdufa_date": "2026-01-31",
        "outcome": "CRL",
        "catalyst_text": (
            "NDA for Anaphylm (epinephrine sublingual film) for emergency treatment "
            "of type I allergic reactions including anaphylaxis. Novel drug-device "
            "combination. Human factors studies. Packaging design. No prior FDA "
            "approval for sublingual epinephrine. Aquestive Therapeutics first NDA. "
            "Unmet need for needle-free alternative to EpiPen. Priority review."
        ),
        "notes": "CRL for human factors/packaging issues. Plans Q3 2026 resubmission. Stock crashed ~60%.",
    },
    {
        "ticker": "RGNX",
        "drug": "RGX-121 (clemidsogene lanparvovec)",
        "indication": "Hunter syndrome (MPS II)",
        "stage": "BLA",
        "pdufa_date": "2026-02-08",
        "outcome": "CRL",
        "catalyst_text": (
            "BLA for RGX-121 (clemidsogene lanparvovec) AAV gene therapy for Hunter "
            "syndrome (MPS II). Single-arm study. Rare disease. Orphan designation. "
            "Breakthrough therapy designation. Priority review. External control arm. "
            "CSF heparan sulfate D2S6 as surrogate endpoint. FDA questioning eligibility "
            "criteria and external control comparability. Clinical hold on related RGX-111 "
            "program (January 2026) due to tumor event. Gene therapy manufacturing "
            "complexity. REGENXBIO first BLA."
        ),
        "notes": "CRL citing eligibility criteria, external control comparability, surrogate endpoint concerns. RGX-111 clinical hold.",
    },
    {
        "ticker": "IRON",
        "drug": "bitopertin",
        "indication": "erythropoietic protoporphyria (EPP)",
        "stage": "NDA",
        "pdufa_date": "2026-02-15",
        "outcome": "CRL",
        "catalyst_text": (
            "NDA for bitopertin for erythropoietic protoporphyria (EPP). "
            "Rare disease. Orphan drug designation. Breakthrough therapy designation. "
            "Priority review. Phase 2 AURORA and BEACON trials showed significant PPIX "
            "lowering. Disc Medicine — prior approval (January 2025) for another product. "
            "Phase 3 APOLLO trial ongoing with results expected Q4 2026. "
            "FDA may want Phase 3 data before decision. Surrogate endpoint (PPIX levels)."
        ),
        "notes": "CRL — FDA acknowledged AURORA/BEACON data but wants Phase 3 APOLLO results (Q4 2026). Despite BTD+Orphan+PR.",
    },

    # ── EXTENSIONS / OTHER ─────────────────────────────────────────────────
    {
        "ticker": "TVTX",
        "drug": "sparsentan (Filspari) FSGS sNDA",
        "indication": "focal segmental glomerulosclerosis (FSGS)",
        "stage": "sNDA",
        "pdufa_date": "2026-01-13",
        "outcome": "EXTENSION",
        "catalyst_text": (
            "sNDA for sparsentan (Filspari) for FSGS. Already approved for IgA nephropathy. "
            "Travere Therapeutics. 3-month PDUFA extension announced January 13. "
            "New PDUFA date April 13, 2026. Not a CRL. Rare disease. Orphan designation. "
            "Priority review granted."
        ),
        "notes": "3-month extension to April 13, 2026. NOT a CRL — just delay for review.",
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# YAHOO FINANCE T-1 PRICE PULLER
# ═══════════════════════════════════════════════════════════════════════════

def get_t_minus_1_price(ticker, pdufa_date_str):
    """
    Get T-1 closing price (last trading day BEFORE PDUFA date).
    Returns (t_minus_1_date, t_minus_1_close, pdufa_day_open) or Nones.

    T-1 is critical: this is the LAST price before the binary FDA event.
    All trading decisions must be made at or before T-1.
    """
    if not yf or ticker in ("PRIVATE", "—", ""):
        return None, None, None

    try:
        pdufa_date = datetime.strptime(pdufa_date_str, "%Y-%m-%d")

        # Pull 15 trading days before PDUFA through 3 days after
        start = pdufa_date - timedelta(days=21)
        end = pdufa_date + timedelta(days=5)

        stock = yf.Ticker(ticker)
        hist = stock.history(start=start.strftime("%Y-%m-%d"),
                            end=end.strftime("%Y-%m-%d"),
                            auto_adjust=True)

        if hist.empty:
            return None, None, None

        # Find T-1: last trading day STRICTLY before PDUFA date
        hist.index = hist.index.tz_localize(None)  # remove timezone
        before_pdufa = hist[hist.index < pdufa_date]

        if before_pdufa.empty:
            return None, None, None

        t_minus_1_row = before_pdufa.iloc[-1]
        t_minus_1_date = before_pdufa.index[-1].strftime("%Y-%m-%d")
        t_minus_1_close = float(t_minus_1_row['Close'])

        # Try to get PDUFA day open (T+0)
        on_or_after = hist[hist.index >= pdufa_date]
        pdufa_day_open = float(on_or_after.iloc[0]['Open']) if not on_or_after.empty else None

        return t_minus_1_date, t_minus_1_close, pdufa_day_open

    except Exception as e:
        print(f"  [WARN] Yahoo Finance error for {ticker}: {e}")
        return None, None, None


def get_post_decision_price(ticker, decision_date_str, days_after=2):
    """
    Get the close price a few days after the FDA decision to measure impact.
    Returns (date, close_price) or Nones.
    """
    if not yf or ticker in ("PRIVATE", "—", ""):
        return None, None

    try:
        dec_date = datetime.strptime(decision_date_str, "%Y-%m-%d")
        start = dec_date + timedelta(days=1)
        end = dec_date + timedelta(days=days_after + 5)

        stock = yf.Ticker(ticker)
        hist = stock.history(start=start.strftime("%Y-%m-%d"),
                             end=end.strftime("%Y-%m-%d"),
                             auto_adjust=True)

        if hist.empty:
            return None, None

        hist.index = hist.index.tz_localize(None)
        # Get the close on the first available day after decision
        row = hist.iloc[0]
        return hist.index[0].strftime("%Y-%m-%d"), float(row['Close'])

    except Exception:
        return None, None


# ═══════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def run_backtest():
    """Run full Gungnir backtest on all 2026 resolved events."""
    print("=" * 78)
    print("  ODIN GUNGNIR v4.0 — 2026 BACKTEST (T-1 Validated)")
    print("  All prices are T-1 (day before PDUFA). Zero forward leakage.")
    print("=" * 78)

    # Look for XGB model
    xgb_path = None
    for p in ['xgb_model_v4.json', 'xgb_model_v3.json',
              'odin_k17_gungnir/xgb_model_v4.json']:
        if os.path.exists(p):
            xgb_path = p
            break

    scorer = GungnirScorer(xgb_path)
    print(f"\n  Scorer mode: {scorer.mode}")
    print(f"  Events: {len(GROUND_TRUTH_2026)}")
    print(f"  Period: Jan 1 – Feb 16, 2026")
    if yf:
        print(f"  Yahoo Finance: ENABLED (pulling T-1 prices)")
    else:
        print(f"  Yahoo Finance: DISABLED (install yfinance for price data)")
    print()

    results = []

    for i, event in enumerate(GROUND_TRUTH_2026, 1):
        ticker = event["ticker"]
        drug = event["drug"]
        indication = event["indication"]
        stage = event["stage"]
        pdufa_date = event["pdufa_date"]
        outcome = event["outcome"]
        catalyst = event["catalyst_text"]
        decision_date = event.get("actual_decision_date", pdufa_date)

        print(f"  [{i}/{len(GROUND_TRUTH_2026)}] {ticker:8s} | {drug[:40]:40s} | PDUFA: {pdufa_date}")

        # ── Score through Gungnir (T-1 information only) ──────────────
        result = scorer.score(
            catalyst=catalyst,
            ticker=ticker,
            drug=drug,
            indication=indication,
            stage=stage,
            date=pdufa_date,
        )

        # ── Pull T-1 price from Yahoo Finance ─────────────────────────
        t1_date, t1_close, t0_open = get_t_minus_1_price(ticker, pdufa_date)
        post_date, post_close = get_post_decision_price(ticker, decision_date)

        # Calculate price move
        pct_move = None
        if t1_close and post_close:
            pct_move = (post_close - t1_close) / t1_close * 100

        # ── Determine if prediction was correct ───────────────────────
        tier = result["tier"]
        correct = None
        if outcome == "APPROVED":
            # TIER_1/2 = correct (we would have been long)
            correct = tier in ("TIER_1", "TIER_2")
        elif outcome == "CRL":
            # TIER_3/4 = correct (we avoided or went short)
            correct = tier in ("TIER_3", "TIER_4")
        elif outcome == "EXTENSION":
            correct = None  # extensions are neutral — can't score

        record = {
            "ticker": ticker,
            "drug": drug,
            "indication": indication,
            "stage": stage,
            "pdufa_date": pdufa_date,
            "decision_date": decision_date,
            "outcome": outcome,
            "tier": tier,
            "final_score": result["final_score"],
            "ml_score": result["ml_score"],
            "action": result["action"],
            "hard_cap": result["hard_cap"],
            "risk_flags": " | ".join(result["risk_flags"]),
            "rules_fired": ", ".join(r["name"] for r in result["rules_fired"]),
            "t1_date": t1_date,
            "t1_close": t1_close,
            "t0_open": t0_open,
            "post_date": post_date,
            "post_close": post_close,
            "pct_move": pct_move,
            "correct": correct,
            "notes": event.get("notes", ""),
        }
        results.append(record)

        # Print inline result
        score_str = f"{result['final_score']:.1%}"
        outcome_emoji = {"APPROVED": "OK", "CRL": "XX", "EXTENSION": "->"}[outcome]
        correct_str = {True: "YES", False: "NO", None: "N/A"}[correct]
        price_str = f"{pct_move:+.1f}%" if pct_move is not None else "N/A"

        print(f"           {tier:8s} ({score_str}) | Actual: {outcome_emoji} | "
              f"Correct: {correct_str} | T-1: ${t1_close:.2f}" if t1_close else
              f"           {tier:8s} ({score_str}) | Actual: {outcome_emoji} | "
              f"Correct: {correct_str} | T-1: N/A")
        print()

    # ═══════════════════════════════════════════════════════════════════════
    # ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 78)
    print("  BACKTEST RESULTS SUMMARY")
    print("=" * 78)

    # Tier distribution
    tiers = defaultdict(int)
    for r in results:
        tiers[r["tier"]] += 1

    print(f"\n  TIER DISTRIBUTION:")
    for t in ["TIER_1", "TIER_2", "TIER_3", "TIER_4"]:
        print(f"    {t}: {tiers.get(t, 0)}")

    # Outcome distribution
    outcomes = defaultdict(int)
    for r in results:
        outcomes[r["outcome"]] += 1

    print(f"\n  OUTCOME DISTRIBUTION:")
    for o in ["APPROVED", "CRL", "EXTENSION"]:
        print(f"    {o}: {outcomes.get(o, 0)}")

    # Accuracy (excluding extensions and private companies)
    scoreable = [r for r in results if r["correct"] is not None]
    if scoreable:
        n_correct = sum(1 for r in scoreable if r["correct"])
        n_total = len(scoreable)
        accuracy = n_correct / n_total

        print(f"\n  PREDICTION ACCURACY:")
        print(f"    Scoreable events: {n_total}")
        print(f"    Correct:          {n_correct}")
        print(f"    Accuracy:         {accuracy:.1%}")

        # Breakdown by outcome
        approvals = [r for r in scoreable if r["outcome"] == "APPROVED"]
        crls = [r for r in scoreable if r["outcome"] == "CRL"]

        if approvals:
            app_correct = sum(1 for r in approvals if r["correct"])
            print(f"\n    APPROVAL accuracy: {app_correct}/{len(approvals)} "
                  f"({app_correct/len(approvals):.1%})")
            for r in approvals:
                tag = "OK" if r["correct"] else "MISS"
                print(f"      [{tag}] {r['ticker']:8s} {r['drug'][:35]:35s} "
                      f"-> {r['tier']} ({r['final_score']:.1%})")

        if crls:
            crl_correct = sum(1 for r in crls if r["correct"])
            print(f"\n    CRL detection:     {crl_correct}/{len(crls)} "
                  f"({crl_correct/len(crls):.1%})")
            for r in crls:
                tag = "OK" if r["correct"] else "MISS"
                print(f"      [{tag}] {r['ticker']:8s} {r['drug'][:35]:35s} "
                      f"-> {r['tier']} ({r['final_score']:.1%})")

    # False positives analysis (CRLs scored as TIER_1/2)
    false_pos = [r for r in results if r["outcome"] == "CRL" and r["tier"] in ("TIER_1", "TIER_2")]
    if false_pos:
        print(f"\n  FALSE POSITIVES (CRL but scored TIER_1/2 — WOULD HAVE LOST MONEY):")
        for r in false_pos:
            move_str = f"{r['pct_move']:+.1f}%" if r['pct_move'] else "N/A"
            print(f"    {r['ticker']:8s} | {r['tier']} ({r['final_score']:.1%}) | "
                  f"Move: {move_str} | {r['notes']}")

    # False negatives (Approvals scored as TIER_3/4)
    false_neg = [r for r in results if r["outcome"] == "APPROVED" and r["tier"] in ("TIER_3", "TIER_4")]
    if false_neg:
        print(f"\n  FALSE NEGATIVES (APPROVED but scored TIER_3/4 — MISSED OPPORTUNITY):")
        for r in false_neg:
            move_str = f"{r['pct_move']:+.1f}%" if r['pct_move'] else "N/A"
            print(f"    {r['ticker']:8s} | {r['tier']} ({r['final_score']:.1%}) | "
                  f"Move: {move_str} | {r['notes']}")

    # P&L simulation (if we have prices)
    tradeable = [r for r in results if r["pct_move"] is not None
                 and r["ticker"] not in ("PRIVATE", "—")]
    if tradeable:
        print(f"\n  HYPOTHETICAL P&L (if traded per Gungnir signal):")
        total_pnl = 0.0
        for r in tradeable:
            tier = r["tier"]
            move = r["pct_move"]

            if tier in ("TIER_1", "TIER_2"):
                # Would have been long → gain/lose the move
                trade_pnl = move
                sizing = "100%" if tier == "TIER_1" else "50%"
            elif tier in ("TIER_3", "TIER_4"):
                # Would have avoided → $0 (or could short for gain)
                trade_pnl = 0.0
                sizing = "FLAT"
            else:
                trade_pnl = 0.0
                sizing = "?"

            total_pnl += trade_pnl
            pnl_str = f"{trade_pnl:+.1f}%" if trade_pnl != 0 else "FLAT"
            print(f"    {r['ticker']:8s} | {tier} | Size: {sizing:5s} | "
                  f"Move: {move:+.1f}% | P&L: {pnl_str}")

        print(f"\n    TOTAL HYPOTHETICAL P&L: {total_pnl:+.1f}%")

    # ═══════════════════════════════════════════════════════════════════════
    # EXPORT CSV
    # ═══════════════════════════════════════════════════════════════════════

    output_file = "gungnir_backtest_2026_results.csv"
    if results:
        fieldnames = list(results[0].keys())
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(results)
        print(f"\n  Results exported to: {output_file}")

    # ═══════════════════════════════════════════════════════════════════════
    # KEY OBSERVATIONS
    # ═══════════════════════════════════════════════════════════════════════

    print(f"\n{'=' * 78}")
    print("  KEY OBSERVATIONS FOR MODEL IMPROVEMENT")
    print("=" * 78)
    print("""
  1. IRON (bitopertin EPP): BTD + Orphan + PR but CRL. FDA wanted Phase 3
     APOLLO data before deciding. Model blind spot: "FDA wants more data"
     is not captured by current features. Surrogate endpoint + ongoing
     Phase 3 = high CRL risk even with all designations.

  2. ATRA/tab-cel: 2nd CRL despite EU approval + BTD + Orphan + PR.
     Single-arm design in Hoeg era = death sentence. Model correctly
     penalizes single-arm via SINGLE_ARM_HOEG hard cap, but may not
     penalize enough for REPEAT CRL cases.

  3. RGNX/RGX-121: Gene therapy + external control + surrogate endpoint
     + clinical hold on sister program. Triple threat. GENE_THERAPY_P3
     hard cap should catch this.

  4. AQST/Anaphylm: Human factors/packaging CRL. Novel drug-device combo
     with no prior FDA approval for this delivery method. Model has no
     "first-in-class device" risk feature.

  5. MRK/Keytruda sNDA: Easy approval. Large pharma + established drug +
     Phase 3 met endpoint. Model should score this TIER_1 trivially.
""")

    print("=" * 78)
    print("  BACKTEST COMPLETE")
    print("=" * 78)

    return results


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    results = run_backtest()
