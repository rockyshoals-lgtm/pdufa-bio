# -*- coding: utf-8 -*-
"""mark_calendar_decided.py -- mark decided PDUFAs on every calendar page.

The calendar pages list SCHEDULED PDUFA dates. Once a catalyst decides, its row should show the
outcome and link to the decision page instead of sitting there as if still pending. This scans the
decisions archive and, for any calendar row whose ticker has a decision within +/-14 days of the
scheduled date (so OTLK scheduled 07-29 -> decided 07-24 is caught), rewrites that row as
Approved (green check) / CRL (red x), linked to /fda-decision/{T}-{decision-date}.

Idempotent: a marked row carries data-dec="1" and is skipped on re-run. Safe to run every rebuild.
Uses inline styles for the marker so no per-page CSS edits are needed.

    python mark_calendar_decided.py [--dry-run]
"""
import argparse, glob, os, re
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DECISIONS = os.path.join(SITE, "decisions", "index.html")
WINDOW = 14  # days: how far a decision date may sit from the scheduled calendar date to still match

GREEN, RED = "#5fd07a", "#ff8f6b"
# The separator must match BOTH the HTML entity and the literal character.
#
# This is the bug that made this script a no-op. The pages once wrote "VTRS &middot; 2026-07-30";
# somewhere along the way they started writing the literal "VTRS · 2026-07-30", and this regex only
# knew the entity. So the script matched zero rows, printed "0 calendar row(s) marked decided", and
# exited 0. Every PDUFA that decided after that point sat on the calendar as if still pending, and
# nothing anywhere reported a problem. VTRS was approved on 2026-07-29, had a published decision
# page, and was still listed as an upcoming July decision days later.
#
# A silent no-op is the worst failure mode for a maintenance script: it looks like there was simply
# nothing to do. Hence both the widened pattern and the loud check in main().
SEP = r'(?:&middot;|·|&#183;)'
ROW = re.compile(
    r'<a class="row"([^>]*)>\s*<div class="t">([A-Z]{1,6})\s*' + SEP + r'\s*(\d{4}-\d{2}-\d{2})</div>'
    r'<div class="d">(.*?)</div>\s*</a>', re.S)


def load_decisions():
    """ticker -> list of (date, outcome) from the decisions archive."""
    html = open(DECISIONS, encoding="utf-8").read()
    by_tk, seen = {}, set()
    for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', html):
        tk, date = m.group(1), m.group(2)
        if (tk, date) in seen:
            continue
        seen.add((tk, date))
        tail = html[m.end():m.end() + 200].lower()
        outcome = "crl" if ("crl" in tail or "complete response" in tail) else "ap"
        by_tk.setdefault(tk, []).append((date, outcome))
    return by_tk


# How far BEFORE a scheduled date an FDA action may sit and still be that application's outcome.
# The FDA is not obliged to use its full clock and frequently does not: Corcept's relacorilant was
# approved 108 days before its PDUFA date, Arvinas's vepdegestrant 35 days before. With only the
# symmetric 14-day window, both sat on the calendar as pending months after they had resolved, and
# no check anywhere noticed, because "no match" and "nothing to do" produced identical output.
EARLY_WINDOW = 270


def match_decision(by_tk, tk, caldate):
    """Return (decision_date, outcome) for the decision this calendar row is waiting on.

    Two regimes, and the split is deliberately conservative:

      FUTURE-dated row  -> only a decision within WINDOW days counts. A row that has not come due
                           must never be marked from an older, unrelated decision by the same
                           company. Several issuers here have three open applications at once.
      PAST-dated row    -> a row whose date has passed with no outcome is stale by definition, so
                           accept the closest decision up to EARLY_WINDOW days BEFORE it. Early
                           action is the normal case this is fixing.

    Matching on drug name was tried and is not reliable: the calendar row for Arvinas says
    "ARV-471" while the decision says "VEPPANU (vepdegestrant)", the development code against the
    approved brand. Names diverge exactly when a drug gets approved, which is precisely when this
    has to work.
    """
    if tk not in by_tk:
        return None
    cd = dt.date.fromisoformat(caldate)
    is_past = cd < dt.date.today()
    best = None
    for date, outcome in by_tk[tk]:
        signed = (dt.date.fromisoformat(date) - cd).days      # negative = decided early
        gap = abs(signed)

        near = gap <= WINDOW
        # An EARLY decision may only be carried forward when it ENDED the application.
        #
        # An approval terminates the review, so a later scheduled date for that drug is simply
        # stale and should show the approval. A Complete Response Letter does the opposite: it is
        # the reason a later date exists at all, because the company resubmits and the FDA sets a
        # fresh clock. Carrying a CRL forward therefore reports the previous cycle's rejection as
        # though it were the outcome of a review that has not happened yet.
        #
        # This is not hypothetical. Replimune's RP1 was rejected on 2026-04-10, resubmitted, and
        # given a new 2026-08-02 action date. The first version of this rule marked the August row
        # "CRL" and linked April's letter, announcing an FDA decision that the FDA had not made.
        early_ok = is_past and -EARLY_WINDOW <= signed <= 0 and outcome != "crl"

        if (near or early_ok) and (best is None or gap < best[0]):
            best = (gap, date, outcome)
    return (best[1], best[2]) if best else None


def strip_marker(dtext):
    """Remove a previously-injected outcome span so re-marking never stacks."""
    return re.sub(r'^\s*<span style="color:#[0-9a-fA-F]{6};font-weight:700">[^<]*</span>\s*: \s*', "", dtext)


def mark_page(path, by_tk, dry):
    html = open(path, encoding="utf-8").read()
    changed = [0]

    def repl(m):
        attrs, tk, caldate, dtext = m.group(1), m.group(2), m.group(3), m.group(4)
        if "data-dec=" in attrs:
            return m.group(0)  # already marked -> leave as-is (idempotent)
        hit = match_decision(by_tk, tk, caldate)
        if not hit:
            return m.group(0)
        decdate, outcome = hit
        col = GREEN if outcome == "ap" else RED
        icon = "✓" if outcome == "ap" else "✗"
        word = "Approved" if outcome == "ap" else "CRL"
        body = strip_marker(dtext)
        changed[0] += 1
        return (f'<a class="row" data-dec="1" href="/fda-decision/{tk}-{decdate}">'
                f'<div class="t">{tk} &middot; {caldate} '
                f'<span style="color:{col};font-weight:700">{icon}</span></div>'
                f'<div class="d"><span style="color:{col};font-weight:700">{word}</span>: {body}</div></a>')

    new = ROW.sub(repl, html)
    if changed[0] and not dry:
        open(path, "w", encoding="utf-8").write(new)
    return changed[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    by_tk = load_decisions()
    pages = sorted(glob.glob(os.path.join(SITE, "calendar", "**", "index.html"), recursive=True))
    total = 0
    for p in pages:
        n = mark_page(p, by_tk, a.dry_run)
        if n:
            print(f"  {'would mark' if a.dry_run else 'marked'} {n:3d}  {os.path.relpath(p, SITE)}")
        total += n
    print(f"{'DRY RUN ' if a.dry_run else ''}{total} calendar row(s) marked decided across {len(pages)} pages "
          f"({sum(len(v) for v in by_tk.values())} decisions known).")

    # Did this script actually see the calendar at all?
    #
    # It reported "0 rows marked" for weeks while VTRS sat approved-but-listed-as-pending, because
    # the separator in the row markup changed and the pattern silently stopped matching. Counting
    # zero and counting nothing look identical in the output, so report them separately: if the
    # pattern matches no rows on pages that plainly contain rows, the pattern is broken, not the
    # data. Also name any past-dated row still unmarked, which is either a decision we have not
    # published or a match we are missing.
    seen_rows = past_unmarked = 0
    today = dt.date.today().isoformat()
    for p in pages:
        html = open(p, encoding="utf-8", errors="replace").read()
        # Count only rows NOT already marked. A fully-marked page legitimately matches nothing,
        # because a marked row carries extra markup inside div.t. Warning on that would make the
        # check cry wolf on exactly the pages where the script has done its job.
        unmarked = len(re.findall(r'<a class="row"(?![^>]*data-dec)', html))
        matched = len(ROW.findall(html))
        seen_rows += matched
        if unmarked and not matched:
            print(f"  WARNING: {os.path.relpath(p, SITE)} has {unmarked} UNMARKED row anchor(s) but "
                  f"the row pattern matched none. The markup has changed and this script is a no-op "
                  f"on that page.")
        for _attrs, tk, d, _desc in ROW.findall(html):
            if d < today:
                past_unmarked += 1
                if past_unmarked <= 8:
                    print(f"  past-dated and still unmarked: {tk} {d}  "
                          f"({os.path.relpath(p, SITE)})")

    if past_unmarked:
        print(f"  {past_unmarked} past-dated row(s) carry no outcome. Each is either a decision we "
              f"have not verified and published yet, or one this script failed to match.")
    if not seen_rows:
        print("  WARNING: the row pattern matched NOTHING anywhere. Treat this as a failure, not "
              "as 'no work to do'.")


if __name__ == "__main__":
    main()
