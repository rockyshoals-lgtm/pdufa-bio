# -*- coding: utf-8 -*-
"""migrate_mined_presenters.py -- repair conference_presenters_mined.csv's header drift.

THE DEFECT (found 2026-08-22)
conference_presenter_miner.py appends with csv.DictWriter(fieldnames=COLS) but writes a header
only when the file does not yet exist. COLS grew to 15 columns -- edition_year, confidence, form
were added for the edition gate -- while the file on disk still carried the original 12-column
header. So every row mined since then was written with 15 values under a 12-name header: read
back with DictReader, the three new values fall into the restkey and `confidence` reads as
absent. build_conferences.py publishes a mined row ONLY when confidence == "high", so the entire
mined pipeline had been silently unpublishable. 145 rows mined, 0 publishable, no error anywhere.

Same shape as the incidents the red team keeps finding: the failure produced fewer rows instead
of a complaint.

THE REPAIR
Rewrite the file with the full COLS header. Rows that already carry 15 values keep them (their
extras are recovered from the restkey in COLS order). Rows written under the old 12-column
format get empty strings for the three new columns -- which the gate then treats as
not-high-confidence, i.e. still unpublished. Nothing becomes publishable by migration alone;
only a fresh mine can produce a high-confidence row. That is the conservative direction.

    python migrate_mined_presenters.py [--dry-run]
"""
import argparse, csv, io, os, shutil, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "catalysts_out", "conference_presenters_mined.csv")
from conference_presenter_miner import COLS


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(P):
        print("SKIP: no mined file")
        return 0

    # POSITIONAL recovery, not restkey. The three new columns are inserted at index 7, not
    # appended, so DictReader's restkey holds the TAIL of the row (filing_url onward shifted by
    # three) rather than the new fields. A first attempt using restkey wrote matched_sentence
    # into `confidence` -- caught by reading the result back before trusting it. Map each row by
    # its WIDTH: 15 values are in COLS order, 12 are in the old header's order.
    src = os.path.join(HERE, "catalysts_out", "conference_presenters_mined.csv.bak_headerfix")
    src = src if os.path.exists(src) else P
    with io.open(src, encoding="utf-8-sig", newline="") as f:
        raw = list(csv.reader(f))
    header, body = raw[0], raw[1:]
    rows = []
    for row in body:
        if len(row) == len(COLS):
            rows.append(dict(zip(COLS, row)))
        elif len(row) == len(header):
            rows.append(dict(zip(header, row)))
        else:
            rows.append(dict(zip(COLS, row + [""] * (len(COLS) - len(row)))))
    print(f"header on disk : {len(header)} cols")
    print(f"miner emits    : {len(COLS)} cols")
    missing = [c for c in COLS if c not in header]
    if not missing:
        print("PASS: header already matches the miner -- nothing to migrate")
        return 0
    print(f"missing        : {missing}")

    out = [{c: (r.get(c) or "") for c in COLS} for r in rows]
    recovered = sum(1 for r in out if r.get("confidence"))
    print(f"rows           : {len(out)} ({recovered} carry a confidence value after recovery)")

    if a.dry_run:
        print("DRY RUN -- not written")
        return 0
    shutil.copy2(P, P + ".bak_headerfix")
    with io.open(P, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)
    hi = sum(1 for r in out if (r.get("confidence") or "").lower() == "high")
    print(f"rewrote with {len(COLS)}-col header; {hi} row(s) now read as high confidence")
    return 0


if __name__ == "__main__":
    sys.exit(main())
