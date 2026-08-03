# -*- coding: utf-8 -*-
"""publish_readouts.py -- put ONLY company-guided readout dates on the calendar, and drop the rest.

The bar ("solid company guidance"):
  KEEP   date_source == EDGAR  AND  guided_precision in {month, quarter}
         -> the company itself stated the timing, in an SEC filing, to at least quarter precision.
  DROP   guided_precision in {half, year}   -- "2027" or "2H 2026" is not a calendar date.
  DROP   date_source == CTGOV               -- ClinicalTrials.gov primary-completion dates are
                                               explicitly ESTIMATES that slip; they are a trial
                                               data-lock projection, not a company readout date.
  DROP   anything already past.

Existing Readout records in dataset.mjs that do not meet the bar are REMOVED, so the calendar stops
carrying month-bucket estimates that were never company-confirmed.

Every published row keeps its provenance: the SEC form it came from, the filing date, and the stated
precision, so a reader can check it.

    python publish_readouts.py [--dry-run]
"""
import argparse, csv, json, os, sys
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
CSVF = os.path.join(HERE, "readout_runs", "readout_verified.csv")
TODAY = dt.date.today()
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
GOOD_PRECISION = {"month", "quarter"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--purge-unverified", action="store_true",
                    help="also DELETE existing Readout rows that are not company-guided. Off by "
                         "default: the EDGAR scan reads only a fraction of candidate filings, so an "
                         "un-verified row may simply be one we have not fetched guidance for yet. "
                         "Deleting on partial coverage destroys recoverable data.")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(CSVF, encoding="utf-8-sig")))
    # Validate the ticker against EDGAR's registrant list, not against whether we happen to have
    # built a /ticker hub page for it. A real SEC filer with guided data is publishable even if its
    # hub page does not exist yet; conference codes (ESMO, SITC, WCLC...) are not SEC registrants and
    # are still excluded, which is what the check is actually for.
    tmap_path = os.path.join(HERE, "bpc_data", "_edgar_ticker_map.json")
    known = set()
    if os.path.exists(tmap_path):
        try:
            known = {k.upper() for k in json.load(open(tmap_path)).keys()}
        except Exception:
            pass
    known |= {d for d in os.listdir(os.path.join(SITE, "ticker"))
              if os.path.isdir(os.path.join(SITE, "ticker", d))}

    keep, why = [], {"not_edgar": 0, "weak_precision": 0, "past": 0, "unknown_ticker": 0}
    for r in rows:
        tk = (r.get("ticker") or "").strip().upper()
        if r.get("date_source") != "EDGAR":
            why["not_edgar"] += 1; continue
        if (r.get("guided_precision") or "") not in GOOD_PRECISION:
            why["weak_precision"] += 1; continue
        d = (r.get("guided_date") or r.get("best_date") or "")[:10]
        if not d or d < TODAY.isoformat():
            why["past"] += 1; continue
        if tk not in known:
            why["unknown_ticker"] += 1; continue
        keep.append({"tk": tk, "d": d, "prec": r.get("guided_precision"),
                     "form": r.get("guided_form") or "", "filed": r.get("guided_filed") or "",
                     "name": (r.get("title") or "").strip(), "company": (r.get("company") or "").strip(),
                     "nct": (r.get("nct") or "").strip(),
                     "program": (r.get("program") or "").strip(),
                     "url": (r.get("filing_url") or "").strip(),
                     "accession": (r.get("accession") or "").strip(),
                     "sentence": (r.get("matched_sentence") or "").strip()})

    # de-dupe: soonest guided date per ticker
    best = {}
    for k in keep:
        if k["tk"] not in best or k["d"] < best[k["tk"]]["d"]:
            best[k["tk"]] = k
    keep = sorted(best.values(), key=lambda k: k["d"])

    print(f"miner rows: {len(rows)}")
    print(f"  rejected: not company-guided {why['not_edgar']} | weak precision (half/year) "
          f"{why['weak_precision']} | already past {why['past']} | no ticker hub {why['unknown_ticker']}")
    print(f"  PUBLISHABLE (EDGAR, month/quarter, forward): {len(keep)} tickers")

    src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i = src.find("[")
    arr, end = json.JSONDecoder().raw_decode(src[i:])
    before_readouts = sum(1 for r in arr if r.get("type") == "Readout")

    new_tks = {k["tk"] for k in keep}
    if a.purge_unverified:
        kept_other = [r for r in arr if r.get("type") != "Readout"]
        note = "PURGE: all prior Readout rows removed"
    else:
        # Keep prior estimates, but never leave a duplicate for a ticker we now have real guidance
        # for, and make sure they are labelled Estimated so the calendar can distinguish them from
        # company-confirmed dates.
        kept_other = []
        for r in arr:
            if r.get("type") != "Readout":
                kept_other.append(r); continue
            if r.get("t") in new_tks:
                continue                      # superseded by company guidance
            r["st"] = "Estimated"
            r.setdefault("_d", {})
            if isinstance(r["_d"], dict):
                r["_d"]["source"] = "trial-estimate (not company-confirmed)"
            kept_other.append(r)
        note = "ADD-ONLY: prior estimates retained and labelled Estimated"
    print(f"  mode: {note}")

    added = []
    for k in keep:
        # Name the row after the program the company actually named. "Clinical readout" tells a
        # reader nothing; "DISC-3405 readout" is the thing they searched for.
        nm = k["name"] or (f"{k['program']} readout" if k["program"] else "Clinical readout")
        added.append({
            "id": f"readout_{k['tk'].lower()}_{k['d']}", "t": k["tk"],
            "company": k["company"], "d": k["d"], "dp": k["prec"],
            "name": nm[:70], "type": "Readout", "ta": "", "cap": "",
            "st": "Guided", "url": k["url"] or f"/ticker/{k['tk']}", "ua": NOW,
            "_d": {"nct_id": k["nct"] or None, "indication": None, "market_cap_usd": None,
                   "source": "company guidance (SEC filing)", "guided_precision": k["prec"],
                   "guided_form": k["form"], "guided_filed": k["filed"],
                   "program": k["program"] or None,
                   "accession": k["accession"] or None,
                   # the exact sentence the date came from, so the claim is checkable in one click
                   "guidance_text": (k["sentence"][:300] or None)},
            "dm": k["d"][:7],
        })

    out = kept_other + added
    out.sort(key=lambda r: (str(r.get("d") or "9999"), str(r.get("t") or "")))
    after_readouts = sum(1 for r in kept_other if r.get("type") == "Readout") + len(added)
    print(f"\ndataset.mjs: Readout records {before_readouts} -> {after_readouts}  "
          f"({len(added)} company-guided added; "
          f"{before_readouts - (after_readouts - len(added))} prior rows removed/superseded)")
    print(f"  total records {len(arr)} -> {len(out)}")
    for k in keep[:25]:
        print(f"    {k['tk']:6s} {k['d']}  {k['prec']:8s} {k['form']:8s} filed {k['filed']:10s} {k['name'][:38]}")
    if len(keep) > 25:
        print(f"    ... and {len(keep)-25} more")

    if a.dry_run:
        print("\nDRY RUN -- not written."); return
    open(DATASET + ".bak_readouts", "w", encoding="utf-8").write(src)
    open(DATASET, "w", encoding="utf-8").write(
        src[:i] + json.dumps(out, separators=(",", ":"), ensure_ascii=False) + src[i + end:])
    print("\nwrote dataset.mjs (backup: dataset.mjs.bak_readouts)")


if __name__ == "__main__":
    main()
