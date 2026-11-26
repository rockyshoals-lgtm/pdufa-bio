# -*- coding: utf-8 -*-
"""test_decisions_crl_complete.py -- every CRL row on /decisions is on /decisions/crl (2026-11-24).

sync_decisions_listing.py writes a new CRL row as <span class="bad">CRL</span>, while build_decision_subhubs.py read
only the older <span class="no"> style. So SNY 2025-12-24, SMMT 2026-11-15 and CAPR 2026-11-20 were on /decisions and
missing from /decisions/crl, the year pages' CRL counts and /crl/2026/november ("0 tracked"). This reads both pages
by the word CRL in the outcome span, whatever its class, so a new row style cannot drop rows silently again.
"""
import io, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
ROW = re.compile(r'<a class="row" href="(/fda-decision/[^"]+)">(.*?)</a>', re.S)
OUTCOME = re.compile(r'class="d"><span class="[a-z]+">([^<]*)</span>')


def crl_rows(rel, inferred=None):
    """CRL rows on a page; inferred=False keeps only those not marked price-inferred, True only those that are."""
    doc = io.open(os.path.join(SITE, rel, "index.html"), encoding="utf-8").read()
    return {h for h, body in ROW.findall(doc) if (OUTCOME.search(body) or [None, ""])[1].strip() == "CRL"
            and (inferred is None or ("pv-inferred" in body) == inferred)}


def main():
    # 2026-11-26: /decisions/crl lists only CRLs read from a document; price-inferred ones stay on /decisions, labelled.
    arch, sub = crl_rows("decisions", inferred=False), crl_rows("decisions/crl")
    if len(arch) < 30:   # 39 after the 2026-11-26 retirement of 55 price-guessed CRL rows (and 5 inferred kept off)
        print(f"FAIL: read only {len(arch)} CRL rows on /decisions; the row pattern no longer matches")
        return 1
    missing = sorted(arch - sub)
    if missing:
        print(f"FAIL: {len(missing)} CRL row(s) on /decisions are missing from /decisions/crl "
              f"(run build_decision_subhubs.py): " + ", ".join(missing[:10]))
        return 1
    leaked = sorted(sub & crl_rows("decisions", inferred=True))
    if leaked:
        print(f"FAIL: {len(leaked)} price-inferred CRL row(s) are listed on /decisions/crl: " + ", ".join(leaked[:10]))
        return 1
    print(f"  PASS: all {len(arch)} document-read CRL rows on /decisions are on /decisions/crl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
