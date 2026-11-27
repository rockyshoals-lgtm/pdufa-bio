"""Guard (2026-11-27): no dataset row names its company with its own ticker in parentheses.

Pages print "Company (TICKER)" themselves, so a company field of "BridgeBio Oncology Therapeutics (BBOT)"
rendered "(BBOT) (BBOT)" on ~600 pages and blocked rebuild run 562 at test_no_repeated_phrases. This
catches it at the dataset, naming the row, before any page is built.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")


def bad_rows(rows):
    out = []
    for r in rows:
        t = str(r.get("t") or "").strip()
        c = str(r.get("company") or "")
        if t and re.search(r"\(\s*" + re.escape(t) + r"\s*\)", c, re.I):
            out.append((r.get("id"), c))
    return out


def main():
    # self-test: the planted row must be caught, the clean one must not
    assert bad_rows([{"id": "p", "t": "BBOT", "company": "BridgeBio Oncology Therapeutics (BBOT)"}])
    assert not bad_rows([{"id": "c", "t": "BBOT", "company": "BridgeBio Oncology Therapeutics"}])
    src = open(DATASET, encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    bad = bad_rows(rows)
    for rid, c in bad:
        print(f"  FAIL {rid}: company carries its own ticker: {c!r}")
    if bad:
        print(f"FAIL -- {len(bad)} row(s) name the company with its own ticker; pages would print it twice.")
        return 1
    print(f"OK -- {len(rows)} rows; no company field repeats its own ticker.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
