# -*- coding: utf-8 -*-
"""test_readout_miner_extract.py -- the readout miner must never publish a date with no program.

The first deep run produced 222 rows, none of which named a drug, and included gold miners, an
electric utility and Waste Management, because "results are expected in the fourth quarter" is a
sentence every public company writes. Two defences were added: an SEC industry-code gate, and a
requirement that the matched sentence name the thing that reads out.

This locks the second defence. The rejection cases matter more than the acceptance cases: a missed
drug costs one row, a false positive puts a wrong program on a public calendar.

    python tests/test_readout_miner_extract.py
"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("rm", os.path.join(HERE, "readout_miner.py"))
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)

# (sentence, expect_program?) -- False means the row MUST be rejected
CASES = [
    # real guidance, program must be found
    ("Topline data expected in December 2026 for ONS-5010 in wet AMD.", True),
    ("The Company expects to report topline results from NCT05123456 in Q1 2027.", True),
    ("LYTENAVA(R) topline results are expected in the second half of 2027.".replace("(R)", "®"), True),
    ("Topline data from the Phase 3 trial of veligrotug expected Q4 2026.", True),
    ("Results expected in Q2 2027 from the pivotal trial of exagamglogene autotemcel.", True),
    ("Initial data expected in Q3 2026 from the Phase 2 study of DISC-3405.", True),
    ("Topline data for eplontersen are expected in the first quarter of 2027.", True),

    # must be rejected: no program named
    ("Results are expected in the fourth quarter of 2026 for our gold recovery project.", False),
    ("The Company anticipates reporting topline data in the second half of 2027.", False),
    ("We expect to report topline results for our lead candidate in mid-2027.", False),
    ("Interim analysis expected in Q1 2027; the Company reported record production.", False),
    ("Data expected in Q3 2026 from the trial of patients with advanced disease.", False),
    ("The Phase 3 readout expected in 2027 will include 400 patients.", False),

    # must be rejected: SEC document furniture is not a drug
    ("Exhibit EX-99.1 Item 8.01 topline results expected in Q4 2026.", False),
    ("Form 10-Q Part II topline data expected in Q1 2027.", False),
]


def main():
    fails = []
    for text, want in CASES:
        prog, kind = rm.extract_program(text)
        got = prog is not None
        if got != want:
            fails.append((text, want, prog, kind))

    print(f"checked {len(CASES)} sentences")
    if fails:
        print(f"\nFAIL: {len(fails)} case(s) wrong:")
        for text, want, prog, kind in fails:
            exp = "a program" if want else "rejection"
            print(f"   expected {exp}, got {prog!r} ({kind})\n      {text}")
        sys.exit(1)

    # the industry gate must still exclude the classes that contaminated the first run
    for bad in ("1040", "1000", "4911", "4922", "6022", "7372"):   # gold, metal, utility, gas, bank, software
        if bad in rm.DRUG_SIC:
            print(f"\nFAIL: SIC {bad} is not a drug developer but is in DRUG_SIC")
            sys.exit(1)
    for good in ("2834", "2836", "8731"):
        if good not in rm.DRUG_SIC:
            print(f"\nFAIL: SIC {good} (drug developer) missing from DRUG_SIC")
            sys.exit(1)

    print("  PASS: every real program found, every generic/furniture sentence rejected")
    print("  PASS: industry gate admits drug developers and excludes miners/utilities/banks/software")


if __name__ == "__main__":
    main()
