# -*- coding: utf-8 -*-
"""test_open_dates_visible.py -- the date still ahead is always in view.

UX pass 2026-11-20, three findings on the live site:
  1. home, "Next FDA decisions": a card read "{drug} · PDUFA 2026-11-22" on one line cut with an ellipsis, so on a
     phone the date, the one fact the card is for, was cut off on every card. The drug name now truncates in its own
     element (<bdi class="dn">) and the date after it never does.
  2. home, "Recently decided": a card named only the ticker ("SNY 2026-11-18 · Approved"). It now names the drug,
     taken from the decision page's own "Drug / candidate" fact.
  3. /calendar: November listed 13 decided rows before its 7 open ones, under "Upcoming FDA PDUFA dates". In a month
     that still holds an open goal, the open rows now come first and the settled rows fold below them.
This fails if a home card's drug name and date share one truncating run of text, the truncating style is gone, a
decided card whose page names the drug does not, or a /calendar month shows a decided or withdrawn row above an
open one (or its fold miscounts).

    python tests/test_open_dates_visible.py
"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")


def home(bad):
    doc = io.open(os.path.join(SITE, "index.html"), encoding="utf-8", errors="replace").read()
    if ".dg .dn{min-width:0;overflow:hidden;text-overflow:ellipsis" not in doc:
        bad.append("home: the style that truncates the drug name and keeps the date is gone")
    # 2026-11-27 phone pass: at 500px the wrap rule (then max-width:480px) did not apply, so cards read
    # "Bezuclastinib…", "Gazyva (…" and "MR-107A-0…". The name gets its own line on any phone width.
    wrap = re.search(r"@media\(max-width:(\d+)px\)\{\.dg\{flex-wrap:wrap", doc)
    if not wrap or int(wrap.group(1)) < 540:
        bad.append("home: the phone rule that puts the drug name on its own line is missing or stops below 540px")
    lst = doc[doc.find('<div class="list">'):doc.find("Recently decided")]
    cards = re.findall(r'<span class="dg">(.*?)</span></span>', lst, re.S)
    if not cards:
        bad.append("home: no Next FDA decisions cards parsed -- markup changed?")
    for dg in cards:
        if not re.fullmatch(r'<bdi class="dn">[^<]*</bdi> · PDUFA (?:\d{4}-\d{2}-\d{2}|window [^<]+|date not announced)',
                            dg):
            bad.append(f"home: card line {dg[:90]!r} does not keep the date outside the truncated drug name")
    from build_home_board import drug_shown
    decs = re.findall(r'<a class="dec [a-z]+" href="/fda-decision/([A-Z.]+)-(\d{4}-\d{2}-\d{2})"[^>]*>(.*?)</a>', doc, re.S)
    if not decs:
        bad.append("home: no Recently decided cards parsed -- markup changed?")
    for tk, day, body in decs:
        want = drug_shown(tk, day)
        if want and '<span class="dnm">' not in body:
            bad.append(f"home: the {tk} {day} decided card does not name its drug ({want})")
    return len(cards), len(decs)


def calendar(bad):
    import shape_calendar as S
    doc = io.open(S.PAGE, encoding="utf-8", errors="replace").read()
    folds = 0
    for b, e, name in S.month_blocks(doc):
        blk = doc[b:e]
        if not S.is_open(blk):
            continue
        g = blk.find('<div class="grid">')
        rows = S._rows(S.RO.sub("", blk[g + len('<div class="grid">'):-len("</div>")], count=1)) or []
        if any(S._settled(r) for r in rows):
            bad.append(f"/calendar {name}: a decided or withdrawn row sits among the open dates")
        d = S.RD.match(doc, e)
        if d:
            folds += 1
            low = S._rows(d.group(1)) or []
            n = re.search(r"<summary>(\d+) dates? in ", d.group(0))
            if not low or not all(S._settled(r) for r in low) or not n or int(n.group(1)) != len(low):
                bad.append(f"/calendar {name}: the folded rows are not all settled, or the summary miscounts them")
    return folds


def main():
    bad = []
    nc, nd = home(bad)
    folds = calendar(bad)
    print(f"home: {nc} next-decision card(s), {nd} decided card(s); /calendar: {folds} open month(s) with a fold")
    if bad:
        print("FAIL:\n  " + "\n  ".join(bad[:30]))
        return 1
    print("  PASS: the date still ahead is in view, decided cards name the drug, open rows lead their month")
    return 0


if __name__ == "__main__":
    sys.exit(main())
