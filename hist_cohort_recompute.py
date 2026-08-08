#!/usr/bin/env python3
"""pdufa.bio — quarterly cohort base-rate recompute (audit 4.1).
Recomputes the decision-day |move| MEDIAN by market-cap tier from the historic
decision set embedded in the dashboard, and writes a versioned HIST file.
Run quarterly (or via scheduled task). Update engine `const HIST=` + dashboard/app
embeds from the printed values when they drift.
"""
import json, re, statistics, datetime, sys, os

DASH = os.path.join(os.path.dirname(__file__), "pdufa_bio_preview", "pdufa_today_dashboard.html")
OUT_DIR = os.path.dirname(__file__)

def load_historic(path):
    h = open(path, encoding="utf-8").read()
    m = h.find("const HISTORIC=")
    if m < 0:
        sys.exit("HISTORIC array not found in dashboard")
    j = m + len("const HISTORIC=")
    # balanced-bracket scan to end of the array literal
    depth = 0; k = j; started = False
    while k < len(h):
        ch = h[k]
        if ch == '[': depth += 1; started = True
        elif ch == ']':
            depth -= 1
            if started and depth == 0: k += 1; break
        k += 1
    return json.loads(h[j:k])

def main():
    ev = load_historic(DASH)
    tiers = {}
    for e in ev:
        sz = e.get("sz"); dm = e.get("dmove")
        if sz is None or dm is None: continue
        tiers.setdefault(sz, []).append(abs(float(dm)))
    out = {}
    print(f"Cohort recompute {datetime.date.today()}  (n={len(ev)} historic events)")
    print(f"{'tier':<8}{'n':>5}{'median|move|':>14}{'p75':>8}")
    for t in ["Micro", "Small", "Mid", "Large"]:
        vals = sorted(tiers.get(t, []))
        if not vals:
            print(f"{t:<8}{0:>5}{'—':>14}"); continue
        med = round(statistics.median(vals))
        p75 = round(statistics.quantiles(vals, n=4)[2]) if len(vals) > 1 else med
        out[t] = med
        print(f"{t:<8}{len(vals):>5}{med:>13}%{p75:>7}%")
    stamp = datetime.date.today().strftime("%Y%m%d")
    versioned = os.path.join(OUT_DIR, f"hist_moves_cap_v{stamp}.json")
    current   = os.path.join(OUT_DIR, "Odin Perfection", "_hist_moves_cap.json")
    json.dump(out, open(versioned, "w"))
    print(f"\nwrote {versioned}")
    if os.path.exists(os.path.dirname(current)):
        json.dump(out, open(current, "w")); print(f"updated {current}")
    print(f"\n>>> embed in engine/dashboard/app:  const HIST={json.dumps(out)}")
    print("    (only change deployed embeds if these differ from the live values)")

if __name__ == "__main__":
    main()
