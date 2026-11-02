# -*- coding: utf-8 -*-
"""sync_screener_data.py -- /screener renders from the dataset, not from a July snapshot.

Red team 2026-11-01: /screener's table is drawn client-side from an inline `const DATA=[...]`, and that array had
not changed since the site's first commit (2026-07-25). 395 rows, 31 of them "Upcoming" with dates already past
(AGIO on Nov 1 after the goal moved to Feb 2027, IGALMI under BioXcel after the sale to Teva, decided approvals
still listed as pending). No step in the workflow ever rewrote it.

This rewrites DATA from api/v1/dataset.mjs every run: same keys the page's JS reads (t, d, name, type, ta, cap, st,
url), names cut at 50 characters as before, rows from 150 days back onward. Idempotent.

    python sync_screener_data.py [--dry-run]
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "screener", "index.html")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
sys.path.insert(0, HERE)
try:
    from site_dates import eastern_today
except Exception:  # noqa: BLE001
    eastern_today = dt.date.today


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    floor = (eastern_today() - dt.timedelta(days=150)).isoformat()
    out = []
    for r in rows:
        d = str(r.get("d") or "")
        if not d or d < floor or r.get("type") not in ("PDUFA", "Readout", "Conference", "AdComm"):
            continue
        out.append({"t": r.get("t") or "", "d": d, "name": str(r.get("name") or "")[:50], "type": r.get("type"),
                    "ta": r.get("ta") or "", "cap": r.get("cap") or "", "st": r.get("st") or "",
                    "url": r.get("url") or f"/ticker/{r.get('t')}"})
    out.sort(key=lambda x: (x["d"], x["t"]))
    doc = io.open(PAGE, encoding="utf-8").read()
    m = re.search(r"const DATA=(\[.*?\]);", doc, re.S)
    if not m:
        print("::warning::/screener: const DATA not found; nothing written")
        return 0
    new = doc[:m.start(1)] + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + doc[m.end(1):]
    if new != doc and not a.dry_run:
        io.open(PAGE, "w", encoding="utf-8").write(new)
    print(f"/screener DATA: {len(out)} row(s) from the dataset (from {floor})" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
