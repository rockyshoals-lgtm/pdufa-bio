# -*- coding: utf-8 -*-
"""rescore_mined_presenters.py -- re-apply the CURRENT edition rule to already-mined rows.

Mined rows carry the confidence computed by whatever version of edition_ok() was running when
they were written. When that rule is tightened, old rows keep their old verdict and a row the
current rule would reject stays publishable forever -- the same "a stored judgement is trusted
after the rule that produced it changed" shape as the calendar's frozen decision links.

2026-08-22: the month-only branch of edition_ok() gained a filing-year test, because Amgen's
Q3-2025 earnings release ("presented at the AHA Scientific Sessions on November 8th") and
Autolus's December-2025 release ("to be presented at the ASH Annual Meeting in December") were
both scored high-confidence against the 2026 editions -- last year's filings announcing next
year's meetings. This re-scores every stored row against the live rule and demotes any that no
longer passes, so a tightened rule takes effect retroactively.

Demote only. A row is never promoted here: promotion needs the full context (forward phrasing,
verb proximity, form) that only a real mine has.

    python rescore_mined_presenters.py [--dry-run]
"""
import argparse, csv, io, os, shutil, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "catalysts_out", "conference_presenters_mined.csv")
from conference_presenter_miner import COLS, edition_ok


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(P):
        print("SKIP: no mined file")
        return 0
    rows = list(csv.DictReader(io.open(P, encoding="utf-8-sig")))

    demoted = []
    for r in rows:
        if (r.get("confidence") or "").lower() != "high":
            continue
        ok = edition_ok(r.get("matched_sentence", ""), r.get("conference", ""),
                        r.get("conference", ""), r.get("conf_start", ""),
                        r.get("filed", ""))
        if not ok:
            demoted.append(r)
            r["confidence"] = "low"

    print(f"high-confidence rows re-scored; {len(demoted)} demoted under the current rule")
    for r in demoted:
        print(f"   {r['ticker']:<6} {r['conference']:<8} edition {str(r['conf_start'])[:4]} "
              f"but filed {r.get('filed')}  -- {str(r.get('filing_url',''))[:70]}")
    if demoted and not a.dry_run:
        shutil.copy2(P, P + ".bak_rescore")
        with io.open(P, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLS)
            w.writeheader()
            w.writerows(rows)
        print("rewrote mined file")
    elif a.dry_run:
        print("DRY RUN -- not written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
