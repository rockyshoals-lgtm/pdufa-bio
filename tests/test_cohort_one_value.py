# -*- coding: utf-8 -*-
"""test_cohort_one_value.py -- one cohort, one count and one median, wherever a page states them.

Design red team 2026-11-18 (change 6). /pdufa/LLY's cohort card said "840 large-cap decisions" with "a median
decision-day move of 1.0% in either direction", then drew a histogram captioned "n=790 · median +0.0% · 50% up": a July
one-off cut that no rebuild refreshed, with a second count and a second, differently defined "median". Small-cap pages
said 257 and 274. refresh_cohort_figures.py now redraws the histogram from the study rows behind the chip. This fails if,
on any /pdufa/ page:

  1. the histogram's n differs from the chip's n or the lead sentence's count, or from runup_study_stats.json;
  2. the histogram's median differs from the chip's median, or is not labelled as a median size (up or down);
  3. the histogram's bars do not add up to its n, or a bar's count differs from the study rows for that tier;
  4. the histogram names a tier other than the page's market-cap tier.

    python tests/test_cohort_one_value.py
"""
import collections
import csv
import glob
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
KEY = {"nano": "Nano (<$50M)", "micro": "Micro ($50M-$300M)", "small": "Small ($300M-$2B)",
       "mid": "Mid ($2B-$10B)", "large": "Large (>$10B)"}
EDGES = [-30, -15, -7, -3, 3, 7, 15, 30]


def bin_of(x):
    i = 0
    while i < len(EDGES) and x >= EDGES[i]:
        i += 1
    return i


def main():
    stats = json.load(open(os.path.join(HERE, "runup_study_stats.json"), encoding="utf-8")).get("cohort_abs_move", {})
    want = collections.defaultdict(lambda: [0] * 9)
    for r in csv.DictReader(open(os.path.join(HERE, "pdufa_runup_bifrost_v2.csv"), encoding="utf-8-sig", errors="replace")):
        try:
            v = float(r.get("post_1d"))
        except (TypeError, ValueError):
            continue
        if r.get("mcap_tier"):
            want[r["mcap_tier"]][bin_of(v)] += 1

    bad = []
    hists = 0
    for p in sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))):
        slug = "/pdufa/" + os.path.basename(os.path.dirname(p))
        doc = open(p, encoding="utf-8", errors="replace").read()
        blk = re.search(r'<div class="coh-dist-v1".*?<!--PH:E-->', doc, re.S)
        if not blk:
            continue
        blk = blk.group(0)
        hists += 1
        head = re.search(r"Decision-day move &middot; ([a-z]+)-cap cohort</span><span[^>]*>n=([\d,]+) &middot; "
                         r"median size (\d+\.\d)% &middot; (\d+)% up<", blk)
        if not head:
            bad.append(f"{slug}: histogram header is not 'n=N · median size X% · Y% up'")
            continue
        word, n, med = head.group(1), int(head.group(2).replace(",", "")), head.group(3)
        tier = re.search(r"<span>Market-cap tier</span><b>([A-Za-z]+)</b>", doc)
        if tier and tier.group(1).lower() in KEY and tier.group(1).lower() != word:
            bad.append(f"{slug}: histogram is the {word}-cap cohort, the page's tier is {tier.group(1)}")
        st = stats.get(KEY.get(word, ""), {})
        if st and n != st.get("n"):
            bad.append(f"{slug}: histogram n={n}, the study's {word}-cap n={st.get('n')}")
        if st and med != f"{st.get('median_abs_pct'):.1f}":
            bad.append(f"{slug}: histogram median size {med}%, the study's {st.get('median_abs_pct'):.1f}%")
        chip = re.search(r"Cohort decision-day move \(history\)</span><b>(\d+\.\d)% median \(n=([\d,]+)\)", doc)
        if chip and (chip.group(1), int(chip.group(2).replace(",", ""))) != (med, n):
            bad.append(f"{slug}: chip says {chip.group(1)}% (n={chip.group(2)}), histogram {med}% (n={n})")
        lead = re.search(r"median decision-day move of (\d+\.\d)% in either direction \(([\d,]+) \w+-cap decisions", doc)
        if lead and (lead.group(1), int(lead.group(2).replace(",", ""))) != (med, n):
            bad.append(f"{slug}: card text says {lead.group(1)}% across {lead.group(2)}, histogram {med}% (n={n})")
        for svg in re.findall(r"<svg.*?</svg>", blk, re.S):
            counts = [int(m.group(1).replace(",", "")) for m in re.finditer(r"<title>[^<]*: ([\d,]+) of [\d,]+ \(", svg)]
            ofs = {int(x.replace(",", "")) for x in re.findall(r"<title>[^<]*: [\d,]+ of ([\d,]+) \(", svg)}
            if len(counts) != 9 or sum(counts) != n or ofs != {n}:
                bad.append(f"{slug}: histogram bars sum to {sum(counts)} over {len(counts)} bins, caption n={n}")
            elif KEY.get(word) in want and counts != want[KEY[word]]:
                bad.append(f"{slug}: histogram bars {counts}, study rows give {want[KEY[word]]}")
    print(f"{hists} cohort histogram(s) checked")
    if bad:
        for b in bad[:30]:
            print("  FAIL " + b)
        if len(bad) > 30:
            print(f"  ... and {len(bad) - 30} more")
        print("  fix: python runup_study_stats.py && python refresh_cohort_figures.py")
        sys.exit(1)
    print("  PASS: each cohort card states one count and one median, from the study")


if __name__ == "__main__":
    main()
