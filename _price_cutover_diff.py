# -*- coding: utf-8 -*-
"""Close-by-close diff: FMP (price_source._fmp_daily) vs the Polygon cache stock_runup_cache.json, before cutover.
Writes _price_cutover_diff.json and prints a summary. Audit 2026-11-09 §4c step 2: list every day differing by >0.5%."""
import io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import price_source as ps

cache = json.load(io.open(os.path.join(HERE, "stock_runup_cache.json"), encoding="utf-8"))
rep = {"tickers": {}, "big": [], "fmp_missing_series": [], "totals": {}}
tot_days = tot_big = tot_only_poly = tot_only_fmp = 0
for t, series in sorted(cache.items()):
    if not series:
        continue
    poly = {d: float(c) for d, c, *_ in series}
    a, b = min(poly), max(poly)
    fmp = {d: c for d, c, _ in ps._fmp_daily(t, a, b)}
    if not fmp:
        rep["fmp_missing_series"].append(t); print(f"  {t:6s} FMP returned NOTHING for {a}..{b}"); continue
    common = sorted(set(poly) & set(fmp))
    big = [(d, poly[d], fmp[d], round((fmp[d] / poly[d] - 1) * 100, 3)) for d in common
           if poly[d] and abs(fmp[d] / poly[d] - 1) > 0.005]
    only_p, only_f = sorted(set(poly) - set(fmp)), sorted(set(fmp) - set(poly))
    maxd = max((abs(fmp[d] / poly[d] - 1) for d in common if poly[d]), default=0)
    rep["tickers"][t] = {"range": [a, b], "common": len(common), "big": len(big), "only_polygon": only_p[:20],
                         "only_fmp": only_f[:20], "max_abs_pct": round(maxd * 100, 3)}
    for row in big:
        rep["big"].append([t, *row])
    tot_days += len(common); tot_big += len(big); tot_only_poly += len(only_p); tot_only_fmp += len(only_f)
    flag = "  <-- " + f"{len(big)} day(s) >0.5%" if big else ""
    print(f"  {t:6s} {len(common):4d} common days, max |diff| {maxd*100:6.3f}%, only-Polygon {len(only_p)}, "
          f"only-FMP {len(only_f)}{flag}")
rep["totals"] = {"tickers": len(rep["tickers"]), "common_days": tot_days, "days_over_0.5pct": tot_big,
                 "only_polygon_days": tot_only_poly, "only_fmp_days": tot_only_fmp,
                 "fmp_missing_series": len(rep["fmp_missing_series"])}
io.open(os.path.join(HERE, "_price_cutover_diff.json"), "w", encoding="utf-8").write(json.dumps(rep, indent=1))
print("TOTALS", json.dumps(rep["totals"]))
print(ps.summary())
