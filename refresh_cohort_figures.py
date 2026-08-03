# -*- coding: utf-8 -*-
"""refresh_cohort_figures.py -- update the cohort decision-day move quoted on every decision page.

Those pages quote "Cohort decision-day move (history)" for the company's market-cap tier. The values
baked in (±10 / ±7 / ±3 / ±2 / ±1%) came from an earlier cut of the run-up study. Recomputed on the
current 1,827-event dataset the medians are materially different for the small end -- micro-cap is
4.6%, not 7% -- so the pages were overstating the typical move for exactly the companies where the
number matters most.

Values are read from runup_study_stats.json (written by runup_study_stats.py) so the page copy can
never drift from the dataset again.

    python refresh_cohort_figures.py [--dry-run]
"""
import argparse, glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
STATS = os.path.join(HERE, "runup_study_stats.json")

stats = json.load(open(STATS, encoding="utf-8"))
cohort = stats.get("cohort_abs_move", {})
# tier label as written on the pages -> measured median absolute move
TIER = {
    "Nano": cohort.get("Nano (<$50M)", {}),
    "Micro": cohort.get("Micro ($50M-$300M)", {}),
    "Small": cohort.get("Small ($300M-$2B)", {}),
    "Mid": cohort.get("Mid ($2B-$10B)", {}),
    "Large": cohort.get("Large (>$10B)", {}),
}

ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()

print("measured cohort medians (|decision-day move|):")
for k, v in TIER.items():
    if v:
        print(f"  {k:6s} {v['median_abs_pct']:.1f}%  (n={v['n']})")

TIER_RE = re.compile(r'(<span>Market-cap tier</span><b>)([A-Za-z]+)(</b>)')
COH_RE = re.compile(r'(<span>Cohort decision-day move \(history\)</span><b>)([^<]*)(</b>)')

changed, skipped, notier = 0, 0, 0
for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
    h = open(p, encoding="utf-8", errors="replace").read()
    mt = TIER_RE.search(h)
    if not mt:
        notier += 1
        continue
    tier = mt.group(2).strip()
    info = TIER.get(tier)
    if not info:
        notier += 1
        continue
    newval = f"{info['median_abs_pct']:.1f}% median (n={info['n']:,})"
    mc = COH_RE.search(h)
    if not mc:
        skipped += 1
        continue
    if mc.group(2).strip() == newval:
        skipped += 1
        continue
    h2 = COH_RE.sub(lambda m: m.group(1) + newval + m.group(3), h, count=1)
    if not a.dry_run:
        open(p, "w", encoding="utf-8").write(h2)
    changed += 1

print(f"\n{'would update' if a.dry_run else 'updated'} {changed} decision page(s); "
      f"{skipped} already correct/no cohort line; {notier} without a recognised tier")
