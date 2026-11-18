# -*- coding: utf-8 -*-
"""CI guard: every PDUFA row whose date_history records a moved goal day shows the move on its event page and its
calendar row (audit 2026-10-18, order 5). Plant: PLANT_MOVE=1 strips CAPR's block in memory and must FAIL.

Also (2026-11-18, Bing date fix): the dates inside those notes are written as data (2026-08-22), never as prose
("Aug 22, 2026"). Bing printed the prose date beside "goal date moved from" / "(recorded ...)" as the date of
/calendar, /pdufa/CAPR and /pdufa/PRAX-relutrigine instead of the pages' own update date. Plant: PLANT_PROSE=1
puts a prose date back into the /calendar tag in memory and must FAIL.

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
        if "<!--DATEMOVE:BEGIN-->" not in doc or old[:10] not in doc.split("<!--DATEMOVE:BEGIN-->")[-1][:400]:
            fails.append(f"{url}: goal date moved {old} -> {new} but the event page does not say so")
        if r.get("st") in ("Upcoming", "Awaiting"):
            # /calendar's live grid runs through its last month heading; a goal moved beyond it (AGIO and EXEL into
            # 2027, 2026-11-01) lives on its month page, which must carry the tag instead.
            d = str(r.get("d") or "")
            mon = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
                   "november", "december"][int(d[5:7]) - 1] if len(d) >= 7 else ""
            head = f'<div class="mhead">{mon.capitalize()} {d[:4]}</div>'
            where, page = "/calendar", cal
            if head not in cal:
                mp = os.path.join(SITE, "calendar", d[:4], mon, "index.html")
                where = f"/calendar/{d[:4]}/{mon}"
                page = io.open(mp, encoding="utf-8", errors="replace").read() if os.path.exists(mp) else ""
            if f"<!--DM:{r['id']}-->" not in page:
                fails.append(f"{r['id']}: {where} row carries no 'goal date moved' tag")
    # the notes state history as data, not as a prose date an engine can take for the page's own date
    import glob
    if os.environ.get("PLANT_PROSE") == "1":
        cal = cal.replace("goal date moved from 2026-08-22", "goal date moved from Aug 22, 2026")
    n_notes = 0
    for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
        if os.sep + "_" in os.sep + os.path.relpath(p, SITE):
            continue
        doc = cal if p == os.path.join(SITE, "calendar", "index.html") else \
            io.open(p, encoding="utf-8", errors="replace").read()
        if "DATEMOVE:BEGIN" not in doc and "EXTN:BEGIN" not in doc and 'class="dm"' not in doc:
            continue
        notes = (re.findall(r"<!--DATEMOVE:BEGIN-->.*?<!--DATEMOVE:END-->", doc, re.S)
                 + re.findall(r"<!--EXTN:BEGIN-->.*?<!--EXTN:END-->", doc, re.S)
                 + re.findall(r'<span class="dm">.*?</span></span>', doc, re.S))
        for note in notes:
            n_notes += 1
            m = G._PROSE_DATE.search(re.sub(r"<[^>]+>", "", note))
            if m:
                fails.append(f"/{os.path.relpath(os.path.dirname(p), SITE)}: goal-date note states '{m.group(0)}' "
                             f"as a prose date; write it as {G.iso_dates(m.group(0))}")
    if fails:
        print(f"FAIL: {len(fails)} goal-date move(s) not shown, or shown as a prose date:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} moved goal date(s) shown on their event pages and calendar rows; {n_notes} note(s) state their "
          f"dates as data, none as a prose date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
