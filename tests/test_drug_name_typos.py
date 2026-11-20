# -*- coding: utf-8 -*-
"""CI guard: no drug name misspelled with a capital I for a lowercase l.

2026-11-18: "LINZESS (Iinaclotide)" (should be linaclotide; Drugs@FDA NDA 202811 lists LINACLOTIDE) sat on 30
files: the drug page title and h1, two decision pages, the archive and the run-up study. A capital I and a
lowercase l look alike in most fonts, so nobody saw it. No drug name (INN or brand) begins "Ii", so a word that does
is this typo, in title case or in capitals ("IINACLOTIDE"). Some surnames do begin "Ii" (Iizuka, Iijima): put one in
ALLOW when a real one appears. Scans the site, the API dataset and the data stores pages are built from. Base64 and
hex runs are skipped by the boundary rule (a match must stand alone as a word). It cannot see an I/l swap inside a
word; KNOWN lists such typos once found, case-insensitively.
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
WORD = re.compile(r"(?<![A-Za-z0-9+/=_\-])(?:Ii[a-z]{4,}|II(?!I)[A-Z]{4,})(?![A-Za-z0-9+/=_\-])")
KNOWN = re.compile(r"iinaclotide", re.I)
ALLOW = set()
STORES = ["_fda_action_archive.json", "_chart2026_events.json", "pdufa_runup_bifrost_v2.csv",
          "_drug_approvals_confirmed.json", "readout_reported_manual.json", "_decisions_join_slim.csv",
          "_fda_approvals_months.json", "_decision_extra_faq.json", "phase_events.json"]


def main():
    files = glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)
    files += [os.path.join(SITE, "api", "v1", "dataset.mjs")] + [os.path.join(HERE, f) for f in STORES]
    files += glob.glob(os.path.join(HERE, "runup_2020plus_rebuild", "*"))
    bad = []
    for p in files:
        if not os.path.isfile(p):
            continue
        txt = io.open(p, encoding="utf-8", errors="replace").read()
        hits = {m.span(): m for m in list(WORD.finditer(txt)) + list(KNOWN.finditer(txt))}
        for _, m in sorted(hits.items()):
            if m.group(0) in ALLOW:
                continue
            bad.append(f"{os.path.relpath(p, HERE)}: '{m.group(0)}' (a capital I where a lowercase l belongs?)")
    for b in bad[:30]:
        print("  FAIL", b)
    if bad:
        print(f"{len(bad)} misspelled drug name(s)")
        sys.exit(1)
    print(f"OK -- no 'Ii...' misspelling in {len(files)} pages and data files.")


if __name__ == "__main__":
    main()
