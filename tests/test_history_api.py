# -*- coding: utf-8 -*-
"""CI guard: the ULTRA history feed (/api/v1/history) carries the whole study, facts only, and nothing else (2026-11-26).

pdufa_runup_bifrost_v2.csv holds Odin model output beside the study's facts (v5_score, v5_tier, v9_score, v9_tier,
crl_rate, ta_risk, ta_bucket). Odin stays off pdufa.bio. build_history_api.py copies allow-listed columns only into
pdufa_site_src/api/v1/history_data.mjs, which ULTRA keys can download whole. Fails when:

  * any key outside the allow-list reaches the feed, or a key that names model output (score, tier, crl_rate, risk);
  * the feed is not the CSV rebuilt now (a stale file, a dropped or extra decision, an altered value);
  * an outcome is anything but approval or crl;
  * a series_id points at no path in runup_series.mjs, or fewer than 85% of decisions carry a path;
  * history.mjs serves data without first refusing tiers whose `history` flag is off;
  * the second ULTRA feed (/api/v1/implied, implied_data.mjs) carries a key outside its allow-list, a decision that
    is not in the curated study, an outcome or after-decision move that is not the study's own, or is stale;
    or implied.mjs serves before refusing non-ULTRA tiers or drops the two caveats.

It plants each failure against the checker before trusting a pass, so a checker that stopped looking fails too.

    python tests/test_history_api.py
"""
import copy
import csv
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_history_api as B  # noqa: E402

V1 = os.path.join(HERE, "pdufa_site_src", "api", "v1")
DATA = os.path.join(V1, "history_data.mjs")
ENDPOINT = os.path.join(V1, "history.mjs")
IMP_DATA = os.path.join(V1, "implied_data.mjs")
IMP_ENDPOINT = os.path.join(V1, "implied.mjs")
MODEL = re.compile(r"score|(^|_)tier$|crl_rate|risk|bucket|^v\d", re.I)
ALLOWED_TIER_KEY = {"market_cap_tier"}


def load_feed(path=DATA):
    txt = io.open(path, encoding="utf-8").read()
    meta = json.loads(re.search(r"export const META = (\{.*?\});\n", txt).group(1))
    rows = json.loads(re.search(r"export default (\[.*\]);\s*$", txt, re.S).group(1))
    return meta, rows


def check(rows, meta, expected, series_ids):
    probs = []
    allowed = set(B.FIELDS)
    for i, r in enumerate(rows):
        extra = set(r) - allowed
        model = [k for k in r if MODEL.search(k) and k not in ALLOWED_TIER_KEY]
        if extra or model:
            probs.append(f"row {i} ({r.get('ticker')} {r.get('decision_date')}): keys outside the allow-list "
                         f"{sorted(extra | set(model))}")
            break
    if list(meta.get("fields", [])) != B.FIELDS:
        probs.append("META.fields differs from build_history_api.FIELDS")
    bad_out = [r for r in rows if r.get("outcome") not in ("approval", "crl")]
    if bad_out:
        probs.append(f"{len(bad_out)} row(s) with an outcome outside approval/crl, e.g. {bad_out[0].get('ticker')}")
    if rows != expected:
        n_diff = sum(1 for a, b in zip(rows, expected) if a != b) + abs(len(rows) - len(expected))
        probs.append(f"feed is not the study CSV rebuilt now ({len(rows)} rows vs {len(expected)} expected, "
                     f"{n_diff} differ); run build_history_api.py")
    dangling = [r["series_id"] for r in rows if r.get("series_id") and r["series_id"] not in series_ids]
    if dangling:
        probs.append(f"{len(dangling)} series_id(s) with no path in runup_series.mjs, e.g. {dangling[0]}")
    with_path = sum(1 for r in rows if r.get("series_id"))
    if rows and with_path / len(rows) < 0.85:
        probs.append(f"only {with_path} of {len(rows)} decisions carry a daily path (floor 85%)")
    if meta.get("rows") != len(rows) or meta.get("with_series") != with_path:
        probs.append("META counts disagree with the rows")
    return probs


def check_implied(irows, imeta, iexpected, study):
    probs = []
    allowed = set(B.IMPLIED_FIELDS)
    for i, r in enumerate(irows):
        extra = set(r) - allowed
        model = [k for k in r if MODEL.search(k) and k not in ALLOWED_TIER_KEY]
        if extra or model:
            probs.append(f"implied row {i}: keys outside the allow-list {sorted(extra | set(model))}")
            break
    if list(imeta.get("fields", [])) != B.IMPLIED_FIELDS:
        probs.append("implied META.fields differs from build_history_api.IMPLIED_FIELDS")
    by = {(o["ticker"], o["decision_date"]): o for o in study}
    for r in irows:
        s = by.get((r.get("ticker"), r.get("decision_date")))
        if not s:
            probs.append(f"implied row {r.get('ticker')} {r.get('decision_date')} is not in the curated study")
            break
        if (r.get("outcome"), r.get("post_1d_pct"), r.get("post_5d_pct")) != (s["outcome"], s["post_1d_pct"], s["post_5d_pct"]):
            probs.append(f"implied row {r.get('ticker')} {r.get('decision_date')}: outcome or move is not the study's own")
            break
    if irows != iexpected:
        probs.append(f"implied feed is not implied_moves.json rebuilt now ({len(irows)} vs {len(iexpected)} rows); "
                     f"run build_history_api.py")
    if imeta.get("rows") != len(irows):
        probs.append("implied META.rows disagrees with the rows")
    return probs


def check_implied_endpoint(src):
    gate = src.find("if (!TIERS[tier].history)")
    if gate < 0 or (0 <= src.find("meter(req") < gate):
        return ["implied.mjs does not refuse non-ULTRA tiers before metering and serving"]
    if "two weeks of ordinary movement plus the event" not in src or "not investment advice" not in src:
        return ["implied.mjs dropped one of the two caveats that ship with the data"]
    return []


def check_endpoint(src):
    gate = src.find("if (!TIERS[tier].history)")
    first_meter = src.find("meter(req")
    first_data = src.find("ROWS.") if "ROWS." in src else src.find("rows = ROWS")
    if gate < 0:
        return ["history.mjs has no `if (!TIERS[tier].history)` refusal"]
    if (first_meter >= 0 and first_meter < gate) or (first_data >= 0 and first_data < gate):
        return ["history.mjs touches the meter or the data before refusing non-ULTRA tiers"]
    if "dataset.mjs" in src or "bifrost" in src:
        return ["history.mjs imports a source other than history_data.mjs and runup_series.mjs"]
    return []


def main():
    meta, rows = load_feed()
    csv_rows = list(csv.DictReader(io.open(B.CSVF, encoding="utf-8-sig", errors="replace")))
    keys = B.load_series_keys()
    expected = B.build_rows(csv_rows, keys)
    series_ids = set(keys.values()) | set(json.loads(
        re.sub(r"^\s*export\s+default\s*", "", io.open(B.SERIES, encoding="utf-8").read()).rstrip().rstrip(";")).keys())
    src = io.open(ENDPOINT, encoding="utf-8").read()
    imeta, irows = load_feed(IMP_DATA)
    isrc_json = json.load(io.open(B.IMPLIED_SRC, encoding="utf-8"))
    iexpected = B.build_implied(isrc_json.get("events", []), expected)
    isrc = io.open(IMP_ENDPOINT, encoding="utf-8").read()

    # plants first: each must be caught, or the pass below means nothing
    plants = []
    p = copy.deepcopy(rows); p[3]["v9_score"] = 0.81; plants.append(("model column", p, meta, src))
    p = copy.deepcopy(rows); p[7]["ta_risk"] = "HIGH_CRL"; plants.append(("risk column", p, meta, src))
    p = copy.deepcopy(rows); p[1]["outcome"] = "likely"; plants.append(("bad outcome", p, meta, src))
    p = copy.deepcopy(rows)[:-1]; plants.append(("dropped decision", p, dict(meta, rows=len(p)), src))
    p = copy.deepcopy(rows); p[0]["post_1d_pct"] = 99.99; plants.append(("altered value", p, meta, src))
    p = copy.deepcopy(rows); p[2]["series_id"] = "pdufa_zzz_1999-01-01"; plants.append(("dangling path", p, meta, src))
    ungated = src.replace("if (!TIERS[tier].history)", "if (false)")
    plants.append(("ungated endpoint", rows, meta, ungated))
    missed = []
    for name, pr, pm, ps in plants:
        if not (check(pr, pm, expected, series_ids) + check_endpoint(ps)):
            missed.append(name)
    iplants = []
    p = copy.deepcopy(irows); p[4]["v5_tier"] = "T1"; iplants.append(("implied model column", p, isrc))
    p = copy.deepcopy(irows); p[5]["outcome"] = "crl" if p[5]["outcome"] == "approval" else "approval"
    iplants.append(("implied outcome not the study's", p, isrc))
    p = copy.deepcopy(irows); p.append(dict(p[0], ticker="ZZZZ")); iplants.append(("implied row outside the study", p, isrc))
    iplants.append(("implied ungated", irows, isrc.replace("if (!TIERS[tier].history)", "if (false)")))
    iplants.append(("implied caveat dropped", irows, isrc.replace("two weeks of ordinary movement plus the event", "x")))
    for name, pr, ps in iplants:
        if not (check_implied(pr, dict(imeta, rows=len(pr)), iexpected, expected) + check_implied_endpoint(ps)):
            missed.append(name)
    if missed:
        print(f"FAIL: the checker missed planted faults: {missed}")
        return 1

    probs = (check(rows, meta, expected, series_ids) + check_endpoint(src)
             + check_implied(irows, imeta, iexpected, expected) + check_implied_endpoint(isrc))
    if probs:
        print("FAIL: /api/v1/history feed\n  " + "\n  ".join(probs))
        return 1
    print(f"OK -- ULTRA history feed: {len(rows)} decisions, allow-listed fields only, "
          f"{sum(1 for r in rows if r.get('series_id'))} with a daily path; options feed: {len(irows)} decisions, all "
          f"in the study; {len(plants) + len(iplants)} planted faults caught.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
