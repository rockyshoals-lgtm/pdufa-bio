# -*- coding: utf-8 -*-
"""refresh_moved_pdufa_pages.py -- when a PDUFA date moves, fix the event pages that state it.

THE GAP (found 2026-08-24, CAPR)
The FDA extended deramiocel's action date from August 22 to November 22. The dataset, the slate
and every calendar row moved. /pdufa/CAPR and /pdufa/CAPR-deramiocel did not, because
build_pdufa_event_pages.py deliberately never overwrites an existing page -- the hand-grown ones
carry story cards and charts worth more than a regeneration. So the pages kept announcing a date
the FDA had already replaced, in the title, the description, the visible facts and the Event
schema a crawler reads. PDUFA dates move often; nothing was repairing this.

WHAT IT DOES
Surgical, not a rebuild. For each /pdufa/* page it reads the ticker, finds that page's own drug
in the dataset, and if the dataset's date for that event differs from the date the page states,
it replaces ONLY that date -- ISO form, "Aug 22, 2026", "Aug 22 2026", "August 22, 2026" -- and
leaves everything else, including the run-up chart and its own date labels, untouched.

Deliberately conservative:
  * a page whose date matches the dataset is not touched;
  * a page with no matching dataset event is not touched (it may be a decided archive page);
  * a DECIDED event is never rewritten here -- a decided date is history, not a schedule.

    python refresh_moved_pdufa_pages.py [--dry-run]
"""
import argparse, datetime as dt, glob, io, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def forms(iso):
    """Every rendering of a date this site emits, so a move updates all of them."""
    y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    full, abbr = MONTHS[m - 1], MONTHS[m - 1][:3]
    return [iso, f"{abbr} {d}, {y}", f"{abbr} {d} {y}", f"{full} {d}, {y}", f"{full} {d} {y}"]


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]{4,}", str(s or "").lower())
            if w not in ("pdufa", "date", "with", "combination", "therapy")}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    by_tk = {}
    for r in rows:
        if r.get("type") == "PDUFA":
            by_tk.setdefault(str(r.get("t", "")).upper(), []).append(r)

    changed = 0
    for p in sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        tk = slug.split("-")[0].upper()
        cands = by_tk.get(tk)
        if not cands:
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()

        # the date this page currently states, from its own Event schema / canonical facts
        m = re.search(r'"startDate":"(\d{4}-\d{2}-\d{2})"', doc) or \
            re.search(r"PDUFA target date</span><b>(\d{4}-\d{2}-\d{2})", doc) or \
            re.search(r"target <b>(\d{4}-\d{2}-\d{2})", doc)
        stated = m.group(1) if m else None
        if not stated:
            continue

        # WHICH EVENT IS THIS PAGE ABOUT? Match on the SLUG, which is authoritative, and demand
        # an unambiguous answer.
        #
        # A first version scored the page BODY against every event for the ticker and took the
        # first token hit. The dry run showed what that produces on multi-product sponsors:
        # /pdufa/GILD-yeztugo matched the bictegravir+lenacapavir event because both strings
        # contain "lenacapavir", /pdufa/PFE-keytruda matched brepocitinib, and PRAX's
        # ulixacaltamide page matched relutrigine. Rewriting a date from a mismatch would move
        # the wrong event's date onto a live page -- the exact failure this file exists to undo.
        live = [c for c in cands if str(c.get("st", "")).lower() != "decided"]
        drug_part = slug[len(tk):].lstrip("-")
        if drug_part:
            stoks = toks(drug_part.replace("-", " "))
            hits = [c for c in live if stoks & toks(c.get("name"))]
        else:
            hits = live                      # bare /pdufa/{TICKER}: only safe if it is unique
        if len(hits) != 1:
            if len(hits) > 1:
                print(f"  SKIP /pdufa/{slug}: {len(hits)} live events match; a wrong rewrite is "
                      f"worse than a stale date -- resolve by hand")
            continue
        hit = hits[0]
        new = str(hit.get("d") or "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", new) or new == stated:
            continue
        if str(hit.get("st", "")).lower() == "decided":
            continue                       # a decided date is history, not a schedule

        out = doc
        for old_form, new_form in zip(forms(stated), forms(new)):
            out = out.replace(old_form, new_form)
        if out == doc:
            continue
        changed += 1
        print(f"  /pdufa/{slug}: {stated} -> {new}  ({str(hit.get('name'))[:40]})")
        if not a.dry_run:
            io.open(p, "w", encoding="utf-8").write(out)

    print(f"{'DRY RUN ' if a.dry_run else ''}{changed} event page(s) refreshed to the "
          f"dataset's current date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
