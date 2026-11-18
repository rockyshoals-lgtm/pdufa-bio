# -*- coding: utf-8 -*-
"""apply_1118c_filing_quotes.py -- every filing-verified decision carries the sentence that records the FDA action.

2026-11-18 red team (David, 2026-11-17 Eastern: "Red team the readout and pdufa dates again ... as the most
accurate"). verify_decisions.py once accepted any 8-K/6-K that merely CONTAINED "approval of" / "FDA approval" /
"complete response letter"; 35 of 82 pages so verified did not hold up (apply_1118_retire_decisions.py,
apply_1118b_decision_sources.py). Every remaining filing-verified page was re-read by hand. This writes, for each,
the sentence from the cited document that records the FDA action, its URL and the check date into the evidence in
_decision_verification.json, from decision_filing_quotes_2026_11_18.json. tests/test_decision_filing_evidence.py
then requires a quote on every verified result that rests on a filing or a primary document.

Idempotent. Facts only, not investment advice.

    python apply_1118c_filing_quotes.py [--dry-run]
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "_decision_verification.json")
SPEC = os.path.join(HERE, "decision_filing_quotes_2026_11_18.json")


def apply(ledger, spec):
    res, n, missing = ledger["results"], 0, []
    for slug, q in spec["pages"].items():
        r = res.get(slug)
        if not r or not str(r.get("status", "")).startswith("verified"):
            missing.append(slug)
            continue
        ev = r.setdefault("evidence", {})
        want = {"quote": q["quote"], "quote_url": q["quote_url"], "quote_checked": spec["checked"]}
        if all(ev.get(k) == v for k, v in want.items()):
            continue
        ev.update(want)
        n += 1
    return n, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ledger = json.load(io.open(LEDGER, encoding="utf-8"))
    spec = json.load(io.open(SPEC, encoding="utf-8"))
    n, missing = apply(ledger, spec)
    print(f"quotes written: {n} of {len(spec['pages'])}" + (f" | not verified in the ledger: {missing}" if missing else ""))
    if missing:
        raise SystemExit("a listed page is not a verified result; fix the spec")
    if not a.dry_run and n:
        io.open(LEDGER, "w", encoding="utf-8", newline="").write(json.dumps(ledger, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    sys.exit(main())
