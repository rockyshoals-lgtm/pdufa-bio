#!/usr/bin/env python3
"""
FINAL $100K APRIL TRADING PLAN — Step by Step
"""
from datetime import datetime

today = datetime(2026, 3, 29)  # Sunday — markets open Monday Mar 30

print("=" * 100)
print("FINAL APRIL 2026 TRADING PLAN — $100,000")
print("Step-by-step: What to buy, when, how much, and when to exit")
print("=" * 100)

trades = [
    {
        "priority": 1,
        "ticker": "MGNX",
        "drug": "ZYNYZ (retifanlimab) sBLA — NSCLC expansion",
        "pdufa": "Apr 30",
        "odin": "0.78 (T2)",
        "mcap": "$186M (micro)",
        "buy_date": "Mon Mar 30",
        "buy_note": "Already deep in BIFROST window (entered Jan 30). Buy at market open.",
        "exit_date": "Thu Apr 23",
        "exit_note": "BIFROST T-7 exit. 24 days hold from here.",
        "alloc_pct": 20,
        "alloc_usd": 20000,
        "signal": "STRONG_BUY — T2 micro. Best cell in entire BIFROST matrix.",
        "stats": "73% hit rate, +22.0% mean return, Sharpe 1.09, N=30",
        "thesis": "ZYNYZ already approved for Merkel cell carcinoma. This sBLA just expands label to NSCLC. "
                  "Incyte (INCY) is large-cap partner handling commercialization. MGNX is micro-cap so moves are amplified. "
                  "T2 micro historically the single best risk-reward cell: 73% of the time you win, average gain +22%.",
        "risk": "Micro-cap volatility. MGNX also has a partial clinical hold on lorigerlimab (different drug). "
                "FDA could push back on NSCLC indication specifically."
    },
    {
        "priority": 2,
        "ticker": "TVTX",
        "drug": "FILSPARI (sparsentan) sNDA — FSGS",
        "pdufa": "Apr 13",
        "odin": "0.91 (T1)",
        "mcap": "$2.5B (mid)",
        "buy_date": "Mon Mar 30",
        "buy_note": "In BIFROST window (entered Mar 19). Buy at market open.",
        "exit_date": "Fri Apr 10 (latest: Sun Apr 12)",
        "exit_note": "BIFROST T-1 exit. ~13 days hold. Exit before weekend ahead of Apr 13 PDUFA.",
        "alloc_pct": 20,
        "alloc_usd": 20000,
        "signal": "STRONG_BUY — T1 mid. Highest ODIN conviction in April.",
        "stats": "65% hit rate, +5.7% mean return, Sharpe 1.02, N=98",
        "thesis": "FILSPARI already approved for IgA nephropathy (IgAN). FSGS is second indication via sNDA. "
                  "FDA REMOVED the advisory committee (bullish — they don't need external input). "
                  "PDUFA was extended from Jan 13 → Apr 13 after TVTX submitted additional data requested by FDA. "
                  "No approved FSGS treatments exist — huge unmet need. ODD in place.",
        "risk": "PDUFA extension suggests FDA had questions. The additional data submission could go either way. "
                "But removing AdCom after reviewing the data is a strong positive signal."
    },
    {
        "priority": 3,
        "ticker": "AXSM",
        "drug": "AXS-05 (dextromethorphan/bupropion) sNDA — Alzheimer's agitation",
        "pdufa": "Apr 30",
        "odin": "0.84 (T2)",
        "mcap": "$8.0B (mid)",
        "buy_date": "Mon Mar 30",
        "buy_note": "In BIFROST window (entered Mar 1). Buy at market open.",
        "exit_date": "Mon Apr 27",
        "exit_note": "BIFROST T-3 exit. ~28 days hold.",
        "alloc_pct": 20,
        "alloc_usd": 20000,
        "signal": "STRONG_BUY — T2 mid. BTD + Priority Review. High conviction.",
        "stats": "59% hit rate, +9.7% mean return, Sharpe 0.76, N=71",
        "thesis": "AXS-05 is already approved as Auvelity for MDD — this is sNDA for AD agitation. "
                  "Breakthrough Therapy Designation + Priority Review = FDA signaling positive engagement. "
                  "4 randomized Phase 3 trials completed. First-in-class for AD agitation (76% of AD patients affected). "
                  "Axsome is a proven sponsor with Auvelity already on market.",
        "risk": "AD agitation is notoriously hard to get right. CNS TA has moderate CRL rates. "
                "Competition from Rexulti (already approved for AD agitation) limits the unmet-need narrative."
    },
    {
        "priority": 4,
        "ticker": "GRCE",
        "drug": "GTx-104 (IV nimodipine) NDA — Subarachnoid hemorrhage (aSAH)",
        "pdufa": "Apr 23",
        "odin": "0.08 (T4) — BUT 505(b)(2) OVERRIDE: effectively ~T2",
        "mcap": "$63M (micro)",
        "buy_date": "Mon Mar 30",
        "buy_note": "Entering BIFROST window TODAY (T-25 = Mar 29). Buy at market open.",
        "exit_date": "Wed Apr 22",
        "exit_note": "BIFROST T-1 exit. ~23 days hold.",
        "alloc_pct": 15,
        "alloc_usd": 15000,
        "signal": "QUALITATIVE OVERRIDE — ODIN model blind spot on 505(b)(2) reformulations.",
        "stats": "T4 micro: 53% hit, +7.4% mean. BUT 505(b)(2) historical approval >90% when P3 met endpoint.",
        "thesis": "GTx-104 is an IV reformulation of oral nimodipine (already approved and standard of care for aSAH). "
                  "505(b)(2) pathway — NOT a novel drug, just a better delivery route. "
                  "Phase 3 STRIVE-ON met primary endpoint: 19% reduction in hypotension vs oral. "
                  "Secondary endpoints all positive: 29% more favorable outcomes at 90 days, fewer ICU days. "
                  "Orphan Drug Designation = 7 years exclusivity. "
                  "$63M market cap = if approved, this is a 2-4x candidate. Only analyst target is $12 (vs $4.59 current). "
                  "ODIN scores T4 because it sees 'naive sponsor + first NDA' but can't distinguish 505(b)(2) from novel NDA.",
        "risk": "Naive sponsor — Grace (formerly Acasti Pharma) has never gotten a drug approved. "
                "Only $4M raised through warrants recently — cash position may be tight. "
                "505(b)(2) still requires FDA to agree the reformulation provides meaningful clinical benefit over reference product."
    },
    {
        "priority": 5,
        "ticker": "BMY",
        "drug": "Opdivo + AVD sBLA — Classical Hodgkin Lymphoma",
        "pdufa": "Apr 8",
        "odin": "0.97 (T1)",
        "mcap": "$120B (large)",
        "buy_date": "Mon Mar 30",
        "buy_note": "URGENT — BIFROST window closes Apr 1! Only 2 trading days.",
        "exit_date": "Wed Apr 1",
        "exit_note": "BIFROST T-7 exit. 2-DAY TRADE ONLY.",
        "alloc_pct": 5,
        "alloc_usd": 5000,
        "signal": "STRONG_BUY — T1 large. Highest ODIN score (0.97) but only 2 days left in window.",
        "stats": "59% hit rate, +3.0% mean return, Sharpe 0.53, N=599 (best-validated cell)",
        "thesis": "Opdivo is already approved for multiple indications. BMY is mega pharma (97% ODIN). "
                  "BTD + Priority Review for cHL. Virtually certain approval. "
                  "But large-cap = small percentage moves. Only worth doing because window is still barely open.",
        "risk": "2-day hold may not capture enough runup to matter. Only $5K deployed = max $150 expected gain. "
                "Consider skipping and putting this $5K into GRCE or MGNX instead."
    },
    {
        "priority": 6,
        "ticker": "REPL",
        "drug": "RP1 (vusolimogene) BLA resubmission — Advanced melanoma",
        "pdufa": "Apr 10",
        "odin": "0.04 (T4)",
        "mcap": "$596M (small)",
        "buy_date": "Mon Mar 30",
        "buy_note": "In BIFROST window (entered Mar 16). Buy at market open.",
        "exit_date": "Tue Apr 7",
        "exit_note": "BIFROST T-3 exit. ~8 days hold.",
        "alloc_pct": 5,
        "alloc_usd": 5000,
        "signal": "LEAN_LONG — T4 small. Capped position. Momentum play.",
        "stats": "57% hit rate, +4.4% mean return, Sharpe 0.58, N=113",
        "thesis": "BLA resubmission (Class 2 = minor). Stock already surged +86% on resub acceptance. "
                  "BTD for melanoma. Momentum strongly positive. "
                  "T4 because naive sponsor + oncology (high CRL TA) + resubmission + naive×resub interaction all negative in ODIN.",
        "risk": "ODIN says 4% approval probability — very harsh. First BLA was rejected for a reason. "
                "Naive sponsor in competitive oncology. If you're aggressive, could skip this for more GRCE/MGNX."
    },
]

# Skip MRK — AVOID signal
# Skip BIIB — window already closed

CAPITAL = 100000
cash = CAPITAL

print()
print("┌─────────────────────────────────────────────────────────────────┐")
print("│  ALLOCATION SUMMARY                                            │")
print("├─────────┬──────────┬─────────┬────────────┬───────────────────-─┤")
print("│ TICKER  │ BUY DATE │   EXIT  │   AMOUNT   │ % OF PORTFOLIO     │")
print("├─────────┼──────────┼─────────┼────────────┼────────────────────-┤")

total = 0
for t in trades:
    total += t["alloc_usd"]
    bar = "█" * (t["alloc_pct"] // 2) + "░" * ((20 - t["alloc_pct"]) // 2)
    print(f"│ {t['ticker']:>6}  │ {t['buy_date']:>8} │ {t['exit_date'][:7]:>7} │ ${t['alloc_usd']:>8,} │ {t['alloc_pct']:>2}% {bar} │")

cash_left = CAPITAL - total
print(f"│  CASH   │     —    │    —    │ ${cash_left:>8,} │ {cash_left*100//CAPITAL:>2}% {'░' * 10}          │")
print("└─────────┴──────────┴─────────┴────────────┴────────────────────-┘")
print(f"\n  TOTAL DEPLOYED: ${total:,} ({total*100//CAPITAL}%) across 6 positions")
print(f"  CASH RESERVE:   ${cash_left:,} ({cash_left*100//CAPITAL}%) for May redeployment")

print("\n" + "=" * 100)
print("DAY-BY-DAY EXECUTION CALENDAR")
print("=" * 100)

calendar = [
    ("Mon Mar 30", "BUY DAY", [
        "Market open: Buy ALL 6 positions simultaneously",
        "  MGNX  — $20,000 (20%) — limit order near ask, micro-cap spreads can be wide",
        "  TVTX  — $20,000 (20%) — market order fine, mid-cap liquid",
        "  AXSM  — $20,000 (20%) — market order fine, mid-cap liquid",
        "  GRCE  — $15,000 (15%) — limit order near ask, VERY thin micro-cap ($63M)",
        "  BMY   — $ 5,000 ( 5%) — market order, mega-cap ultra liquid",
        "  REPL  — $ 5,000 ( 5%) — market order, small-cap OK liquidity",
        "  CASH  — $15,000 (15%) reserved",
    ]),
    ("Wed Apr 1", "EXIT BMY", [
        "Sell BMY at market open — BIFROST T-7 window closes",
        "Capital freed: ~$5,000 → add to cash reserve",
        "Cash reserve now: ~$20,000",
    ]),
    ("Tue Apr 7", "EXIT REPL", [
        "Sell REPL at market open — BIFROST T-3 window closes",
        "Capital freed: ~$5,000 → add to cash reserve",
        "Cash reserve now: ~$25,000",
    ]),
    ("Fri Apr 10", "EXIT TVTX", [
        "Sell TVTX before market close — PDUFA is Apr 13 (Monday)",
        "DO NOT hold through weekend. Cardinal Rule: never hold through decision.",
        "Capital freed: ~$20,000 → add to cash reserve",
        "Cash reserve now: ~$45,000",
        "NOTE: If stock is running hot into close, sell into strength. Don't get greedy.",
    ]),
    ("Wed Apr 22", "EXIT GRCE", [
        "Sell GRCE at market open — BIFROST T-1 exit, PDUFA Apr 23",
        "Capital freed: ~$15,000 → add to cash reserve",
        "Cash reserve now: ~$60,000",
    ]),
    ("Thu Apr 23", "EXIT MGNX", [
        "Sell MGNX at market open — BIFROST T-7 exit, PDUFA Apr 30",
        "Capital freed: ~$20,000 → add to cash reserve",
        "Cash reserve now: ~$80,000",
    ]),
    ("Mon Apr 27", "EXIT AXSM", [
        "Sell AXSM at market open — BIFROST T-3 exit, PDUFA Apr 30",
        "Capital freed: ~$20,000",
        "ALL APRIL POSITIONS CLOSED. 100% cash.",
        "Ready for May deployment.",
    ]),
]

for date, action, details in calendar:
    print(f"\n  📅 {date} — {action}")
    for d in details:
        print(f"     {d}")

print("\n" + "=" * 100)
print("DETAILED TRADE CARDS")
print("=" * 100)

for t in trades:
    print(f"\n  ╔{'═'*96}╗")
    print(f"  ║  #{t['priority']} — {t['ticker']}  |  {t['drug'][:70]:<70} ║")
    print(f"  ╠{'═'*96}╣")
    print(f"  ║  PDUFA: {t['pdufa']}  |  ODIN: {t['odin']}  |  MCap: {t['mcap']:<35}  ║")
    print(f"  ║  BUY:   {t['buy_date']}  |  EXIT: {t['exit_date']:<55}  ║")
    print(f"  ║  ALLOC: ${t['alloc_usd']:,} ({t['alloc_pct']}%)  |  Signal: {t['signal'][:50]:<50} ║")
    print(f"  ║  Stats: {t['stats']:<86} ║")
    print(f"  ╠{'═'*96}╣")
    # Wrap thesis
    thesis = t['thesis']
    while thesis:
        line = thesis[:92]
        thesis = thesis[92:]
        print(f"  ║  {line:<94} ║")
    print(f"  ╠{'═'*96}╣")
    risk = t['risk']
    while risk:
        line = risk[:92]
        risk = risk[92:]
        print(f"  ║  ⚠ {line:<92} ║")
    print(f"  ╚{'═'*96}╝")

print("\n" + "=" * 100)
print("MAY/JUNE COMPOUNDING TARGETS (PREVIEW)")
print("=" * 100)

may_june = [
    ("May 10", "ARGX", "VYVGART — large-cap ($43B), likely T1-T2", "Redeploy freed capital"),
    ("May 18", "AZN",  "ENHERTU sBLA — mega-cap, BTD candidate", "Small allocation (large-cap small moves)"),
    ("May 24", "BIIB", "LEQEMBI home injection — Priority Review", "T1 large likely"),
    ("May 29", "MNKD", "Afrezza sNDA — small-cap ($700M)", "Score with ODIN closer to date"),
    ("May 31", "CING", "CTx-1301 — micro-cap ($74M)", "Another micro potential mover"),
    ("Jun 5",  "ARVN/PFE", "Vepdegestrant — small+large dual play", "Score with ODIN/Gungnir"),
    ("Jun 20", "ACHV", "Cytisinicline — micro-cap ($141M)", "Smoking cessation, novel"),
    ("Jun 30", "IONS", "Olezarsen — BTD + Priority Review, large-cap", "High conviction target"),
    ("Jun 30", "VRDN", "Veligrotug — BTD, mid-cap ($2.8B)", "Strong signal combo"),
]

for date, ticker, desc, action in may_june:
    print(f"  {date:>6}  {ticker:>8}  {desc:<50}  {action}")

print(f"\n  → Score all May events with ODIN v9 + BIFROST v2 by April 20")
print(f"  → Deploy freed April capital ($100K + gains) into May positions")
print(f"  → Repeat: compound through June, then begin $10K/month drawdown July 1")

print("\n" + "=" * 100)
print("DISCLAIMER")
print("=" * 100)
print("""
  This analysis is for informational and educational purposes only.
  It is NOT investment advice. All trading involves risk of loss.
  Past performance (BIFROST backtests, ODIN scores) does not guarantee future results.
  
  The CARDINAL RULE applies to every trade: EXIT BEFORE THE PDUFA DATE.
  The runup IS the trade. Never hold through the FDA decision.
  
  ODIN v9 scores represent model-estimated approval probabilities, not certainties.
  BIFROST v2 position sizes are based on historical patterns that may not repeat.
  The GRCE qualitative override is a judgment call — the ODIN model score (T4) disagrees.
""")
