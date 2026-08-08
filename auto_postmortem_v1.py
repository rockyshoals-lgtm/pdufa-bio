#!/usr/bin/env python3
"""
AUTO POSTMORTEM v1.0 -- 2026-05-28
Detect fired catalysts via price moves on tracked V-IDs.

LOGIC
-----
1. Load forward V-IDs from MASTER_PREDICTION_LEDGER (active predictions)
2. For each, fetch current price + 1-day change via FMP
3. Flag any with |price change| >= 20% as FIRED (binary catalyst likely just hit)
4. Write postmortem markdown to postmortems/YYYY-MM-DD_TICKER_postmortem.md
5. Print "FIRED: TICKER price_change%" for daemon to pick up

OUTPUT
------
postmortems/YYYY-MM-DD_TICKER_postmortem.md   (one file per fired catalyst)
stdout: machine-readable "FIRED:" lines for daemon alert generation
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER_DIR = HERE / "MASTER_PREDICTION_LEDGER"
POSTMORTEM_DIR = HERE / "postmortems"
POSTMORTEM_DIR.mkdir(exist_ok=True)

THRESHOLD_PCT = 20.0  # Move threshold to flag as "FIRED"

def _load_dotenv():
    for d in [HERE] + list(HERE.parents)[:3]:
        p = d / ".env"
        if p.exists():
            for line in open(p):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
            return
_load_dotenv()
FMP_API_KEY = os.environ.get("FMP_API_KEY", "")

def fmp_quote(ticker):
    if not FMP_API_KEY:
        return None
    try:
        import requests
    except ImportError:
        return None
    try:
        r = requests.get(
            f"https://financialmodelingprep.com/api/v3/quote/{ticker}",
            params={"apikey": FMP_API_KEY},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                return data[0]
        return None
    except Exception:
        return None

def load_tracked_vids():
    """Pull active V-IDs (predictions with no fired outcome) from master ledger."""
    index_path = LEDGER_DIR / "MASTER_LEDGER_INDEX.json"
    if not index_path.exists():
        print(f"INFO: {index_path} not found, no V-IDs to track")
        return []
    try:
        with open(index_path) as f:
            data = json.load(f)
        # Use open_predictions if available, else filter entries by category=prediction + no outcome
        open_preds = data.get("open_predictions", [])
        if open_preds:
            return open_preds
        # Fallback: find entries with category=prediction + status=active
        tracked = []
        for e in data.get("entries", []):
            if e.get("category") == "prediction" and e.get("status") in ("active", "ACTIVE", None):
                tracked.append({
                    "ticker": e.get("ticker"),
                    "catalyst_date": e.get("catalyst_date"),
                    "v_id_file": e.get("file_path"),
                    "sequence": e.get("sequence"),
                })
        return tracked
    except Exception as e:
        print(f"WARNING: failed to load ledger: {e}")
        return []

def write_postmortem(ticker, price_change_pct, quote, vid_info):
    today = datetime.now().strftime('%Y-%m-%d')
    direction = "POSITIVE" if price_change_pct > 0 else "NEGATIVE"
    path = POSTMORTEM_DIR / f"{today}_{ticker}_auto_postmortem.md"
    content = f"""# AUTO POSTMORTEM -- {ticker} {today}

**Trigger:** Price move {price_change_pct:+.2f}% exceeds {THRESHOLD_PCT}% threshold.
**Direction:** {direction}
**Detected by:** auto_postmortem_v1.py at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Quote snapshot
- Current price: ${quote.get('price', 'N/A')}
- Day change: {price_change_pct:+.2f}%
- Day low: ${quote.get('dayLow', 'N/A')}
- Day high: ${quote.get('dayHigh', 'N/A')}
- Volume: {quote.get('volume', 'N/A'):,}
- Market cap: ${(quote.get('marketCap') or 0)/1e6:.1f}M

## V-ID context
- Catalyst date: {vid_info.get('catalyst_date', 'N/A')}
- V-ID file: {vid_info.get('v_id_file', 'N/A')}
- Sequence: {vid_info.get('sequence', 'N/A')}

## Next-step actions (manual)
1. Verify the price move was catalyst-driven (FDA decision, 8-K, news) vs market/sector noise
2. If catalyst-driven: update prediction outcome in MASTER_LEDGER + master log
3. If sector noise: leave V-ID active, document the move
4. Re-check Cardinal Rule exit if position held

## Sources
- FMP quote pulled at {datetime.now().strftime('%H:%M:%S')}

## Auto-generated. Verify before action.
"""
    with open(path, 'w') as f:
        f.write(content)
    return path

def main():
    print(f"AUTO POSTMORTEM v1.0 -- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if not FMP_API_KEY:
        print("WARNING: FMP_API_KEY missing, cannot fetch quotes")
        return

    vids = load_tracked_vids()
    print(f"Tracked V-IDs: {len(vids)}")
    if not vids:
        return

    fired_count = 0
    for v in vids:
        ticker = v.get('ticker')
        if not ticker:
            continue
        quote = fmp_quote(ticker)
        if not quote:
            continue
        change_pct = float(quote.get('changesPercentage', 0) or 0)
        if abs(change_pct) >= THRESHOLD_PCT:
            path = write_postmortem(ticker, change_pct, quote, v)
            print(f"FIRED: {ticker} {change_pct:+.2f}% -- postmortem at {path.name}")
            fired_count += 1

    print(f"\nCompleted. {fired_count} fired catalysts detected (threshold {THRESHOLD_PCT}%).")

if __name__ == "__main__":
    main()
