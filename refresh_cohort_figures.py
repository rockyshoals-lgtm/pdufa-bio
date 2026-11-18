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


# ---------------------------------------------------------------------------------------------------------------
# 2026-11-18 (design red team, change 6: "label every number and give it one value"). Each /pdufa/ page's cohort card
# says "840 large-cap decisions" and "a median decision-day move of 1.0% in either direction", then draws a histogram
# (coh-dist-v1) captioned "n=790 · median +0.0% · 50% up" from a July one-off cut that nothing refreshed: two counts and
# two different "medians" for one cohort on one card. The histogram is now drawn here from the same study rows
# (pdufa_runup_bifrost_v2.csv, post_1d by mcap_tier) that runup_study_stats.py turns into the chip, so its n is the
# chip's n and its median is the same median size of move, labelled as such.
import csv as _csv
import statistics as _st

CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
TIER_KEY = {"Nano": "Nano (<$50M)", "Micro": "Micro ($50M-$300M)", "Small": "Small ($300M-$2B)",
            "Mid": "Mid ($2B-$10B)", "Large": "Large (>$10B)"}
MOVES = {}
try:
    for _r in _csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")):
        try:
            _v = float(_r.get("post_1d"))
        except (TypeError, ValueError):
            continue
        if _r.get("mcap_tier"):
            MOVES.setdefault(_r["mcap_tier"], []).append(_v)
except OSError:
    MOVES = {}
BINS = [(None, -30, "under -30%"), (-30, -15, "-30 to -15%"), (-15, -7, "-15 to -7%"), (-7, -3, "-7 to -3%"),
        (-3, 3, "-3 to +3%"), (3, 7, "+3 to +7%"), (7, 15, "+7 to +15%"), (15, 30, "+15 to +30%"), (30, None, "over +30%")]
AXIS = {0: "&lt;-30", 4: "&#177;3", 8: "&gt;+30"}


def _bin(x):
    for i, (lo, hi, _l) in enumerate(BINS):
        if (lo is None or x >= lo) and (hi is None or x < hi):
            return i
    return len(BINS) - 1


def _svg(word, counts, n, phone):
    w, x0, bw, step, base, top, fs = ((320, 6.4, 31.3, 34.5, 84.5, 16.0, 12.2) if phone else
                                      (300, 6.0, 29.3, 32.33, 76.5, 8.0, 9))
    lab_y = 98.0 if phone else 90
    halo = ' stroke="#071528" stroke-width="3" stroke-linejoin="round" paint-order="stroke"' if phone else ""
    aria = f"Decision-day move distribution for {word}-cap PDUFAs, n={n:,}"
    head = (f'<svg class="pd-phs"  width="100%" style="" xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Mono,monospace" '
            f'role="img" aria-label="{aria}" viewBox="0 0.0 320 104.0">' if phone else
            f'<svg viewBox="0 0 300 96" width="100%" style="max-width:340px" xmlns="http://www.w3.org/2000/svg" '
            f'font-family="IBM Plex Mono,monospace" role="img" aria-label="{aria}">')
    out = [head, f'<line x1="{x0}" y1="{base}" x2="{w - x0}" y2="{base}" stroke="#1e3a63"/>']
    peak = max(counts) or 1
    for i, (lo, hi, lab) in enumerate(BINS):
        c = counts[i]
        h = round(68.0 * c / peak, 1)
        x = round(x0 + i * step, 1)
        fill, op = ("#5b8fd0", "0.55") if i == 4 else (("#ff7a72" if i < 4 else "#46d17f"), "0.92")
        out.append(f'<g><title>{lab}: {c:,} of {n:,} ({round(100 * c / n):.0f}%)</title><rect x="{x}" y="{round(base - 0.5 - h, 1)}" '
                   f'width="{bw}" height="{h}" rx="1.5" fill="{fill}" opacity="{op}"/></g>')
        if i in AXIS:
            out.append(f'<text x="{round(x + bw / 2, 1)}" y="{lab_y}" fill="#7c93b6" font-size="{fs}" text-anchor="middle"{halo}>'
                       f'{AXIS[i]}</text>')
    out.append("</svg>")
    return "".join(out)


def cohort_histogram(word):
    """The coh-dist-v1 card body for a tier word (nano/micro/small/mid/large), or None without study rows."""
    vals = MOVES.get(TIER_KEY[word.capitalize()]) or []
    if not vals:
        return None
    n = len(vals)
    counts = [0] * len(BINS)
    for x in vals:
        counts[_bin(x)] += 1
    # the chip's own figure (runup_study_stats.json rounds to 2 places: 3.45 prints 3.5 there), so the two never
    # print different decimals for the same median
    size = (TIER.get(word.capitalize()) or {}).get("median_abs_pct")
    if size is None or (TIER.get(word.capitalize()) or {}).get("n") != n:
        size = round(_st.median([abs(x) for x in vals]), 2)
    up = round(100 * sum(1 for x in vals if x > 0) / n)
    return ('<div class="coh-dist-v1" style="margin-top:12px"><div style="display:flex;justify-content:space-between;'
            'align-items:baseline;gap:8px;margin-bottom:4px;flex-wrap:wrap"><span class="lit" style="font-size:11px;'
            f'color:#7c93b6;text-transform:uppercase;letter-spacing:.5px">Decision-day move &middot; {word}-cap cohort</span>'
            f'<span class="lit" style="font-size:11px;color:#9db3d4">n={n:,} &middot; median size {size:.1f}% &middot; '
            f'{up}% up</span></div><!--PH:B--><div class="pd-ph">{_svg(word, counts, n, False)}{_svg(word, counts, n, True)}'
            '</div><!--PH:E--><div class="lit" style="font-size:10.5px;color:#7c93b6;margin-top:2px">Next-day % move after '
            f'the FDA decision, {n:,} {word}-cap decisions in our run-up study ({Y0}&#8211;{Y1}). Median size is the '
            'middle move up or down. Red = down, green = up, blue = within &#177;3%. Historical dispersion, not a '
            'forecast.</div></div>')


HIST_RE = re.compile(r'<div class="coh-dist-v1".*?<!--PH:E--><div class="lit"[^>]*>[^<]*</div></div>', re.S)
HIST_WORD = re.compile(r'Decision-day move &middot; (nano|micro|small|mid|large)-cap cohort')
n_hist = 0
for p in glob.glob(os.path.join(SITE, "pdufa", "*", "index.html")):
    h = open(p, encoding="utf-8", errors="replace").read()
    m = HIST_RE.search(h)
    if not m:
        continue
    mt = TIER_RE.search(h)
    wm = HIST_WORD.search(m.group(0))
    word = mt.group(2).strip().lower() if mt and mt.group(2).strip() in TIER else (wm.group(1) if wm else None)
    new = cohort_histogram(word) if word else None
    if new and new != m.group(0):
        n_hist += 1
        if not a.dry_run:
            open(p, "w", encoding="utf-8").write(h[:m.start()] + new + h[m.end():])
print(f"{'would redraw' if a.dry_run else 'redrew'} {n_hist} cohort histogram(s) from the study rows")


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
    # 2026-11-01: the replacement writes "across our", so matching only "across a" froze the number after its first run
    # (CI blocked when the study grew 1,879 -> 1,883).
    h2 = re.sub(r"across (?:a|our) (?:763-PDUFA cohort \(2024-26\)|[\d,]+-decision run-up study \(\d{4}-\d\d\))",
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
