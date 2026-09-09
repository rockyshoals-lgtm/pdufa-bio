# -*- coding: utf-8 -*-
"""One company name per ticker, present on every dated forward row, never a listing blurb.

Audit 2026-09-09b items 4 and 6. 265 of 456 public API rows served a blank `company`,
including CORT's live 2026-12-17 PDUFA -- a forward catalyst with no sponsor, in the endpoint
/developers advertises. Separately, 15 tickers carried several spellings of one company, and
GSK's was "GSK plc American Depositary Shares (Each representing two)", which is an exchange
listing description, not a name.

Contract:
  1. no PDUFA or AdComm row may have a blank company (a dated regulatory event has a sponsor;
     estimated readouts are exempt, some genuinely have no company anywhere and a blank is
     more honest than a guess);
  2. one spelling per ticker across the whole dataset;
  3. no company field carries ADR/listing boilerplate.

Proved 0 -> 1 -> 0 on 2026-09-09 against the pre-backfill dataset, which failed all three.
"""
import collections
import io
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
ADR = re.compile(r"American Depositary|Each representing|\bADS\b|\bADR\b|Sponsored ADR", re.I)
NEEDS_COMPANY = {"PDUFA", "ADCOMM"}


def rows():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    return json.loads(src[src.index("["):src.rindex("]") + 1])


def test_company_names_canonical():
    rs = rows()
    assert rs, "dataset empty -- guard cannot see"
    bad = []

    for r in rs:
        if str(r.get("type") or "").upper().replace(" ", "") not in NEEDS_COMPANY:
            continue
        if not str(r.get("company") or "").strip():
            bad.append(f"{r.get('t')} {r.get('d')} {r.get('type')}: blank company on a dated "
                       f"regulatory event (the CORT 2026-12-17 class)")

    spellings = collections.defaultdict(set)
    for r in rs:
        tk, co = str(r.get("t") or "").upper(), str(r.get("company") or "").strip()
        if tk and co:
            spellings[tk].add(co)
    for tk, names in sorted(spellings.items()):
        if len(names) > 1:
            bad.append(f"{tk}: {len(names)} company spellings {sorted(names)}")
        for n in names:
            if ADR.search(n):
                bad.append(f"{tk}: company field carries listing boilerplate: {n!r}")

    assert not bad, ("company-name defects in the public dataset:\n  " + "\n  ".join(bad[:40])
                     + (f"\n  ... and {len(bad) - 40} more" if len(bad) > 40 else ""))


if __name__ == "__main__":
    test_company_names_canonical()
    print("OK")
