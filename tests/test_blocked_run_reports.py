# -*- coding: utf-8 -*-
"""CI guard: a hard-failed guard run is never silent (audit 2026-10-18 P0).

Both Sunday scheduled runs failed test_no_past_target_pending_pages and the only record was a job log that needs
admin rights to read; live stayed a day old and nobody was told. Fails when:
  1. the workflow's guard step does not run run_ci_guards.py, or no step calls blocked_issue.py on failure,
     or the passing path does not call `blocked_issue.py --resolve`;
  2. a replay in a temp tree with one planted failing guard does not produce _blocked.md naming that guard with its
     output, or blocked_issue.py --dry-run does not compose a "BLOCKED: pdufa.bio rebuild failed <test>" title.
Plant: PLANT_NO_ISSUE_STEP=1 removes the issue step in memory and must FAIL.

    python tests/test_blocked_run_reports.py
"""
import io
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml")


def main():
    fails = []
    wf = io.open(WF, encoding="utf-8").read()
    if os.environ.get("PLANT_NO_ISSUE_STEP") == "1":
        wf = wf.replace("blocked_issue.py --report", "echo nope")
    if "run: python run_ci_guards.py" not in wf:
        fails.append("workflow guard step does not run run_ci_guards.py (a first failure would hide the rest)")
    if not re.search(r"if: \$\{\{ failure\(\) \}\}[\s\S]{0,400}blocked_issue\.py --report", wf):
        fails.append("workflow has no failure() step calling blocked_issue.py --report (a blocked run stays silent)")
    if "blocked_issue.py --resolve" not in wf:
        fails.append("workflow never calls blocked_issue.py --resolve (a BLOCKED issue would outlive the fix)")
    # replay: one passing and one failing guard in a temp tree
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "tests"))
        io.open(os.path.join(tmp, "tests", "test_ok.py"), "w").write("print('OK -- fine')\n")
        io.open(os.path.join(tmp, "tests", "test_planted.py"), "w").write(
            "import sys\nprint('FAIL: /pdufa/ZZZQ: target 2026-10-17 has passed and the page still says pending')\nsys.exit(1)\n")
        for f in ("run_ci_guards.py", "blocked_issue.py"):
            io.open(os.path.join(tmp, f), "w", encoding="utf-8").write(io.open(os.path.join(HERE, f), encoding="utf-8").read())
        env = dict(os.environ, GITHUB_RUN_ID="424242", GITHUB_REPOSITORY="x/y", GITHUB_SHA="abcdef0123456")
        r = subprocess.run([sys.executable, os.path.join(tmp, "run_ci_guards.py"), "--report", os.path.join(tmp, "_blocked.md")],
                           capture_output=True, text=True, env=env, cwd=tmp)
        rep = os.path.join(tmp, "_blocked.md")
        if r.returncode == 0:
            fails.append("replay: run_ci_guards.py exited 0 with a planted failing guard")
        if not os.path.exists(rep):
            fails.append("replay: no _blocked.md written for a failed guard")
        else:
            body = io.open(rep, encoding="utf-8").read()
            if "test_planted.py" not in body or "ZZZQ" not in body or "424242" not in body:
                fails.append("replay: _blocked.md does not name the failing guard, quote its output and name the run")
            if "test_ok.py (exit" in body:
                fails.append("replay: _blocked.md lists a passing guard as failed")
            d = subprocess.run([sys.executable, os.path.join(tmp, "blocked_issue.py"), "--report", rep, "--dry-run"],
                               capture_output=True, text=True, env=env, cwd=tmp)
            if "TITLE: BLOCKED: pdufa.bio rebuild failed test_planted.py" not in d.stdout:
                fails.append(f"replay: blocked_issue.py did not compose the BLOCKED title: {d.stdout[:200]!r} {d.stderr[:200]!r}")
    if fails:
        print(f"FAIL: {len(fails)} blocked-run reporting failure(s):")
        for f in fails:
            print("   " + f)
        return 1
    print("OK -- every guard runs, a failed guard writes _blocked.md, the workflow turns it into one BLOCKED issue and "
          "resolves it on the next green run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
