# -*- coding: utf-8 -*-
"""CI guard: the run-up study's size is stated once, from runup_study_stats.json, everywhere.

Found 2026-09-19 (task #82). One dataset, five published sizes: 1,849 (home), 1,827 (/decisions,
/pricing, /vktx), 1,786 (/developers, the per-event T-120 series) and 1,888 (/fda-approval-rate,
"n=1,888, 73.5% first-cycle"). Four were typed by hand in July and never moved while the study grew
every night. The stats file already owned the home board and /runup-by-year; sync_runup_study_size.py
now owns the rest, and this asserts the RENDER on every indexable page.

Two statistics are legitimate:
  n_events          -- how many PDUFA decisions the study holds
  t120_coverage_n   -- how many of them have the full daily T-120 -> T+5 price path
Anything else described as the run-up study / run-up dataset / T-120 series is a drift.

    python tests/test_runup_study_size_one_owner.py
"""
import glob
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
STATS = os.path.join(HERE, "runup_study_stats.json")
SKIP = re.compile(r"[\\/]_[a-z]+bak|[\\/]_pdufa_")
# a study count near one of these phrases must be an owned number
# "conference run-up study" is a different study (1,425 presentations) and is excluded by the lookbehind
NEAR = re.compile(r"(?<!conference )(?<!Conference )(run-up study|run-up dataset|run-up series|T-120 ?(?:&rarr;|→|->) ?T\+5|events in the run-up study)", re.I)


def text(doc):
    doc = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", doc)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", doc)))


def main():
    s = json.load(io.open(STATS, encoding="utf-8"))
    n, t120, rate = int(s["n_events"]), int(s["t120_coverage_n"]), float(s["approval_rate"])
    ok_counts = {f"{n:,}", f"{t120:,}"}
    fails = []

    # 1. anchored surfaces
    anchors = {
        "index.html": [rf"{n:,} events in the run-up study"],
        "decisions/index.html": [rf"{n:,} PDUFA decisions, 2020 to \d{{4}}, {rate:.1f}% approved"],
        "pricing.html": [rf"the {t120:,}-event T-120→T\+5 daily data"],
        "developers/index.html": [rf"price path for {t120:,} FDA decisions"],
        "vktx/index.html": [rf"run-up study \({n:,} FDA decisions\)"],
        "fda-approval-rate/index.html": [rf"{rate:.1f}% approvals / \(approvals \+ CRLs\), all review cycles: our universe, n={n:,}",
                                         rf"Our figure: {n:,} FDA decisions on listed biotechs"],
        "runup-by-year/index.html": [rf"PDUFA events {n:,}"],
    }
    for rel, pats in anchors.items():
        p = os.path.join(SITE, rel)
        if not os.path.exists(p):
            continue
        t = text(io.open(p, encoding="utf-8", errors="replace").read())
        for pat in pats:
            if not re.search(pat, t):
                fails.append(f"/{rel.replace('/index.html', '').replace('.html', '')}: expected '{pat}'")

    # 2. census: no other study size anywhere near the study's name
    pages = 0
    for f in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        if SKIP.search(f):
            continue
        doc = io.open(f, encoding="utf-8", errors="replace").read()
        if re.search(r'name="robots"[^>]*noindex', doc[:4000]):
            continue
        pages += 1
        t = text(doc)
        for m in NEAR.finditer(t):
            win = t[max(0, m.start() - 80): m.end() + 80]
            for c in re.findall(r"\b\d{1,2},\d{3}\b", win):
                if c not in ok_counts and c != "1,752":      # 1,752 = the readout study, named beside it
                    rel = os.path.relpath(f, SITE).replace("\\", "/")
                    fails.append(f"{rel}: '{c}' near '{m.group(0)}' -- study holds {n:,} (T-120 path: {t120:,})")
                    break

    if fails:
        print(f"FAIL: run-up study size drift on {len(fails)} surface(s) (owner: runup_study_stats.json "
              f"n_events={n:,}, t120_coverage_n={t120:,}):")
        for x in sorted(set(fails))[:20]:
            print("   " + x)
        print("\n   Run sync_runup_study_size.py (and the page's builder). One dataset, one number.")
        return 1
    print(f"OK -- run-up study size {n:,} (T-120 path {t120:,}, approval {rate:.1f}%) consistent on "
          f"{len(anchors)} anchored surfaces and across {pages} indexable pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
