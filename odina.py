"""
ODIN Catalyst Scatter Plot Module
=================================

This module enforces a mandatory visualization artifact for every ODIN run.

PLOT SPEC (IMMUTABLE):
- X-axis: Market Cap (USD), log scale
- Y-axis: Estimated Catalyst Month (bucketed to first of month)
- Color: Odin Tier (Tier 1 / Tier 2 / Tier 3 / Tier ?)
- Output: PNG saved to <output_dir>/plots/
- Safe: Never crashes ODIN if data missing

USAGE (MANDATORY AT END OF ODIN RUN):

    from odin_catalyst_scatter import generate_catalyst_scatter

    generate_catalyst_scatter(
        results_df=results_df,
        out_dir=Path(output_dir) / "plots"
    )

This module does NOT modify scoring, tiers, or predictions.
"""

import math
import datetime as dt
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# -------------------------
# INTERNAL HELPERS
# -------------------------

def _ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _infer_market_cap(df: pd.DataFrame) -> pd.Series:
    candidates = [
        "market_cap",
        "marketcap",
        "mkt_cap",
        "market_cap_usd",
        "mc",
    ]
    for col in candidates:
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            if s.notna().any():
                return s
    return pd.Series([math.nan] * len(df))


def _infer_catalyst_date(df: pd.DataFrame) -> pd.Series:
    candidates = [
        "pdufa_date",
        "catalyst_date",
        "event_date",
        "action_date",
        "estimated_catalyst_date",
        "catalyst_month",
        "pdufa",
        "catalyst",
        "event",
    ]
    for col in candidates:
        if col in df.columns:
            s = pd.to_datetime(df[col], errors="coerce")
            if s.notna().any():
                return s
    return pd.Series([pd.NaT] * len(df))


def _infer_tier(df: pd.DataFrame) -> pd.Series:
    candidates = ["odin_tier", "tier", "odinTier", "ODIN_TIER"]
    for col in candidates:
        if col in df.columns:
            s = df[col].astype(str).str.strip()
            if s.notna().any():
                s = s.replace({"1": "Tier 1", "2": "Tier 2", "3": "Tier 3"})
                s = s.str.replace(r"^tier\s*", "Tier ", regex=True, case=False)
                return s
    return pd.Series(["Tier ?"] * len(df))


# -------------------------
# PUBLIC API
# -------------------------

def generate_catalyst_scatter(
    results_df: pd.DataFrame,
    out_dir,
    title: str | None = None,
    filename_prefix: str = "odin_catalyst_scatter",
    dpi: int = 200,
):
    """
    Generates and saves the ODIN Catalyst Scatter Plot.

    Parameters
    ----------
    results_df : pd.DataFrame
        Final ODIN output dataframe (same one written to CSV)
    out_dir : str | Path
        Directory where plot PNG should be saved
    title : str | None
        Optional plot title override
    filename_prefix : str
        Prefix for saved PNG
    dpi : int
        PNG resolution

    Returns
    -------
    dict
        {"png": "<path>"} or {"png": None, "note": "..."}
    """

    out_dir = _ensure_dir(out_dir)
    df = results_df.copy()

    df["_market_cap"] = _infer_market_cap(df)
    df["_catalyst_date"] = _infer_catalyst_date(df)
    df["_tier"] = _infer_tier(df)

    plot_df = df[
        df["_market_cap"].notna() &
        df["_catalyst_date"].notna()
    ].copy()

    if plot_df.empty:
        return {
            "png": None,
            "note": "No plottable rows: missing market cap or catalyst date."
        }

    # Bucket Y-axis to month
    plot_df["_month"] = (
        plot_df["_catalyst_date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    tier_order = ["Tier 1", "Tier 2", "Tier 3", "Tier ?"]
    tier_colors = {
        "Tier 1": "#1f77b4",
        "Tier 2": "#ff7f0e",
        "Tier 3": "#2ca02c",
        "Tier ?": "#7f7f7f",
    }

    fig = plt.figure(figsize=(12, 7))
    ax = plt.gca()

    for tier in tier_order:
        sub = plot_df[plot_df["_tier"] == tier]
        if sub.empty:
            continue
        ax.scatter(
            sub["_market_cap"],
            sub["_month"],
            s=55,
            alpha=0.80,
            label=f"{tier} (n={len(sub)})",
            c=tier_colors[tier],
            edgecolors="none",
        )

    ax.set_xscale("log")
    ax.set_xlabel("Market Cap (USD, log scale)")
    ax.set_ylabel("Estimated Catalyst Month")

    ax.yaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.yaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.4)

    if not title:
        title = "ODIN Catalyst Map — Market Cap vs Catalyst Month (Color = Tier)"
    ax.set_title(title)

    ax.legend(loc="best", frameon=True)

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    png_path = Path(out_dir) / f"{filename_prefix}_{ts}.png"

    plt.tight_layout()
    fig.savefig(png_path, dpi=dpi)
    plt.close(fig)

    return {"png": str(png_path)}
