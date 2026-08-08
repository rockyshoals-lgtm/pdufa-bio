from datetime import date
from odin_insider_fmp import FMPInsiderTradingClient, parse_fmp_insider_trades, classify_insider_activity

client = FMPInsiderTradingClient()

raw = client.fetch_form4_insider_trades("AQST", limit=100, page=0)
trades = parse_fmp_insider_trades(raw)

features = classify_insider_activity(
    trades,
    as_of_date=date(2026, 1, 31),  # IMPORTANT: pass your ODIN data-cut date (e.g., PDUFA-1)
    lookback_days=180,
    # Optional “post data buy” mode:
    # post_data_date=date(2026, 1, 10),
    # post_data_window_days=30,
)

print(features)
print("cluster_sell_detected:", features.cluster_sell_detected)
