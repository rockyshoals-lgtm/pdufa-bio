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
sys.path.insert(0, HERE)
from site_dates import eastern_today as _eastern_today   # noqa: E402  (one clock: Eastern)
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
    today = _eastern_today()
    n = 0
    # Audit 09-20 (found while working P0-A): the docstring said "when a decision is later
    # published ... the ledger entry is removed" and nothing ever removed it. /pdufa/TLX carried
    # "Goal date passed - no decision has been disclosed as of September 20, 2026" six days after
    # Pixclara's approval was published on the same page. A ledger entry whose dataset row is
    # Decided is retired here: block stripped, pending-tense phrases restored, entry dropped.
    decided = set()
    try:
        src_ds = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                         errors="replace").read().replace("\x00", "")
        rows_ds, _ = json.JSONDecoder().raw_decode(src_ds[src_ds.find("["):])
        for r in rows_ds:
            if r.get("type") == "PDUFA" and str(r.get("st") or "").lower() == "decided":
                decided.add((str(r.get("t") or "").upper(), str(r.get("d") or "")[:10]))
    except Exception:
        pass
    keep = []
    for e in entries:
        slug = e["slug"]
        p = os.path.join(SITE, "pdufa", slug, "index.html")
        tk = slug.split("-")[0].upper()
        if (tk, str(e.get("goal_date") or "")[:10]) in decided:
            if os.path.isfile(p):
                doc = io.open(p, encoding="utf-8", errors="replace").read()
                new = doc
                if B in new:
                    new = new.split(B, 1)[0] + new.split(E, 1)[1]
                g = pretty(e["goal_date"])
                for tail in (" to treat", " for"):
                    new = new.replace(f" was under FDA review, with a goal date of {g} that has "
                                      f"passed with no public decision,{tail}", " is under FDA review" + tail)
                new = new.replace(f"candidate whose FDA goal date of {g} passed with no public decision, for",
                                  "candidate under FDA review for")
                if new != doc:
                    io.open(p, "w", encoding="utf-8").write(new)
                    n += 1
            print(f"  /pdufa/{slug}: RETIRED -- the dataset row is Decided; passed-banner removed, "
                  f"ledger entry dropped")
            continue
        keep.append(e)
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
        # Audit 2026-09-07 C3 (after 09-06c): "passed with no public decision" was not what
        # the sponsor filed. When the ledger carries a first-cycle action (an FDA letter the
        # sponsor disclosed in a filing after the goal date), the page states THAT action,
        # dated, and says only that no approval has been published -- never "no decision".
        fc_date = e.get("first_cycle_date")
        fc_text = _html.escape(str(e.get("first_cycle_text", "")))
        if fc_date and fc_text:
            headline = "First-cycle review completed"
            lead = (f"the FDA goal date for this {app} was <b>{pretty(goal)}</b>; on "
                    f"<b>{pretty(fc_date)}</b> {fc_text} No approval has been published as of "
                    f"{pretty(today.isoformat())}. ")
            story = (f" was under FDA review with a goal date of {pretty(goal)}; on "
                     f"{pretty(fc_date)} {fc_text} It is intended")
            faq = (f"candidate whose FDA goal date was {pretty(goal)}; on {pretty(fc_date)} "
                   f"{fc_text} It is intended")
        else:
            headline = "Goal date passed"
            lead = (f"the FDA goal date for this {app} was <b>{pretty(goal)}</b> and no "
                    f"decision has been disclosed as of {pretty(today.isoformat())}. ")
            story = (f" was under FDA review, with a goal date of {pretty(goal)} that has "
                     f"passed with no public decision,")
            faq = (f"candidate whose FDA goal date of {pretty(goal)} passed with no "
                   f"public decision,")
        block = (
            f'{B}<div style="background:#0c1d38;border:1px solid #f0c86a;'
            f'border-radius:10px;padding:11px 14px;margin:10px 0 14px;font-size:14.5px">'
            f'<b style="color:#f0c86a">{headline}</b> &middot; ' + lead
            + (f"{note} " if note else "")
            + (f'<a href="{_html.escape(src)}" rel="nofollow" style="color:#9ec5ff">{lbl}</a>'
               if src else "")
            + (f'; <a href="{_html.escape(str(e["source_2"]))}" rel="nofollow" '
               f'style="color:#9ec5ff">{_html.escape(str(e.get("source_2_label", "sponsor release")))}</a>'
               if e.get("source_2") else "")
            + ("." if src else "")
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
        old_story = (f" was under FDA review, with a goal date of {pretty(goal)} that has "
                     f"passed with no public decision,")
        old_faq = f"candidate whose FDA goal date of {pretty(goal)} passed with no public decision,"
        for tail in (" to treat", " for"):
            new = new.replace(" is under FDA review" + tail, story + tail)
            if old_story != story:            # re-render: retire the earlier wording
                new = new.replace(old_story + tail, story + tail)
        new = new.replace("candidate under FDA review for", faq + " for")
        if old_faq != faq:
            new = new.replace(old_faq + " for", faq + " for")
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
    if len(keep) != len(entries):
        led = json.load(io.open(LEDGER, encoding="utf-8"))
        led["passed"] = keep
        io.open(LEDGER, "w", encoding="utf-8").write(json.dumps(led, indent=1, ensure_ascii=False) + "\n")
    print(f"goal-date-passed: {n} page(s) updated from {len(entries)} ledger entr(ies)"
          + (f", {len(entries) - len(keep)} retired (decided)" if len(keep) != len(entries) else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
