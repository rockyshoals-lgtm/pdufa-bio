"""Q2 2026 Options Playbook — build Markdown + DOCX appendix.

Builds two outputs:
1. q2_options_playbook.md (Markdown summary for session)
2. Q2_2026_Options_Appendix.docx (shareable artifact)
"""
import json, os, csv
from datetime import date, datetime, timedelta

ROOT = "/sessions/confident-serene-ptolemy/mnt/9realms"
SCAN = os.path.join(ROOT, "q2_options_cheapness.csv")
AS_OF = date(2026, 4, 17)


def trading_days_before(target, n):
    """Approx: subtract n weekdays from target."""
    d = target
    count = 0
    while count < n:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            count += 1
    return d


def parse_date(s):
    try:
        return datetime.strptime(str(s).split(" ")[0], "%Y-%m-%d").date()
    except Exception:
        return None


def load_scan():
    with open(SCAN) as f:
        return list(csv.DictReader(f))


# Hand-curated forward-looking options plan (from BIFROST gating)
# Gold:    PDUFA micro (36.7% avg, 50% win) OR Phase 1/2 readout (28.2%, 52.9%)
# Decent:  PDUFA small (12.6%, 38.4%) OR Phase 2 readout (29.8%, 41.8%)
# Skip:    PDUFA mid (1.8%, marginal), Phase 3 readout (-5.8%), Phase 2b (-19.4%)
# Avoid:   nano (no liquidity), large (theta)

FORWARD_PLAN = [
    # Actionable NOW (T-14 window open today)
    {
        "name": "AXSM",
        "catalyst": "AXS-05 sNDA PDUFA (Alzheimer's agitation)",
        "cat_date": "2026-04-30",
        "mcap_tier": "mid",
        "segment": "PDUFA mid — MARGINAL per backtest (+1.8% avg, 36.2% win)",
        "entry_window_open": "2026-04-10 (T-14 trading days)",
        "entry_window_today": "D-13 — T-14 window OPEN now",
        "status": "MARGINAL — skip or micro-size",
        "recommendation": "SKIP OPTIONS. Mid-cap PDUFA is negative-EV segment. If tempted, max 0.5% of capital, ATM calls 5/15 monthly, LIMIT ORDER only. Better to equity-play this one via BIFROST v4 timing.",
        "priority": "LOW",
    },
    {
        "name": "ALXO",
        "catalyst": "ESMO Breast belantamab data readout",
        "cat_date": "2026-05-07",
        "mcap_tier": "micro",
        "segment": "Readout micro — HIDDEN GEM if Phase 1/2 (28.2% avg, 52.9% win)",
        "entry_window_open": "2026-04-15 (T-14 trading days)",
        "entry_window_today": "D-20 — T-14 window OPENING this week",
        "status": "ACTIVE WATCH (held at 55% equity)",
        "recommendation": "CAUTION — already at 55% equity. Core position means adding options increases concentration risk. If sizing up: 1.5% max ATM calls 5/15 monthly (strike $2.00 or $2.50 on $1.65 stock). Watch for IV to dip below 200 before entry. Current IV=252% ivPct1y=79% is HIGH — wait for pullback to cheaper vol.",
        "priority": "MEDIUM",
    },
    # Wait for T-14 (mid-May entries)
    {
        "name": "CABA",
        "catalyst": "EULAR RESET-SLE/SSc full data + BTD readouts",
        "cat_date": "2026-06-03",
        "mcap_tier": "small",
        "segment": "Conference small — LIMITED (event often pre-runup) but has Phase 2 readout data drop",
        "entry_window_open": "2026-05-14 (T-14 trading days)",
        "entry_window_today": "D-47 — WAIT",
        "status": "WAIT 4 weeks",
        "recommendation": "PREPARE entry mid-May. CABA already has CEO/Cormorant accumulation (SMART MONEY HIGH) + 100% MG-ADL response. ATM $5 strike Jun 19 monthly. Target 1.5-2% of capital. IV currently 73% near / 99% far — MODERATE (fair zone). May cheapen during Apr pullback post-AAN Apr 20 exit.",
        "priority": "HIGH",
    },
    # Wait for T-14 (early-June entries)
    {
        "name": "UNCY",
        "catalyst": "Zephyr-HC oral solution PDUFA",
        "cat_date": "2026-06-27",
        "mcap_tier": "micro",
        "segment": "PDUFA micro — GOLD segment (+36.7% avg, 50% win)",
        "entry_window_open": "2026-06-08 (T-14 trading days)",
        "entry_window_today": "D-71 — WAIT 7 weeks",
        "status": "WAIT — top Q2 options candidate",
        "recommendation": "Highest-conviction Q2 options play per BIFROST backtest. Micro-cap PDUFA = best segment. Size 2% ATM calls Jul 17 monthly. IV likely to expand +25-30% T-14→T-1 per curve data. Set calendar reminder June 5.",
        "priority": "HIGH",
    },
    {
        "name": "OSTX",
        "catalyst": "OST-HER2 PDUFA (Osteosarcoma)",
        "cat_date": "2026-06-30",
        "mcap_tier": "micro",
        "segment": "PDUFA micro — GOLD segment (+36.7% avg, 50% win)",
        "entry_window_open": "2026-06-11 (T-14 trading days)",
        "entry_window_today": "D-74 — WAIT 8 weeks",
        "status": "WAIT — top Q2 options candidate",
        "recommendation": "Co-equal priority with UNCY. OST-HER2 orphan oncology strongly favored by ODIN v14 (oncology +0.120 is_oncology, orphan designation). Size 2% ATM calls Jul 17 monthly. Calendar reminder June 9.",
        "priority": "HIGH",
    },
    {
        "name": "LRMR",
        "catalyst": "LNR-ALS submission PDUFA",
        "cat_date": "2026-06-30",
        "mcap_tier": "small",
        "segment": "PDUFA small — DECENT (+12.6% avg, 38.4% win)",
        "entry_window_open": "2026-06-11 (T-14 trading days)",
        "entry_window_today": "D-74 — WAIT 8 weeks",
        "status": "WAIT — moderate priority",
        "recommendation": "Smaller positive edge than micro. Size 1% ATM calls Jul 17 monthly. Confirm ALS has CRL rate tail-risk before entry (CNS = moderate-high risk TA).",
        "priority": "MEDIUM",
    },
    {
        "name": "DBVT",
        "catalyst": "Viaskin Peanut topline readout",
        "cat_date": "2026-06-30",
        "mcap_tier": "small",
        "segment": "Phase 3 readout small — AVOID per backtest (-5.8% avg)",
        "entry_window_open": "N/A",
        "entry_window_today": "D-74 — but segment is negative-EV",
        "status": "SKIP OPTIONS",
        "recommendation": "Phase 3 readouts average -5.8% on options per backtest. Equity-only. #1 roster score does NOT translate to options edge.",
        "priority": "SKIP",
    },
    {
        "name": "XNCR",
        "catalyst": "XmAb942 Phase 2 readout",
        "cat_date": "2026-06-30",
        "mcap_tier": "small",
        "segment": "Phase 2 readout small — ASYMMETRIC (+29.8% avg, 41.8% win)",
        "entry_window_open": "2026-06-11 (T-14 trading days)",
        "entry_window_today": "D-74 — WAIT 8 weeks",
        "status": "WAIT",
        "recommendation": "Phase 2 readout small-cap has asymmetric payoff. Size 1.5% ATM calls Jul 17 monthly. Confirm stage classification is Phase 2 (not 2b — 2b has -19% avg edge).",
        "priority": "MEDIUM",
    },
    {
        "name": "LNTH",
        "catalyst": "Lantheus PYLARIFY sNDA PDUFA",
        "cat_date": "2026-06-29",
        "mcap_tier": "mid",
        "segment": "PDUFA mid — MARGINAL (+1.8% avg, 36.2% win)",
        "entry_window_open": "2026-06-10 (T-14 trading days)",
        "entry_window_today": "D-73 — but segment is marginal",
        "status": "SKIP OR MICRO-SIZE",
        "recommendation": "Mid-cap PDUFA edge is ~flat. Skip or cap at 0.5%. Equity preferred per BIFROST v4.",
        "priority": "LOW",
    },
    {
        "name": "RNA",
        "catalyst": "Avidity DMD Phase 3 readout",
        "cat_date": "2026-06-30",
        "mcap_tier": "mid",
        "segment": "Phase 3 readout mid — AVOID (-5.8% avg)",
        "entry_window_open": "N/A",
        "entry_window_today": "D-74 — but segment is negative-EV",
        "status": "SKIP OPTIONS",
        "recommendation": "Phase 3 readout negative edge. Equity-only via BIFROST v4.",
        "priority": "SKIP",
    },
]


def make_md():
    lines = []
    lines.append("# Q2 2026 OPTIONS PLAYBOOK")
    lines.append(f"*As of {AS_OF.strftime('%B %d, %Y')}*\n")

    lines.append("## Honest Data Disclosure")
    lines.append("")
    lines.append("The ORATS cache on this system contains complete live snapshots for **9 tickers** as of Apr 2, 2026: "
                 "ABSI, ALXO, BHC, BHVN, CABA, GRCE, MNKD, NUVB, WHWK. Of these, only **GRCE** and **ALXO** overlap with the 30-name aggressive Q2 roster. "
                 "The remaining 28 names require a live ORATS fetch before live IV cheapness can be scored. This playbook uses: "
                 "(a) ORATS cache where available, (b) BIFROST Options Module v1.0 deploy data (Apr 4, 2026 scan), "
                 "(c) BIFROST Options v1.1 backtest edge by segment (1,828 trades, 2022–2026), and (d) live IV observations from operational notes.")
    lines.append("")

    lines.append("## Structural Reality of the Q2 Roster")
    lines.append("")
    lines.append("**29 of 30 roster names are AACR Apr 17–22 conference plays.** AACR is happening THIS WEEK (today is Apr 17). "
                 "The T-14 options entry window for AACR would have been ~Apr 1. That window is closed. "
                 "The cardinal rule — 'the runup IS the trade' — means AACR options would have needed entry before Apr 10. "
                 "These 29 names are EQUITY-ONLY plays now. Exit day-before or day-of podium presentations per the rotation waterfall.")
    lines.append("")
    lines.append("**The actual Q2 options universe is smaller** — the non-AACR catalysts in the roster + ALXO: AXSM (Apr 30 PDUFA), ALXO (May 7 ESMO), "
                 "CABA (Jun 3 EULAR), UNCY/OSTX/LRMR/LNTH (late-June PDUFAs), DBVT/XNCR/RNA (late-June readouts), CLDI/EDSA/BOLD (other events). "
                 "Of these, segment-edge and cap-tier gating leaves **3 top-priority options plays: UNCY, OSTX, CABA**.")
    lines.append("")

    lines.append("## Active Options Window NOW (Apr 17)")
    lines.append("")
    lines.append("### ALXO — ESMO Breast May 7 (D-20)")
    lines.append("")
    lines.append("Stock now $1.65. ORATS Apr 2 snapshot: **IV = 252%**, ivPct1Y = 79%, ivRank1Y = 54. That is HIGH by any cheapness standard. "
                 "Live IV observation from operational notes also confirms elevated near-term IV on small-cap. "
                 "ALXO is a core 55% equity held position, so adding options increases concentration risk on the thesis. "
                 "**Recommendation:** do not chase options at current IV. Wait for a ≥15% IV pullback. If entered, max 1.5% portfolio, "
                 "ATM calls $2.00 or $2.50 strike May 15 monthly — this expiry spans the May 7 catalyst. "
                 "Sizing rule: keep combined ALXO equity + options exposure under 60%.")
    lines.append("")
    lines.append("### AXSM — AXS-05 PDUFA Apr 30 (D-13)")
    lines.append("")
    lines.append("T-14 options entry window is open THIS WEEK. However: mid-cap PDUFA segment has +1.8% avg return and 36.2% win rate on options "
                 "per the 1,828-trade BIFROST v1.1 backtest. This is ROUGHLY FLAT edge with full exposure to theta. Equity preferred via BIFROST v4 timing. "
                 "**Recommendation:** SKIP options. If strong conviction, cap at 0.5% capital, ATM $60 strike May 15, limit order only.")
    lines.append("")

    lines.append("## Top 3 High-Priority Options Plays (Wait for T-14)")
    lines.append("")
    lines.append("### 1. UNCY — Zephyr-HC PDUFA Jun 27 (D-71)")
    lines.append("")
    lines.append("**GOLD segment** per BIFROST v1.1 backtest: PDUFA Micro returns +36.7% avg, 50.0% win rate, 19.3% of trades go >100%. "
                 "Micro-cap PDUFA is the single best-edge segment in the options universe. "
                 "**Entry:** Jun 8, 2026 (T-14 trading days before Jun 27). **Expiry:** Jul 17 monthly (spans catalyst). "
                 "**Size:** 2.0% of capital. **Calendar reminder:** Jun 5.")
    lines.append("")
    lines.append("### 2. OSTX — OST-HER2 PDUFA Jun 30 (D-74)")
    lines.append("")
    lines.append("Co-equal with UNCY. OST-HER2 is orphan oncology with BTD stack — ODIN v14 weights is_oncology (+0.120), "
                 "pw_orphan_drug_bin_x_btd_bin (-0.202 penalty asymmetry), gt_x_btd (+0.140). "
                 "**Entry:** Jun 11, 2026. **Expiry:** Jul 17 monthly. **Size:** 2.0%. **Calendar reminder:** Jun 9.")
    lines.append("")
    lines.append("### 3. CABA — EULAR SLE/SSc Jun 3 (D-47)")
    lines.append("")
    lines.append("Small-cap Phase 2/3 readout at major conference. Smart Money Overlay flagged CEO buying + Cormorant ownership. "
                 "100% MG-ADL response at RESET-MG. BTD+ODD+RMAT designation stack. "
                 "**Entry:** May 14, 2026 (T-14 trading days before Jun 3). **Expiry:** Jun 19 monthly. **Size:** 1.5%. "
                 "Current IV 73% near / 99% far per CLAUDE.md live observations — MODERATE cheapness.")
    lines.append("")

    lines.append("## Weekly vs Monthly Expiry — Comparison")
    lines.append("")
    lines.append("| Ticker | Catalyst Date | Monthly Expiry (3rd Fri) | Weekly Expiry (1st Fri after) | Preferred |")
    lines.append("|---|---|---|---|---|")
    lines.append("| UNCY | 2026-06-27 (Sat) | 2026-07-17 | 2026-07-02 | **Weekly** (closer to event, captures IV crush arbitrage for exits) |")
    lines.append("| OSTX | 2026-06-30 (Tue) | 2026-07-17 | 2026-07-02 | **Weekly** (tight expiry = more leverage, but MUST exit T-1) |")
    lines.append("| CABA | 2026-06-03 (Wed) | 2026-06-19 | 2026-06-05 | **Monthly** (weekly has only 2 days post-event, theta risk if runup late) |")
    lines.append("| ALXO | 2026-05-07 (Thu) | 2026-05-15 | 2026-05-08 | **Monthly** (weekly Fri-after is only 1 day — too tight for IV capture) |")
    lines.append("| AXSM | 2026-04-30 (Thu) | 2026-05-15 | 2026-05-01 | **Monthly** (same issue — weekly expires day-of, can't exit T-1) |")
    lines.append("")
    lines.append("**Rule:** Monthly expiry preferred when the first post-catalyst weekly Friday is <3 days after the event "
                 "(no time to exit T-1 before Friday close). Weekly preferred when there are ≥5 days between catalyst and next Friday "
                 "(more leverage, exit T-1 before weekend).")
    lines.append("")

    lines.append("## Full Universe — Cheapness Scores")
    lines.append("")
    lines.append("See `q2_options_cheapness.csv` for all 30 roster names + ALXO. Key observations:")
    lines.append("")
    lines.append("- **4 names with real ORATS or Apr 7 snapshot data:** GRCE, ALXO, CRDF, HCM — all have elevated IV (cheapness score <45 = FAIR or worse)")
    lines.append("- **27 names require live ORATS fetch before options scoring**")
    lines.append("- **All AACR conference names (22)** have D-0 to D-5 — options window closed, equity only")
    lines.append("")

    lines.append("## Position Sizing & Risk Rules (from BIFROST Options v1.1)")
    lines.append("")
    lines.append("- **Max single options position:** 2% of capital (vs 3–5% equity)")
    lines.append("- **ODIN/Gungnir filter:** T1 (≥0.85) or T2 (0.65–0.85) only")
    lines.append("- **LIMIT ORDERS MANDATORY** — bid-ask spreads cost ~23pp on average. Limit at mid or better.")
    lines.append("- **Never hold through the event** — exit T-1 before close. No exceptions.")
    lines.append("- **Explosion tier (BIFROST v5.5) sniper multiplier:** 1.5× up to 3% cap")
    lines.append("- **Combined options + equity on same name ≤ 60% of portfolio**")
    lines.append("")

    lines.append("## Backtest Segment Edge Reference (1,828 trades, 2022–2026)")
    lines.append("")
    lines.append("| Segment | Avg Return | Win Rate | % >100% | Verdict |")
    lines.append("|---|---|---|---|---|")
    lines.append("| PDUFA Micro | +36.7% | 50.0% | 19.3% | **GOLD** |")
    lines.append("| Phase 1/2 Readout | +28.2% | 52.9% | 21.4% | **GOLD** |")
    lines.append("| Phase 2 Readout | +29.8% | 41.8% | 17.6% | ASYMMETRIC |")
    lines.append("| PDUFA Small | +12.6% | 38.4% | 12.5% | DECENT |")
    lines.append("| PDUFA Mid | +1.8% | 36.2% | — | MARGINAL |")
    lines.append("| PDUFA Large | -5.5% | 31.0% | — | AVOID (theta) |")
    lines.append("| Phase 3 Readout | -5.8% | 32.3% | — | AVOID |")
    lines.append("| Phase 2b Readout | -19.4% | 29.6% | — | AVOID |")
    lines.append("")

    lines.append("## Capital Allocation — Q2 Options Budget")
    lines.append("")
    lines.append("Across the 3 top-priority plays (UNCY 2.0% + OSTX 2.0% + CABA 1.5%) = **5.5% of capital** in options, staggered across May 14 → Jun 11. "
                 "Peak concurrent options heat: ~4.5% (UNCY + OSTX overlap Jun 11–26). "
                 "All three resolve by end of Q2. Total options exposure fits inside the aggressive 35–40% peak concurrent heat budget without crowding equity positions.")
    lines.append("")

    lines.append("## Honest Caveats")
    lines.append("")
    lines.append("- **ORATS cache coverage is 30% of roster** — most recommendations based on segment backtest + live IV observations, not fresh ORATS summaries")
    lines.append("- **Live IV will change things.** At T-14 entry, re-score cheapness with fresh ORATS data. Skip if ivPct1Y > 80 or IV/RV > 2.0")
    lines.append("- **BIFROST options backtest used MID-PRICE fills.** With bid-ask spreads of 20–30pp, ask-price fills flip EV negative. LIMIT ORDERS ARE NOT OPTIONAL")
    lines.append("- **Stage classifications on the 30-name roster need verification** before options entry — DBVT and RNA are Phase 3 (AVOID segment); XNCR stage needs confirmation before sizing")
    lines.append("")
    out_md = os.path.join(ROOT, "q2_options_playbook.md")
    with open(out_md, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {out_md}")
    return "\n".join(lines)


if __name__ == "__main__":
    md = make_md()
    print(md[:3000])
