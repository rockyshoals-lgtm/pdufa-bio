# -*- coding: utf-8 -*-
"""inject_verified_against.py -- one "Verified against" line on every decision page (audit 2026-10-18, order 1).

Three dates, three sources, one sentence, placed right under the decision banner so it is the line an answer
engine lifts when it wants to be right about "October 15 or 16":

  Verified against: FDA action day October 14, 2026 (FDA approval notification) · Announcement October 14, 2026
  (ImmunityBio 8-K) · Goal date January 6, 2027 (ImmunityBio 8-K, August 4, 2026).

Each part states only what the row holds:
  * FDA action day: _d.fda_action_date with its record (_d.fda_action_record / fda_action_source_url). When the
    row's decision date is only an announcement (decision_date_unsourced, no fda_action_date): "FDA action day:
    not yet posted on Drugs@FDA".
  * Announcement: dcd with the announcing party and its URL (_d.announcement / announcement_url, else
    decision_source). A second dateline (_d.announcement_2, e.g. Roche's Basel release the day after Genentech's)
    is named too, so the reader sees why two dates circulate.
  * Goal date: the row's d with _d.source (and source_url); only when day-precision and not goal_unsourced,
    otherwise "Goal date: none sourced".
Marker-bounded (<!--VERIFIED:BEGIN-->...<!--VERIFIED:END-->), idempotent. Only /fda-decision/{T}-{dcd} pages that
a dataset row points at are written.

    python inject_verified_against.py [--dry-run]
"""
import argparse
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--VERIFIED:BEGIN-->", "<!--VERIFIED:END-->"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
       "November", "December"]


def pretty(iso):
    try:
        y, m, d = (int(x) for x in str(iso)[:10].split("-"))
        return f"{MON[m]} {d}, {y}"
    except Exception:  # noqa: BLE001
        return str(iso)


def esc(s):
    return html.escape(str(s or ""), quote=True)


def link(label, url):
    return f'<a href="{esc(url)}" rel="noopener" style="color:#e3ba5e">{esc(label)}</a>' if url else esc(label)


def short_source(s):
    """The source's name only; its date is stated once, before the parenthesis."""
    s = re.sub(r"\s*\(.*?\)\s*", " ", str(s or "")).strip()
    s = re.sub(r",?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)"
               r" \d{1,2},? \d{4}.*$", "", s)
    s = re.sub(r",?\s+\d{4}-\d{2}-\d{2}.*$", "", s)
    return s.strip(" ,")[:70]


def line(r):
    d = r.get("_d") or {}
    parts = []
    fad = d.get("fda_action_date")
    if fad:
        rec = d.get("fda_action_record") or "FDA record"
        parts.append(f"FDA action day {pretty(fad)} ({link(short_source(rec), d.get('fda_action_source_url'))})")
    elif d.get("decision_date_unsourced"):
        parts.append("FDA action day not yet posted on Drugs@FDA")
    dcd = r.get("dcd")
    if dcd:
        who = d.get("announcement") or d.get("decision_source") or "sponsor announcement"
        url = d.get("announcement_url") or d.get("decision_source_url")
        a = f"Announcement {pretty(dcd)} ({link(short_source(who), url)})"
        a2 = d.get("announcement_2") or {}
        if a2.get("date") and a2.get("who"):
            a += f"; also {link(esc(a2['who']), a2.get('url'))}, dated {pretty(a2['date'])}"
        parts.append(a)
    goal = r.get("d")
    if goal and str(r.get("dp") or "day") == "day" and not d.get("goal_unsourced") and (d.get("source") or d.get("source_url")):
        parts.append(f"Goal date {pretty(goal)} ({link(short_source(d.get('source') or 'sponsor filing'), d.get('source_url'))})")
    elif goal and str(r.get("dp") or "day") == "day" and not d.get("goal_unsourced"):
        parts.append(f"Goal date {pretty(goal)} (source not recorded on this row)")
    elif (goal and str(r.get("dp")) == "month" and not d.get("goal_unsourced") and (d.get("source") or d.get("source_url"))
          and d.get("source_url") not in (d.get("decision_source_url"), d.get("fda_action_source_url"))
          and not re.search(r"never sourced|not sourced|no .* states (?:it|a goal)", str(d.get("date_note") or ""), re.I)):
        # 2026-10-19 (Jemperli LARC): GSK stated the goal as "February 2027". A sourced month is a fact worth
        # naming; it is still not a day, so no margin is computed anywhere and this line says "month". A row
        # whose `source` is its own decision letter (HYRNUO: date_note "never sourced") does not qualify.
        y, m = (int(x) for x in str(goal)[:7].split("-"))
        parts.append(f"Goal month {MON[m]} {y}, no day stated ({link(short_source(d.get('source') or 'sponsor filing'), d.get('source_url'))})")
    else:
        parts.append("Goal date none sourced")
    return (f'{B}<p class="note" style="margin:6px 0 10px;font-size:12.5px;color:#a7bcd9">'
            f'<b style="color:#cfe0f5">Verified against:</b> ' + " &middot; ".join(parts) + f'.</p>{E}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    n = changed = 0
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st")) != "Decided" or not r.get("dcd"):
            continue
        slug = f"{str(r.get('t') or '').upper()}-{str(r['dcd'])[:10]}"
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        block = line(r)
        # strip any earlier placement, then insert after the fact-first lede when one is present (the lede must sit
        # directly under the banner for test_decision_lede_fact_first), else directly after the banner.
        doc0 = re.sub(re.escape(B) + ".*?" + re.escape(E) + r"\s*", "", doc, flags=re.S)   # 2026-10-24: and the whitespace after it (newlines were accumulating, one per run, against build_decision_lede)
        m = re.search(r'<div class="ban (?:ap|cr|wd)[^"]*">.*?</div>\s*(?:<!--FACTLEDE:BEGIN-->.*?<!--FACTLEDE:END-->)?', doc0, re.S)
        if not m:
            continue
        new = doc0[:m.end()] + block + doc0[m.end():]
        n += 1
        if new != doc:
            changed += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(new)
    print(f"verified-against line: {n} decision page(s) carry it, {changed} written" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
