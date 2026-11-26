# -*- coding: utf-8 -*-
"""news_watch_keeper.py -- keep the rebuild on its daily slots when GitHub drops the crons.

Red team 2026-11-26 (news speed, second pass). The 15-minute news watch (PR 228) ran ONCE on its schedule in its
first 12 hours: GitHub dropped the other ~45 starts. The same scheduler starts this repo's crons hours late or not at
all, measured on run history:
  * pdufa-blocked-watchdog.yml, "17 * * * *" (hourly): 18 scheduled runs from Nov 20 to Nov 26, about one every 8 h;
  * pdufa-rebuild.yml, 10:00Z and 12:00Z: the morning build started 17:30Z to 21:10Z most days, and on Nov 26 had
    not started at all by 16:43Z; the 21:00Z build started 01:00Z to 05:00Z the next day.
So a release after the close waited for a build that came the next afternoon, and the watch meant to close that gap
never ran.

The fix is to stop depending on cron: news-watch.yml now runs as one long job that does a watch pass every 15
minutes for about 5.5 hours and then starts its own successor with workflow_dispatch (GitHub lets GITHUB_TOKEN
dispatch a workflow; that is the documented exception to "a token-triggered event starts no run"). The cron stays
only as a restart if the chain ever breaks.

Each pass also calls this script, which does two things the dropped crons were meant to do:
  1. REBUILD SLOTS. For the latest of today's 10:00, 12:00 and 21:00 UTC slots that is at least GRACE minutes old,
     if no pdufa-rebuild.yml run of any kind was created at or after the slot, it dispatches one. One dispatch per
     slot: the dispatched run itself counts as the slot's run on the next pass. A late cron start that also lands
     queues behind it (concurrency group pdufa-rebuild, cancel-in-progress false) and is harmless.
  2. WATCHDOG. Once an hour it runs blocked_issue.py --watchdog, the check pdufa-blocked-watchdog.yml exists for.
It builds, commits and publishes nothing itself.

    python news_watch_keeper.py [--dry-run]
tests/test_news_watch_keeper.py pins the slot rule and the workflow's loop.
"""
import datetime as dt
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SLOTS_UTC = (10, 12, 21)          # pdufa-rebuild.yml's daily crons, in UTC hours
GRACE = dt.timedelta(minutes=50)  # give GitHub's own start this long before dispatching for it
REBUILD = "pdufa-rebuild.yml"


def _utc(s):
    return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def latest_slot(now):
    """The most recent rebuild slot that is at least GRACE old, as an aware UTC datetime."""
    cands = []
    for back in (0, 1):
        day = (now - dt.timedelta(days=back)).date()
        for h in SLOTS_UTC:
            s = dt.datetime(day.year, day.month, day.day, h, tzinfo=dt.timezone.utc)
            if s + GRACE <= now:
                cands.append(s)
    return max(cands)


def due_slot(now, run_created):
    """The slot that still needs a rebuild, or None. run_created: creation times of recent pdufa-rebuild runs (any
    event, any status)."""
    s = latest_slot(now)
    if any(_utc(c) >= s for c in run_created):
        return None
    return s


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, cwd=HERE)


def main():
    dry = "--dry-run" in sys.argv[1:]
    now = dt.datetime.now(dt.timezone.utc)
    repo = os.environ.get("GITHUB_REPOSITORY", "rockyshoals-lgtm/pdufa-bio")

    r = gh("api", f"repos/{repo}/actions/workflows/{REBUILD}/runs?per_page=20", "--jq",
           "[.workflow_runs[].created_at]")
    if r.returncode != 0:
        print(f"::warning::keeper: could not read {REBUILD} runs ({r.stderr.strip()[:200]}); no dispatch this pass")
    else:
        created = json.loads(r.stdout or "[]")
        s = due_slot(now, created)
        if s is None:
            print(f"keeper: the {latest_slot(now):%H:%M}Z rebuild slot has its run")
        elif dry:
            print(f"keeper: would dispatch {REBUILD} for the {s:%Y-%m-%d %H:%M}Z slot [dry run]")
        else:
            d = gh("workflow", "run", REBUILD, "--ref", "main", "-R", repo)
            if d.returncode == 0:
                print(f"keeper: no rebuild started for the {s:%Y-%m-%d %H:%M}Z slot; dispatched {REBUILD}")
            else:
                print(f"::warning::keeper: dispatch of {REBUILD} failed: {d.stderr.strip()[:200]}")

    # the hourly watchdog, whose own cron fires about every 8 hours; once per ~hour of this job's life
    stamp = os.path.join(os.environ.get("RUNNER_TEMP", HERE), ".keeper_watchdog_at")
    try:
        last = float(open(stamp).read().strip())
    except (OSError, ValueError):
        last = 0.0
    if now.timestamp() - last >= 55 * 60 and not dry:
        try:
            open(stamp, "w").write(str(now.timestamp()))
        except OSError:
            pass
        w = subprocess.run([sys.executable, os.path.join(HERE, "blocked_issue.py"), "--watchdog"], cwd=HERE)
        if w.returncode != 0:
            print(f"::warning::keeper: blocked_issue.py --watchdog exited {w.returncode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
