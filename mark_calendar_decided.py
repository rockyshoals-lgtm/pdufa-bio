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
# The ticker cell may carry a DUAL label for a partner-listed event -- "NUVL / RPRX", "OTSKY /
# CNS". Those rows were invisible to this script (2026-08-22), so a dual-listed event stayed
# pending after it decided. Capture the whole label, look the decision up under the FIRST ticker
# (the one whose decision page exists), and write the label back unchanged.
TKLABEL = r'([A-Z]{1,6}(?:\s*/\s*[A-Z]{1,6})?)'
ROW = re.compile(
    r'<a class="row"([^>]*)>\s*<div class="t">' + TKLABEL + r'\s*' + SEP +
    r'\s*(\d{4}-\d{2}-\d{2})</div>'
    r'<div class="d">(.*?)</div>\s*</a>', re.S)
# ALREADY-MARKED rows: div.t carries the outcome span after the date, so ROW cannot match them.
MARKED = re.compile(
    r'<a class="row"([^>]*data-dec[^>]*)>\s*<div class="t">([A-Z]{1,6})\s*' + SEP +
    r'\s*(\d{4}-\d{2}-\d{2})\s*(<span[^>]*>[^<]*</span>)</div>'
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
        # the decision's own drug text, used ONLY to reject a clearly-different molecule on an
        # early carry-forward (see match_decision) -- never to require a match
        # Cut at this row's OWN closing anchor. A fixed-width slice bled into the NEXT row
        # ("...Cream 0.3 UNCY - 2026-06-30"), which both truncated the strength and offered a
        # neighbouring drug's name for matching.
        seg = html[m.end():m.end() + 400]
        seg = seg.split("</a>", 1)[0]
        drug = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", seg))
        drug = re.split(r"(?:Approved|CRL)\s*:?\s*", drug, maxsplit=1)[-1].strip()
        by_tk.setdefault(tk, []).append((date, outcome, drug[:90]))
    return by_tk


# How far BEFORE a scheduled date an FDA action may sit and still be that application's outcome.
# The FDA is not obliged to use its full clock and frequently does not: Corcept's relacorilant was
# approved 108 days before its PDUFA date, Arvinas's vepdegestrant 35 days before. With only the
# symmetric 14-day window, both sat on the calendar as pending months after they had resolved, and
# no check anywhere noticed, because "no match" and "nothing to do" produced identical output.
EARLY_WINDOW = 270


def strengths(s):
    """Dose strengths stated in a drug string: '0.05%', '150 mg', or a bare decimal.

    The bare-decimal case is needed because the listing text is truncated and often loses the
    unit: ARQT's archive row reads "ZORYVE (roflumilast) Cream 0.3" with the % cut off, while
    the calendar row reads "cream 0.05%". Those are two different products and must not match.
    """
    txt = str(s or "")
    return (set(re.findall(r"(\d+(?:\.\d+)?)\s*(?:%|mg|mcg|ug|g/|units)", txt, re.I))
            | set(re.findall(r"\b(\d+\.\d+)\b", txt)))


def match_decision(by_tk, tk, caldate, caldate_desc=""):
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
    has to work. So names are never REQUIRED to match -- they are only used to REJECT, and only
    on a far-away carry-forward, per the multi-product rule below.

    THE MULTI-PRODUCT RULE (2026-08-22). BMY's 2026-08-17 iberdomide row was marked "Approved"
    and linked to BMY-2026-06-01 -- Camzyos (mavacamten), a different molecule 77 days earlier --
    because the early branch accepted ANY approval by that ticker inside 270 days. For a sponsor
    with nine decisions on file that is guaranteed to mislabel, and it published an FDA approval
    against the wrong drug. An early carry-forward that is further away than WINDOW now requires
    EITHER a shared drug token OR that the ticker has exactly one decision in the early window
    (the single-product case this rule was written for: Corcept, Arvinas). Multi-product sponsors
    must produce a real name overlap.
    """
    cd = dt.date.fromisoformat(caldate)
    is_past = cd < dt.date.today()

    def toks(s):
        return {w for w in re.findall(r"[a-z]{5,}", str(s or "").lower())
                if w not in ("combination", "injection", "tablets", "therapy", "approved",
                             "priority", "review", "solution", "capsules", "vs")}
    row_toks = toks(caldate_desc)
    in_early = [d for d, o, _g in by_tk.get(tk, [])
                if o != "crl" and -EARLY_WINDOW <= (dt.date.fromisoformat(d) - cd).days <= 0]
    sole_product = len(in_early) <= 1

    # CROSS-TICKER MATCHING WAS TRIED AND REJECTED (2026-08-22). Dual-listed rows (RPRX's row for
    # Nuvalent's zidesamtinib) have no decision under their own ticker, so a fallback that
    # searched every OTHER ticker on a drug-token match was written. Previewed before applying,
    # it produced eight matches and every one was wrong: rows matched on shared vocabulary --
    # "unresectable", "once-weekly", "ophthalmic", and worst of all "deruxtecan", the shared
    # payload suffix that made MRK's ifinatamab deruxtecan match AZN's datopotamab deruxtecan.
    # Requiring the first token instead would have rejected the one true case (zidesamtinib vs
    # JIDEYTRO). There is no safe automatic rule here, so partner rows are left pending and a
    # human links them; publishing a wrong approval is far worse than a late one.
    candidates = [(d, o, g, tk) for d, o, g in by_tk.get(tk, [])]
    if not candidates:
        return None

    best = None
    for date, outcome, drugtext, dec_tk in candidates:
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
        # FUTURE rows may now be early-marked too, but ONLY on a drug-name match (2026-08-22).
        # Nuvalent's zidesamtinib was approved 2026-07-22, 58 days before its September 18 goal
        # date, and the calendar carried it as pending for a month because early marking was
        # restricted to past-dated rows. Requiring the row and the decision to name the same drug
        # makes forward marking safe: it cannot borrow an unrelated approval by the same sponsor,
        # which is the failure the past-only restriction existed to prevent.
        # A brand can have several applications in flight at different STRENGTHS: ARQT's row is
        # "ZORYVE (roflumilast) cream 0.05%" with a 2027 goal date, while the archive holds
        # "ZORYVE (roflumilast) Cream 0.3%" approved 2026-06-30. The names match perfectly and
        # the products are different, which is exactly why the later date exists. When both sides
        # state a strength and the strengths disagree, they are not the same application.
        rs, ds_ = strengths(caldate_desc), strengths(drugtext)
        name_match = bool(row_toks & toks(drugtext)) and not (rs and ds_ and not (rs & ds_))
        early_ok = (-EARLY_WINDOW <= signed <= 0 and outcome != "crl"
                    and (is_past or name_match))
        # ...and, when it is a FAR carry-forward, the multi-product rule above.
        if early_ok and not near and not sole_product and not name_match:
            continue

        if (near or early_ok) and (best is None or gap < best[0]):
            best = (gap, date, outcome, dec_tk)
    return (best[1], best[2], best[3]) if best else None


def strip_marker(dtext):
    """Remove a previously-injected outcome span so re-marking never stacks."""
    return re.sub(r'^\s*<span style="color:#[0-9a-fA-F]{6};font-weight:700">[^<]*</span>\s*: \s*', "", dtext)


def mark_page(path, by_tk, dry):
    html = open(path, encoding="utf-8").read()
    changed = [0]
    reverted = [0]

    # RE-VALIDATION PASS (2026-08-22). "Already marked -> leave as-is" made a bad mark permanent:
    # BMY's 2026-08-17 iberdomide row kept asserting an approval linked to Camzyos's June decision.
    # ROW cannot see marked rows (their div.t carries the outcome span), so marked rows need their
    # own pattern. A mark the CURRENT rule would not produce is relinked or returned to pending.
    def reval(m):
        attrs, tk, caldate, span, dtext = m.groups()
        body_now = strip_marker(dtext)
        hit = match_decision(by_tk, tk, caldate, body_now)
        cur = re.search(r'href="/fda-decision/[A-Z]{1,6}-(\d{4}-\d{2}-\d{2})"', attrs)
        if hit and cur and cur.group(1) == hit[0]:
            return m.group(0)                                   # still correct
        if not hit:
            reverted[0] += 1
            print(f"  REVERTED {tk} {caldate}: decision link {cur.group(1) if cur else '?'} no "
                  f"longer validates under the multi-product rule -- row returned to pending")
            return (f'<a class="row" href="/pdufa/{tk}"><div class="t">{tk} &middot; {caldate}'
                    f'</div><div class="d">{body_now}</div></a>')
        decdate, outcome, dec_tk = hit
        col = GREEN if outcome == "ap" else RED
        icon = "✓" if outcome == "ap" else "✗"
        word = "Approved" if outcome == "ap" else "CRL"
        reverted[0] += 1
        print(f"  RELINKED {tk} {caldate}: {cur.group(1) if cur else '?'} -> {decdate}")
        return (f'<a class="row" data-dec="1" href="/fda-decision/{dec_tk}-{decdate}">'
                f'<div class="t">{tk} &middot; {caldate} '
                f'<span style="color:{col};font-weight:700">{icon}</span></div>'
                f'<div class="d"><span style="color:{col};font-weight:700">{word}</span>: '
                f'{body_now}</div></a>')

    html = MARKED.sub(reval, html)

    def repl(m):
        attrs, label, caldate, dtext = m.group(1), m.group(2), m.group(3), m.group(4)
        tk = label.split("/")[0].strip()          # dual labels resolve on the first ticker
        hit = match_decision(by_tk, tk, caldate, strip_marker(dtext))
        if not hit:
            return m.group(0)
        decdate, outcome, dec_tk = hit
        col = GREEN if outcome == "ap" else RED
        icon = "✓" if outcome == "ap" else "✗"
        word = "Approved" if outcome == "ap" else "CRL"
        body = strip_marker(dtext)
        changed[0] += 1
        return (f'<a class="row" data-dec="1" href="/fda-decision/{dec_tk}-{decdate}">'
                f'<div class="t">{label} &middot; {caldate} '
                f'<span style="color:{col};font-weight:700">{icon}</span></div>'
                f'<div class="d"><span style="color:{col};font-weight:700">{word}</span>: {body}</div></a>')

    new = ROW.sub(repl, html)
    if (changed[0] or reverted[0]) and not dry:
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
