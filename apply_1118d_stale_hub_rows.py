# -*- coding: utf-8 -*-
"""apply_1118d_stale_hub_rows.py -- three /ticker hubs still listed a decision retired on 2026-10-15 as an approval.

2026-11-18 (design change 2's guard, tests/test_decision_dates_labeled.py, found it). apply_1015_anktiva_and_corrections.py
retired six decision pages that recorded no FDA action (its docstring gives each reason and source) and removed them
from /decisions/approvals, but not from the old /ticker hubs of JAGX, XOMA and ZVRA. No builder rewrites those three
hubs (build_ticker_hubs.py builds only tickers with a current catalyst, decision or readout), so each still showed
"FDA decision history (1)" with a "Approved" badge on the retired day, linking a URL that 301s back to the hub:
    JAGX-2026-04-29  Canalevia-CA1: an effectiveness-trial topline, not an approval (NADA filed June 2026)
    XOMA-2026-06-08, ZVRA-2026-06-08  Miplyffa: an Orange Book patent listing, no FDA action (approved 2024-09-20)

This removes every link to those six slugs from built pages (the row, its JSON-LD item), corrects the hub's
"N past FDA decision(s)" line and its "FDA decision history (N)" heading, and drops the heading when no row is left.
tests/test_no_retracted_claims.py now lists the six slugs, so a page that links one fails the rebuild.
Idempotent. Facts only, not investment advice.

    python apply_1118d_stale_hub_rows.py [--dry-run]
"""
import argparse
import glob
import io
import json
import os
import re

from apply_1118_retire_decisions import unlink, fix_jsonld

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")

# slug -> why, from apply_1015_anktiva_and_corrections.py (verified 2026-10-14 against FDA records and sponsor releases)
RETIRED_1015 = {
    "BMY-2026-06-01": "June 1, 2026 was the FDA's acceptance of the Camzyos filing, not an action; it was approved "
                      "on September 30, 2026.",
    "JAGX-2026-04-29": "Canalevia-CA1 reported an effectiveness-trial topline that day; it was not approved.",
    "LGND-2026-06-08": "Miplyffa had an Orange Book patent listing that day, not an FDA action; it was approved on "
                       "September 20, 2024.",
    "XOMA-2026-06-08": "Miplyffa had an Orange Book patent listing that day, not an FDA action; it was approved on "
                       "September 20, 2024.",
    "ZVRA-2026-06-08": "Miplyffa had an Orange Book patent listing that day, not an FDA action; it was approved on "
                       "September 20, 2024.",
    "PGEN-2026-05-27": "Papzimeos had no FDA action on or near that day; it was approved on August 14, 2025.",
}
ALLOWED = {"corrections/index.html", "changelog/index.html"}
HIST = re.compile(r'<h2>FDA decision history \((\d+)\)</h2>')
PAST = re.compile(r'(\d+) past FDA decisions?(?=</div>)')
DESC = re.compile(r'(\d+) past FDA decisions?\.( Source document and measured run-up on every one\.)?(?=")')
ROW = re.compile(r'<a class="row" href="/fda-decision/[^"]+"')


def fix_counts(doc):
    i = doc.find('<h2>FDA decision history (')
    rows = len(ROW.findall(doc[i:])) if i >= 0 else 0
    if i >= 0:
        doc = HIST.sub(f'<h2>FDA decision history ({rows})</h2>' if rows else '', doc, 1)
    doc = PAST.sub(f'{rows} past FDA decision{"s" if rows != 1 else ""}' if rows else 'no past FDA decision on file',
                   doc, 1)
    # the meta and og descriptions say the same count
    doc = DESC.sub(lambda m: (f'{rows} past FDA decision{"s" if rows != 1 else ""}.' + (m.group(2) or "")) if rows
                   else 'No past FDA decision on file.', doc)

    def ld(m):
        try:
            j = json.loads(m.group(2))
        except Exception:  # noqa: BLE001
            return m.group(0)
        changed = False
        for node in j.get("@graph", []) if isinstance(j, dict) else []:
            if isinstance(node, dict) and node.get("@type") == "ItemList":
                n = len(node.get("itemListElement") or [])
                if node.get("numberOfItems") != n:
                    node["numberOfItems"] = n
                    changed = True
        return m.group(1) + json.dumps(j) + m.group(3) if changed else m.group(0)
    return re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)', ld, doc, flags=re.S)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    gone = [f"/fda-decision/{s}" for s in RETIRED_1015]
    changed = []
    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        rel = os.path.relpath(p, SITE).replace("\\", "/")
        if rel in ALLOWED or "_bak" in rel or "_xbak" in rel:
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if not any(g in doc for g in gone):
            continue
        new = doc
        for s in RETIRED_1015:
            new = unlink(new, s)
        new = fix_jsonld(new, gone)
        if rel.startswith("ticker/"):
            new = fix_counts(new)
        if new != doc:
            changed.append(rel)
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    left = [os.path.relpath(p, SITE) for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)
            if "_bak" not in p and "_xbak" not in p
            and os.path.relpath(p, SITE).replace("\\", "/") not in ALLOWED
            and any(g in io.open(p, encoding="utf-8", errors="replace").read() for g in gone)]
    print(f"pages changed: {len(changed)} {changed}; still linking a retired slug: {left or 'none'}")


if __name__ == "__main__":
    main()
