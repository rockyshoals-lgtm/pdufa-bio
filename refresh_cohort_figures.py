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

# ---------------------------------------------------------------------------------------------------------------
# 2026-10-22 (audit: "run-up study figures site-wide"). The decision pages above were the only surface refreshed.
# 70 upcoming-event pages (/pdufa/*) still carried the OLD chips ("±7% median" for micro-caps; the study now measures
# 4.6%), 130 of them carried an FAQ answer (HTML and FAQPage JSON-LD) quoting a "763-PDUFA cohort, 2024-26", and the
# /learn and /fda-approval-rate explainers quoted the same stale table. All of it is now written from the same
# runup_study_stats.json, every CI run, so none of it can drift again. Patterns accept both the old wording and the
# wording this script writes, so the next study size updates them in place.
N_ALL = int(stats["n_events"])
Y0, Y1 = str(stats["date_min"])[:4], str(stats["date_max"])[2:4]
PM = r"(?:±|&plusmn;|\\u00b1)"


def v(t):
    return TIER[t]["median_abs_pct"], TIER[t]["n"]


def faq_sentence(word):
    t = word.capitalize()
    pct, n = v(t)
    return (f"Historically, {word}-cap names had a median decision-day move of {pct:.1f}% in either direction "
            f"({n:,} {word}-cap decisions in our {N_ALL:,}-decision run-up study, {Y0}-{Y1}).")


FAQ_RE = re.compile(r"Historically, (nano|micro|small|mid|large)-cap names had a median decision-day move "
                    r"(?:around " + PM + r"(?:\d+(?:\.\d)?|\?)%|of \d+\.\d% in either direction) "
                    r"\((?:763-PDUFA cohort, 2024-26|[\d,]+ \w+-cap decisions in our [\d,]+-decision run-up study, \d{4}-\d\d)\)\.")
EV_CHIP_RE = re.compile(r'(<span>Cohort decision-day move \(history\)</span><b>)(' + PM + r'(?:\d+|\?)% median|\d+\.\d% median \(n=[\d,]+\))(</b>)')
n_chip = n_faq = n_ev = 0
# A page whose tier reads "Not listed" while its dataset row carries a cap (/pdufa/INCY: Large, $25B) quoted a cohort
# figure for no stated tier. The row's own cap fills the tier, so the chip and the tier always agree.
try:
    _src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    _rows = json.loads(_src[_src.index("["):_src.rindex("]") + 1])
    ROW_CAP = {str(r.get("url") or "").strip("/").split("/")[-1]: str(r.get("cap") or "")
               for r in _rows if str(r.get("url") or "").startswith("/pdufa/") and r.get("cap") in TIER}
except Exception:  # noqa: BLE001
    ROW_CAP = {}
TIER_ANY_RE = re.compile(r'(<span>Market-cap tier</span><b>)([^<]*)(</b>)')
for p in glob.glob(os.path.join(SITE, "pdufa", "*", "index.html")):
    h = open(p, encoding="utf-8", errors="replace").read()
    slug = os.path.basename(os.path.dirname(p))
    h2 = h
    mt0 = TIER_ANY_RE.search(h2)
    if mt0 and mt0.group(2).strip() not in TIER and ROW_CAP.get(slug):
        h2 = TIER_ANY_RE.sub(lambda m: m.group(1) + ROW_CAP[slug] + m.group(3), h2, count=1)
    h3 = FAQ_RE.sub(lambda m: faq_sentence(m.group(1)), h2)
    n_faq += len(FAQ_RE.findall(h2)) if h3 != h2 else 0
    h2 = h3
    mt = TIER_RE.search(h2)
    info = TIER.get(mt.group(2).strip()) if mt else None
    if info:
        newval = f"{info['median_abs_pct']:.1f}% median (n={info['n']:,})"
        h3 = EV_CHIP_RE.sub(lambda m: m.group(1) + newval + m.group(3), h2, count=1)
        n_chip += int(h3 != h2)
        h2 = h3
    if h2 != h:
        n_ev += 1
        if not a.dry_run:
            open(p, "w", encoding="utf-8").write(h2)


def table_rows(sep=" "):
    return (f"about {v('Nano')[0]:.1f}% for nano-caps, {v('Micro')[0]:.1f}% micro, {v('Small')[0]:.1f}% small, "
            f"{v('Mid')[0]:.1f}% mid and {v('Large')[0]:.1f}% large")


LEARN = os.path.join(SITE, "learn", "what-happens-to-a-stock-on-a-pdufa-date", "index.html")
RATE = os.path.join(SITE, "fda-approval-rate", "index.html")
COHORT_TXT = f"{N_ALL:,}-decision run-up study, {Y0}-{Y1}"
n_misc = 0
if os.path.exists(LEARN):
    h = open(LEARN, encoding="utf-8", errors="replace").read()
    h2 = re.sub(r"about " + PM + r"\d+% for micro-caps, " + PM + r"\d+% small, " + PM + r"\d+% mid, " + PM + r"\d+% large "
                r"\(763-PDUFA cohort, 2024-26\)|about [\d.]+% for nano-caps, [\d.]+% micro, [\d.]+% small, [\d.]+% mid and "
                r"[\d.]+% large \([\d,]+-decision run-up study, \d{4}-\d\d\)",
                lambda m: f"{table_rows()} ({COHORT_TXT})", h)
    rows = "".join(
        f"<div class='kv'><span>{lab}</span><b>{v(t)[0]:.1f}% median (n={v(t)[1]:,})</b></div>"
        for t, lab in (("Nano", "Nano-cap (&lt;$50M)"), ("Micro", "Micro-cap ($50M: $300M)"), ("Small", "Small-cap ($300M: $2B)"),
                       ("Mid", "Mid-cap ($2B: $10B)"), ("Large", "Large-cap (&gt;$10B)")))
    h2 = re.sub(r"(Decision-day move by company size \(history\)</h2><div class='card'>).*?(</div><p class='sub'>)",
                lambda m: m.group(1) + rows + m.group(2), h2, count=1, flags=re.S)
    h2 = re.sub(r"across a (?:763-PDUFA cohort \(2024-26\)|[\d,]+-decision run-up study \(\d{4}-\d\d\))",
                f"across our {N_ALL:,}-decision run-up study ({Y0}-{Y1})", h2)
    if h2 != h:
        n_misc += 1
        if not a.dry_run:
            open(LEARN, "w", encoding="utf-8").write(h2)
if os.path.exists(RATE):
    h = open(RATE, encoding="utf-8", errors="replace").read()
    h2 = re.sub(r"in our (?:763-PDUFA cohort|[\d,]+-decision run-up study \(\d{4}-\d\d\)), median absolute move on the decision was "
                r"(?:roughly " + PM + r"\d+% for micro-caps, " + PM + r"\d+% small, " + PM + r"\d+% mid, " + PM + r"\d+% large|"
                r"about [\d.]+% for nano-caps, [\d.]+% micro, [\d.]+% small, [\d.]+% mid and [\d.]+% large)",
                lambda m: f"in our {N_ALL:,}-decision run-up study ({Y0}-{Y1}), median absolute move on the decision was "
                          f"{table_rows()}", h)
    if h2 != h:
        n_misc += 1
        if not a.dry_run:
            open(RATE, "w", encoding="utf-8").write(h2)
print(f"{'would update' if a.dry_run else 'updated'} {n_ev} event page(s) ({n_chip} chip(s), {n_faq} FAQ sentence(s)); "
      f"{n_misc} explainer page(s) (/learn, /fda-approval-rate)")
