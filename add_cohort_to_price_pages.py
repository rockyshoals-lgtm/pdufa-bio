# -*- coding: utf-8 -*-
"""add_cohort_to_price_pages.py -- put the cohort base rate on the 435 price-only decision pages.

Two decision-page templates exist. The 20 fully-sourced pages carry "Market-cap tier" and
"Cohort decision-day move (history)"; the 435 older price-only pages carry neither, so the single
most useful number the site owns was absent from 96% of the decision archive.

369 of those pages join to the run-up study on (ticker, decision date), which already knows the
market-cap tier for the event. This inserts both rows into their "Decision facts" table, sourced
from our own dataset, in exactly the markup refresh_cohort_figures.py already maintains. That
matters: once the row exists, the nightly job keeps its number current forever. Pages that do not
join are left alone rather than given a guessed tier.

    python add_cohort_to_price_pages.py [--dry-run]
"""
import argparse, csv, glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
STATS = os.path.join(HERE, "runup_study_stats.json")

SHORT = {"Nano (<$50M)": "Nano", "Micro ($50M-$300M)": "Micro", "Small ($300M-$2B)": "Small",
         "Mid ($2B-$10B)": "Mid", "Large (>$10B)": "Large"}

NOTE = ('<p class="sub" style="font-size:13px;color:#94a9c9">Cohort move is the historical median '
        'absolute decision-day move for this market-cap tier across our run-up study. History, not '
        'a prediction.</p>')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cohort = json.load(open(STATS, encoding="utf-8")).get("cohort_abs_move", {})
    study = {}
    for r in csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")):
        study[(r["ticker"].strip().upper(), r["pdufa_date"][:10])] = r

    added = skipped = nojoin = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        html = open(p, encoding="utf-8", errors="replace").read()
        if "Cohort decision-day move" in html:
            skipped += 1
            continue
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]+)-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            nojoin += 1
            continue
        row = study.get((m.group(1), m.group(2)))
        tier_full = (row or {}).get("mcap_tier") or ""
        info = cohort.get(tier_full)
        if not row or not info:
            nojoin += 1
            continue

        block = (f'<div class="kv"><span>Market-cap tier</span><b>{SHORT.get(tier_full, tier_full)}</b></div>'
                 f'<div class="kv"><span>Cohort decision-day move (history)</span>'
                 f'<b>{info["median_abs_pct"]:.1f}% median (n={info["n"]:,})</b></div>')

        # append inside the Decision facts card, immediately before its closing </div>
        i = html.find("Decision facts")
        if i < 0:
            nojoin += 1
            continue
        j = html.find('<div class="card">', i)
        k = html.find('<a class="cta"', j)
        if j < 0 or k < 0:
            nojoin += 1
            continue
        end = html.rfind("</div>", j, k)
        if end < 0:
            nojoin += 1
            continue
        html = html[:end] + block + html[end:end + 6] + NOTE + html[end + 6:]
        if not a.dry_run:
            open(p, "w", encoding="utf-8").write(html)
        added += 1

    print(f"{'would add' if a.dry_run else 'added'} cohort rows to {added} page(s); "
          f"{skipped} already had them; {nojoin} could not be joined to the study (left alone)")


if __name__ == "__main__":
    main()
