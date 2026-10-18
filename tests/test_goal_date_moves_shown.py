# -*- coding: utf-8 -*-
"""CI guard: every PDUFA row whose date_history records a moved goal day shows the move on its event page and its
calendar row (audit 2026-10-18, order 5). Plant: PLANT_MOVE=1 strips CAPR's block in memory and must FAIL.

    python tests/test_goal_date_moves_shown.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
_argv, sys.argv = sys.argv, sys.argv[:1]
import inject_goal_date_moves as G  # noqa: E402
sys.argv = _argv


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    cal = io.open(os.path.join(SITE, "calendar", "index.html"), encoding="utf-8", errors="replace").read()
    fails, n = [], 0
    for r in rows:
        if r.get("type") != "PDUFA" or not G.moves(r):
            continue
        n += 1
        old, new, changed, why = G.moves(r)[-1]
        url = str(r.get("url") or "")
        p = os.path.join(SITE, url.strip("/").replace("/", os.sep), "index.html")
        doc = io.open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else ""
        if os.environ.get("PLANT_MOVE") == "1" and r["id"].startswith("pdufa_capr"):
            doc = re.sub(r"<!--DATEMOVE:BEGIN-->.*?<!--DATEMOVE:END-->", "", doc, flags=re.S)
        if "<!--DATEMOVE:BEGIN-->" not in doc or G.pretty(old) not in doc.split("<!--DATEMOVE:BEGIN-->")[-1][:400]:
            fails.append(f"{url}: goal date moved {old} -> {new} but the event page does not say so")
        if r.get("st") in ("Upcoming", "Awaiting") and f"<!--DM:{r['id']}-->" not in cal:
            fails.append(f"{r['id']}: /calendar row carries no 'goal date moved' tag")
    if fails:
        print(f"FAIL: {len(fails)} goal-date move(s) not shown:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} moved goal date(s) shown on their event pages and calendar rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
