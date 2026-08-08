import csv
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "readout_forward_enriched.csv")
if not os.path.exists(p):
    p = os.path.join(HERE, "readout_forward.csv")
rows = [x for x in csv.DictReader(open(p, encoding="utf-8-sig")) if x.get("window", "").strip()]
rows.sort(key=lambda x: x.get("filed", ""), reverse=True)

print(f"source: {os.path.basename(p)}   (windowed catalysts, newest first)\n")
print(f"{'tkr':<6}{'window':<22}{'signal':<9}{'C/P':>6}{'unus_x':>7}"
      f"{'dark$':>9}{'lean':>9}{'gex':>6}")
print("-" * 74)
for x in rows:
    dp = x.get("sm_dp_prem", "") or ""
    dpm = f"{int(dp)/1e6:.1f}M" if dp.isdigit() and int(dp) > 0 else "-"
    print(f"{x['ticker']:<6}{x['window'][:20]:<22}{x.get('sm_signal',''):<9}"
          f"{str(x.get('sm_cp_ratio','')):>6}{str(x.get('sm_unusual_x','')):>7}"
          f"{dpm:>9}{x.get('sm_dp_lean',''):>9}{x.get('sm_gex_sign',''):>6}")

bull = [x for x in rows if x.get("sm_signal") == "BULLISH"]
print(f"\nBULLISH options/dark-pool lean into a dated readout ({len(bull)}):")
for x in bull:
    print(f"  {x['ticker']:<6} {x['window'][:20]:<22} "
          f"C/P {x.get('sm_cp_ratio','')}  unusual {x.get('sm_unusual_x','')}x  "
          f"dark-pool {x.get('sm_dp_lean','')}")
print("\nREAD, not signal — options flow mixes smart money, dealer hedging, and retail. "
      "Not investment advice.")
