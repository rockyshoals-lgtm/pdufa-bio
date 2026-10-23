# -*- coding: utf-8 -*-
"""CI guard: run-up study figures are the current ones on every surface, and every indexable decision page carries
its NewsArticle block (audit 2026-10-22).

Fails when
  * any rendered page still quotes the retired "763-PDUFA cohort" or a placeholder "±?%";
  * an event or decision page's "Cohort decision-day move (history)" chip differs from runup_study_stats.json for
    the page's stated tier, or a page states a chip with no recognised tier;
  * the home board's cohort chips differ from the stats;
  * an indexable /fda-decision page lacks the NewsArticle block, or its datePublished is after its dateModified.
Plants: PLANT_RUNUP=chip (pretends /pdufa/INO's chip reads "±7% median"), =home (Mid chip "2.2%"),
        =article (drops GSK-2026-10-20's NewsArticle). Each must FAIL.

    python tests/test_runup_figures_current.py
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
PLANT = os.environ.get("PLANT_RUNUP", "")


def main():
    s = json.load(io.open(os.path.join(HERE, "runup_study_stats.json"), encoding="utf-8"))
    want = {k.split(" ")[0]: f"{v['median_abs_pct']:.1f}% median (n={v['n']:,})" for k, v in s["cohort_abs_move"].items()}
    fails = []
    for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
        rel = p[len(SITE):].replace("\\", "/")
        if rel.startswith("/_"):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "763-PDUFA cohort" in doc:
            fails.append(f"{rel}: quotes the retired 763-PDUFA cohort")
        if re.search(r"(?:±|\\u00b1|&plusmn;)\?%", doc):
            fails.append(f"{rel}: placeholder ±?% rendered")
        chip = re.search(r"<span>Cohort decision-day move \(history\)</span><b>([^<]*)</b>", doc)
        if chip and (rel.startswith("/pdufa/") or rel.startswith("/fda-decision/")):
            val = chip.group(1)
            if PLANT == "chip" and rel == "/pdufa/INO/index.html":
                val = "±7% median"
            tier = re.search(r"<span>Market-cap tier</span><b>([^<]*)</b>", doc)
            t = tier.group(1).strip() if tier else ""
            if t not in want:
                fails.append(f"{rel}: cohort chip '{val}' with no recognised tier ('{t}')")
            elif val != want[t]:
                fails.append(f"{rel}: cohort chip '{val}', study says '{want[t]}' for {t}")
    home = io.open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
    pairs = re.findall(r'<em class="cap">(Nano|Micro|Small|Mid|Large)</em>.*?<span class="coh">\s*([\d.]+%)<i>cohort',
                       home, re.S)
    if not pairs:
        fails.append("/: home board cohort chips not found (markup changed?)")
    for t, c in pairs:
        if PLANT == "home" and t == "Mid":
            c = "2.2%"
        if c != want[t].split(" ")[0]:
            fails.append(f"/: home board {t} chip {c}, study says {want[t].split(' ')[0]}")
    for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if '<meta name="robots" content="noindex' in doc:
            continue
        if PLANT == "article" and slug == "GSK-2026-10-20":
            doc = re.sub(r'<script type="application/ld\+json" id="ld-article">.*?</script>', "", doc, flags=re.S)
        m = re.search(r'<script type="application/ld\+json" id="ld-article">(.*?)</script>', doc, re.S)
        if not m:
            fails.append(f"/fda-decision/{slug}: no NewsArticle block")
            continue
        art = json.loads(m.group(1))
        if not (art.get("headline") and art.get("publisher") and art.get("datePublished")):
            fails.append(f"/fda-decision/{slug}: NewsArticle lacks headline/publisher/datePublished")
        elif art["datePublished"] > art.get("dateModified", art["datePublished"]):
            fails.append(f"/fda-decision/{slug}: datePublished {art['datePublished']} after dateModified")
    if fails:
        print(f"FAIL: {len(fails)} run-up figure / article schema failure(s):")
        for f in fails[:25]:
            print("   " + f)
        return 1
    print(f"OK -- cohort figures match the {s['n_events']:,}-decision study everywhere; every indexable decision page "
          f"carries its NewsArticle block.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
