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
ROW = re.compile(
    r'<a class="row"([^>]*)>\s*<div class="t">([A-Z]{1,6})\s*&middot;\s*(\d{4}-\d{2}-\d{2})</div>'
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


def match_decision(by_tk, tk, caldate):
    """Return (decision_date, outcome) for the closest decision within WINDOW days, else None."""
    if tk not in by_tk:
        return None
    cd = dt.date.fromisoformat(caldate)
    best = None
    for date, outcome in by_tk[tk]:
        gap = abs((dt.date.fromisoformat(date) - cd).days)
        if gap <= WINDOW and (best is None or gap < best[0]):
            best = (gap, date, outcome)
    return (best[1], best[2]) if best else None


def strip_marker(dtext):
    """Remove a previously-injected outcome span so re-marking never stacks."""
    return re.sub(r'^\s*<span style="color:#[0-9a-fA-F]{6};font-weight:700">[^<]*</span>\s*&mdash;\s*', "", dtext)


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
                f'<div class="d"><span style="color:{col};font-weight:700">{word}</span> &mdash; {body}</div></a>')

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


if __name__ == "__main__":
    main()
