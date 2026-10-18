# -*- coding: utf-8 -*-
"""CI guard: every decided row's decision page carries the "Verified against" line, and it states only what the
row holds (audit 2026-10-18, order 1).

Fails when a decided row's /fda-decision/{T}-{dcd} page lacks the VERIFIED block; when the block states an FDA
action day for a row with none (decision_date_unsourced and no fda_action_date); when it omits the FDA day the
row holds; when it states a goal date the row cannot source; or when Enspryng's omits either dateline.
Plant: PLANT_VERIFIED=1 pretends RHHBY-2026-10-15 states "FDA action day October 15, 2026" and must FAIL.

    python tests/test_verified_against_line.py
"""
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
       "November", "December"]


def pretty(iso):
    y, m, d = (int(x) for x in str(iso)[:10].split("-"))
    return f"{MON[m]} {d}, {y}"


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    fails, n = [], 0
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st")) != "Decided" or not r.get("dcd"):
            continue
        slug = f"{str(r.get('t') or '').upper()}-{str(r['dcd'])[:10]}"
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"<!--VERIFIED:BEGIN-->(.*?)<!--VERIFIED:END-->", doc, re.S)
        if not m:
            fails.append(f"/fda-decision/{slug}: no Verified-against line")
            continue
        n += 1
        txt = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
        if os.environ.get("PLANT_VERIFIED") == "1" and slug == "RHHBY-2026-10-15":
            txt = txt.replace("FDA action day not yet posted on Drugs@FDA", "FDA action day October 15, 2026 (FDA letter)")
        d = r.get("_d") or {}
        fad = d.get("fda_action_date")
        if fad and f"FDA action day {pretty(fad)}" not in txt:
            fails.append(f"/fda-decision/{slug}: line omits the FDA action day the row holds ({fad})")
        if not fad and d.get("decision_date_unsourced") and re.search(r"FDA action day [A-Z][a-z]+ \d", txt):
            fails.append(f"/fda-decision/{slug}: line states an FDA action day the row does not hold")
        goal_ok = str(r.get("dp") or "day") == "day" and not d.get("goal_unsourced")
        if goal_ok and f"Goal date {pretty(r['d'])}" not in txt:
            fails.append(f"/fda-decision/{slug}: line omits the sourced goal date {r['d']}")
        if not goal_ok and re.search(r"Goal date [A-Z][a-z]+ \d", txt):
            fails.append(f"/fda-decision/{slug}: line states a goal date the row cannot source")
        if goal_ok and not (d.get("source") or d.get("source_url")) and "source not recorded on this row" not in txt:
            fails.append(f"/fda-decision/{slug}: goal date shown as sourced but the row records no source")
        if f"Announcement {pretty(r['dcd'])}" not in txt:
            fails.append(f"/fda-decision/{slug}: line omits the announcement date {r['dcd']}")
        a2 = d.get("announcement_2") or {}
        if a2.get("date") and pretty(a2["date"]) not in txt:
            fails.append(f"/fda-decision/{slug}: line omits the second dateline {a2['date']} ({a2.get('who')})")
    if fails:
        print(f"FAIL: {len(fails)} Verified-against failure(s):")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} decision pages state their three dates with sources, and nothing the row does not hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
