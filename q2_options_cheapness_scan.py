"""Q2 2026 Options Cheapness Scan — 30-name aggressive roster + ALXO.

Methodology:
- 4-component ORATS cheapness score (0-100) from ORATS v1.0:
    * IV Percentile 1Y (35 pts): <30 cheap, 30-60 fair, >60 expensive
    * IV/RV Ratio       (25 pts): <1.2 very cheap, 1.2-1.5 fair, >1.5 expensive
    * Timing Sweet Spot (25 pts): 14-35 days to catalyst = optimal (T-14 entry)
    * Term Structure    (15 pts): flat (<1.1) = cheap, steep (>1.3) = priced in
- BIFROST Options Module v1.1 gating (backtest 1,828 trades):
    * PDUFA Micro:          +36.7% avg, 50.0% win   — BEST
    * Phase 1/2 Readout:    +28.2% avg, 52.9% win   — BEST readout
    * Phase 2 Readout:      +29.8% avg, 41.8% win   — asymmetric
    * PDUFA Small:          +12.6% avg, 38.4% win   — decent
    * PDUFA Mid:            +1.8% avg, 36.2% win    — marginal
    * PDUFA Large:          -5.5% avg, 31.0% win    — AVOID (theta)
    * Phase 3 Readout:      -5.8% avg, 32.3% win    — AVOID
    * Phase 2b Readout:    -19.4% avg, 29.6% win    — AVOID
- Sizing:  T1 = 2% max, T2 = 1.5% max, explosion SNIPER multiplier up to 1.5x (cap 3%)
"""
import os, json, math, csv
from datetime import date, datetime

ROOT = "/sessions/confident-serene-ptolemy/mnt/9realms"
TIERED = os.path.join(ROOT, "q2_tiered_portfolio.csv")
CACHE_DIR = os.path.join(ROOT, "orats_cache")
PORTFOLIO_APR7 = os.path.join(ROOT, "portfolio_options_apr7.json")
BIFROST_DEPLOY = os.path.join(ROOT, "bifrost_options_v1_deploy.json")

AS_OF = date(2026, 4, 17)

# ---- Live IV observations from CLAUDE.md (April 2026)
LIVE_IV = {
    "GRCE": {"near_iv": 116.0, "far_iv": 371.0, "note": "Apr17 IV=116% vs May15 IV=371% — May15 spans PDUFA"},
    "BHVN": {"near_iv": 80.0,  "far_iv": 113.0, "note": "Near vs far IV"},
    "CABA": {"near_iv": 73.0,  "far_iv": 99.0,  "note": "Near vs far IV"},
    "ALXO": {"near_iv": 252.0, "far_iv": None,  "note": "Apr 2 snapshot: IV=252% ivPct1y=79 (very elevated)"},
    "ABSI": {"near_iv": 104.7, "far_iv": None,  "note": "BIFROST deploy: IV=105%, liq=64"},
    "MNKD": {"near_iv": 109.0, "far_iv": None,  "note": "BIFROST deploy: IV=109%, liq=76"},
    "HCM":  {"near_iv": 62.5,  "far_iv": None,  "note": "BIFROST deploy: IV=63%, liq=29 (ILLIQUID)"},
}

# ---- BIFROST v1.1 backtest segment edge by catalyst_type × mcap_tier
SEGMENT_EDGE = {
    # (catalyst_type, mcap_tier) -> (avg_return_pct, win_rate, edge_label)
    ("PDUFA",    "nano"):   (None, None, "NO DATA — equity only, no options chain"),
    ("PDUFA",    "micro"):  (36.7, 50.0, "GOLD — best segment"),
    ("PDUFA",    "small"):  (12.6, 38.4, "DECENT — second-tier"),
    ("PDUFA",    "mid"):    (1.8,  36.2, "MARGINAL"),
    ("PDUFA",    "large"):  (-5.5, 31.0, "AVOID — theta destroys"),
    ("Readout",  "nano"):   (28.2, 52.9, "HIDDEN GEM — if Phase 1/2"),
    ("Readout",  "micro"):  (28.2, 52.9, "HIDDEN GEM — if Phase 1/2"),
    ("Readout",  "small"):  (29.8, 41.8, "ASYMMETRIC — if Phase 2"),
    ("Readout",  "mid"):    (-5.8, 32.3, "AVOID — Phase 3"),
    ("Readout",  "large"):  (-5.8, 32.3, "AVOID — Phase 3"),
    ("Conference","nano"):  (None, None, "NO options — nano liquidity"),
    ("Conference","micro"): (None, None, "LIMITED — thin chains"),
    ("Conference","small"): (None, None, "LIMITED — event often pre-runup"),
}


def load_roster():
    rows = []
    with open(TIERED) as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows


def load_orats_cache():
    """Return dict[ticker] -> list of {date, iv, ivRank1y, ivPct1y, stockPrice, iv30d, iv90d, rVol30, contango}"""
    by_ticker = {}
    for fn in sorted(os.listdir(CACHE_DIR)):
        fp = os.path.join(CACHE_DIR, fn)
        try:
            with open(fp) as f:
                d = json.load(f)
        except Exception:
            continue
        data = d.get("data", d)
        if not isinstance(data, list) or not data:
            continue
        for row in data:
            tkr = row.get("ticker")
            if not tkr:
                continue
            by_ticker.setdefault(tkr, []).append(row)
    # Dedupe by tradeDate (keep first)
    for t in by_ticker:
        seen = {}
        for r in by_ticker[t]:
            k = r.get("tradeDate")
            if k not in seen:
                seen[k] = r
        by_ticker[t] = sorted(seen.values(), key=lambda r: r.get("tradeDate") or "")
    return by_ticker


def load_portfolio_apr7():
    with open(PORTFOLIO_APR7) as f:
        return json.load(f)


def load_bifrost_plays():
    with open(BIFROST_DEPLOY) as f:
        d = json.load(f)
    return {p["ticker"]: p for p in d["options_plays"]}


def parse_date(s):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(str(s).split(" ")[0], fmt).date()
        except Exception:
            pass
    return None


def score_cheapness(iv_pct_1y, iv_rv_ratio, days_to_cat, contango):
    """4-component ORATS cheapness score 0-100."""
    score = 0
    breakdown = {}

    # Component 1: IV Percentile 1Y (35 pts) — lower = cheaper
    if iv_pct_1y is not None:
        if iv_pct_1y < 30:   c1 = 35
        elif iv_pct_1y < 60: c1 = 22
        elif iv_pct_1y < 80: c1 = 10
        else:                c1 = 3
        score += c1
        breakdown["iv_pct_1y_pts"] = c1
    else:
        breakdown["iv_pct_1y_pts"] = None

    # Component 2: IV/RV Ratio (25 pts) — lower = options priced below realized
    if iv_rv_ratio is not None:
        if iv_rv_ratio < 1.2:   c2 = 25
        elif iv_rv_ratio < 1.5: c2 = 15
        elif iv_rv_ratio < 2.0: c2 = 7
        else:                   c2 = 2
        score += c2
        breakdown["iv_rv_pts"] = c2
    else:
        breakdown["iv_rv_pts"] = None

    # Component 3: Timing Sweet Spot (25 pts) — T-14 optimal
    if days_to_cat is not None:
        if 14 <= days_to_cat <= 35:   c3 = 25
        elif 7 <= days_to_cat < 14:   c3 = 18   # late but still tradeable
        elif 35 < days_to_cat <= 60:  c3 = 15   # early
        elif 3 <= days_to_cat < 7:    c3 = 8    # too late (IV peaked)
        elif days_to_cat < 3:         c3 = 0    # AVOID — IV crush imminent
        else:                         c3 = 10   # >60 days, theta risk
        score += c3
        breakdown["timing_pts"] = c3

    # Component 4: Term Structure Tilt (15 pts) — flat = cheap, steep = priced in
    if contango is not None:
        if contango < 1.1:   c4 = 15
        elif contango < 1.3: c4 = 8
        else:                c4 = 2
        score += c4
        breakdown["term_structure_pts"] = c4

    return score, breakdown


def cheapness_tier(score):
    if score >= 80: return "DIRT CHEAP"
    if score >= 65: return "CHEAP"
    if score >= 45: return "FAIR"
    if score >= 30: return "EXPENSIVE"
    return "OVERPRICED"


def suggest_expiries(cat_date, as_of=AS_OF):
    """Suggest monthly and weekly expiries spanning the catalyst (3rd Fri monthly, Fri weekly)."""
    if not cat_date:
        return None, None
    # Monthly: 3rd Friday of months cat_date month and next month
    def third_friday(y, m):
        d = date(y, m, 1)
        # First Friday
        offset = (4 - d.weekday()) % 7
        first_fri = date(y, m, 1 + offset)
        return date(y, m, first_fri.day + 14)

    cat_y, cat_m = cat_date.year, cat_date.month
    this_3f = third_friday(cat_y, cat_m)
    next_y, next_m = (cat_y, cat_m+1) if cat_m < 12 else (cat_y+1, 1)
    next_3f = third_friday(next_y, next_m)
    monthly = this_3f if this_3f >= cat_date else next_3f

    # Weekly: first Friday after catalyst
    d = cat_date
    while d.weekday() != 4:  # Friday
        d = date(d.year, d.month, d.day + 1) if d.day < 28 else d  # safe-ish; limit
        try:
            d = date.fromordinal(d.toordinal() + 1)
        except ValueError:
            break
    weekly = d if d.weekday() == 4 and d >= cat_date else monthly

    return weekly, monthly


def main():
    roster = load_roster()
    orats = load_orats_cache()
    apr7 = load_portfolio_apr7()
    bifrost_plays = load_bifrost_plays()

    # Include ALXO in broad scan (not on 30-name roster but user requested)
    alxo_row = {
        "Ticker": "ALXO",
        "Name": "ALX Oncology",
        "Drug": "Evorpacept (belantamab combo)",
        "Stage": "Conference/ESMO Breast",
        "cat_class": "Readout",
        "catalyst_date": "2026-05-07",
        "mcap_tier": "micro",
        "price": "1.65",
        "tier": "HELD-55%",
        "inv_score_final": "95",
        "catalyst_text": "ESMO Breast belantamab May 7 — CORE 55% hold",
    }
    scan_universe = list(roster) + [alxo_row]

    results = []
    for r in scan_universe:
        tkr = r["Ticker"].upper()
        cat_date = parse_date(r.get("catalyst_date"))
        days_to_cat = (cat_date - AS_OF).days if cat_date else None
        mcap_tier = (r.get("mcap_tier") or "").lower()
        cat_class = r.get("cat_class") or ""

        # --- Attempt ORATS-based scoring
        cache_rows = orats.get(tkr, [])
        latest = cache_rows[-1] if cache_rows else None
        iv_pct_1y = None
        iv_rank_1y = None
        iv_current = None
        rv30 = None
        iv30 = None
        iv90 = None
        contango_val = None
        term_tilt = None
        if latest:
            iv_pct_1y = latest.get("ivPct1y")
            iv_rank_1y = latest.get("ivRank1y")
            iv_current = latest.get("iv")  # % format
            rv30 = latest.get("rVol30")
            iv30 = latest.get("iv30d")
            iv90 = latest.get("iv90d")
            contango_val = latest.get("contango")
            if iv30 and iv90:
                term_tilt = iv90 / iv30 if iv30 else None
            else:
                term_tilt = None

        # IV/RV ratio
        iv_rv = None
        if iv30 and rv30 and rv30 > 0:
            iv_rv = iv30 / rv30
        elif iv_current and rv30:
            # Both in same units
            iv_rv = (iv_current/100.0) / rv30 if rv30 > 2 else iv_current/rv30

        # Contango proxy: if term_tilt available use it, else use ORATS contango field
        tilt = term_tilt if term_tilt is not None else contango_val

        score, bd = score_cheapness(iv_pct_1y, iv_rv, days_to_cat, tilt)

        # --- Portfolio Apr 7 options activity
        ap7 = apr7.get(tkr)
        apr7_vol = None
        apr7_expiries = None
        if ap7:
            apr7_expiries = ap7.get("expirations", [])
            # Total liquidity across chains
            total_vol = 0
            for exp, ch in (ap7.get("chains") or {}).items():
                total_vol += ch.get("total_call_vol", 0) + ch.get("total_put_vol", 0)
            apr7_vol = total_vol

        # --- BIFROST v1 options play match
        bif = bifrost_plays.get(tkr)

        # --- Segment edge
        edge = None
        if cat_class and mcap_tier:
            # Normalize cat_class
            cc_key = "PDUFA" if "pdufa" in cat_class.lower() or "regulatory" in cat_class.lower() or "approval" in cat_class.lower() else ("Readout" if "readout" in cat_class.lower() or "topline" in cat_class.lower() else ("Conference" if "conference" in cat_class.lower() else "Readout"))
            edge = SEGMENT_EDGE.get((cc_key, mcap_tier), (None, None, f"NO SEGMENT DATA ({cc_key}/{mcap_tier})"))

        # --- Live IV observation
        live = LIVE_IV.get(tkr)

        # --- Suggest expiries
        weekly, monthly = suggest_expiries(cat_date)

        # --- Data quality flag
        has_orats = latest is not None
        has_apr7 = ap7 is not None
        has_live = live is not None
        has_bif = bif is not None
        data_sources = []
        if has_orats: data_sources.append("ORATS")
        if has_apr7:  data_sources.append("Apr7 snap")
        if has_live:  data_sources.append("Live IV")
        if has_bif:   data_sources.append("BIFROST v1")
        data_label = "+".join(data_sources) if data_sources else "NEEDS_LIVE_FETCH"

        # --- Recommended action
        if not has_orats and not has_bif and not has_live:
            recommendation = "LIVE FETCH required — score ORATS summaries at T-14"
        elif edge and edge[0] is not None and edge[0] < 0:
            recommendation = "SKIP options (segment has negative edge per backtest)"
        elif days_to_cat and days_to_cat < 3:
            recommendation = "TOO LATE — IV crush imminent, skip options"
        elif days_to_cat and days_to_cat > 60:
            recommendation = "TOO EARLY — wait until T-35 or later"
        elif days_to_cat and 7 <= days_to_cat <= 35:
            if score >= 45 or (edge and edge[0] and edge[0] > 10):
                recommendation = f"BUY ATM calls T-14 entry — {cheapness_tier(score) if score>0 else 'check live IV'}"
            else:
                recommendation = "HOLD — await cheaper IV or better entry"
        elif days_to_cat is None:
            recommendation = "NO CATALYST DATE"
        else:
            recommendation = "MONITOR"

        results.append({
            "ticker": tkr,
            "name": r.get("Name",""),
            "cat_class": cat_class,
            "stage": r.get("Stage",""),
            "catalyst_date": r.get("catalyst_date",""),
            "days_to_cat": days_to_cat,
            "mcap_tier": mcap_tier,
            "price": r.get("price",""),
            "tier": r.get("tier",""),
            "inv_score": r.get("inv_score_final",""),
            "iv_current_pct": iv_current,
            "iv_pct_1y": iv_pct_1y,
            "iv_rank_1y": iv_rank_1y,
            "iv_rv_ratio": round(iv_rv,2) if iv_rv else None,
            "term_tilt": round(tilt,3) if tilt else None,
            "cheapness_score": score,
            "cheapness_tier": cheapness_tier(score) if score > 0 else "NO DATA",
            "segment_avg_return": edge[0] if edge else None,
            "segment_win_rate": edge[1] if edge else None,
            "segment_label": edge[2] if edge else None,
            "apr7_options_vol": apr7_vol,
            "suggested_weekly": str(weekly) if weekly else None,
            "suggested_monthly": str(monthly) if monthly else None,
            "data_sources": data_label,
            "bifrost_deploy_strike": bif.get("strike") if bif else None,
            "bifrost_deploy_iv": bif.get("iv") if bif else None,
            "bifrost_deploy_liq": bif.get("liquidity") if bif else None,
            "live_iv_note": live.get("note") if live else None,
            "recommendation": recommendation,
        })

    # Sort: NEEDS_LIVE_FETCH last, then by cheapness desc, then by segment_avg desc, then by days_to_cat asc
    def sort_key(r):
        has_data = r["data_sources"] != "NEEDS_LIVE_FETCH"
        return (
            0 if has_data else 1,
            -(r["cheapness_score"] or 0),
            -(r["segment_avg_return"] or -99),
            r["days_to_cat"] if r["days_to_cat"] is not None else 999,
        )

    results.sort(key=sort_key)

    # Write CSV
    out_csv = os.path.join(ROOT, "q2_options_cheapness.csv")
    keys = list(results[0].keys())
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in results:
            w.writerow(r)
    print(f"Wrote {out_csv}")
    print(f"Total roster: {len(results)}")
    has_data = sum(1 for r in results if r["data_sources"] != "NEEDS_LIVE_FETCH")
    print(f"With data: {has_data}, Needs live fetch: {len(results)-has_data}")

    # Console preview
    print("\nTop 15 cheapness-ranked options candidates:")
    print(f"{'Ticker':<6} {'Class':<12} {'Cat Date':<11} {'D2C':>4} {'Mcap':<6} {'Cheap':>5} {'Tier':<12} {'Sources':<30} {'Recommendation'}")
    print("-" * 170)
    for r in results[:15]:
        print(f"{r['ticker']:<6} {r['cat_class']:<12} {r['catalyst_date']:<11} {r['days_to_cat'] if r['days_to_cat'] is not None else '?':>4} {r['mcap_tier']:<6} {r['cheapness_score']:>5} {r['cheapness_tier']:<12} {r['data_sources']:<30} {r['recommendation'][:70]}")

    print("\nRoster names needing live fetch (20 of 30):")
    needs = [r for r in results if r["data_sources"] == "NEEDS_LIVE_FETCH"][:25]
    for r in needs:
        seg = r["segment_label"] or "?"
        print(f"  {r['ticker']:<6} {r['cat_class']:<12} {r['mcap_tier']:<6} D-{r['days_to_cat']:<3}  seg={seg}")

    # Also save JSON for detailed access
    out_json = os.path.join(ROOT, "q2_options_cheapness.json")
    with open(out_json, "w") as f:
        json.dump({"as_of": str(AS_OF), "results": results}, f, indent=2, default=str)
    print(f"\nWrote {out_json}")

    return results


if __name__ == "__main__":
    main()
