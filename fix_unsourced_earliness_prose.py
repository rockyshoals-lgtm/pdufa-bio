# -*- coding: utf-8 -*-
"""Remove earliness claims from hand-written prose where the goal date is not a sourced day.

Audit 09-14 P0-C named BAYRY. The new cross-surface guard found FOUR MORE the audit did not
reach, and they are the same rows the 09-10 pass downgraded:

  /fda-decision/PFE-2026-08-27   "34 days early"   goal was a sponsor-stated QUARTER
  /fda-decision/ROIV-2026-08-27  "34 days early"   same event, other ticker
  /fda-decision/PTGX-2026-08-28  "33 days early"   goal was a sponsor-stated QUARTER
  /fda-decision/IONS-2026-09-03  "19 days early"   goal date carries no source_url

On 09-10 these exact four margins were removed from /research/fda-decision-timing because a
quarter-end placeholder manufactures the largest possible earliness. They stayed on the decision
pages, in prose a generator does not own. So the number the statistic refuses to use is still
the number the page tells a reader -- and the page tells it in a sentence like "The PDUFA goal
date was September 30, 2026 ... The FDA approved on August 27, 2026, 34 days early."

The generators are now gated (site_windows.earliness_allowed). This cleans the prose they cannot
reach, and states why the figure is absent rather than silently deleting it -- a missing number
with no explanation invites someone to "fix" it back.

    python fix_unsourced_earliness_prose.py [--dry-run]
"""
import argparse
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_windows import earliness_allowed, window_label  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = "pdufa_site_src"
WHY = ("We do not state how early it was: the goal date we hold for this application is not a "
       "sourced calendar day, and an unsourced goal cannot measure earliness.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
                  encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    blocked = {}
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st") or "").lower() != "decided":
            continue
        if not earliness_allowed(r):
            blocked[(str(r.get("t") or "").upper(), str(r.get("dcd") or "")[:10])] = r

    n = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"^([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug)
        if not m or (m.group(1), m.group(2)) not in blocked:
            continue
        row = blocked[(m.group(1), m.group(2))]
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        orig = doc

        # The prose is hand-written and says this four different ways. Cover the CLAUSE
        # generally rather than chasing each sentence:
        #   "..., 34 days early."      "..., 33 days early, under Priority Review."
        #   "... - 33 days before its September 30 PDUFA goal date - ..."
        doc = re.sub(r",\s*\d+\s+days?\s+early\.", ". " + WHY, doc)
        doc = re.sub(r",\s*\d+\s+days?\s+early(?=[,;])", "", doc)
        doc = re.sub(r"\s*\(\s*\d+\s+days?\s+early\s*\)", "", doc)
        doc = re.sub(r",\s*\d+\s+[Dd]ays?\s+[Ee]arly(?=\s*\|)", "", doc)
        doc = re.sub(r",\s*\d+\s+days?\s+before its [^.]{0,60}goal date", "", doc)
        # PTGX's lede uses hyphen delimiters, not commas:
        #   "approved on August 28, 2026 - 33 days before its September 30 PDUFA goal date - as"
        doc = re.sub(r"\s*-\s*\d+\s+days?\s+before its [^-<]{0,60}?goal date\s*-\s*", " - ", doc)
        doc = re.sub(r"\s*—\s*\d+\s+days?\s+before its [^—<]{0,60}?goal date\s*—\s*",
                     " - ", doc)

        # "The PDUFA goal date was September 30, 2026" -- that day is the withdrawn one
        lab = window_label(row)
        doc = re.sub(r"The PDUFA (?:goal date|target action date) was "
                     r"[A-Z][a-z]+ \d{1,2},? \d{4}",
                     (f"The sponsor guided this decision to {lab}" if lab and
                      not re.match(r"^\d{4}-\d{2}-\d{2}$", lab)
                      else "We hold no sourced PDUFA goal date for this application"), doc)

        if doc != orig:
            n += 1
            print(f"  /fda-decision/{slug}")
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(doc)

    # NVCR: a quarter-precision row rendered as a month. Its own note says "company guides
    # decision in Q4 2026 ... date is the quarter midpoint", so "November 2026" over-claims.
    q = os.path.join(SITE, "pdufa", "NVCR-ttfields-therapy", "index.html")
    if os.path.isfile(q):
        d = io.open(q, encoding="utf-8", errors="replace").read()
        if "November 2026 (window)" in d:
            d = d.replace("November 2026 (window)", "Q4 2026")
            print("  /pdufa/NVCR-ttfields-therapy: 'November 2026 (window)' -> 'Q4 2026' "
                  "(the row is quarter precision; the sponsor guided Q4)")
            n += 1
            if not a.dry_run:
                io.open(q, "w", encoding="utf-8").write(d)

    print(f"\n{n} page(s) cleaned" + ("   (--dry-run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
