# -*- coding: utf-8 -*-
"""/learn/what-is-a-pdufa-date and /calendar state the same decision-timing numbers.

Audit 2026-09-08c item 2: the explainer's snippet said "15 of 26 sourced decisions came
early"; the calendar said 32 decisions, 20 early. One statistic, one source
(build_early_decisions.collect via inject_calendar_explainer.timing_split), so the rendered
learn page must carry exactly the numbers that function returns -- in the meta description
AND the body sentence. Proved 0 -> 1 -> 0 on 2026-09-08 by planting "15 of 26" back into the
description.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
PAGE = os.path.join(HERE, "pdufa_site_src", "learn", "what-is-a-pdufa-date", "index.html")


def test_learn_timing_matches_calendar():
    from inject_calendar_explainer import timing_split
    n, early, on, late, _ = timing_split()
    doc = io.open(PAGE, encoding="utf-8", errors="replace").read()
    metas = re.findall(r"In 2026, (\d+) of (\d+) sourced decisions came early\.", doc)
    assert metas, "learn page lost its timing sentence in the description"
    bad = [f"description says {e} of {t}, calendar source says {early} of {n}"
           for e, t in metas if (int(e), int(t)) != (early, n)]
    body = re.search(r"of the (\d+) sourced 2026 decisions in <a [^>]*>our decision-timing study</a>, "
                     r"(\d+) came before the goal date, (\d+) landed on it and (\d+) ", doc)
    assert body, "learn page lost its body timing sentence"
    if tuple(int(x) for x in body.groups()) != (n, early, on, late):
        bad.append(f"body says {body.groups()}, calendar source says {(n, early, on, late)}")
    assert not bad, "learn page timing numbers disagree with /calendar:\n  " + "\n  ".join(bad)


if __name__ == "__main__":
    test_learn_timing_matches_calendar()
    print("OK")
