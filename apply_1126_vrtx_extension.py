# -*- coding: utf-8 -*-
"""apply_1126_vrtx_extension.py -- Vertex's povetacicept goal date moved from November 30, 2026 to no later than
February 28, 2027.

Found 2026-11-26 (Eastern) by the same replay of watch_fmp_press.py that found Belite Bio: pdufa.bio still counted
down to November 30, 2026 a day after Vertex announced the extension.

Source (RULE 1: release times are Eastern):
  * Vertex release, Business Wire, 2026-11-25 16:02 ET, "Vertex Announces Extension of PDUFA Target Action Date by
    up to Three Months as FDA Completes Review of the Biologics License Application for Povetacicept in IgA
    Nephropathy", read on Vertex's own investor site 2026-11-26: the FDA "informed the company on November 24, 2026"
    of the extension; "The original PDUFA target action date was November 30, 2026, and the revised target action
    date for the FDA decision is no later than February 28, 2027." Reason: a major amendment (Vertex's response to
    an FDA information request late in the review).
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
RID = "pdufa_vrtx_2026-11-30"
OLD, NEW, CHANGED = "2026-11-30", "2027-02-28", "2026-11-24"
URL = ("https://investors.vrtx.com/news-releases/news-release-details/vertex-announces-extension-pdufa-target-"
       "action-date-three-months")
BW = "https://www.businesswire.com/news/home/20261125185870/en/"
QUOTE = "the revised target action date for the FDA decision is no later than February 28, 2027"
WHY = ("The FDA classified Vertex's response to a late information request as a major amendment and extended the "
       "review by up to three months; Vertex's release of November 25, 2026 states the revised target action date "
       "is no later than February 28, 2027.")


def main():
    src = io.open(DATASET, encoding="utf-8").read()
    a, b = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[a:b])
    r = next(x for x in rows if x.get("id") == RID)
    d = r.setdefault("_d", {})
    if r.get("d") == NEW and d.get("prior_pdufa_date") == OLD:
        print("VRTX already moved; nothing to do")
        return 0
    if r.get("d") != OLD or r.get("st") != "Upcoming":
        print(f"VRTX row is {r.get('d')} {r.get('st')}, not {OLD} Upcoming; not touched")
        return 1
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    r["d"] = NEW
    r["ua"] = now
    d.update({
        "prior_pdufa_date": OLD,
        "date_provenance": URL,
        "date_history": [
            {"date": OLD, "changed": "2026-08-03", "url": d.get("source_url"), "note": "original PDUFA target action date"},
            {"date": NEW, "changed": CHANGED, "url": URL, "why": WHY},
        ],
        "source": "Vertex release, Business Wire, November 25, 2026 (Vertex investor site)",
        "source_url": URL,
        "source_wire_url": BW,
        "source_quote": QUOTE,
        "source_note": "Extension found 2026-11-26 by the press-release watch; the date is the sponsor's own statement "
                       "and is a latest date (\"no later than\"), so a decision can come earlier.",
        "review": "BLA for accelerated approval in IgA nephropathy. The FDA extended the review by up to three months "
                  "after a major amendment; the revised target action date is no later than February 28, 2027 "
                  "(Vertex, November 25, 2026). The original date was November 30, 2026.",
    })
    if DRY:
        print(json.dumps(r, indent=1)[:1500])
        return 0
    io.open(DATASET, "w", encoding="utf-8", newline="").write(src[:a] + json.dumps(rows, indent=1) + src[b:])
    import subprocess
    subprocess.run([sys.executable, os.path.join(HERE, "record_date_check.py"), RID, "FIXED", URL,
                    f"Goal date moved {OLD} -> {NEW}: Vertex release 2026-11-25 16:02 ET (FDA told Vertex 2026-11-24) states "
                    f"the revised target action date is no later than February 28, 2027."], check=True)
    print(f"VRTX povetacicept: goal date {OLD} -> {NEW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
