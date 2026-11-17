# -*- coding: utf-8 -*-
"""Replay guard: a goal date that passes with no decision builds GREEN, without a human (order 2026-11-17, #83).

Builds a throwaway tree with one planted pending PDUFA row whose goal was yesterday (Eastern), a /calendar row for it and
its /pdufa event page in the pending tense, then runs the two CI fixers on that tree:
  mark_calendar_awaiting.py  -> the calendar row must carry the Awaiting badge;
  mark_goal_date_passed.py   -> the event page must carry the automatic PASSED block naming the sources checked,
                                and no longer say "is under FDA review" (test_no_past_target_pending_pages' contract).
Nothing in the real site tree is touched.
"""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def main():
    from site_dates import eastern_today
    y = (eastern_today() - dt.timedelta(days=1)).isoformat()
    tmp = tempfile.mkdtemp(prefix="pdufa_replay_")
    try:
        for f in ("mark_calendar_awaiting.py", "mark_goal_date_passed.py", "site_dates.py"):
            shutil.copy(os.path.join(HERE, f), tmp)
        site = os.path.join(tmp, "pdufa_site_src")
        os.makedirs(os.path.join(site, "api", "v1")); os.makedirs(os.path.join(site, "calendar"))
        os.makedirs(os.path.join(site, "pdufa", "ZZZQ-testdrug"))
        row = {"id": f"pdufa_zzzq_{y}", "t": "ZZZQ", "d": y, "dp": "day", "type": "PDUFA", "st": "Upcoming",
               "name": "Testdrug", "url": "/pdufa/ZZZQ-testdrug", "_d": {}}
        open(os.path.join(site, "api", "v1", "dataset.mjs"), "w", encoding="utf-8").write(
            "export const DATA = " + json.dumps([row]) + ";\n")
        open(os.path.join(site, "calendar", "index.html"), "w", encoding="utf-8").write(
            f'<html><body><a class="row" href="/pdufa/ZZZQ-testdrug"><div class="t">ZZZQ &middot; {y}</div>'
            f'<div class="d">Testdrug</div></a></body></html>')
        open(os.path.join(site, "pdufa", "ZZZQ-testdrug", "index.html"), "w", encoding="utf-8").write(
            f'<html><body><h1>ZZZQ PDUFA Date: <span class="g">Testdrug</span></h1><!--FRESH:BEGIN--><!--FRESH:END-->'
            f'<div class="kv"><span>FDA PDUFA target date</span><b>{y}</b></div>'
            f'<p>Testdrug is under FDA review for a test indication.</p></body></html>')
        open(os.path.join(tmp, "_goal_date_passed.json"), "w", encoding="utf-8").write('{"passed": []}\n')
        out = ""
        for s in ("mark_calendar_awaiting.py", "mark_goal_date_passed.py"):
            r = subprocess.run([sys.executable, s], cwd=tmp, capture_output=True, text=True, encoding="utf-8")
            out += r.stdout + r.stderr
            if r.returncode != 0:
                print(f"FAIL: {s} exited {r.returncode} on the replay tree:\n{out[-800:]}"); return 1
        cal = open(os.path.join(site, "calendar", "index.html"), encoding="utf-8").read()
        page = open(os.path.join(site, "pdufa", "ZZZQ-testdrug", "index.html"), encoding="utf-8").read()
        fails = []
        if 'class="awaiting"' not in cal:
            fails.append("calendar row for a passed, undecided goal has no Awaiting badge")
        if "<!--PASSED:BEGIN-->" not in page or "sources checked" not in page:
            fails.append("event page has no automatic goal-date-passed block naming the sources checked")
        if "is under FDA review" in page:
            fails.append("event page still says 'is under FDA review' after its goal date")
        if fails:
            print("FAIL: past-goal replay:"); [print("   " + f) for f in fails]; print(out[-600:]); return 1
        print(f"OK -- replay of a goal dated {y} with no decision: calendar shows Awaiting, the event page states the "
              "date passed with the sources checked, no pending tense. CI needs no human for this case.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
