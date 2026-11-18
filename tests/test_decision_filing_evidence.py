# -*- coding: utf-8 -*-
"""CI guard: a decision verified from a filing or a primary document must quote the sentence that records the action.

WHY (red team 2026-11-18)
verify_decisions.py (2026-08-12) marked a decision page "verified" when ANY 8-K/6-K filed within 14 days merely
contained "approval of", "FDA approval" or "complete response letter". On 2026-11-18, 35 of the 82 pages verified
that way did not hold up: the cited documents were shareholder-vote results, warrants, debt underwriting
agreements, an employment contract, earnings recaps and trial-data releases. Seventeen pages recorded an FDA action
that never happened (apply_1118_retire_decisions.py) and the rest were dated or sourced wrongly
(apply_1118b_decision_sources.py). A word match is not evidence; the sentence is.

THE INVARIANT. Every result in _decision_verification.json whose status starts "verified" and whose evidence kind
is "filing" or "primary":
  1. carries `evidence.quote`: the sentence (or an exact excerpt of it) that records the FDA action;
  2. carries `evidence.quote_checked`, an ISO date (the day a person or verify_decisions.py read it);
  3. the quote names the action the status claims (approved/approval for verified_approved; complete response
     or CRL for verified_crl), unless it is a primary FDA document (an FDA letter or FDA page) whose text the
     ledger quotes for the drug and use;
  4. the quote is not about the future ("if approved", "expects", "potential approval", ...).
Drugs@FDA matches (kind "approval") carry their own application number and action date and are not covered here.

    python tests/test_decision_filing_evidence.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(HERE, "_decision_verification.json")

ACT = {"verified_approved": re.compile(r"approv", re.I),
       "verified_crl": re.compile(r"complete response|\bCRL\b", re.I)}
FUTURE = re.compile(r"\b(?:if approved|potential(?:ly)? (?:FDA )?approval|seek(?:ing)? approval|expects?|expected|"
                    r"anticipate[sd]?|plans? to|intends? to|may receive|path to approval)\b", re.I)
FDA_DOC = re.compile(r"(?:accessdata\.fda\.gov|www\.fda\.gov|open\.fda\.gov|download\.open\.fda\.gov|fda\.report)", re.I)


def check(results):
    fails = []
    for slug, r in sorted(results.items()):
        st = str(r.get("status") or "")
        ev = r.get("evidence")
        if not st.startswith("verified") or not isinstance(ev, dict) or ev.get("kind") not in ("filing", "primary"):
            continue
        q = re.sub(r"\s+", " ", str(ev.get("quote") or "")).strip()
        why = []
        if len(q) < 15:
            why.append("no quote of the sentence that records the FDA action")
        else:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(ev.get("quote_checked") or "")):
                why.append("quote never checked (no quote_checked date)")
            fda_doc = ev.get("kind") == "primary" and FDA_DOC.search(str(ev.get("source_url") or ""))
            pat = ACT.get(st)
            if pat and not pat.search(q) and not fda_doc:
                why.append(f"quote does not state the action the page claims ({st}): {q[:90]!r}")
            if FUTURE.search(q):
                why.append(f"quote is about the future, not an FDA action: {q[:90]!r}")
        if why:
            fails.append(f"{slug} [{st}, {ev.get('kind')}] " + "; ".join(why))
    return fails


def self_test():
    bad = {"A-2026-01-01": {"status": "verified_approved", "evidence": {"kind": "filing", "phrase": "approval of"}},
           "B-2026-01-01": {"status": "verified_crl", "evidence": {"kind": "filing", "quote_checked": "2026-11-18",
                                                                     "quote": "Shareholders voted on the approval of auditors"}},
           "C-2026-01-01": {"status": "verified_approved", "evidence": {"kind": "filing", "quote_checked": "2026-11-18",
                                                                          "quote": "The company expects FDA approval of X in 2027"}},
           "D-2026-01-01": {"status": "verified_approved", "evidence": {"kind": "primary",
                                                                          "quote": "the FDA has approved X for Y"}}}
    good = {"E-2026-01-01": {"status": "verified_approved", "evidence": {"kind": "filing", "quote_checked": "2026-11-18",
                                                                           "quote": "today announced the FDA has approved X"}},
            "F-2026-01-01": {"status": "verified_crl", "evidence": {"kind": "primary", "quote_checked": "2026-11-18",
                                                                      "quote": "X Receives Complete Response Letter from FDA"}},
            "G-2026-01-01": {"status": "verified_approved", "evidence": {"kind": "primary", "quote_checked": "2026-11-18",
                             "source_url": "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/1ltr.pdf",
                             "quote": "provides for the use of X in combination with Y"}},
            "H-2026-01-01": {"status": "verified_approved", "evidence": {"kind": "approval", "appl_no": "NDA1"}},
            "I-2026-01-01": {"status": "unverified", "evidence": None}}
    ok = len(check(bad)) == 4 and not check(good)
    if not ok:
        print("SELF-TEST FAILED", check(bad), check(good))
    return ok


def main():
    if not self_test():
        return 1
    res = json.load(io.open(LEDGER, encoding="utf-8"))["results"]
    fails = check(res)
    if fails:
        print(f"FAIL: {len(fails)} decision(s) verified from a document that is not quoted for the FDA action "
              f"(quote the sentence, or set the result back to unverified):")
        for f in fails[:80]:
            print("   " + f)
        return 1
    n = sum(1 for r in res.values() if str(r.get("status") or "").startswith("verified")
            and isinstance(r.get("evidence"), dict) and r["evidence"].get("kind") in ("filing", "primary"))
    print(f"OK -- {n} decisions verified from a filing or primary document each quote the sentence that records the action.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
