# -*- coding: utf-8 -*-
"""sync_decision_runup_chip.py -- each decision page's run-up figures are the run-up study's figures for that event.

Found 2026-11-18: 306 of 336 /fda-decision pages carried a "T-120 run-up (low→high)" chip whose percentage did not
match its own price range (LLY Jan 15, 2025: "+1.0% ($725.72→$932.06)", a 28% range), and matched neither the study's
T-120-to-eve nor its T-120-to-peak figure. The chip came from the old app's whole-number field and was never
recomputed. The 159 newer pages carry "120-day run-up (T-120→T-1)" from build_decision_page.py's own price window,
anchored on the decision day rather than the eve, and 147 of them differ from the study by up to several points.
The run-up study (pdufa_runup_bifrost_v2.csv) is the one measurement of these events; this step writes its figures
onto every page, in one vocabulary:

    120-day run-up (T-120→T-1)   -15.2%   (study T-120_T-1: close 120 sessions before the eve, to the eve)
    Decision-day move            +0.2%    (study post_1d: first session on/after the decision vs the eve)

A page with the old chip whose event is not in the study (unverified, excluded, or not measurable) loses that chip
rather than keep a figure nobody measured; a newer page not in the study keeps its own measured figure.

2026-11-18 (design red team, change 10): the 159 newer pages gave the run-up and the cohort's typical move but never
this event's own move (GSK Nov 17: the FAQ said "moved -2.3%" of the run-up; the decision day itself was nowhere).
Every page whose event the study measured now carries "Decision-day move", and every such page says what the move
is measured on, in a row of its own:

    Move measured on             2026-11-17 close, against the 2026-11-16 close

(the study's eve_date; a page day that is not a trading day reads "close on the first trading day after ...").
fix_chart_captions.py, which runs later, writes the same row with the same function. Runs after
runup_study_stats.py and before build_decision_faq.py (which quotes these chips), every rebuild. Idempotent.
tests/test_runup_study_current.py fails if a page's figures differ from the study.

    python sync_decision_runup_chip.py [--dry-run]
"""
import argparse
import csv
import glob
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")

OLD_CHIP = re.compile(r'<div class="kv"><span>T-120 run-up \(low→high\)</span><b>[^<]*</b></div>')
RUN_CHIP = re.compile(r'(<div class="kv"><span>120-day run-up \(T-120→T-1\)</span><b>)[^<]*(</b></div>)')
DAY_CHIP = re.compile(r'(<div class="kv"><span>Decision-day move</span><b>)[^<]*(</b></div>)')
DAY_ROW = re.compile(r'<div class="kv"><span>Decision-day move</span><b>[^<]*</b></div>'
                     r'(?:\s*<div class="kv"><span>Move measured on</span><b>[^<]*</b></div>)?')
BASIS_ROW = re.compile(r'\s*<div class="kv"><span>Move measured on</span><b>[^<]*</b></div>')
RUN_ROW = re.compile(r'<div class="kv"><span>120-day run-up \(T-120→T-1\)</span><b>[^<]*</b></div>')
OUTCOME_ROW = re.compile(r'<div class="kv"><span>Outcome</span><b[^>]*>.*?</b></div>', re.S)


def _nth(year, month, weekday, n):
    """The n-th weekday (0=Mon) of a month; n=-1 is the last."""
    import datetime as dt
    if n > 0:
        d = dt.date(year, month, 1)
        d += dt.timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))
        return d
    d = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d, saturday_back=True):
    import datetime as dt
    if d.weekday() == 5:
        return d - dt.timedelta(days=1) if saturday_back else None
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d


def nyse_closed(iso):
    """True when the NYSE did not trade that day: weekends, its standing holidays (the rules it publishes), and the
    two national days of mourning since 2018. Used only to say which session a move is measured on."""
    import datetime as dt
    d = dt.date.fromisoformat(iso)
    if d.weekday() >= 5:
        return True
    y = d.year
    # Easter (anonymous Gregorian algorithm); Good Friday is two days before it
    a, b, c = y % 19, y // 100, y % 100
    h = (19 * a + b - b // 4 - (b - (b + 8) // 25 + 1) // 3 + 15) % 30
    ll = (32 + 2 * (b % 4) + 2 * (c // 4) - h - c % 4) % 7
    m = (a + 11 * h + 22 * ll) // 451
    month, day = divmod(h + ll - 7 * m + 114, 31)
    easter = dt.date(y, month, day + 1)
    days = {_observed(dt.date(y, 1, 1), saturday_back=False), _nth(y, 1, 0, 3), _nth(y, 2, 0, 3),
            easter - dt.timedelta(days=2), _nth(y, 5, 0, -1), _observed(dt.date(y, 7, 4)), _nth(y, 9, 0, 1),
            _nth(y, 11, 3, 4), _observed(dt.date(y, 12, 25))}
    if y >= 2022:
        days.add(_observed(dt.date(y, 6, 19)))
    days |= {dt.date(2018, 12, 5), dt.date(2025, 1, 9)}
    return d in days


def basis_text(day, eve, announced=False, after_close=False):
    """What "Decision-day move" is measured on: the study's post_1d is the close of the first session on or after the
    page's day, against the eve's close. When the page's own Announced row puts the news after that day's close
    (NVO-2026-03-26), the move predates the news, and the row says so."""
    tag = " (the announcement day)" if announced else ""
    if nyse_closed(day):
        text = f"close on the first trading day after {day}{tag}, against the {eve} close"
    else:
        text = f"{day} close{tag}, against the {eve} close"
    if after_close and not nyse_closed(day):
        text += "; the news came after this close, so the move does not include the reaction to it"
    return text


NOT_RECORDED = ('<div class="kv"><span>Move measured on</span><b>not recorded; this figure is not in the run-up '
                "study</b></div>")


def after_close(doc, day):
    m = re.search(r'<div class="kv"><span>Announced</span><b>(\d{4}-\d{2}-\d{2})([^<]*)</b>', doc)
    return bool(m and m.group(1) == day and "after the close" in m.group(2).lower())


def basis_row(day, eve, announced=False, late=False):
    return f'<div class="kv"><span>Move measured on</span><b>{basis_text(day, eve, announced, late)}</b></div>'


def study_eves():
    out = {}
    for r in csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")):
        e = (r.get("eve_date") or "")[:10]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", e) and fnum(r.get("post_1d")) is not None:
            out[(r["ticker"].strip().upper(), r["pdufa_date"][:10])] = e
    return out


def place_move(doc, day_value, row):
    """Write "Decision-day move" and its basis row into key facts: in place when the page has them, else right after
    the 120-day run-up row (or the Outcome row)."""
    block = f'<div class="kv"><span>Decision-day move</span><b>{day_value}</b></div>{row}'
    if DAY_ROW.search(doc):
        return DAY_ROW.sub(lambda m: block, doc, count=1)
    for anchor in (RUN_ROW, OUTCOME_ROW):
        m = anchor.search(doc)
        if m:
            return doc[:m.end()] + block + doc[m.end():]
    # one page (CORT-2026-03-25) keeps its key facts in a table: the same two rows, as table rows
    vb = re.search(r"<b>([^<]*)</b>", row)
    td = '<td style="padding:6px 0;color:#9db3d4">'
    trs = (f'<tr>{td}Decision-day move</td><td class="lit">{day_value}</td></tr>'
           f'<tr>{td}Move measured on</td><td class="lit">{vb.group(1) if vb else ""}</td></tr>')
    doc = re.sub(r'<tr><td[^>]*>Decision-day move</td><td class="lit"[^>]*>[^<]*</td></tr>'
                 r'(?:<tr><td[^>]*>Move measured on</td><td class="lit"[^>]*>[^<]*</td></tr>)?', "", doc, count=1)
    m = re.search(r'<tr><td[^>]*>Actual decision</td><td class="lit"[^>]*>[^<]*</td></tr>', doc)
    if m:
        return doc[:m.end()] + trs + doc[m.end():]
    return doc


def fnum(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x else None


def study_figures():
    out = {}
    for r in csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")):
        t1, pk, d1 = fnum(r.get("T-120_T-1")), fnum(r.get("T-120_peak")), fnum(r.get("post_1d"))
        out[(r["ticker"].strip().upper(), r["pdufa_date"][:10])] = (t1, pk, d1)
    return out


def run_text(t1):
    return f"{t1 * 100:+.1f}%"


def day_text(d1):
    return f"{d1:+.1f}%"


def expected(fig, tk, d):
    """(run-up chip value, decision-day value) the page must show, each None when the study has no figure."""
    t1, _pk, d1 = fig.get((tk, d), (None, None, None))
    return (run_text(t1) if t1 is not None else None), (day_text(d1) if d1 is not None else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    fig = study_figures()
    eves = study_eves()
    import fix_chart_captions as fcc
    ds = fcc.pairs()
    changed = removed = day_fixed = day_added = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        pid = os.path.basename(os.path.dirname(p))
        tk, d = pid.split("-", 1)
        doc = open(p, encoding="utf-8").read()
        new = doc
        run, day = expected(fig, tk, d)
        if OLD_CHIP.search(new):
            if run is None:
                new = OLD_CHIP.sub("", new)
                removed += 1
            else:
                new = OLD_CHIP.sub(f'<div class="kv"><span>120-day run-up (T-120→T-1)</span><b>{run}</b></div>', new)
        if run is not None and RUN_CHIP.search(new):
            new = RUN_CHIP.sub(lambda m: m.group(1) + run + m.group(2), new)
        if day is not None and (tk, d) in eves:
            had = DAY_CHIP.search(new)
            label, _cap = fcc.basis(new, d, ds.get((tk, d)))
            nd = place_move(new, day, basis_row(d, eves[(tk, d)], label == "announced", after_close(new, d)))
            if had:
                day_fixed += DAY_CHIP.search(nd).group(0) != had.group(0)
            else:
                day_added += nd != new
            new = nd
        elif DAY_CHIP.search(new):
            # a move the old app recorded for an event the study did not measure: say that, rather than imply a basis
            cur = DAY_CHIP.search(new).group(0)
            new = DAY_ROW.sub(lambda m: cur + NOT_RECORDED, new, count=1)
        if new != doc:
            changed += 1
            if not a.dry_run:
                with open(p, "w", encoding="utf-8", newline="") as fh:
                    fh.write(new)
    print(f"decision pages: {changed} updated ({removed} old low-high chips removed: event not in the study; "
          f"{day_fixed} decision-day moves corrected, {day_added} added to key facts){' DRY RUN' if a.dry_run else ''}")


if __name__ == "__main__":
    main()
