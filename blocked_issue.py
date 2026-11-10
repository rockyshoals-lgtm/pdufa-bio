# -*- coding: utf-8 -*-
"""blocked_issue.py -- turn run_ci_guards.py's _blocked.md into ONE open GitHub issue (audit 2026-10-18 P0).

Title: "BLOCKED: pdufa.bio rebuild failed {tests}". If an open issue with a BLOCKED: title already exists, its body is
replaced and a comment names the new run, so a freeze that persists across runs stays one issue (the 10-15
escalation lesson: six duplicates for one episode). Closing the issue is the human's acknowledgement; the next
passing run also closes it (`--resolve`).

    python blocked_issue.py --report _blocked.md            # on a failed guard step
    python blocked_issue.py --resolve                       # on a passing run: close any open BLOCKED issue
    python blocked_issue.py --report _blocked.md --dry-run  # print the title/body, call nothing
"""
import argparse
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PREFIX = "BLOCKED: pdufa.bio rebuild failed "


def gh(*args, inp=None):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", input=inp)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout


def open_blocked():
    out = gh("issue", "list", "--state", "open", "--search", f'"{PREFIX.strip()}" in:title', "--json", "number,title",
             "--limit", "20")
    return [i for i in json.loads(out or "[]") if str(i.get("title", "")).startswith("BLOCKED:")]


def since_last_deploy():
    """'Days since last green deploy: N (run R, finished YYYY-MM-DD HH:MM ET)'. Audit 2026-11-09 §2a: each frozen build
    cut Bing AI citations ~80% within a day, so the age of the live build is the number that matters on this issue."""
    import datetime as dt
    try:
        out = gh("run", "list", "--workflow", "pdufa-rebuild.yml", "--status", "success", "--limit", "1",
                 "--json", "databaseId,updatedAt")
        last = (json.loads(out or "[]") or [None])[0]
        if not last:
            return "Days since last green deploy: unknown (no successful run found)."
        t = dt.datetime.fromisoformat(last["updatedAt"].replace("Z", "+00:00"))
        try:
            from site_dates import _ET
        except Exception:  # noqa: BLE001
            _ET = dt.timezone(dt.timedelta(hours=-5))
        now = dt.datetime.now(dt.timezone.utc)
        days = (now - t).total_seconds() / 86400
        return (f"Days since last green deploy: {days:.1f} (run {last['databaseId']}, finished "
                f"{t.astimezone(_ET):%Y-%m-%d %H:%M} ET). Bing AI citations fell ~80% within a day of past freezes.")
    except Exception as e:  # noqa: BLE001
        return f"Days since last green deploy: unavailable ({str(e)[:100]})."


OWNER = "@rockyshoals-lgtm"  # a mention makes GitHub email the owner (no SMTP secret yet)


def compose(report):
    body = io.open(report, encoding="utf-8").read()
    if not body.startswith("**Days since last green deploy"):
        body = f"**{since_last_deploy()}**\n\ncc {OWNER}\n\n" + body
        io.open(report, "w", encoding="utf-8").write(body)
    meta = json.load(io.open(os.path.splitext(report)[0] + ".json", encoding="utf-8"))
    names = ", ".join(os.path.basename(f) for f in meta["failed"])
    title = (PREFIX + names)[:230]
    return title, body, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=os.path.join(HERE, "_blocked.md"))
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.resolve:
        if a.dry_run:
            print("dry run: would close any open BLOCKED issue"); return 0
        for i in open_blocked():
            gh("issue", "close", str(i["number"]), "--comment",
               f"A later run passed every guard and deployed (run {os.environ.get('GITHUB_RUN_ID', '?')}).")
            print(f"closed #{i['number']}")
        return 0
    if not os.path.exists(a.report):
        # 2026-10-22: three of four runs (39695890711, 39798814880, 39874039652) failed in a BUILD step
        # (build_sls_deepdive.py: Polygon 429 -> empty closes -> min() of an empty list), before the guards ran. With
        # no _blocked.md this step printed "nothing to report", the commit and deploy were skipped, and no issue was
        # opened: a silent freeze, the exact failure 10-18 was meant to end. Any failure now opens the issue, naming
        # the failed step(s) when the API allows it.
        run_id = os.environ.get("GITHUB_RUN_ID", "local")
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        steps = []
        try:
            jobs = json.loads(gh("run", "view", run_id, "--json", "jobs")).get("jobs", [])
            steps = [s.get("name") for j in jobs for s in j.get("steps", []) if s.get("conclusion") == "failure"]
        except Exception as e:  # noqa: BLE001
            steps = [f"(step names unavailable: {str(e)[:120]})"]
        names = ", ".join(steps) or "a build step"
        body = (f"# BLOCKED: rebuild run {run_id} failed in a build step, before the guards\n\n"
                f"Commit `{os.environ.get('GITHUB_SHA', '')[:9]}`. Failed: {names}. The commit and deploy were skipped; "
                f"live stays on the previous build until a run passes. Run page: "
                f"https://github.com/{repo}/actions/runs/{run_id}\n")
        a.report = os.path.join(HERE, "_blocked.md")
        io.open(a.report, "w", encoding="utf-8").write(body)
        io.open(os.path.splitext(a.report)[0] + ".json", "w", encoding="utf-8").write(json.dumps(
            {"failed": [f"step: {s}" for s in steps] or ["build step"], "run_id": run_id,
             "sha": os.environ.get("GITHUB_SHA", "")[:9]}))
    title, body, meta = compose(a.report)
    if a.dry_run:
        print("TITLE:", title); print(body[:1500]); return 0
    existing = open_blocked()
    if existing:
        n = str(existing[0]["number"])
        gh("issue", "edit", n, "--title", title, "--body-file", a.report)
        gh("issue", "comment", n, "--body", f"Still blocked: run {meta['run_id']} on `{meta['sha']}` failed "
                                            f"{', '.join(os.path.basename(f) for f in meta['failed'])}. "
                                            f"{body.splitlines()[0].strip('*')}")
        print(f"updated #{n}: {title}")
    else:
        out = gh("issue", "create", "--title", title, "--body-file", a.report)
        print(f"opened: {out.strip()}  {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
