# -*- coding: utf-8 -*-
"""test_data_sources_present.py -- every builder input must EXIST, be GIT-TRACKED, and carry a
minimum row count. A missing data file must fail the build, never thin the page.

Red team 2026-08-18, third instance of the same root cause:
    73faf74f  verification scripts read a workstation-only CSV -> 4 CI runs dead
    6bf22f9b  .gitignore's *.csv swallowed patent_cliff_2026_2031_TA.csv -> 2 CI runs dead
    2026-08-18  *.csv swallowed conference_presenters_VERIFIED_2026-08-12.csv -> 9 true,
                hand-verified presenter rows silently ABSENT from the live page for two days

The generalisable defect (their words): "the build degrades silently when a data file is
absent. A missing input produces fewer rows, not an error. That is a check that can only ever
pass." Builders do `if not os.path.exists(path): continue` -- correct for optional inputs,
fatal for required ones.

Why TRACKED matters and exists() does not suffice: on the workstation every file exists, so an
existence check passes here and dies in CI. The thing all three incidents shared is that the
file was not in git. `git ls-files` is the ground truth for what CI will see.

Minimums are FLOORS chosen well below current counts (shrinkage headroom for legitimate pruning)
but far above zero; the failure mode being caught is absence/emptiness, not natural drift. Raise
a floor deliberately when a source legitimately shrinks below it -- with a reviewed commit, the
same contract as _calendar_flags_known.json.
"""
import csv, json, os, subprocess, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (relative path, minimum data rows, what breaks silently without it)
REQUIRED = [
    ("catalysts_out/conference_presenters_VERIFIED_2026-08-12.csv", 8,
     "the 9 hand-verified presenter rows vanish from /conferences (the 2026-08-18 regression)"),
    ("catalysts_out/conference_presentations_history.csv", 5,
     "history-file presenter rows vanish from /conferences"),
    ("catalysts_out/catalysts_public.csv", 100,
     "the public catalyst dataset behind the API thins out"),
    ("patent_cliff_2026_2031_TA.csv", 300,
     "all 40 patent-cliff pages stop building (the 6bf22f9b incident)"),
    ("_decisions_join_slim.csv", 2000,
     "decision verification loses its drug/indication join (the 73faf74f incident)"),
    ("conferences.json", 20,
     "the /conferences page and API lose their meeting list"),
    ("readout_reported_manual.json", 1,
     "confirmed readout outcomes (ABCL, AMLX) fall off /readouts"),
    ("conf_study/conference_runup_PUBLISHED.csv", 50,
     "the conference run-up study page loses its dataset"),
]


def _rows(path):
    """Data rows in a source file: CSV = rows after the header; JSON = len of the main list
    (top-level list, or the longest list value of a top-level dict)."""
    if path.endswith(".json"):
        d = json.load(open(path, encoding="utf-8"))
        if isinstance(d, list):
            return len(d)
        if isinstance(d, dict):
            lists = [v for v in d.values() if isinstance(v, list)]
            return max((len(v) for v in lists), default=0)
        return 0
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return max(0, sum(1 for _ in csv.reader(f)) - 1)


def main():
    tracked = set(subprocess.run(
        ["git", "ls-files"], cwd=HERE, capture_output=True, text=True,
        check=True).stdout.split("\n"))

    bad = []
    for rel, floor, consequence in REQUIRED:
        p = os.path.join(HERE, rel)
        if rel not in tracked:
            bad.append(f"{rel}: NOT GIT-TRACKED -- exists here, invisible to CI; {consequence}. "
                       f"Check .gitignore (line 35 is a blanket *.csv) and `git add -f` it.")
            continue
        if not os.path.exists(p):
            bad.append(f"{rel}: tracked but MISSING from the working tree; {consequence}.")
            continue
        try:
            n = _rows(p)
        except Exception as e:
            bad.append(f"{rel}: unreadable ({e}); {consequence}.")
            continue
        if n < floor:
            bad.append(f"{rel}: {n} row(s), floor is {floor}; {consequence}.")

    if bad:
        print(f"FAIL: {len(bad)} required data source(s) absent, untracked, or below floor.")
        for b in bad:
            print(f"   {b}")
        print("\n   A build with a missing input must FAIL, not publish a thinner page --")
        print("   this exact silent degradation shipped three times (73faf74f, 6bf22f9b,")
        print("   2026-08-18). Fix the source, don't lower the floor without review.")
        return 1
    print(f"  PASS: {len(REQUIRED)} required data sources tracked, present, and above floor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
