# -*- coding: utf-8 -*-
"""blocked_issue.py -- turn run_ci_guards.py's _blocked.md into ONE open GitHub issue (audit 2026-10-18 P0).

Title: "BLOCKED: pdufa.bio rebuild failed {tests}". If an open issue with a BLOCKED: title already exists, its body is
replaced and a comment names the new run, so a freeze that persists across runs stays one issue (the 10-15
escalation lesson: six duplicates for one episode). Closing the issue is the human's acknowledgement; the next
passing run also closes it (`--resolve`).

2026-11-18 (David: "we are getting more blocked notices from github"): one failed run that the next run fixes is
not a freeze. Runs 443 and 446 each opened an issue that @-mentioned the owner, then closed it minutes later, so
every one-off failure cost three emails. Now:
  * ESCALATE only when the freeze is real: the previous completed run also failed (second failure in a row), or the
    live build is RECENT_HOURS or more old. Any guard, dates and accuracy guards included, escalates on the second
    failure in a row, so a real freeze reaches the owner within one or two runs.
  * A first failure inside that window opens no issue and mentions no one: it prints a ::warning:: and a step-summary
    line naming the failed tests, and the next run either passes or escalates.
  * One ROLLING issue: escalation reopens the newest closed BLOCKED issue this script made (marked ROLLING) instead of
    opening a new one, and the owner is @-mentioned in a comment at that moment.

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
ROLLING = "<!-- pdufa-rolling-blocked-issue -->"
RECENT_HOURS = 6.0   # a live build older than this is a freeze whatever the run count


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


def hours_since_green():
    """Hours since the last successful rebuild finished, or None when GitHub can't say."""
    import datetime as dt
    try:
        out = gh("run", "list", "--workflow", "pdufa-rebuild.yml", "--status", "success", "--limit", "1",
                 "--json", "updatedAt")
        last = (json.loads(out or "[]") or [None])[0]
        if not last:
            return None
        t = dt.datetime.fromisoformat(last["updatedAt"].replace("Z", "+00:00"))
        return (dt.datetime.now(dt.timezone.utc) - t).total_seconds() / 3600
    except Exception:  # noqa: BLE001
        return None


def previous_run_failed():
    """Did the last COMPLETED rebuild before this one fail? None when GitHub can't say."""
    try:
        out = gh("run", "list", "--workflow", "pdufa-rebuild.yml", "--limit", "10",
                 "--json", "databaseId,status,conclusion")
        me = str(os.environ.get("GITHUB_RUN_ID", ""))
        for r in json.loads(out or "[]"):
            if str(r.get("databaseId")) == me or r.get("status") != "completed":
                continue
            if r.get("conclusion") in ("cancelled", "skipped"):
                continue
            return r.get("conclusion") == "failure"
        return None
    except Exception:  # noqa: BLE001
        return None


def should_escalate(prev_failed, hours):
    """The rule, kept pure so the self-test can pin it. Unknown is treated as real: a check that cannot see
    the run history must not be the reason a freeze goes unreported."""
    if prev_failed is None or hours is None:
        return True, "run history unavailable"
    if prev_failed:
        return True, "second failed run in a row"
    if hours >= RECENT_HOURS:
        return True, f"live build is {hours:.1f} h old"
    return False, f"first failure; live build is {hours:.1f} h old"


def closed_rolling():
    out = gh("issue", "list", "--state", "closed", "--search", f'"{PREFIX.strip()}" in:title', "--json",
             "number,title,body", "--limit", "30")
    for i in json.loads(out or "[]"):   # newest first
        if str(i.get("title", "")).startswith("BLOCKED:") and ROLLING in (i.get("body") or ""):
            return str(i["number"])
    return None


def compose(report):
    body = io.open(report, encoding="utf-8").read()
    if not body.startswith("**Days since last green deploy"):
        body = f"**{since_last_deploy()}**\n\n" + body + f"\n\n{ROLLING}\n"
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
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
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
    failed = ", ".join(os.path.basename(f) for f in meta["failed"])
    if a.dry_run:
        print("TITLE:", title); print(body[:1500]); return 0
    existing = open_blocked()
    if existing:
        # already escalated this episode: the owner is subscribed, so the comment reaches him without a new mention
        n = str(existing[0]["number"])
        gh("issue", "edit", n, "--title", title, "--body-file", a.report)
        gh("issue", "comment", n, "--body", f"Still blocked: run {meta['run_id']} on `{meta['sha']}` failed "
                                            f"{failed}. {body.splitlines()[0].strip('*')}")
        print(f"updated #{n}: {title}")
        return 0
    esc, why = should_escalate(previous_run_failed(), hours_since_green())
    if not esc:
        msg = (f"Rebuild failed {failed} ({why}). No issue opened and no one mentioned: the next run either "
               f"passes or opens the BLOCKED issue. Live stays on the previous build until a run passes.")
        print(f"::warning::{msg}")
        summ = os.environ.get("GITHUB_STEP_SUMMARY")
        if summ:
            io.open(summ, "a", encoding="utf-8").write(f"### BLOCKED (first failure, not escalated)\n\n{msg}\n\n")
        return 0
    alert = (f"{OWNER} the rebuild is blocked ({why}): run {meta['run_id']} on `{meta['sha']}` failed {failed}. "
             f"{body.splitlines()[0].strip('*')}")
    n = closed_rolling()
    if n:
        gh("issue", "reopen", n)
        gh("issue", "edit", n, "--title", title, "--body-file", a.report)
        gh("issue", "comment", n, "--body", alert)
        print(f"reopened rolling #{n} ({why}): {title}")
    else:
        out = gh("issue", "create", "--title", title, "--body-file", a.report)
        n = out.strip().rstrip("/").rsplit("/", 1)[-1]
        gh("issue", "comment", n, "--body", alert)
        print(f"opened: {out.strip()} ({why})  {title}")
    return 0


def self_test():
    cases = [((False, 1.0), False), ((True, 1.0), True), ((False, 6.0), True), ((False, 30.0), True),
             ((None, 1.0), True), ((False, None), True), ((True, None), True)]
    ok = True
    for (pf, h), want in cases:
        got = should_escalate(pf, h)[0]
        if got != want:
            ok = False
            print(f"  FAIL should_escalate(prev_failed={pf}, hours={h}) -> {got}, want {want}")
    print("blocked_issue self-test:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
