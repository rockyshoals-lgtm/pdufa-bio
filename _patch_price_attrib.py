# One-off 2026-11-10: page attributions follow the feed (price_source.py: FMP primary since 2026-11-10).
import io, os
H = r"C:\Users\dcmoo\Documents\Python\9realms"
R = {
 "add_decision_chart.py": [("Daily closes via Polygon.", "Split-adjusted daily closes (FMP).")],
 "build_readout_results.py": [("'Polygon-adjusted close vs the prior close.", "'split-adjusted close (FMP) vs the prior close.")],
 "build_runup_by_year.py": [("Prices are split-adjusted daily closes (Polygon).",
                             "Prices are split-adjusted daily closes (Polygon through 2026-11-09, FMP since; checked close by close at the switch).")],
 "build_sls_deepdive.py": [("(Polygon, split-adjusted)", "(split-adjusted)"),
                           ("Computed from Polygon split-adjusted daily closes.", "Computed from split-adjusted daily closes (FMP; Polygon before 2026-11-10)."),
                           ("computed by pdufa.bio from Polygon split-adjusted daily", "computed by pdufa.bio from split-adjusted daily")],
 "build_sls_hub.py": [("(Polygon, split-adjusted)", "(FMP, split-adjusted)"),
                      ("Computed from Polygon split-adjusted daily closes.", "Computed from FMP split-adjusted daily closes."),
                      ("computed by pdufa.bio from Polygon split-adjusted daily closes", "computed by pdufa.bio from FMP split-adjusted daily closes")],
 "build_vktx_hub.py": [("computed from Polygon split-adjusted daily closes at build time", "computed from FMP split-adjusted daily closes at build time")],
}
for f, subs in R.items():
    p = os.path.join(H, f); s = io.open(p, encoding="utf-8").read(); o = s
    for a, b in subs:
        if a not in s:
            print("  MISSING in", f, ":", a[:60]); continue
        s = s.replace(a, b)
    if s != o:
        io.open(p, "w", encoding="utf-8").write(s); print("patched", f)
