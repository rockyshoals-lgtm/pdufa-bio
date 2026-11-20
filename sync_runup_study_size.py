# -*- coding: utf-8 -*-
"""One owner for the SIZE of the run-up study wherever prose states it.

Found 2026-09-19 (task #82): the same study was described as 1,849 events (home), 1,827 (/decisions,
/pricing, /vktx), 1,786 (/developers, the per-event T-120 series) and 1,888 (/fda-approval-rate,
"n=1,888, 73.5% first-cycle") -- five numbers for one dataset, four of them hand-typed in July and
never touched while the study grew nightly. The home board and /runup-by-year already read
runup_study_stats.json (written by runup_study_stats.py from pdufa_runup_bifrost_v2.csv every
CI run); this script brings the remaining prose under the same owner.

What each surface states and which statistic it is:
  /decisions            "N PDUFA decisions, 2020 to YYYY, R% approved"      n_events, approval_rate
  /pricing              "the N-event T-120->T+5 daily data"                 t120_coverage_n
                        (Pro's export is the per-event daily path; only events WITH a path count)
  /developers           "price path for N FDA decisions"                    t120_coverage_n
  /vktx                 "run-up study (N FDA decisions)"                    n_events
  /fda-approval-rate    headline rate + n + the 2024-26 by-year sentence     approval_rate, n_events,
                                                                             by_year
    The page used to call its figure a "first-cycle approval rate". The run-up dataset carries no
    review-cycle flag, so a first-cycle rate cannot be computed from it and the 73.5% / 1,888 had
    no reproducible source. The block now says what the number IS: the share of tracked PDUFA
    decisions (all review cycles) ending in approval. Resubmissions after a CRL are approved far
    more often than first submissions, so an all-cycle rate is the HIGHER of the two; the honest
    comparison to FDA's first-cycle reports says so.

Idempotent; runs after runup_study_stats.py in CI. tests/test_runup_study_size_one_owner.py
asserts the render.

    python sync_runup_study_size.py [--dry-run]
"""
import argparse
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
STATS = os.path.join(HERE, "runup_study_stats.json")


def load_stats():
    s = json.load(io.open(STATS, encoding="utf-8"))
    n = int(s["n_events"]); t120 = int(s["t120_coverage_n"]); rate = float(s["approval_rate"])
    y0, y1 = s["date_min"][:4], s["date_max"][:4]
    by = {y: v for y, v in (s.get("by_year") or {}).items()}
    # 2026-11-20: floor lowered from 1,500 when the research set was source-checked (1,671 -> ~1,120 events)
    if not (1000 <= n <= 5000 and 0 < t120 <= n and 50 <= rate <= 95):
        raise SystemExit(f"REFUSING: implausible stats n={n} t120={t120} rate={rate}")
    return n, t120, rate, y0, y1, by


def fmt(n):
    return f"{n:,}"


# 2026-11-20: the research set was checked row by row (runup_study_research_sources.json); the note says so. It must
# keep matching the pattern below ("Its events from 2020 to 2024 come from our research set ... has none.").
STUDY_NOTE = ("Its events from 2020 to 2024 come from our research set, each re-checked on 2026-11-20 against the FDA's "
              "records or a dated report of the action; every record below links its own page, which names its source "
              "or says plainly that it has none.")


FDA_RANGE = (75.0, 81.0)   # the FDA's first-cycle figure as /fda-approval-rate states it ("75-81%")


def gap_paragraph(rate):
    """The paragraph under the two rates on /fda-approval-rate, true for where our rate sits against the FDA's."""
    if rate < FDA_RANGE[0]:
        return ("<b>The gap is real, and it&rsquo;s the honest part.</b> Our rate sits below the FDA&rsquo;s even though "
                "ours counts every review cycle and the FDA&rsquo;s counts only the first: a resubmission after a CRL is "
                "approved far more often than a first submission, so an all-cycle rate is the flattering one, and ours is "
                "still lower. That is what you should expect: <b>our universe is publicly-traded biotech</b>, smaller "
                "sponsors, first-in-class assets, thinner CMC and clinical-operations budgets. The FDA&rsquo;s figure "
                "covers <i>all</i> NDAs and BLAs, including big-pharma supplements that are far easier to get through on "
                "the first pass.")
    if rate <= FDA_RANGE[1]:
        return ("<b>Ours sits inside the FDA&rsquo;s range.</b> The two are not the same measure: ours counts every "
                "review cycle and the FDA&rsquo;s counts only the first, and a resubmission after a CRL is approved far "
                "more often than a first submission. Our universe is <b>publicly-traded drugmakers</b>; the FDA&rsquo;s "
                "figure covers <i>all</i> NDAs and BLAs.")
    return ("<b>Why ours is higher.</b> The two are not the same measure. Ours counts every review cycle and the "
            "FDA&rsquo;s counts only the first, and a resubmission after a CRL is approved far more often than a first "
            "submission, so an all-cycle rate runs higher. Ours also counts a supplemental approval for a new use, which "
            "large drugmakers file often and usually win, the same as a first approval, and a CRL enters it only once the "
            "company or the FDA has made the letter public. Our universe is <b>publicly-traded drugmakers</b>, from small "
            "biotechs to the largest companies; the FDA&rsquo;s figure covers <i>all</i> NDAs and BLAs.")


def edit(rel, subs, dry):
    p = os.path.join(SITE, rel)
    if not os.path.exists(p):
        print(f"  SKIP {rel}: missing"); return 0
    t = io.open(p, encoding="utf-8", errors="replace").read()
    o = t
    for pat, repl in subs:
        t, k = re.subn(pat, repl, t, count=1)
        if k == 0:
            print(f"  WARN {rel}: anchor not found: {pat[:70]}")
    if t != o and not dry:
        io.open(p, "w", encoding="utf-8").write(t)
    print(f"  {rel}: {'updated' if t != o else 'already current'}")
    return int(t != o)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    n, t120, rate, y0, y1, by = load_stats()
    print(f"run-up study: n_events={fmt(n)} t120_coverage={fmt(t120)} approval_rate={rate:.1f}% ({y0}-{y1})")
    N, T = re.escape("") + r"\d{1,2},\d{3}", None  # a thousands-formatted count
    changed = 0

    changed += edit("decisions/index.html", [(
        r"(run-up study</a>, which is built for it: )\d{1,2},\d{3}( PDUFA decisions, 2020 to )\d{4}(, <b>)[\d.]+(% approved</b>)",
        rf"\g<1>{fmt(n)}\g<2>{y1}\g<3>{rate:.1f}\g<4>"), (
        # 2026-11-18 (design red team, change 5): the study's 2020 to 2024 events are not each checked against a
        # source, and some archive rows are inferred; the sentence after the study's size says so. "sour[c]e" matches
        # the old sentence without spelling it, so tests/test_provenance_badges.py does not read the pattern as the promise
        r"(% approved</b>\. )(?:Every record below links to its sour[c]e, and unverified ones say so on the page\.|"
        r"Its events from 2020 to 2024 come from our research set[^<]*?says plainly that it has none\.)",
        r"\g<1>" + STUDY_NOTE)], a.dry_run)

    # 2026-11-18 (design red team, change 11): /pricing said "1,618-event" while every other page says the study has
    # 1,684 events. Both are right (1,618 is the events with a full daily path), but nothing said so. Name the subset.
    changed += edit("pricing.html", [(
        r"(<b>Full run-up dataset</b>: )(?:the \d{1,2},\d{3}-event T-120&rarr;T\+5 daily data(?: \([^)]*\))?|T-120&rarr;T\+5 "
        r"daily data for [\d,]+ of the study&rsquo;s [\d,]+ events \((?:those with a full daily price path|those with "
        r"120 trading days of history before the decision; the days after fill in as they trade)\))",
        # red team: 1,618 counts events with 120 sessions of history before the decision (runup_study_stats.py);
        # the newest have no T+5 yet, so "a full daily price path" overstated it
        rf"\g<1>T-120&rarr;T+5 daily data for {fmt(t120)} of the study&rsquo;s {fmt(n)} events (those with 120 trading "
        "days of history before the decision; the days after fill in as they trade)")], a.dry_run)

    changed += edit("developers/index.html", [(
        r"(the (?:full )?daily T-120 &rarr; T\+5 price path for <b>)\d{1,2},\d{3}( FDA decisions</b>)(?: \(of the "
        r"study&rsquo;s [\d,]+(?:; the rest lack a full daily path|, those with 120 trading days of history before the "
        r"decision; the days after fill in as they trade)\))?",
        rf"the daily T-120 &rarr; T+5 price path for <b>{fmt(t120)}\g<2> (of the study&rsquo;s {fmt(n)}, those with 120 trading days of history before the "
        "decision; the days after fill in as they trade)")], a.dry_run)

    changed += edit("vktx/index.html", [(
        r'(<a href="/runup-by-year">run-up study</a> \()\d{1,2},\d{3}( FDA decisions\))',
        rf"\g<1>{fmt(n)}\g<2>")], a.dry_run)

    # /fda-approval-rate: headline block + sources line + the by-year sentence
    yrs = [y for y in ("2024", "2025", "2026") if y in by]
    parts = []
    for y in yrs:
        r = by[y]["approval_rate"]
        parts.append(f"{r:.1f}% in {y}" + (" so far" if y == y1 else ""))
    by_sentence = ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1] if parts else ""
    changed += edit("fda-approval-rate/index.html", [
        (r"(own number: )(?:first-cycle approval rate|approval rate, all review cycles)(</h2>)", r"\g<1>approval rate, all review cycles\g<2>"),
        (r'(<div class="lit" style="font-size:34px;font-weight:800;color:#46d17f">)[\d.]+%(</div>)',
         rf"\g<1>{rate:.1f}%\g<2>"),
        (r'(<div style="font-size:12px;color:#7c93b6">)[^<]*n=\d{1,2},\d{3}[^<]*(</div>)',
         rf"\g<1>approvals / (approvals + CRLs), all review cycles: our universe, n={fmt(n)}, {y0}-{y1}\g<2>"),
        # 2026-11-20: the gap paragraph follows the numbers. It said "ours is still lower" whatever the rate; after the
        # research set was source-checked (trial readouts logged as CRLs removed) ours is above the FDA's 75-81%.
        (r"(?s)<b>(?:The gap is real, and it&rsquo;s the honest part\.|Ours sits inside the FDA&rsquo;s range\.|"
         r"Why ours is higher\.)</b>.*?(?=<br><br>\s*We publish both numbers)", gap_paragraph(rate)),
        (r"(Our figure: )\d{1,2},\d{3}( FDA decisions on listed biotechs\.)(?: All review cycles, \d{4}(?:&ndash;|-)\d{4}; the run-up dataset carries no review-cycle flag, so we do not publish a first-cycle rate of our own\.)*",
         rf"\g<1>{fmt(n)}\g<2> All review cycles, {y0}-{y1}; the run-up dataset carries no review-cycle flag, so we do not publish a first-cycle rate of our own."),
        (r"We publish both numbers rather than (?:the flattering one|only ours)\.", "We publish both numbers rather than only ours."),
        (r"(the share of decisions ending in approval \(vs a Complete Response Letter\) ran )[^<]*?(, but note)",
         rf"\g<1>{by_sentence}\g<2>"),
    ], a.dry_run)

    print(f"{changed} page(s) changed" + ("  [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
