# -*- coding: utf-8 -*-
"""fix_stale_margin_note.py -- a decision page that names the FDA's action day does not also say it cannot.

Red team 2026-11-18. /fda-decision/CYTK-2026-11-16 was titled "Approved Nov 13, 2026, 1 Day Early" and its Verified
line read "FDA action day November 13, 2026 (NDA 219083 S-002)", yet its note under the key facts still said
"Cytokinetics' release, dated Monday November 16, does not state the FDA's action day, so no early or late margin is
stated." TEVA-2026-11-16 said the same beside "FDA action day November 13, 2026 (NDA 215390 S-003)". The note was
true when the page was built (the sponsors announced on the Monday; Drugs@FDA had not posted the supplements), and
nothing rewrote it once sync_fda_action_dates.py found the FDA's record.

Rule: on an /fda-decision page whose Verified line names both the FDA action day and the goal date, a sentence
"<Sponsor>'s release[, dated ...,] does not state the FDA's action day, so no [early or late ]margin is stated."
becomes "The FDA's own record dates the action <day>, <N days before|on|N days after> the goal date; <Sponsor>
announced it on <announcement day>." The dataset row's decision_note gets the same change when the row carries
fda_action_date and a day-precise goal date. Runs after the Verified line and the FDA record are on the page.
Idempotent. Guard: tests/test_no_stale_margin_note.py. Facts only; not investment advice.

    python fix_stale_margin_note.py [--dry-run]
"""
import argparse
import datetime as dt
import glob
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
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
LONG = r"[A-Z][a-z]+ \d{1,2}, \d{4}"
VER = re.compile(r"Verified against:</b>(.*?)<!--VERIFIED:END-->", re.S)
ACT = re.compile(r"FDA action day (" + LONG + r")")
ANN = re.compile(r"Announcement (" + LONG + r")")
GOAL = re.compile(r"Goal date (" + LONG + r")")
# the stale sentence, on a page (apostrophes raw or as &#x27;) and in a dataset note
APOS = r"(?:'|&#x27;|&#39;|’)"
STALE = re.compile(r"(?P<who>[A-Z][\w.&\- ]{0,40}?)" + APOS + r"s? release(?:, dated [^,<]{3,40},)? does not state the FDA"
                   + APOS + r"s action day, so no (?:early or late )?margin is (?:stated|computed)\.")
# 2026-11-27, PYPD-2026-11-24 (run 46065678522): the page written before Drugs@FDA posted the letter said "The FDA's
# own record of the action day had not been read when this page was published, so no early or late margin is given
# yet." and "pdufa.bio publishes a margin only from the FDA's own record of the action day, which had not been read
# when this page was published." (the FAQ and its schema too). Once the Verified line names the FDA day, both go.
UNREAD = re.compile(r"(?:The FDA" + APOS + r"s own record of the action day had not been read when this page was published, "
                    r"so no (?:early or late )?margin is (?:given|stated)(?: yet)?\.|pdufa\.bio publishes a margin only from "
                    r"the FDA" + APOS + r"s own record of the action day, which had not been read when this page was "
                    r"published\.)")
NOTE_STALE = re.compile(r"(?:the|[A-Z][\w.&\- ]{0,40}?" + APOS + r"s?) release does not state the FDA" + APOS
                        + r"s action day, so no (?:early or late )?margin is (?:stated|computed)")


def day(s):
    return dt.datetime.strptime(s, "%B %d, %Y").date()


def long_(d):
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def margin(action, goal):
    n = (goal - action).days
    if n == 0:
        return "on the goal date"
    return f"{abs(n)} day{'s' if abs(n) != 1 else ''} {'before' if n > 0 else 'after'} the goal date"


def fix_page(doc):
    v = VER.search(doc)
    if not v:
        return doc
    a, g, n = ACT.search(v.group(1)), GOAL.search(v.group(1)), ANN.search(v.group(1))
    if not (a and g):
        return doc
    action, goal = day(a.group(1)), day(g.group(1))

    def rep(m):
        who = m.group("who").strip()
        tail = f"; {who} announced it on {n.group(1)}" if n else ""
        return f"The FDA's own record dates the action {long_(action)}, {margin(action, goal)}{tail}."
    doc = STALE.sub(rep, doc)
    return UNREAD.sub(lambda m: f"The FDA's own record dates the action {long_(action)}, {margin(action, goal)}.", doc)


def fix_dataset(text):
    """Edit only the stale decision_note strings in place, so the rest of the file keeps its own escaping."""
    i, j = text.index("["), text.rindex("]") + 1
    rows = json.loads(text[i:j])
    n = 0
    for r in rows:
        d = r.get("_d") or {}
        note, fad, goal = d.get("decision_note") or "", d.get("fda_action_date") or r.get("fda_action_date"), r.get("d")
        if not (note and fad and goal and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(goal))
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(fad)) and NOTE_STALE.search(note)):
            continue
        action, g = dt.date.fromisoformat(fad), dt.date.fromisoformat(goal)
        said = f"the FDA's own record dates the action {long_(action)}, {margin(action, g)}"
        m = NOTE_STALE.search(note)
        if m.start() == 0 or note[:m.start()].rstrip().endswith((".", "!", "?")):
            said = said[0].upper() + said[1:]  # it opens a sentence
        fixed = note[:m.start()] + said + note[m.end():]
        for ascii_ in (False, True):
            was = '"decision_note": ' + json.dumps(note, ensure_ascii=ascii_)
            if was in text:
                text = text.replace(was, '"decision_note": ' + json.dumps(fixed, ensure_ascii=ascii_), 1)
                n += 1
                break
    return text, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    pages = []
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        new = fix_page(doc)
        if new != doc:
            pages.append(os.path.basename(os.path.dirname(p)))
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    rows = 0
    if os.path.exists(DATASET):
        text = io.open(DATASET, encoding="utf-8").read()
        new, rows = fix_dataset(text)
        if rows and not a.dry_run:
            io.open(DATASET, "w", encoding="utf-8", newline="").write(new)
    print(f"stale margin notes: {len(pages)} page(s) {'would change' if a.dry_run else 'fixed'}"
          + (f" ({', '.join(pages)})" if pages else "") + f"; {rows} dataset note(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
