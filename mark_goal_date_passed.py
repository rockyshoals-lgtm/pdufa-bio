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


def unpast_faq(doc):
    """Undo the past-tense FAQ sentence (when a row is decided, withdrawn or re-dated, the page's own builders own it)."""
    def _back(m):
        try:
            iso = dt.datetime.strptime(m.group(3), "%B %d, %Y").date().isoformat()
        except ValueError:
            return m.group(0)
        return f"The FDA PDUFA target date for {m.group(1)} ({m.group(2)}) is {iso} for "
    return re.sub(r"The FDA PDUFA goal date for ([A-Z]{1,6}) \(([^)]{1,120})\) was ([A-Z][a-z]+ \d{1,2}, \d{4}), "
                  r"which has passed[^.]*\. That goal date was for ", _back, doc)


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
            if r.get("type") == "PDUFA" and str(r.get("st") or "").lower() in ("decided", "withdrawn"):
                decided.add((str(r.get("t") or "").upper(), str(r.get("d") or "")[:10]))
    except Exception:
        pass
    # 2026-11-17 (urgent order, BLOCKED #83): the ledger was hand-written, so every goal date that passed without a
    # same-day decision froze CI (test_no_past_target_pending_pages) until a human edited it -- INO on Nov 1, CYTK/SMMT/
    # TEVA on Nov 15-17. Every day-dated pending PDUFA row past its goal now gets an AUTOMATIC entry. Its claim is
    # dated and names what was checked, which is what the watchers do every run; the hand ledger still wins (it carries
    # sponsor quotes, NRXP).
    hand = {e["slug"] for e in entries}
    auto = []
    try:
        for r in rows_ds:
            u = str(r.get("url") or "")
            if (r.get("type") == "PDUFA" and str(r.get("st") or "").lower() in ("upcoming", "awaiting")
                    and str(r.get("dp") or "day") == "day" and u.startswith("/pdufa/")
                    and str(r.get("d") or "")[:10] < today.isoformat()
                    and str((r.get("_d") or {}).get("goal_date") or "").lower() != "not announced"):
                slug = u.split("/")[2]
                if slug not in hand:
                    auto.append({"slug": slug, "goal_date": str(r["d"])[:10], "application_type": "application", "auto": True})
    except NameError:
        pass
    keep = []
    for e in entries + auto:
        slug = e["slug"]
        p = os.path.join(SITE, "pdufa", slug, "index.html")
        tk = slug.split("-")[0].upper()
        if (tk, str(e.get("goal_date") or "")[:10]) in decided:
            if os.path.isfile(p):
                doc = io.open(p, encoding="utf-8", errors="replace").read()
                new = doc
                if B in new:
                    new = new.split(B, 1)[0] + new.split(E, 1)[1]
                new = unpast_faq(new)
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
        # 2026-11-21: a sponsor can say BEFORE the goal date that the FDA will not act by it (Savara, Nov 20, for a
        # Nov 22 goal). That is a sourced fact about this page's own target, so it is stated from the announcement on,
        # not two days later. The application is still under review, so the pending-tense phrases stay as they are.
        miss_date = e.get("announced_miss_date")
        miss_text = _html.escape(str(e.get("announced_miss_text", "")))
        if dt.date.fromisoformat(goal) >= today and not (miss_date and miss_text
                                                         and dt.date.fromisoformat(miss_date) <= today):
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
        if miss_date and miss_text:
            headline = "FDA will not act by the goal date"
            was = "was" if dt.date.fromisoformat(goal) < today else "is"
            lead = (f"the FDA goal date for this {app} {was} <b>{pretty(goal)}</b>. On <b>{pretty(miss_date)}</b> "
                    f"{miss_text} No decision has been published as of {pretty(today.isoformat())}. ")
            story = " is under FDA review"
            faq = "candidate under FDA review"
        elif fc_date and fc_text:
            headline = "First-cycle review completed"
            lead = (f"the FDA goal date for this {app} was <b>{pretty(goal)}</b>; on "
                    f"<b>{pretty(fc_date)}</b> {fc_text} No approval has been published as of "
                    f"{pretty(today.isoformat())}. ")
            story = (f" was under FDA review with a goal date of {pretty(goal)}; on "
                     f"{pretty(fc_date)} {fc_text} It is intended")
            faq = (f"candidate whose FDA goal date was {pretty(goal)}; on {pretty(fc_date)} "
                   f"{fc_text} It is intended")
        elif e.get("auto"):
            headline = "Goal date passed"
            lead = (f"the FDA goal date for this application was <b>{pretty(goal)}</b>. As of "
                    f"{pretty(today.isoformat())} (Eastern), pdufa.bio has found no FDA decision or sponsor announcement "
                    f"for this application; sources checked: the FDA press and drug feeds, Drugs@FDA, the sponsor&#x27;s "
                    f"newsroom and EDGAR. ")
            story = (f" was under FDA review, with a goal date of {pretty(goal)} that has "
                     f"passed with no public decision,")
            faq = (f"candidate whose FDA goal date of {pretty(goal)} passed with no "
                   f"public decision,")
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
        # 2026-11-27 (Savara): the FAQ still answered "When is the SVRA PDUFA date?" with "The FDA PDUFA target date for
        # SVRA (Savara) is 2026-11-22", present tense, five days after that date passed. Once the goal date is behind us,
        # restate it in the past tense (visible FAQ and FAQPage JSON-LD carry the same sentence). Idempotent: the new
        # sentence carries no "as of" date, so a re-run leaves it unchanged.
        if dt.date.fromisoformat(goal) < today:
            if miss_date and miss_text:
                tail = (f"; on {pretty(miss_date)} the sponsor said the FDA would not act by it"
                        + (" and that the review is ongoing" if "ongoing" in miss_text.lower() else "")
                        + ", and no decision has been published")
            elif fc_date and fc_text:
                tail = f"; the sponsor disclosed a first-cycle action on {pretty(fc_date)} and no approval has been published"
            else:
                tail = ", with no decision published"
            new = re.sub(
                r"The FDA PDUFA target date for ([A-Z]{1,6}) \(([^)]{1,120})\) is " + re.escape(goal) + r" for ",
                lambda m: (f"The FDA PDUFA goal date for {m.group(1)} ({m.group(2)}) was {pretty(goal)}, which has "
                           f"passed{tail}. That goal date was for "), new)
        # 2026-11-21 red team: the sponsor says the FDA will not act by the goal date and gives no new date, so the page's
        # schema.org Event is postponed, not scheduled (EventPostponed: "postponed to a date not yet known").
        if miss_date and miss_text:
            new = re.sub(r'("eventStatus"\s*:\s*")https://schema\.org/EventScheduled(")',
                         r"\1https://schema.org/EventPostponed\2", new)
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
            n += 1
            print(f"  /pdufa/{slug}: goal date {goal} passed, stated (application "
                  f"type {app})")
    # Retire automatic blocks whose row is no longer pending past its goal (decided, withdrawn or re-dated): any
    # /pdufa page carrying the PASSED block that is neither a kept ledger entry nor a current automatic one.
    import glob as _glob
    active = {e["slug"] for e in keep}
    for p in _glob.glob(os.path.join(SITE, "pdufa", "*", "index.html")):
        slug = os.path.basename(os.path.dirname(p))
        if slug in active:
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if B not in doc:
            continue
        new = doc.split(B, 1)[0] + doc.split(E, 1)[1]
        new = re.sub(r" was under FDA review, with a goal date of [A-Z][a-z]+ \d{1,2}, \d{4} that has passed with no "
                     r"public decision,( to treat| for)", r" is under FDA review\1", new)
        new = re.sub(r"candidate whose FDA goal date of [A-Z][a-z]+ \d{1,2}, \d{4} passed with no public decision, for",
                     "candidate under FDA review for", new)
        new = unpast_faq(new)
        io.open(p, "w", encoding="utf-8").write(new)
        n += 1
        print(f"  /pdufa/{slug}: passed-banner retired (row no longer pending past its goal)")
    keep_hand = [e for e in keep if not e.get("auto")]
    if len(keep_hand) != len(entries):
        led = json.load(io.open(LEDGER, encoding="utf-8"))
        led["passed"] = keep_hand
        io.open(LEDGER, "w", encoding="utf-8").write(json.dumps(led, indent=1, ensure_ascii=False) + "\n")
    print(f"goal-date-passed: {n} page(s) updated from {len(entries)} ledger entr(ies)"
          + (f", {len(entries) - len(keep)} retired (decided)" if len(keep) != len(entries) else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
