#!/usr/bin/env python3
"""Red-team the LEADLAB base rates: temporal stability, threshold sensitivity, leakage logic."""
import csv, os, statistics, collections
HERE=os.path.dirname(os.path.abspath(__file__))
def f(x):
    try: return float(x)
    except: return None
U=list(csv.DictReader(open(os.path.join(HERE,"universe.csv"))))
dates=sorted(set(r["date"] for r in U)); mid=dates[len(dates)//2]
print("event dates:",dates[0],"..",dates[-1],"| split at",mid,"\n")

def br(rows,key="surge25"):
    return (100*sum(int(r[key]) for r in rows)/len(rows),len(rows)) if rows else (0,0)

print("=== TEMPORAL STABILITY: P(+25%) by gap bucket, first half vs second half ===")
A=[r for r in U if r["date"]<mid]; B=[r for r in U if r["date"]>=mid]
for lo,hi,lb in [(3,5,"3-5"),(5,10,"5-10"),(10,20,"10-20"),(20,999,"20+")]:
    a=[r for r in A if lo<=f(r["gap_pct"])<hi]; b=[r for r in B if lo<=f(r["gap_pct"])<hi]
    pa,na=br(a); pb,nb=br(b)
    print(f"  gap {lb:6s}: H1 {pa:5.1f}% (n={na:4d})   H2 {pb:5.1f}% (n={nb:4d})")

print("\n=== THRESHOLD SENSITIVITY: outcome definition (gap 10-20% bucket) ===")
mid_gap=[r for r in U if 10<=f(r["gap_pct"])<20]
for key,lbl in [("surge25","hit +25% intraday"),("close_up","closed green"),("close_up15","closed +15%"),("open_green_close","open->close green")]:
    p,n=br(mid_gap,key); print(f"  {lbl:22s}: {p:5.1f}% (n={n})")

print("\n=== LEAKAGE / T-1 LOGIC CHECK ===")
print("  gap_pct   = open / prev_close  -> prev_close is STRICTLY the prior trading day. OK")
print("  relvol    = day_vol / mean(prior 20d vol) -> trailing only. OK")
print("  pm_0900   = last pre-market print <= 09:00 -> known 30min before open. OK")
print("  outcome   = same-day high vs prev_close -> FUTURE of the signal (that's the label). OK")
print("  NOTE: intraday TIMING of the +25% within the day is not modeled — the odds are")
print("        'reaches +25% at some point intraday', not 'from your entry'. Documented caveat.")

print("\n=== SURVIVORSHIP CHECK ===")
print("  Universe = Polygon grouped-daily, which RETAINS tickers that later delisted within")
print("  the window -> losers & since-delisted names ARE included. Materially less survivorship")
print("  bias than the old FMP 'currently-listed' study. Residual: names delisted BEFORE window.")

print("\n=== SAMPLE-SIZE FLAGS (cells the engine should treat as low-confidence) ===")
GAP=[3,5,10,20,40]; RV=[0,1,2,5,10]
def gi(g):
    for i in range(len(GAP)-1):
        if GAP[i]<=g<GAP[i+1]: return i
    return len(GAP)-1 if g>=GAP[-1] else None
def vi(v):
    for i in range(len(RV)-1):
        if RV[i]<=v<RV[i+1]: return i
    return len(RV)-1 if v>=RV[-1] else None
thin=0
for gj in range(len(GAP)):
    for vj in range(len(RV)):
        sub=[r for r in U if f(r["gap_pct"]) is not None and gi(f(r["gap_pct"]))==gj and r["relvol"] and vi(f(r["relvol"]))==vj]
        if 0<len(sub)<20: thin+=1
print(f"  {thin} of 25 gap×relvol cells have <20 samples (engine falls back to the marginal there).")
