# -*- coding: utf-8 -*-
"""CI guard: every fixer a guard tells you to run, and the local chain runs, also runs in CI (order 2026-11-17).

BLOCKED #83 (Nov 15-17, six failed runs): test_awaiting_marked_on_calendar.py says "run mark_calendar_awaiting.py";
the local chain (_chain_0919.bat) ran it, the CI workflow never did, so CI could only fail until a human published a
decision. This reads every tests/test_*.py for the scripts its failure text names ("Run X.py", "python X.py",
"fix: python X.py") and fails when such a script is in the local chain but absent from the rebuild workflow.

    python tests/test_workflow_runs_chain_fixers.py [--workflow PATH]   (the flag exists for the 0 -> 1 -> 0 proof)
"""
import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMED = re.compile(r"(?:\b[Rr]un|python|fix:)\s+(?:python\s+)?(?:pdufa_site_src/)?([a-z_0-9]+\.py)")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", default=os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml"))
    a = ap.parse_args(argv)
    wf = open(a.workflow, encoding="utf-8").read()
    in_ci = set(re.findall(r"([a-z_0-9]+\.py)", wf))
    chain = set(re.findall(r"([a-z_0-9]+\.py)", open(os.path.join(HERE, "_chain_0919.bat"), encoding="utf-8",
                                                      errors="replace").read()))
    named = {}
    for t in sorted(glob.glob(os.path.join(HERE, "tests", "test_*.py"))):
        for m in NAMED.finditer(open(t, encoding="utf-8", errors="replace").read()):
            s = m.group(1)
            if not s.startswith("test_") and os.path.exists(os.path.join(HERE, s)):
                named.setdefault(s, set()).add(os.path.basename(t))
    missing = sorted(s for s in named if s in chain and s not in in_ci)
    if missing:
        print(f"FAIL: {len(missing)} fixer(s) named by a guard run in the local chain but not in CI:")
        for s in missing:
            print(f"   {s}  (named by {', '.join(sorted(named[s]))})")
        print("   Add each to .github/workflows/pdufa-rebuild.yml in the chain's position, or CI blocks itself.")
        return 1
    print(f"OK -- {len(named)} fixer(s) named by guards; every one the local chain runs is also in the CI workflow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
