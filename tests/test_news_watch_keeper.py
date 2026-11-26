# -*- coding: utf-8 -*-
"""test_news_watch_keeper.py -- the news watch runs without cron, and a skipped rebuild slot gets its build.

Red team 2026-11-26: GitHub ran news-watch.yml's "every 15 minutes" cron once in 12 hours and the rebuild's 10:00Z
and 12:00Z crons 7 to 10 hours late, so the watch meant to post decisions within the hour never ran. This fails if:
  1. news_watch_keeper.due_slot() does not ask for a rebuild when a slot passed with no run, asks twice for one
     slot, or asks before the grace period;
  2. news-watch.yml stops looping (a sleep between passes, a ~5.5 h budget under the job's timeout), stops
     dispatching its own successor, lets a new start cancel the running loop, lacks actions: write, or loops on a
     private repo where minutes are billed;
  3. the loop stops calling news_watch_keeper.py or quarantine_leads.py, or starts publishing (git push, commit).
PLANT=oneshot replays the single-pass workflow from PR 228; it must FAIL.

    python tests/test_news_watch_keeper.py
"""
import datetime as dt
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import news_watch_keeper as K  # noqa: E402

WF = os.path.join(HERE, ".github", "workflows", "news-watch.yml")
U = dt.timezone.utc


def t(s):
    return dt.datetime.fromisoformat(s).replace(tzinfo=U)


def main():
    bad = []
    # 1. the slot rule, on the real Nov 26 history: last rebuild created 06:57Z, nothing since
    hist = ["2026-11-26T06:57:41Z", "2026-11-26T06:36:16Z", "2026-11-26T03:18:45Z"]
    cases = [
        ("16:43Z Nov 26, no run since 06:57Z", t("2026-11-26T16:43"), hist, t("2026-11-26T12:00")),
        ("10:30Z, inside the grace period", t("2026-11-26T10:30"), hist, None),
        ("10:55Z, 10:00Z slot unrun", t("2026-11-26T10:55"), hist, t("2026-11-26T10:00")),
        ("11:10Z, after our 10:55Z dispatch", t("2026-11-26T11:10"), hist + ["2026-11-26T10:55:03Z"], None),
        ("02:00Z, yesterday's 21:00Z ran late at 01:00Z", t("2026-11-27T02:00"), ["2026-11-27T01:00:00Z"], None),
        ("02:00Z, yesterday's 21:00Z never ran", t("2026-11-27T02:00"), hist, t("2026-11-26T21:00")),
    ]
    for name, now, runs, want in cases:
        got = K.due_slot(now, runs)
        if got != want:
            bad.append(f"slot rule, {name}: got {got}, want {want}")

    # 2-3. the workflow loops and chains
    wf = io.open(WF, encoding="utf-8").read()
    if os.environ.get("PLANT") == "oneshot":
        wf = re.sub(r"while :; do.*?done\n", "", wf, flags=re.S).replace("cancel-in-progress: false",
                                                                       "cancel-in-progress: true")
        wf = wf.replace("gh workflow run news-watch.yml", "true").replace("actions: write", "")
    m = re.search(r"timeout-minutes:\s*(\d+)", wf)
    loop = re.search(r'LOOP_SECONDS:\s*"(\d+)"', wf)
    need = {
        "a loop of passes": "while :; do" in wf and re.search(r'sleep "\$wait"', wf),
        "a ~5.5 h budget under the job timeout": bool(m and loop and int(loop.group(1)) + 15 * 60 <= int(m.group(1)) * 60
                                                      and int(m.group(1)) <= 360 and int(loop.group(1)) >= 4 * 3600),
        "a 15-minute pass": re.search(r'PASS_EVERY:\s*"900"', wf),
        "the successor dispatch": "gh workflow run news-watch.yml" in wf,
        "a running loop never cancelled by a new start": re.search(r"cancel-in-progress:\s*false", wf),
        "actions: write": re.search(r"actions:\s*write", wf),
        "no loop on a private repo": "REPO_PRIVATE" in wf and "github.event.repository.private" in wf,
        "news_watch_keeper.py each pass": "python news_watch_keeper.py" in wf,
        "quarantine_leads.py collect each pass": "quarantine_leads.py collect" in wf,
    }
    for what, ok in need.items():
        if not ok:
            bad.append(f"news-watch.yml lacks {what}")
    if re.search(r"git (push|commit)", wf):
        bad.append("news-watch.yml publishes (git push/commit); it must only raise leads")

    print(f"news watch keeper: {len(cases)} slot cases, {len(need)} workflow properties")
    if bad:
        print("FAIL")
        for b in bad:
            print("  " + b)
        return 1
    print("  PASS: the watch loops every 15 minutes and chains itself, and a skipped rebuild slot is dispatched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
