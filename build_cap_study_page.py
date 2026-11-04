# -*- coding: utf-8 -*-
"""build_cap_study_page.py -- /research/pdufa-stock-run-up-by-market-cap from the living run-up study.

2026-11-03: the page was a frozen "763 FDA decisions (2024-26)" cohort written in September with no builder, while
the run-up study kept growing (and 97 of its rows had no tier until backfill_runup_mcap_tier.py). It now recomputes
from pdufa_runup_bifrost_v2.csv every run, for every 2024-onward decision with a tier:

  reaction  = the larger of |decision-day move| (post_1d) and |next-day move| ((1+post_2d)/(1+post_1d)-1), the
              definition the page always stated (the FDA can announce either side of the close)
  run-up    = T-120 -> T-1 close-to-close (the study's T-120_T-1 field), where the row has the path

The two charts, the counts in the title/description/lede/source/citation and the size-ratio sentence are rewritten;
the caveat sentences are only kept when the new numbers still say what they say. Idempotent.

    python build_cap_study_page.py [--dry-run]
"""
import argparse
import csv
import html
import io
import os
import re
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "pdufa_site_src", "research", "pdufa-stock-run-up-by-market-cap", "index.html")
CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
FROM = "2024-01-01"
TIERS = [("Nano (<$50M)", "Nano &lt;$50M"), ("Micro ($50M-$300M)", "Micro $50-300M"), ("Small ($300M-$2B)", "Small $0.3-2B"),
         ("Mid ($2B-$10B)", "Mid $2-10B"), ("Large (>$10B)", "Large &gt;$10B")]


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def stats():
    rows = list(csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")))
    reac, run, last = {}, {}, ""
    for r in rows:
        d = r["pdufa_date"][:10]
        if d < FROM or r.get("mcap_tier") not in dict(TIERS):
            continue
        p1, p2 = f(r.get("post_1d")), f(r.get("post_2d"))
        if p1 is None or p2 is None:
            continue
        nd = ((1 + p2 / 100) / (1 + p1 / 100) - 1) * 100
        reac.setdefault(r["mcap_tier"], []).append(max(abs(p1), abs(nd)))
        t = f(r.get("T-120_T-1"))
        if t is not None:
            run.setdefault(r["mcap_tier"], []).append(t * 100)
        last = max(last, d)
    return ({k: (st.median(v), len(v)) for k, v in reac.items()},
            {k: (st.median(v), len(v)) for k, v in run.items()}, last)


def bars(vals, colour_neg="#ff7a72", base_pos=False):
    """vals: [(label, value, n)] -> the page's SVG geometry."""
    out = ['<svg viewBox="0 0 640 250" role="img" style="width:100%;display:block;aspect-ratio:640/250;background:#071528;'
           'border:1px solid #1a3358;border-radius:12px">']
    if base_pos:
        base, span = 204.0, 158.0
        scale = span / max(v for _, v, _ in vals)
    else:
        base = 166.0
        pos = max([v for _, v, _ in vals if v > 0] or [1])
        scale = 120.0 / pos
    out.append(f'<line x1="30" y1="{base:.0f}" x2="610" y2="{base:.0f}" stroke="#294d80" stroke-width="1"/>')
    for i, (lab, v, n) in enumerate(vals):
        x = 36.0 + 116.8 * i
        cx = x + 50.4
        h = abs(v) * scale
        txt = f"{v:.1f}%" if base_pos else f"{v:+.1f}%"
        if v >= 0:
            y = base - h
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="100.8" height="{h:.1f}" rx="3" fill="#e3ba5e"/>')
            out.append(f'<text x="{cx:.1f}" y="{y - 7:.1f}" fill="#f2f6fc" font-size="13" font-weight="700" text-anchor="middle">{txt}</text>')
        else:
            h = min(h, 88.0)
            out.append(f'<rect x="{x:.1f}" y="{base:.1f}" width="100.8" height="{h:.1f}" rx="3" fill="{colour_neg}"/>')
            out.append(f'<text x="{cx:.1f}" y="{base + h + 15:.1f}" fill="#f2f6fc" font-size="13" font-weight="700" text-anchor="middle">{txt}</text>')
        out.append(f'<text x="{cx:.1f}" y="226" fill="#cdd9eb" font-size="10.5" text-anchor="middle">{lab}</text>')
        out.append(f'<text x="{cx:.1f}" y="240" fill="#94a9c9" font-size="10" text-anchor="middle">n={n:,}</text>')
    out.append("</svg>")
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    reac, run, last = stats()
    N = sum(n for _, n in reac.values())
    y1 = last[2:4]
    rv = [(lab, reac[k][0], reac[k][1]) for k, lab in TIERS if k in reac]
    uv = [(lab, run[k][0], run[k][1]) for k, lab in TIERS if k in run]
    for lab, v, n in rv:
        print(f"  reaction {lab:16s} {v:5.1f}%  n={n}")
    for lab, v, n in uv:
        print(f"  run-up   {lab:16s} {v:+6.1f}%  n={n}")
    doc = io.open(PAGE, encoding="utf-8").read()
    svgs = list(re.finditer(r'<svg viewBox="0 0 640 250".*?</svg>', doc, re.S))
    if len(svgs) != 2:
        print("::warning::chart markup not found; nothing written"); return 0
    new = doc[:svgs[0].start()] + bars(rv, base_pos=True) + doc[svgs[0].end():svgs[1].start()] + bars(uv) + doc[svgs[1].end():]
    span = f"2024-{y1}"
    new = re.sub(r"[\d,]+ FDA Decisions \(2024-\d\d\)", f"{N:,} FDA Decisions ({span})", new)
    new = re.sub(r"across [\d,]+ FDA decisions \(2024-20\d\d\)", f"across {N:,} FDA decisions (2024-20{y1})", new)
    new = re.sub(r"across <b>[\d,]+</b> decisions", f"across <b>{N:,}</b> decisions", new)
    new = re.sub(r"(PDUFA stock <span class='g'>run-up by market cap</span>) \(2024-\d\d\)", rf"\1 ({span})", new)
    new = re.sub(r"internal cohort of [\d,]+ FDA decisions \(2024-\d\d\) with complete price data",
                 f"run-up study: {N:,} FDA decisions ({span}) with a market-cap tier and decision-day prices", new)
    new = re.sub(r"\(2024-20\d\d\)</a>?, n=[\d,]+ FDA decisions", f"(2024-20{y1}), n={N:,} FDA decisions", new)
    new = re.sub(r"\(2024-20\d\d\), n=[\d,]+ FDA decisions", f"(2024-20{y1}), n={N:,} FDA decisions", new)
    new = re.sub(r"\(2024-20\d\d\)</i>, n=[\d,]+ FDA decisions", f"(2024-20{y1})</i>, n={N:,} FDA decisions", new)
    # the /research hub's card, ItemList description and FAQ quote the same count
    hub = os.path.join(os.path.dirname(os.path.dirname(PAGE)), "index.html")
    if os.path.exists(hub):
        h = io.open(hub, encoding="utf-8").read()
        h2 = re.sub(r"PDUFA stock run-up by market cap \([\d,]+ decisions\)",
                    f"PDUFA stock run-up by market cap ({N:,} decisions)", h)
        h2 = re.sub(r"[\d,]+ FDA decisions \(2024-20\d\d\) with pre-decision stock run-up by market-cap cohort",
                    f"{N:,} FDA decisions (2024-20{y1}) with pre-decision stock run-up by market-cap cohort", h2)
        if h2 != h and not a.dry_run:
            io.open(hub, "w", encoding="utf-8").write(h2)
            print("  /research hub: market-cap study count updated")
    ratio = rv[0][1] / rv[-1][1] if rv and rv[-1][1] else 0
    new = re.sub(r"a <b>nano-cap swings about \d+&times; more than a large-cap</b>",
                 f"a <b>nano-cap swings about {round(ratio):d}&times; more than a large-cap</b>", new)
    # caveat sentences stay only while they are still true
    u = {lab.split()[0]: v for lab, v, _ in uv}
    if not (u.get("Mid", 0) > u.get("Small", 0)):
        new = new.replace("mid-caps run up more than small-caps, and ", "")
    if not (u.get("Nano", 0) < 0):
        new = new.replace(", and <b>nano-caps have historically drifted <i>down</i></b> into the date", "")
    if new != doc and not a.dry_run:
        io.open(PAGE, "w", encoding="utf-8").write(new)
    print(f"/research/pdufa-stock-run-up-by-market-cap: n={N:,} ({span})" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
