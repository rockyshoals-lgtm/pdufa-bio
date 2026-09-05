# -*- coding: utf-8 -*-
"""No log file may silently eat the disk again.

Audit 2026-09-05c: `Momentum Scanner/_DATA/_runall_test.err` had grown to 77 GB --
82% of everything measured on the disk -- and nothing noticed because a log that
grows is indistinguishable from a log that works. Deleted with David's approval
2026-09-05. This guard fails when any log-shaped file (*.err, *.log, *.out) under
the scanner data dir or the repo root exceeds the cap, so the next runaway gets
caught at 2 GB instead of 77.

Skips silently when the scanner dir is absent (GitHub CI checks out only the repo).
"""
import glob
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP_BYTES = 2 * 1024 ** 3        # 2 GB: far above any legitimate log here
ROOTS = [os.path.join(HERE, "Momentum Scanner", "_DATA"), HERE]
PATTERNS = ("*.err", "*.log", "*.out")


def test_no_log_exceeds_cap():
    bad = []
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        for pat in PATTERNS:
            for p in glob.glob(os.path.join(root, pat)):
                try:
                    size = os.path.getsize(p)
                except OSError:
                    continue
                if size > CAP_BYTES:
                    bad.append(f"{os.path.relpath(p, HERE)}: "
                               f"{size / 1024**3:.1f} GB (cap {CAP_BYTES / 1024**3:.0f} GB)")
    assert not bad, ("runaway log(s) -- rotate or investigate, do not let 77 GB "
                     "happen twice:\n  " + "\n  ".join(bad))


if __name__ == "__main__":
    test_no_log_exceeds_cap()
    print("OK")
