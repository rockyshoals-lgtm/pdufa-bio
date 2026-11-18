# -*- coding: utf-8 -*-
"""CI guard: fewer alert emails, never a hidden freeze (David 2026-11-18: "we are getting more blocked notices").

Pins three rules so a later edit cannot quietly turn them into silence:
  * blocked_issue.should_escalate: a first failure with a fresh live build opens no issue; a second failure in a
    row, a live build RECENT_HOURS or older, or a run history GitHub could not return ALWAYS escalates.
  * quarantine_leads.resolved_issues: a HELD / ESCALATION issue closes only when EVERY ack key it names is on
    file; one unacked key, no key at all, or an unrelated issue stays open.
  * the rebuild never builds across midnight Eastern (the wait step runs before checkout).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import blocked_issue as B  # noqa: E402
import quarantine_leads as Q  # noqa: E402


def watchdog_cases():
    """B.watchdog() against faked run history: escalates only a finished failure, nothing running, no open issue,
    and a live build RECENT_HOURS or more old."""
    bad = []
    saved = (B.gh, B.open_blocked, B.hours_since_green, B.escalate, B.since_last_deploy)
    fail = {"databaseId": 9, "status": "completed", "conclusion": "failure", "headSha": "abc", "url": "u"}
    ok = dict(fail, conclusion="success")
    running = dict(fail, status="in_progress", conclusion="")
    cases = [  # (runs, open issue?, hours, want escalate)
        ([fail, ok], False, 7.0, True), ([fail, ok], False, 2.0, False), ([ok, fail], False, 9.0, False),
        ([running, fail], False, 9.0, False), ([fail], True, 9.0, False), ([fail], False, None, True)]
    try:
        for runs, is_open, hours, want in cases:
            hit = []
            B.gh = lambda *a, inp=None, _r=runs: json.dumps(_r)
            B.open_blocked = lambda _o=is_open: [{"number": 1}] if _o else []
            B.hours_since_green = lambda _h=hours: _h
            B.since_last_deploy = lambda: "Days since last green deploy: 0"
            B.escalate = lambda *a: hit.append(a)
            B.watchdog()
            if bool(hit) != want:
                bad.append(f"watchdog(runs={[r['conclusion'] or r['status'] for r in runs]}, open={is_open}, "
                           f"hours={hours}) escalated={bool(hit)}, want {want}")
    finally:
        B.gh, B.open_blocked, B.hours_since_green, B.escalate, B.since_last_deploy = saved
    return bad


def main():
    bad = []
    if B.self_test() != 0:
        bad.append("blocked_issue.should_escalate drifted (see self-test output above)")
    acked = {"a|src1", "b|src2", "pdufa_x_2026-01-01|http://www.fda.gov/x"}
    issues = [
        {"number": 1, "title": "HELD: drug:a (drug_pages) lead to verify", "body": "x ack key: `a|src1`\n\nThis issue"},
        {"number": 2, "title": "HELD: drug:c (drug_pages) lead to verify", "body": "x ack key: `c|src9`\n\nThis issue"},
        {"number": 3, "title": "ESCALATION: pdufa.bio: 2 lead(s) holding rows since T",
         "body": "  ack key: a|src1  (first seen T)\n  ack key: c|src9  (first seen T)"},
        {"number": 4, "title": "ESCALATION: pdufa.bio: 2 lead(s) holding rows since T",
         "body": "  ack key: a|src1  (first seen T)\n  ack key: pdufa_x_2026-01-01|http://www.fda.gov/x  (first seen T)"},
        {"number": 5, "title": "HELD: drug:d (drug_pages) lead to verify", "body": "no key printed"},
        {"number": 6, "title": "BLOCKED: pdufa.bio rebuild failed x.py", "body": "ack key: `a|src1`"},
        {"number": 7, "title": "pdufa.bio review: verify + publish", "body": "ack key: `a|src1`"},
        # a key the pattern cannot read (a backtick inside a title-only newswire key) keeps the issue open
        {"number": 8, "title": "ESCALATION: pdufa.bio: 2 lead(s) holding rows since T",
         "body": "  ack key: a|src1  (first seen T)\n  ack key: b|Company`s drug approved  (first seen T)"},
    ]
    got = sorted(n for n, _ in Q.resolved_issues(issues, acked))
    if got != [1, 4]:
        bad.append(f"quarantine_leads.resolved_issues closed {got}, want [1, 4]")
    import inspect
    if "close_resolved()" not in inspect.getsource(Q.cmd_collect):
        bad.append("quarantine_leads.cmd_collect no longer calls close_resolved(): acked HELD issues never close")
    bad += watchdog_cases()
    dog = os.path.join(HERE, ".github", "workflows", "pdufa-blocked-watchdog.yml")
    if not os.path.exists(dog) or "blocked_issue.py --watchdog" not in open(dog, encoding="utf-8").read():
        bad.append("the hourly watchdog workflow is missing: a suppressed first failure could wait a day")
    wf = open(os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml"), encoding="utf-8").read()
    g, c = wf.find("Midnight guard"), wf.find("actions/checkout@")
    if g < 0 or c < 0 or g > c:
        bad.append("the midnight guard step is missing or runs after checkout")
    if not re.search(r"date -d 'tomorrow 00:00:30'", wf):
        bad.append("the midnight guard no longer waits for 00:00:30 Eastern")
    for b in bad:
        print("  FAIL", b)
    if bad:
        sys.exit(1)
    print("OK -- one-off failures stay quiet, real freezes escalate, only fully acked HELD issues close, "
          "and no build crosses midnight Eastern.")


if __name__ == "__main__":
    main()
