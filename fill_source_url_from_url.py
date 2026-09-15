# -*- coding: utf-8 -*-
"""Audit 09-15 ORDER 4: `source_url` in the API was 0 of 456 because the provenance lived in the
wrong field. 246 rows carry their primary document in `url` (the row's link target) -- 55 SEC
filings, 180 ClinicalTrials.gov registry records, press releases -- and `_d.source_url` was set on
only 16 rows by hand this week. The API now ships `source_url`; this copies each row's external
document into it so the field is populated where the provenance already exists, and stays null
where it does not (37 forward PDUFAs whose only link is our own page -- the EDGAR pass works those).

Rule: an external `url` on a PDUFA or Readout row IS the row's source (a registry record for an
Estimated readout, a filing or release for a Guided/Reported readout or a PDUFA). Site-internal
urls (/pdufa/...) are never a source. `source` is filled from the domain only when absent.

    python fill_source_url_from_url.py [--dry-run]
"""
import argparse
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")


def label(url):
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    if host.endswith("sec.gov"):
        return "company filing (SEC)"
    if host.endswith("clinicaltrials.gov"):
        return "trial-estimate (not company-confirmed)"
    if host.endswith("fda.gov"):
        return "FDA announcement"
    return "company press release"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    n = 0
    for r in rows:
        if r.get("type") not in ("PDUFA", "Readout"):
            continue
        url = str(r.get("url") or "")
        dd = r.setdefault("_d", {})
        if dd.get("source_url") or not url.startswith("http"):
            continue
        dd["source_url"] = url
        if not dd.get("source"):
            dd["source"] = label(url)
        n += 1
    if not a.dry_run:
        io.open(DATASET, "w", encoding="utf-8").write(
            src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    have = sum(1 for r in rows if (r.get("_d") or {}).get("source_url"))
    print(f"{n} row(s) given source_url from their external url; {have}/{len(rows)} rows now carry "
          f"source_url" + ("   (--dry-run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
