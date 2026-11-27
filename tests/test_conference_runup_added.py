# -*- coding: utf-8 -*-
"""Guard: the company-release conference rows sit BESIDE the curated study, never inside it, and every figure the
study page shows for them recomputes from the rows.

2026-11-27: David approved adding the red-teamed company-release rows to the study. The study page's own rule (after
the July 2026 revert of an SEC-crawler merge that re-weighted the cap mix) is that a new sampling frame is published
side by side, never folded into the headline in the same step. So:
  1. conf_study/conference_runup_PUBLISHED.csv holds no company-release row (the headline sample is unchanged).
  2. added_rows on SYNTHETIC cache rows: a pending, held or window-missing row is left out; a row the study already
     holds is left out; the same presentation from both caches is shown once; the tier follows the study thresholds.
  3. When the page is built: the CSTUDYADD block follows CSTUDYX, and its counts and medians equal a recomputation
     from the published CSV of added rows; every row there has an https release link and a closed window.

    python tests/test_conference_runup_added.py   (PLANT=1 plants a bad figure; the guard must fail)
"""
import csv
import io
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import conference_runup_added as A  # noqa: E402

fails = []


def check(ok, msg):
    if not ok:
        fails.append(msg)


# 1. the headline sample is untouched
study = A.study_rows()
check(not any(r.get("src") == "company_release" or r.get("release_url") for r in study),
      "a company-release row is inside conference_runup_PUBLISHED.csv; it must stay beside the study")

# 2. synthetic rows (tickers invented)
W = {w: "1.0" for w in A.WINDOWS}
fake_study = [{"ticker": "ZZQA", "conf": "ASCO", "year": "2025"}]
caches = {
    "add": {"rows": {
        "OK1": dict(W, ticker="ZZQB", conf="ESMO", year="2026", anchor="2026-10-18", status="complete",
                    d_minus_1="2026-10-16", release_url="https://example.com/a"),
        "PEND": dict(W, ticker="ZZQC", conf="ASH", year="2026", anchor="2026-12-06", status="pending"),
        "HELD": dict(W, ticker="ZZQD", conf="ASH", year="2026", anchor="2026-12-06", status="check"),
        "GAP": dict(W, ticker="ZZQE", conf="ESMO", year="2026", anchor="2026-10-18", status="complete", post_10d=""),
        "IN": dict(W, ticker="ZZQA", conf="ASCO", year="2025", anchor="2025-06-01", status="complete"),
    }},
    "backfill": {"rows": {
        "DUP": dict(W, ticker="ZZQB", conf="ESMO", year="2026", anchor="2026-10-19", status="complete"),
        "OK2": dict(W, ticker="ZZQF", conf="AACR", year="2024", anchor="2024-04-07", status="complete",
                    d_minus_1="2024-04-05", conf_full="AACR Annual Meeting 2024 2024"),
    }},
}
tmp = tempfile.mkdtemp()
saved = A.CACHES
A.CACHES = []
for name, d in caches.items():
    p = os.path.join(tmp, f"_conference_runup_{name}.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(d))
    A.CACHES.append(p)
rows, left, mc = A.added_rows(fake_study, lookup=lambda t, d: {"ZZQB": 120e6, "ZZQF": 5e9}.get(t))
A.CACHES = saved
got = sorted(r["ticker"] for r in rows)
check(got == ["ZZQB", "ZZQF"], f"synthetic: expected ZZQB and ZZQF only, got {got}")
check(left == {"window not closed or held": 3, "already in the study": 1, "duplicate": 1}, f"synthetic left-out {left}")
tiers = {r["ticker"]: r["cap_tier_pit"] for r in rows}
check(tiers == {"ZZQB": "micro", "ZZQF": "mid"}, f"synthetic tiers {tiers}")
check(all(r["conf_full"] != "AACR Annual Meeting 2024 2024" for r in rows), "a doubled year in conf_full was kept")
check(A.tier(49e6) == "nano" and A.tier(300e6) == "small" and A.tier(10e9) == "large", "tier thresholds moved")

# 3. the built page, when present
page = io.open(A.PAGE, encoding="utf-8", errors="replace").read() if os.path.exists(A.PAGE) else ""
if A.B in page and os.path.exists(A.CSV_OUT):
    pub = list(csv.DictReader(l for l in io.open(A.CSV_OUT, encoding="utf-8") if not l.startswith("#")))
    check(page.index(A.B) > page.index(A.AFTER), "the CSTUDYADD block does not follow the CSTUDYX block")
    check(all(r["release_url"].startswith("https://") for r in pub), "an added row has no https release link")
    check(all(A.num(r.get(w)) is not None for r in pub for w in A.WINDOWS), "an added row has an open window")
    keys = {(r["ticker"], r["conf"], r["year"]) for r in study}
    check(not any((r["ticker"], r["conf"], r["year"]) in keys for r in pub), "an added row repeats a study row")
    blk = page[page.index(A.B):page.index(A.E)]
    if os.environ.get("PLANT"):
        blk = blk.replace(f"{len(pub):,} more presentations", f"{len(pub) + 1:,} more presentations")
    check(f"{len(pub):,} more presentations" in blk, f"the block does not state the {len(pub)} published rows")
    check(f"not in the {len(study):,}-row figures" in blk, "the block does not say the study figures exclude these rows")
    for w, label in A.SHOWN:
        for name, rs in (("added", pub), ("together", study + pub)):
            m = A.medians(rs)[w]
            cell = f"<td>{m['n']:,}</td><td>{A.fmt(m['median'])}</td>"
            check(cell in blk, f"{label}: {name} n/median {m['n']}/{A.fmt(m['median'])} not on the page")
else:
    print("  (study page not built with the company-release block here; page checks skipped)")

if fails:
    print("FAIL conference run-up added rows:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("OK -- company-release conference rows sit beside the study; every shown figure recomputes from its rows")
