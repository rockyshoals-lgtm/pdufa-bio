# -*- coding: utf-8 -*-
"""Say so when an application's goal date has passed and no decision is public.

Audit 2026-09-06 NEW-2: /pdufa/NRXP sat 39 days past its 2026-07-29 goal date still
reading "KETAFREE is under FDA review", with no decision page, no dataset row and
nothing on any FDA surface either way. The decided-banner injector cannot help --
there is no decision to name. Silence is the wrong answer: the page's own stated
target had passed, and the honest sentence is that the date passed and no decision
has been disclosed, with whatever the sponsor last said about the review.

This renders that sentence from a hand-verified ledger (`_goal_date_passed.json`),
one entry per application, each carrying the sponsor or FDA primary source read at
write time. It is never automatic: a page saying "the FDA has not decided" is a
claim, and claims here are sourced.

Marker-bounded and idempotent (<!--PASSED:BEGIN/END-->). When a decision is later
published, the decided-banner injector takes over and the ledger entry is removed.
"""
import datetime as dt
import html as _html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
LEDGER = os.path.join(HERE, "_goal_date_passed.json")
B, E = "<!--PASSED:BEGIN-->", "<!--PASSED:END-->"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August",
       "September", "October", "November", "December"]


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month]} {d.day}, {d.year}"


def main():
    try:
        entries = json.load(io.open(LEDGER, encoding="utf-8")).get("passed", [])
    except Exception:
        print("goal-date-passed: no ledger, nothing to do")
        return 0
    today = dt.date.today()
    n = 0
    for e in entries:
        slug = e["slug"]
        p = os.path.join(SITE, "pdufa", slug, "index.html")
        if not os.path.isfile(p):
            print(f"  SKIP /pdufa/{slug}: page missing")
            continue
        goal = e["goal_date"]
        if dt.date.fromisoformat(goal) >= today:
            continue                      # not past yet
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        app = _html.escape(str(e.get("application_type", "application")))
        note = _html.escape(str(e.get("status_note", "")))
        src = str(e.get("source", ""))
        lbl = _html.escape(str(e.get("source_label", "the sponsor's release")))
        block = (
            f'{B}<div style="background:#0c1d38;border:1px solid #f0c86a;'
            f'border-radius:10px;padding:11px 14px;margin:10px 0 14px;font-size:14.5px">'
            f'<b style="color:#f0c86a">Goal date passed</b> &middot; the FDA goal date for '
            f'this {app} was <b>{pretty(goal)}</b> and no decision has been disclosed as of '
            f'{pretty(today.isoformat())}. '
            + (f"{note} " if note else "")
            + (f'<a href="{_html.escape(src)}" rel="nofollow" style="color:#9ec5ff">{lbl}</a>.'
               if src else "")
            + f"</div>{E}")
        if B in doc:
            new = doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
        else:
            anchor = "<!--FRESH:END-->" if "<!--FRESH:END-->" in doc else "</h1>"
            if anchor not in doc:
                print(f"  SKIP /pdufa/{slug}: no insertion anchor")
                continue
            new = doc.replace(anchor, anchor + block, 1)

        # The pending-tense template phrases are now false: the review window this page
        # describes has closed without a public decision. Restate, do not delete -- the
        # application IS still pending, but the page must say the date passed.
        new = new.replace(" is under FDA review to treat",
                          f" was under FDA review, with a goal date of {pretty(goal)} that has "
                          f"passed with no public decision, to treat")
        new = new.replace(" is under FDA review for",
                          f" was under FDA review, with a goal date of {pretty(goal)} that has "
                          f"passed with no public decision, for")
        new = new.replace("candidate under FDA review for",
                          f"candidate whose FDA goal date of {pretty(goal)} passed with no "
                          f"public decision, for")
        # An ANDA carries a GDUFA goal date, not a PDUFA date. Saying "PDUFA date" of an
        # ANDA is wrong by statute, and this site's whole product is dates being right.
        if str(e.get("application_type", "")).upper().startswith("ANDA"):
            # One string, several carriers: <title>, og:title, twitter:title and the
            # WebPage JSON-LD "name" all repeat it. Fixing only <title> leaves the wrong
            # statutory label in the two places social cards and schema consumers read
            # (found on the first run of this script, 2026-09-06).
            new = re.sub(r"([A-Z]{1,6}) PDUFA date: ",
                         lambda m: f"{m.group(1)} FDA goal date (ANDA): ", new)
            new = new.replace("FDA PDUFA target date", "FDA goal date (ANDA)")
            new = new.replace(f"When is the {slug.split('-')[0]} PDUFA date?",
                              f"When is the {slug.split('-')[0]} FDA goal date?")
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
            n += 1
            print(f"  /pdufa/{slug}: goal date {goal} passed, stated (application "
                  f"type {app})")
    print(f"goal-date-passed: {n} page(s) updated from {len(entries)} ledger entr(ies)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
