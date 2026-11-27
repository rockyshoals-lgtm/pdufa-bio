# -*- coding: utf-8 -*-
"""The rebuild builds the newest main, not the commit it was dispatched on.

2026-11-27, run 46051901417: a workflow_dispatch run checks out the commit main was at when it was dispatched. That run
waited in the pdufa-rebuild concurrency queue while the run ahead of it pushed 3,323 regenerated pages; it then built
every page from the older tree, its push conflicted on nearly all of them, the push-race step kept main's copies, and
a build that had passed every guard shipped 5 files. The workflow now fetches and resets to origin/main right after
checkout. This fails if that step goes missing, moves after the first build step, or stops resetting to main.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml")


def check(text):
    bad = []
    steps = [m.start() for m in re.finditer(r"^      - (?:uses|name):", text, re.M)]
    co = text.find("uses: actions/checkout@")
    st = text.find("Start from the newest main")
    if co < 0:
        return ["no checkout step"]
    if st < 0:
        return ["the 'Start from the newest main' step is missing"]
    after_co = [p for p in steps if p > co]
    if not after_co or not (after_co[0] < st < (after_co[1] if len(after_co) > 1 else len(text))):
        bad.append("'Start from the newest main' is not the step right after checkout")
    block = text[st:st + 900]
    if "git fetch" not in block or "origin main" not in block or "reset --hard FETCH_HEAD" not in block:
        bad.append("'Start from the newest main' no longer fetches origin main and resets to it")
    if "refs/heads/main" not in block:
        bad.append("'Start from the newest main' is not limited to runs on main")
    return bad


def main():
    text = io.open(WF, encoding="utf-8").read()
    bad = check(text)
    planted = text.replace("Start from the newest main", "Start from somewhere")
    if not check(planted):
        bad.append("a workflow without the step was not caught")
    planted = text.replace("git reset --hard FETCH_HEAD", "true")
    if not check(planted):
        bad.append("a step that no longer resets was not caught")
    if bad:
        print("FAIL test_rebuild_starts_from_newest_main:")
        for b in bad:
            print("  -", b)
        return 1
    print("PASS test_rebuild_starts_from_newest_main: the rebuild resets to the newest main right after checkout")
    return 0


if __name__ == "__main__":
    sys.exit(main())
