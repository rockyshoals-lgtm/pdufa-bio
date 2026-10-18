# -*- coding: utf-8 -*-
"""run_ci_guards.py -- run every tests/test_*.py, report ALL failures, and leave a BLOCKED report for the issue step.

Audit 2026-10-18 P0: both Sunday scheduled runs failed a guard and nobody was told. The guard step used `set -e`
and stopped at the first failing test, the run went red, and the only record was a job log that needs repository
admin rights to read. A guard that blocks a deploy must say so where people look: a GitHub issue.

This runner:
  * runs every guard (a later failure is not hidden behind an earlier one);
  * prints each guard's output in a log group, as before;
  * on failure writes `_blocked.md` (test names + the tail of each failing guard's output), and `_blocked.json`,
    and exits 1 so the job blocks as before. The next workflow step turns `_blocked.md` into one open issue
    titled "BLOCKED: pdufa.bio rebuild {run id}: {tests}", updating it instead of opening a second.

    python run_ci_guards.py [--only test_x.py] [--report _blocked.md]
"""
import argparse
import glob
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=os.path.join(HERE, "_blocked.md"))
    ap.add_argument("--only", action="append", default=[])
    a = ap.parse_args()
    tests = sorted(glob.glob(os.path.join(HERE, "tests", "test_*.py")))
    if a.only:
        tests = [t for t in tests if os.path.basename(t) in a.only]
    failed = []
    for t in tests:
        rel = os.path.relpath(t, HERE).replace("\\", "/")
        print(f"::group::{rel}", flush=True)
        r = subprocess.run([sys.executable, "-X", "utf8", t], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        print(out, end="" if out.endswith("\n") else "\n", flush=True)
        print("::endgroup::", flush=True)
        if r.returncode != 0:
            tail = "\n".join(out.strip().splitlines()[-25:])
            failed.append((rel, r.returncode, tail))
            print(f"::error file={rel}::guard failed (exit {r.returncode})", flush=True)
    for p in (a.report, os.path.splitext(a.report)[0] + ".json"):
        if os.path.exists(p):
            os.remove(p)
    if not failed:
        print(f"CI guards: {len(tests)} passed, 0 failed")
        return 0
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_SHA", "")[:9]
    names = ", ".join(os.path.basename(f[0]) for f in failed)
    lines = [f"# BLOCKED: rebuild run {run_id} failed {len(failed)} guard(s): {names}", "",
             f"Commit `{sha}`. The run stopped before commit and deploy; live stays on the previous build until a "
             f"run passes. Run page: https://github.com/{repo}/actions/runs/{run_id}", "",
             "Each guard's own output is quoted below. Fix the tree or the guard, push, and dispatch.", ""]
    for rel, rc, tail in failed:
        lines += [f"## {rel} (exit {rc})", "```", tail, "```", ""]
    lines += ["Facts only; not investment advice."]
    io.open(a.report, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    io.open(os.path.splitext(a.report)[0] + ".json", "w", encoding="utf-8").write(json.dumps(
        {"run_id": run_id, "sha": sha, "failed": [f[0] for f in failed]}, indent=1) + "\n")
    print(f"CI guards: {len(tests) - len(failed)} passed, {len(failed)} FAILED: {names}  -> {a.report}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
