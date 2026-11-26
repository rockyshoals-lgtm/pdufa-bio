# -*- coding: utf-8 -*-
"""build_history_api.py -- the ULTRA bulk history dataset behind /api/v1/history (2026-11-26).

David, 2026-11-26: ULTRA (the API's "quant" tier, $149/mo, price unchanged) must get "a lot of information".
Until today the tier's `history` flag gated nothing: ULTRA bought quota and burst, no data Pro lacked.
This writes the whole run-up study, one row per FDA decision, for ULTRA only:

  * every event in pdufa_runup_bifrost_v2.csv (the curated study the site's statistics are computed from),
  * the facts of the decision (ticker, company, drug, indication, area, decision date, outcome, cap tier),
  * the study's own measured windows, with the study's own conventions (extend_runup_study.py docstring):
      eve_date / eve_close     last session strictly before the decision, and its close
      runup_Nd_pct             % from the close N sessions before eve to the eve close
      post_Nd_pct              % from the eve close to the close N sessions after
      pre_tA_tB_pct            % from A sessions before eve to B sessions before eve (the CSV stores a fraction;
                               it is multiplied by 100 here so every return in the feed is one unit)
      pre_t120_peak_pct        % from the close 120 sessions before eve to the highest close before eve
      volume_ratio             decision-day volume / mean volume over the 30 sessions before eve
  * series_id: the key of the event's daily T-120 -> T+5 indexed path in runup_series.mjs, joined on
    (ticker, decision date), so the endpoint can attach the whole path to the row.

What it NEVER writes: the CSV also carries Odin model output (v5_score, v5_tier, v9_score, v9_tier, crl_rate,
ta_risk, ta_bucket). Odin stays off pdufa.bio (David). Only the columns in KEEP leave this script, by allow-list,
so a column added to the CSV later is dropped unless someone adds it here on purpose.
tests/test_history_api.py fails if a model column, or any column outside the allow-list, reaches the output.

It also writes the second ULTRA feed, /api/v1/implied: what the options market priced before each decision
(implied_moves.json, build_implied_moves.py: the ATM straddle from the chain snapshot nearest 14 days before, through
the first expiry after the decision) beside what happened. implied_moves.json was computed over the study's old,
uncurated universe, so ONLY decisions still in the curated study are kept, and the outcome and the after-decision
moves are the study's own (they agree today on every kept row; the study is the owner if they ever do not).

    python build_history_api.py            # writes history_data.mjs and implied_data.mjs in pdufa_site_src/api/v1/
"""
import csv
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
SERIES = os.path.join(HERE, "pdufa_site_src", "api", "v1", "runup_series.mjs")
OUT = os.path.join(HERE, "pdufa_site_src", "api", "v1", "history_data.mjs")
IMPLIED_SRC = os.path.join(HERE, "implied_moves.json")
IMPLIED_OUT = os.path.join(HERE, "pdufa_site_src", "api", "v1", "implied_data.mjs")
IMPLIED_FIELDS = ["ticker", "drug", "decision_date", "outcome", "market_cap_tier", "snapshot_date",
                  "days_before", "expiry", "spot", "priced_move_pct", "atm_iv_pct", "post_1d_pct", "post_5d_pct",
                  "exceeded_1d", "exceeded_5d"]

OUTCOMES = {"APPROVAL": "approval", "CRL": "crl"}
# (output field, csv column, kind). kind: text | pct (already percent) | frac (fraction -> percent) | num
KEEP = [
    ("ticker", "ticker", "text"), ("company", "company", "text"), ("drug", "asset", "text"),
    ("indication", "indication", "text"), ("therapeutic_area", "therapeutic_area", "text"),
    ("decision_date", "pdufa_date", "text"), ("outcome", "outcome", "outcome"),
    ("market_cap_tier", "mcap_tier", "text"),
    ("eve_date", "eve_date", "text"), ("eve_close", "eve_price", "price"),
    ("runup_30d_pct", "runup_30d", "pct"), ("runup_21d_pct", "runup_21d", "pct"),
    ("runup_14d_pct", "runup_14d", "pct"), ("runup_7d_pct", "runup_7d", "pct"),
    ("runup_5d_pct", "runup_5d", "pct"), ("runup_3d_pct", "runup_3d", "pct"),
    ("post_1d_pct", "post_1d", "pct"), ("post_2d_pct", "post_2d", "pct"), ("post_5d_pct", "post_5d", "pct"),
    ("volume_ratio", "vol_ratio", "num"),
    ("pre_t120_t1_pct", "T-120_T-1", "frac"), ("pre_t120_t3_pct", "T-120_T-3", "frac"),
    ("pre_t120_t7_pct", "T-120_T-7", "frac"), ("pre_t120_peak_pct", "T-120_peak", "frac"),
    ("pre_t90_t1_pct", "T-90_T-1", "frac"), ("pre_t90_t3_pct", "T-90_T-3", "frac"), ("pre_t90_t7_pct", "T-90_T-7", "frac"),
    ("pre_t60_t1_pct", "T-60_T-1", "frac"), ("pre_t60_t3_pct", "T-60_T-3", "frac"), ("pre_t60_t7_pct", "T-60_T-7", "frac"),
    ("pre_t45_t1_pct", "T-45_T-1", "frac"), ("pre_t45_t3_pct", "T-45_T-3", "frac"), ("pre_t45_t7_pct", "T-45_T-7", "frac"),
    ("pre_t25_t1_pct", "T-25_T-1", "frac"), ("pre_t25_t3_pct", "T-25_T-3", "frac"), ("pre_t25_t7_pct", "T-25_T-7", "frac"),
]
FIELDS = [k for k, _, _ in KEEP] + ["series_id"]


def num(v):
    try:
        x = float(str(v).strip())
    except (TypeError, ValueError):
        return None
    return x if x == x and abs(x) != float("inf") else None


def load_series_keys(path=SERIES):
    """{(ticker, date): series_id} from runup_series.mjs, read as JSON (it is `export default {...};`)."""
    if not os.path.exists(path):
        return {}
    txt = io.open(path, encoding="utf-8").read()
    body = re.sub(r"^\s*export\s+default\s*", "", txt).rstrip().rstrip(";")
    ser = json.loads(body)
    out = {}
    for sid in sorted(ser):
        v = ser[sid]
        out.setdefault((str(v.get("t", "")).upper(), str(v.get("d", ""))[:10]), sid)
    return out


def build_rows(csv_rows, series_keys):
    rows = []
    for r in csv_rows:
        o = {}
        for out_k, col, kind in KEEP:
            v = r.get(col, "")
            if kind == "text":
                o[out_k] = (str(v).strip() or None)
            elif kind == "outcome":
                o[out_k] = OUTCOMES.get(str(v).strip().upper())
            elif kind == "price":
                x = num(v); o[out_k] = None if x is None else round(x, 4)
            elif kind == "pct":
                x = num(v); o[out_k] = None if x is None else round(x, 2)
            elif kind == "frac":
                x = num(v); o[out_k] = None if x is None else round(x * 100, 2)
            else:
                x = num(v); o[out_k] = None if x is None else round(x, 3)
        if o["ticker"]:
            o["ticker"] = o["ticker"].upper()
        o["series_id"] = series_keys.get((o["ticker"] or "", (o["decision_date"] or "")[:10]))
        rows.append(o)
    rows.sort(key=lambda o: (o["decision_date"] or "", o["ticker"] or ""))
    return rows


def build_implied(implied_events, study_rows):
    """Options-priced vs actual, one row per decision that is still in the curated study."""
    by = {(o["ticker"], o["decision_date"]): o for o in study_rows}
    out = []
    for e in implied_events:
        s = by.get((str(e.get("t", "")).upper(), str(e.get("pdufa", ""))[:10]))
        priced = num(e.get("priced_pct"))
        if not s or priced is None:
            continue
        a1, a5 = s["post_1d_pct"], s["post_5d_pct"]
        out.append({
            "ticker": s["ticker"], "drug": s["drug"], "decision_date": s["decision_date"], "outcome": s["outcome"],
            "market_cap_tier": s["market_cap_tier"], "snapshot_date": str(e.get("snap") or "")[:10] or None,
            "days_before": e.get("days_before"), "expiry": str(e.get("expiry") or "")[:10] or None,
            "spot": num(e.get("spot")), "priced_move_pct": round(priced, 1), "atm_iv_pct": num(e.get("atm_iv_pct")),
            "post_1d_pct": a1, "post_5d_pct": a5,
            "exceeded_1d": None if a1 is None else abs(a1) > priced,
            "exceeded_5d": None if a5 is None else abs(a5) > priced,
        })
    out.sort(key=lambda o: (o["decision_date"] or "", o["ticker"] or ""))
    return out


def write(path, meta, rows, what):
    body = ("// Generated by build_history_api.py. Do not edit by hand. " + what + "\n"
            "export const META = " + json.dumps(meta, separators=(",", ":")) + ";\n"
            "export default " + json.dumps(rows, separators=(",", ":"), ensure_ascii=False) + ";\n")
    old = io.open(path, encoding="utf-8").read() if os.path.exists(path) else None
    if old != body:
        io.open(path, "w", encoding="utf-8", newline="\n").write(body)
    return old != body


def main():
    csv_rows = list(csv.DictReader(io.open(CSVF, encoding="utf-8-sig", errors="replace")))
    rows = build_rows(csv_rows, load_series_keys())
    bad = [o for o in rows if o["outcome"] is None]
    if bad:
        print(f"FAIL: {len(bad)} study row(s) with an outcome outside APPROVAL/CRL, e.g. {bad[0]['ticker']} "
              f"{bad[0]['decision_date']}; nothing written")
        return 1
    dates = [o["decision_date"] for o in rows if o["decision_date"]]
    meta = {"rows": len(rows), "with_series": sum(1 for o in rows if o["series_id"]),
            "approvals": sum(1 for o in rows if o["outcome"] == "approval"),
            "crls": sum(1 for o in rows if o["outcome"] == "crl"),
            "date_min": min(dates) if dates else None, "date_max": max(dates) if dates else None,
            "fields": FIELDS}
    changed = write(OUT, meta, rows, "ULTRA-only (/api/v1/history), from pdufa_runup_bifrost_v2.csv; "
                    "allow-listed study columns, no model output.")
    print(f"history_data.mjs: {meta['rows']} decisions ({meta['approvals']} approvals, {meta['crls']} CRLs), "
          f"{meta['with_series']} with a daily path, {meta['date_min']} to {meta['date_max']}"
          + ("" if changed else " (unchanged)"))

    src = json.load(io.open(IMPLIED_SRC, encoding="utf-8")) if os.path.exists(IMPLIED_SRC) else {"events": []}
    imp = build_implied(src.get("events", []), rows)
    idates = [o["decision_date"] for o in imp]
    imeta = {"rows": len(imp), "of_computed": len(src.get("events", [])),
             "computed_as_of": (src.get("aggregate") or {}).get("as_of"),
             "date_min": min(idates) if idates else None, "date_max": max(idates) if idates else None,
             "fields": IMPLIED_FIELDS}
    changed = write(IMPLIED_OUT, imeta, imp, "ULTRA-only (/api/v1/implied), from implied_moves.json joined to "
                    "the curated study.")
    print(f"implied_data.mjs: {imeta['rows']} decisions with an options snapshot (of {imeta['of_computed']} computed, "
          f"the rest are no longer in the curated study), computed {imeta['computed_as_of']}"
          + ("" if changed else " (unchanged)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
