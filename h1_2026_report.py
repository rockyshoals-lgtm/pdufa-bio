#!/usr/bin/env python3
"""
H1 2026 Catalyst Report Generator
Prepares comprehensive catalyst data for professional DOCX generation

Engines:
- ODIN v14: PDUFA scoring (51 features)
- Gungnir v43: Phase readout scoring (144 features)
- BIFROST v4: Runup timing/sizing
- Explosion v5.4: >25% move prediction

Output: JSON data file for Node.js DOCX generation
"""

import json
import csv
from datetime import datetime, date
from pathlib import Path
import sys

# Configuration
DATA_DIR = Path("/sessions/loving-nifty-dirac/mnt/Python/9realms")
OUTPUT_DIR = Path("/sessions/loving-nifty-dirac/mnt/Odin Perfection")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Data files
CATALYST_SCORES_FILE = DATA_DIR / "catalyst_scores_v33.json"
ODIN_CSV_FILE = DATA_DIR / "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv"
BIFROST_DEPLOY_FILE = DATA_DIR / "bifrost_v4_deploy.json"

OUTPUT_JSON = OUTPUT_DIR / "h1_2026_report_data.json"

# Current portfolio (from CLAUDE.md context)
CURRENT_PORTFOLIO = {
    "GRCE": {"ticker": "GRCE", "drug": "GTX-104", "catalyst_date": "2026-04-23"},
    "WHWK": {"ticker": "WHWK", "drug": "WH1211", "catalyst_date": "2026-04-17"},
    "CRDF": {"ticker": "CRDF", "drug": "", "catalyst_date": "2026-04-17"},
    "CABA": {"ticker": "CABA", "drug": "PF-06940434", "catalyst_date": "2026-06-03"},
    "ALXO": {"ticker": "ALXO", "drug": "", "catalyst_date": "2026-05-07"},
}

# Tier colors
TIER_COLORS = {
    "ALPHA": {"text": "#2E7D32", "bg": "#E8F5E9"},
    "BETA": {"text": "#1565C0", "bg": "#E3F2FD"},
    "GAMMA": {"text": "#424242", "bg": "#F5F5F5"},
    "DELTA": {"text": "#C62828", "bg": "#FFEBEE"},
    "OMEGA": {"text": "#B71C1C", "bg": "#FFCDD2"},
    "T1": {"text": "#2E7D32", "bg": "#E8F5E9"},
    "T2": {"text": "#1565C0", "bg": "#E3F2FD"},
    "T3": {"text": "#424242", "bg": "#F5F5F5"},
    "T4": {"text": "#C62828", "bg": "#FFEBEE"},
}

def parse_date(date_str):
    """Parse catalyst date string"""
    if not date_str or date_str == "2026-12-31":
        return None
    try:
        return datetime.fromisoformat(date_str).date()
    except:
        return None

def is_h1_2026(date_obj):
    """Check if date is in H1 2026 (Jan-Jun)"""
    if not date_obj:
        return False
    return date_obj.year == 2026 and date_obj.month <= 6

def load_catalyst_scores():
    """Load Gungnir v33 catalyst scores"""
    print(f"Loading catalyst scores from {CATALYST_SCORES_FILE}...")
    with open(CATALYST_SCORES_FILE, "r") as f:
        data = json.load(f)

    print(f"  Total catalysts: {len(data)}")

    # Filter H1 2026
    h1_catalysts = []
    for cat in data:
        cat_date = parse_date(cat.get("catalyst_date"))
        if is_h1_2026(cat_date):
            h1_catalysts.append(cat)

    print(f"  H1 2026 catalysts: {len(h1_catalysts)}")
    return h1_catalysts

def load_odin_training_data():
    """Load ODIN training CSV for feature access"""
    print(f"Loading ODIN training data from {ODIN_CSV_FILE}...")
    data = {}
    with open(ODIN_CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.get("ticker", "").strip()
            if ticker:
                data[ticker] = row
    print(f"  Total records: {len(data)}")
    return data

def load_bifrost_config():
    """Load BIFROST v4 configuration"""
    print(f"Loading BIFROST v4 config from {BIFROST_DEPLOY_FILE}...")
    try:
        with open(BIFROST_DEPLOY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def get_bifrost_timing(market_cap_usd, odin_tier):
    """Get BIFROST timing and sizing recommendations"""
    if market_cap_usd is None or odin_tier is None:
        return None

    mcap = market_cap_usd

    # Determine size tier
    if mcap < 50_000_000:
        size_tier = "nano"
        entry_days = 45
        exit_days = 3
    elif mcap < 300_000_000:
        size_tier = "micro"
        entry_days = 30
        exit_days = 1
    elif mcap < 2_000_000_000:
        size_tier = "small"
        entry_days = 21
        exit_days = 3
    elif mcap < 10_000_000_000:
        size_tier = "mid"
        entry_days = 14
        exit_days = 1
    else:
        size_tier = "large"
        entry_days = 7
        exit_days = 1

    # Position sizing by ODIN tier
    tier_to_odin = {
        "T1": 0.85,
        "T2": 0.65,
        "T3": 0.40,
        "T4": 0.00,
    }

    odin_score = tier_to_odin.get(odin_tier, 0.65)

    if odin_score >= 0.85:
        size_pct = "4-6%"
        max_size = 6
    elif odin_score >= 0.65:
        size_pct = "3-4%"
        max_size = 4
    elif odin_score >= 0.40:
        size_pct = "1-2%"
        max_size = 2
    else:
        size_pct = "No trade"
        max_size = 0

    return {
        "size_tier": size_tier,
        "entry_days_before": entry_days,
        "exit_days_before": exit_days,
        "position_size": size_pct,
        "max_position_pct": max_size,
    }

def build_portfolio_section(catalysts):
    """Build detailed portfolio section"""
    portfolio = []

    for ticker, info in CURRENT_PORTFOLIO.items():
        # Find matching catalyst
        matching = next(
            (cat for cat in catalysts if cat["ticker"] == ticker),
            None
        )

        if matching:
            bifrost = get_bifrost_timing(
                matching.get("market_cap"),
                matching.get("gungnir_tier")
            )

            portfolio.append({
                "ticker": ticker,
                "drug": matching.get("drug", ""),
                "indication": matching.get("indication", ""),
                "catalyst_date": matching.get("catalyst_date", ""),
                "gungnir_probability": matching.get("gungnir_probability", 0),
                "gungnir_tier": matching.get("gungnir_tier", ""),
                "investment_score": matching.get("investment_score", 0),
                "investment_tier": matching.get("investment_tier", ""),
                "p_good_plus": matching.get("p_good_plus", 0),
                "p_crash": matching.get("p_crash", 0),
                "market_cap": matching.get("market_cap", 0),
                "price": matching.get("price", 0),
                "bifrost": bifrost,
                "flags": matching.get("flags", []),
            })

    return portfolio

def build_pdufa_section(catalysts):
    """Build PDUFA catalysts section"""
    pdufa = [cat for cat in catalysts if cat.get("is_pdufa")]
    pdufa.sort(key=lambda x: x.get("catalyst_date", ""))

    # Add BIFROST timing
    for cat in pdufa:
        bifrost = get_bifrost_timing(
            cat.get("market_cap"),
            cat.get("gungnir_tier")
        )
        cat["bifrost"] = bifrost

    return pdufa

def build_readout_section(catalysts):
    """Build top phase readout catalysts (non-PDUFA)"""
    readouts = [cat for cat in catalysts if not cat.get("is_pdufa")]
    readouts.sort(
        key=lambda x: x.get("investment_score", 0),
        reverse=True
    )
    return readouts[:50]  # Top 50 readouts

def build_executive_summary(catalysts, portfolio):
    """Build executive summary data"""
    pdufa_count = sum(1 for cat in catalysts if cat.get("is_pdufa"))
    readout_count = sum(1 for cat in catalysts if not cat.get("is_pdufa"))

    tier_distribution = {tier: 0 for tier in ["ALPHA", "BETA", "GAMMA", "DELTA", "OMEGA"]}
    for cat in catalysts:
        tier = cat.get("investment_tier", "DELTA")
        if tier in tier_distribution:
            tier_distribution[tier] += 1

    return {
        "total_catalysts": len(catalysts),
        "pdufa_count": pdufa_count,
        "readout_count": readout_count,
        "tier_distribution": tier_distribution,
        "portfolio_count": len(portfolio),
    }

def build_engine_summary():
    """Build engine performance summary"""
    return {
        "odin_v14": {
            "name": "ODIN v14 (PDUFA Approval)",
            "architecture": "51-feature L2 Ridge Logistic Regression",
            "regularization": "C=0.10",
            "training_events": 1845,
            "holdout_events": 358,
            "wf_auc": 0.9011,
            "ho_auc": 0.9363,
            "ho_brier": 0.0895,
            "t1_win_rate": "98.7%",
            "t1_picks": 154,
            "tier_thresholds": {"T1": "≥0.85", "T2": "0.65-0.85", "T3": "0.40-0.65", "T4": "<0.40"},
        },
        "gungnir_v43": {
            "name": "Gungnir v43 (Phase Readout)",
            "architecture": "144-feature meta-ensemble (85% Ridge + 15% XGB)",
            "training_events": 1752,
            "wf_auc": 0.8001,
            "brier": 0.1330,
            "ev_spread": "+6.64pp",
            "key_discovery": "Drug modality × trial context interactions unlock strongest signals",
        },
        "bifrost_v4": {
            "name": "BIFROST v4 (Runup Timing & Sizing)",
            "architecture": "v2 decision matrix + triple-ensemble magnitude regression",
            "training_events": 1705,
            "windows": 12,
            "backtest_sharpe": 5.45,
            "backtest_win_rate": "70.8%",
            "backtest_max_dd": "-4.9%",
            "backtest_return": "$100K → $18.1M",
            "cardinal_rule": "Never hold through FDA decision",
        },
        "explosion_v54": {
            "name": "Explosion Detector v5.4 (>25% Moves)",
            "architecture": "Ensemble (80% Ridge + 5% GBM + 15% LightGBM)",
            "features": 57,
            "lr_test_auc": 0.9332,
            "ensemble_auc": 0.9307,
            "key_discovery": "Orphan × 7d runup = maximum explosion potential",
            "tiers": {"SNIPER": "≥20%, 2x size", "ELEVATED": "≥10%, 1.5x", "NORMAL": "≥5%, 1x", "QUIET": "<5%, 0.8x"},
        },
    }

def main():
    """Main report generation"""
    print("\n" + "="*70)
    print("H1 2026 CATALYST REPORT GENERATOR")
    print("="*70)

    # Load all data
    catalysts = load_catalyst_scores()
    odin_data = load_odin_training_data()
    bifrost_config = load_bifrost_config()

    # Build sections
    print("\nBuilding report sections...")
    portfolio = build_portfolio_section(catalysts)
    pdufa = build_pdufa_section(catalysts)
    readouts = build_readout_section(catalysts)
    summary = build_executive_summary(catalysts, portfolio)
    engines = build_engine_summary()

    print(f"  Portfolio: {len(portfolio)} positions")
    print(f"  PDUFA catalysts: {len(pdufa)}")
    print(f"  Phase readouts: {len(readouts)} (top 50 shown)")

    # Build report JSON
    report_data = {
        "generated_at": datetime.now().isoformat(),
        "report_title": "9 Realms H1 2026 Catalyst Report",
        "report_subtitle": "ODIN v14 • Gungnir v43 • BIFROST v4 • Explosion v5.4",
        "report_date": "April 7, 2026",
        "disclaimer": "For informational and educational purposes only. Not investment advice.",

        # Sections
        "executive_summary": summary,
        "portfolio": portfolio,
        "pdufa_catalysts": pdufa,
        "readout_catalysts": readouts,
        "engine_summary": engines,

        # Metadata
        "tier_colors": TIER_COLORS,
        "page_config": {
            "page_width_dxa": 12240,
            "page_height_dxa": 15840,
            "margins_dxa": 720,  # 0.5 inches
        },
    }

    # Write output JSON
    print(f"\nWriting report data to {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, "w") as f:
        json.dump(report_data, f, indent=2, default=str)

    print(f"  ✓ Report data written ({OUTPUT_JSON.stat().st_size / 1024:.1f} KB)")
    print("\n" + "="*70)
    print("DATA PREPARATION COMPLETE")
    print(f"Output: {OUTPUT_JSON}")
    print("Next: Run 'node h1_report_gen.js' to generate DOCX")
    print("="*70 + "\n")

    return OUTPUT_JSON

if __name__ == "__main__":
    main()
