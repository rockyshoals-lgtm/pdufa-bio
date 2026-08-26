# -*- coding: utf-8 -*-
"""fix_duplicate_decisions_2026_08_26.py -- one FDA action, one decision page.

WHAT WAS WRONG
Chasing the calendar's page-vs-API gap (six audits) led to the actual cause, which was not a
counting bug: FOUR 2026 FDA actions each had TWO decision pages, at adjacent dates, both
unsourced. One page was created at the PDUFA GOAL date and another at the real ANNOUNCEMENT
date, and nothing reconciled them. That inflated the archive's count, split the record for each
event, and left `dcd` pointing at the goal date -- which is why mark_calendar_decided could not
link these rows (it looks for a decision page at dcd) and why the timing page excluded them.

VERIFIED AGAINST EACH COMPANY'S OWN RELEASE (2026-08-26)
    ACHV  CRL announced 2026-06-22   (goal was 06-20)  -> drop the 06-20 page
    ARQT  approved      2026-06-29   (goal was 06-29)  -> drop the 06-30 page
    LNTH  CRL announced 2026-06-26   (goal was 06-29)  -> drop the 06-29 page, 3 days EARLY
    UNCY  CRL announced 2026-06-30   (goal was 06-29)  -> drop the 06-29 page, 1 day late

Note what the corrected dates do to the headline question this site now answers: LNTH's CRL came
three days BEFORE its goal date and UNCY's came one day AFTER. Keeping the goal-dated duplicates
would have recorded both as landing exactly on the date, which is the very artefact the red team
flagged on the timing page.

WHAT THIS DOES
  1. deletes the wrong-dated duplicate page,
  2. removes its row from /decisions,
  3. corrects `dcd` on the dataset row to the verified announcement date.
The surviving pages are then re-published WITH their primary source by
decision_pages_2026_08_26.json, so they stop being "unsourced" and re-enter the timing sample.

Idempotent.

    python fix_duplicate_decisions_2026_08_26.py [--dry-run]
"""
import argparse, io, json, os, re, shutil, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")

# (ticker, duplicate page to remove, verified true announcement date)
DUPES = [("ACHV", "2026-06-20", "2026-06-22"),
         ("ARQT", "2026-06-30", "2026-06-29"),
         ("LNTH", "2026-06-29", "2026-06-26"),
         ("UNCY", "2026-06-29", "2026-06-30")]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    removed = rows_cut = 0
    listing = os.path.join(SITE, "decisions", "index.html")
    doc = io.open(listing, encoding="utf-8", errors="replace").read()

    for tk, dup, true_date in DUPES:
        d = os.path.join(SITE, "fda-decision", f"{tk}-{dup}")
        keep = os.path.join(SITE, "fda-decision", f"{tk}-{true_date}")
        if not os.path.isdir(keep):
            print(f"  SKIP {tk}: the page to KEEP ({tk}-{true_date}) does not exist; "
                  f"refusing to delete {tk}-{dup} and leave no record")
            continue
        if os.path.isdir(d):
            print(f"  remove /fda-decision/{tk}-{dup}  (keeping {tk}-{true_date})")
            if not a.dry_run:
                shutil.rmtree(d, ignore_errors=True)
            removed += 1
        pat = re.compile(r'<a class="row" href="/fda-decision/' + tk + '-' + dup +
                         r'".*?</a>', re.S)
        doc, k = pat.subn("", doc)
        rows_cut += k

    if rows_cut and not a.dry_run:
        io.open(listing, "w", encoding="utf-8").write(doc)
    print(f"pages removed: {removed}; /decisions rows removed: {rows_cut}")

    # ---- correct dcd on the dataset rows ------------------------------------------------
    p = os.path.join(SITE, "api", "v1", "dataset.mjs")
    src = io.open(p, encoding="utf-8", errors="replace").read().replace("\x00", "")
    j = src.find("[")
    arr, end = json.JSONDecoder().raw_decode(src[j:])
    fixed = 0
    for tk, _dup, true_date in DUPES:
        for r in arr:
            if (r.get("t") == tk and r.get("type") == "PDUFA"
                    and str(r.get("st", "")).lower() == "decided"
                    and str(r.get("dcd") or "")[:4] == "2026"
                    and str(r.get("dcd")) != true_date
                    and abs(int(str(r.get("dcd"))[8:10]) - int(true_date[8:10])) <= 5):
                print(f"  dcd {tk}: {r.get('dcd')} -> {true_date}  (goal {r.get('d')})")
                r["dcd"] = true_date
                fixed += 1
    if fixed and not a.dry_run:
        io.open(p, "w", encoding="utf-8").write(
            src[:j] + json.dumps(arr, separators=(",", ":"), ensure_ascii=False) + src[j + end:])
    print(f"dataset dcd corrections: {fixed}")
    if a.dry_run:
        print("DRY RUN -- nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
