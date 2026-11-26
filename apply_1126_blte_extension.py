# -*- coding: utf-8 -*-
"""apply_1126_blte_extension.py -- Belite Bio's tinlarebant goal date moved from February 12 to May 12, 2027.

Found 2026-11-26 (Eastern) by the first replay of watch_fmp_press.py over the last ten days of armed sponsors'
releases: pdufa.bio still showed February 12, 2027 six days after the FDA extended the review.

Sources (RULE 1: release times are Eastern):
  * Belite Bio release, GlobeNewswire, 2026-11-20 08:00 ET, "Belite Bio Announces Extension of FDA Review Timeline
    for Tinlarebant NDA", read through FMP's press-release feed 2026-11-26: the FDA "has extended the review period
    for the New Drug Application (NDA) for tinlarebant for the treatment of Stargardt disease type 1 (STGD1) by three
    months, with the extended Prescription Drug User Fee Act (PDUFA) action date being May 12, 2027".
  * Belite Bio 6-K accepted by the SEC 2026-11-20 08:05:16 ET (accession 0001104659-26-130425), per FMP's filing
    index; it carries the release.
The row keeps its id (the way pdufa_capr_2026-08-22 kept its id when deramiocel's date moved) and gains the
date_history that inject_goal_date_moves.py shows on the event page and the calendar row; the rebuild's
refresh_moved_pdufa_pages.py and calendar steps move the page and the row.

Idempotent. Facts only; not investment advice.

    python apply_1126_blte_extension.py [--dry-run]
"""
import datetime as dt
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
DRY = "--dry-run" in sys.argv
RID = "pdufa_blte_2027-02-12"
OLD, NEW, CHANGED = "2027-02-12", "2027-05-12", "2026-11-20"
URL = ("https://www.globenewswire.com/news-release/2026/11/20/3407395/0/en/belite-bio-announces-extension-of-fda-"
       "review-timeline-for-tinlarebant-nda.html")
SEC = "https://www.sec.gov/Archives/edgar/data/1889109/000110465926130425/0001104659-26-130425-index.htm"
# the release's own words, cut to the clause that states the date (inject_event_page_source.py prints a quote of at
# most 240 characters, and the full sentence runs 250)
QUOTE = "with the extended Prescription Drug User Fee Act (PDUFA) action date being May 12, 2027"
WHY = ("The FDA extended the review period by three months; Belite Bio's release of November 20, 2026 (6-K the same "
       "day) states the extended PDUFA action date of May 12, 2027.")


def main():
    src = io.open(DATASET, encoding="utf-8").read()
    a, b = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[a:b])
    r = next(x for x in rows if x.get("id") == RID)
    d = r.setdefault("_d", {})
    if r.get("d") == NEW and d.get("prior_pdufa_date") == OLD:
        print("BLTE already moved; nothing to do")
        return 0
    if r.get("d") != OLD or r.get("st") != "Upcoming":
        print(f"BLTE row is {r.get('d')} {r.get('st')}, not {OLD} Upcoming; not touched")
        return 1
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    r["d"] = NEW
    r["ua"] = now
    d.update({
        "prior_pdufa_date": OLD,
        "date_provenance": URL,
        "date_history": [
            {"date": OLD, "changed": "2026-08-11", "url": d.get("source_url"), "note": "original PDUFA target action date"},
            {"date": NEW, "changed": CHANGED, "url": URL, "why": WHY},
        ],
        "source": "Belite Bio release, GlobeNewswire, November 20, 2026 (6-K accepted 2026-11-20)",
        "source_url": URL,
        "source_sec_url": SEC,
        "source_quote": QUOTE,
        "source_note": "Extension found 2026-11-26 by the press-release watch; the date is the sponsor's own statement.",
        "review": "NDA for Stargardt disease type 1, priority review. Review extended by three months to May 12, 2027 "
                  "(Belite Bio, November 20, 2026).",
    })
    if DRY:
        print(json.dumps(r, indent=1)[:1500])
        return 0
    io.open(DATASET, "w", encoding="utf-8", newline="").write(src[:a] + json.dumps(rows, indent=1) + src[b:])
    import subprocess
    subprocess.run([sys.executable, os.path.join(HERE, "record_date_check.py"), RID, "FIXED", URL,
                    f"Goal date moved {OLD} -> {NEW}: Belite Bio release 2026-11-20 08:00 ET and 6-K accepted "
                    f"2026-11-20 08:05 ET state the extended PDUFA action date of May 12, 2027."], check=True)
    print(f"BLTE tinlarebant: goal date {OLD} -> {NEW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
