# -*- coding: utf-8 -*-
"""What the options market priced before each FDA decision, vs what happened.

Audit 2026-09-05c section 6: the single most-asked pre-catalyst question a retail
reader has, and no free source publishes it. The red team's 389-event proof of
concept was explicitly indicative-only; THIS is the production computation, run over
the same 1,840-event universe as the published run-up study
(pdufa_runup_bifrost_v2.csv) and the 2,714 ORATS chain snapshots on disk.

Method, stated exactly as the page states it:
  - For each event, the chain snapshot closest to 14 days before the decision
    (accepted anywhere in the 30 days before it; the snapshot date is recorded).
  - The nearest listed expiry AFTER the decision date.
  - The at-the-money straddle: call mid + put mid at the strike nearest the stock
    price, divided by the stock price = the move the market priced from the
    snapshot date through that expiry.
  - The actual move is the study's own across-the-decision close-to-close move
    (post_1d), so this page and /runup-by-year can never disagree about what
    happened.

THE TWO CAVEATS (audit section 6 -- they ship with the data or the data does not
ship):
  1. A straddle two weeks out prices two weeks of ordinary movement PLUS the event.
     It is "the move the options market priced from the snapshot date through the
     first expiry after the decision" -- never "the event-implied move".
  2. The exceed rate describes history and invites a strategy reading. It is
     published as a measurement with its distribution. No strategy verb appears on
     the page, and the full disclaimer stack applies.

Output: implied_moves.json (per-event rows + aggregates), consumed by the research
page builder and the decision-page block injector.
"""
import collections
import csv
import datetime as dt
import io
import json
import os
import statistics as st
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "Odin Perfection", "orats_strikes_cache")
CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
OUT = os.path.join(HERE, "implied_moves.json")
LOOKBACK = 30          # snapshot accepted up to 30 days before the decision
TARGET = 14            # ...preferring the one closest to T-14 calendar days


def load_universe():
    return list(csv.DictReader(io.open(CSVF, encoding="utf-8-sig", errors="replace")))


def snapshots_by_ticker():
    out = collections.defaultdict(list)
    for f in os.listdir(CACHE):
        if f.endswith(".json") and "_" in f:
            tk, d = f[:-5].rsplit("_", 1)
            try:
                dt.date.fromisoformat(d)
            except ValueError:
                continue
            out[tk].append(d)
    return out


def mid(bid, ask):
    try:
        b, a = float(bid), float(ask)
    except (TypeError, ValueError):
        return None
    if a <= 0 or b < 0 or a < b:
        return None
    return (b + a) / 2.0


def compute_event(tk, pdufa, snap_date):
    """(priced_pct, atm_iv_pct, expiry, stock_price) or None."""
    try:
        rows = json.load(io.open(os.path.join(CACHE, f"{tk}_{snap_date}.json"),
                                 encoding="utf-8", errors="replace"))
    except Exception:
        return None
    if not isinstance(rows, list) or not rows:
        return None
    expiries = sorted({r["expirDate"] for r in rows
                       if str(r.get("expirDate", "")) > pdufa})
    if not expiries:
        return None
    exp = expiries[0]
    chain = [r for r in rows if r.get("expirDate") == exp]
    if not chain:
        return None
    spot = None
    for r in chain:
        try:
            spot = float(r.get("stockPrice") or r.get("spotPrice") or 0) or spot
        except (TypeError, ValueError):
            pass
    if not spot or spot <= 0:
        return None
    best = min(chain, key=lambda r: abs(float(r.get("strike") or 0) - spot))
    cm = mid(best.get("callBidPrice"), best.get("callAskPrice"))
    pm = mid(best.get("putBidPrice"), best.get("putAskPrice"))
    if cm is None or pm is None or cm + pm <= 0:
        return None
    priced = (cm + pm) / spot * 100.0
    ivs = [float(best.get(k) or 0) for k in ("callMidIv", "putMidIv")]
    ivs = [v for v in ivs if v > 0]
    iv = round(sum(ivs) / len(ivs) * 100.0, 1) if ivs else None
    return round(priced, 1), iv, exp, round(spot, 2)


def main():
    uni = load_universe()
    snaps = snapshots_by_ticker()
    out_rows = []
    n_events = 0
    seen = set()
    for r in uni:
        tk, pd = str(r.get("ticker") or "").upper(), str(r.get("pdufa_date") or "")
        if (tk, pd) in seen:
            continue                    # the universe carries occasional duplicate rows
        seen.add((tk, pd))
        try:
            p = dt.date.fromisoformat(pd)
            actual = float(r.get("post_1d"))
        except (ValueError, TypeError):
            continue
        # OTLK 2025-12-31 taught why ONE horizon misleads: the first close after the
        # decision was -15.3%, and five days later the stock was down ~65%. Reporting
        # only the one-day close would make the options market look wildly wrong-footed
        # in the priced direction and hide the realized move. Both horizons ship.
        try:
            actual5 = float(r.get("post_5d"))
        except (ValueError, TypeError):
            actual5 = None
        n_events += 1
        cands = [(abs((p - dt.date.fromisoformat(d)).days - TARGET), d)
                 for d in snaps.get(tk, [])
                 if 0 < (p - dt.date.fromisoformat(d)).days <= LOOKBACK]
        if not cands:
            continue
        _, snap = min(cands)
        got = compute_event(tk, pd, snap)
        if not got:
            continue
        priced, iv, exp, spot = got
        out_rows.append({
            "t": tk, "pdufa": pd, "snap": snap,
            "days_before": (p - dt.date.fromisoformat(snap)).days,
            "expiry": exp, "spot": spot,
            "priced_pct": priced, "atm_iv_pct": iv,
            "actual_pct": round(actual, 1),
            "actual_5d_pct": round(actual5, 1) if actual5 is not None else None,
            "exceeded": abs(actual) > priced,
            "exceeded_5d": (abs(actual5) > priced) if actual5 is not None else None,
            "outcome": str(r.get("outcome") or ""),
            "drug": str(r.get("asset") or "")[:60],
            "mcap_tier": str(r.get("mcap_tier") or ""),
        })

    priced = [x["priced_pct"] for x in out_rows]
    actual = [abs(x["actual_pct"]) for x in out_rows]
    actual5 = [abs(x["actual_5d_pct"]) for x in out_rows if x["actual_5d_pct"] is not None]
    n_ex = sum(1 for x in out_rows if x["exceeded"])
    n_ex5 = sum(1 for x in out_rows if x["exceeded_5d"])
    by_year = collections.defaultdict(lambda: [0, 0, [], []])
    for x in out_rows:
        y = x["pdufa"][:4]
        b = by_year[y]
        b[0] += 1
        b[1] += 1 if x["exceeded"] else 0
        b[2].append(x["priced_pct"])
        b[3].append(abs(x["actual_pct"]))

    agg = {
        "as_of": dt.date.today().isoformat(),
        "universe_events": n_events,
        "computed": len(out_rows),
        "coverage_pct": round(len(out_rows) / n_events * 100, 1) if n_events else 0,
        "median_priced_pct": round(st.median(priced), 1) if priced else None,
        "median_actual_abs_pct": round(st.median(actual), 1) if actual else None,
        "median_actual_5d_abs_pct": round(st.median(actual5), 1) if actual5 else None,
        "n_exceeded": n_ex,
        "exceed_rate_pct": round(n_ex / len(out_rows) * 100, 1) if out_rows else None,
        "n_exceeded_5d": n_ex5,
        "exceed_5d_rate_pct": round(n_ex5 / len(actual5) * 100, 1) if actual5 else None,
        "by_year": {y: {"n": b[0], "exceeded": b[1],
                        "median_priced_pct": round(st.median(b[2]), 1),
                        "median_actual_abs_pct": round(st.median(b[3]), 1)}
                    for y, b in sorted(by_year.items())},
    }
    json.dump({"aggregate": agg, "events": sorted(out_rows, key=lambda x: x["pdufa"])},
              io.open(OUT, "w", encoding="utf-8"), indent=1)
    print(f"implied_moves.json: {len(out_rows)} of {n_events} events computed "
          f"({agg['coverage_pct']}%) | median priced ±{agg['median_priced_pct']}% | "
          f"median actual {agg['median_actual_abs_pct']}% | exceeded "
          f"{n_ex} ({agg['exceed_rate_pct']}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
