# -*- coding: utf-8 -*-
"""Quotable explainer block at the top of /calendar -- the sentence supply.

Strategy audit 2026-09-05b, section 3: AI answer boxes select SENTENCES, not tables.
On Bing 'pdufa dates 2026' the answer box above our #1 organic result quoted five
other sites for facts we hold better: the 10/6-month review clocks, the 3-month
extension, "the FDA does not publish a calendar", and the early/on/late record.
This injects those sentences on the page that already ranks, computed fresh from
the dataset each build so the numbers never go stale (the Pharmacy Times article
is frozen at publication; ours rebuilds daily).

Idempotent: writes between <!--EXPLAINER:BEGIN--> and <!--EXPLAINER:END-->, placed
after <!--LEDE:END-->. Numbers come from the same dataset.mjs the page's own lede
and guards use, so the surfaces cannot disagree.
"""
import datetime as dt
import html
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
PAGE = os.path.join(SITE, "calendar", "index.html")
YEAR = "2026"


def esc(s):
    return html.escape(str(s), quote=False)


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f'{["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][d.month]} {d.day}'


def timing_split():
    """(n, early, on, late, biggest) over the SAME sourced-decision set the
    /research/fda-decision-timing page publishes. One source of rule: importing
    build_early_decisions.collect() is what keeps the two surfaces from disagreeing
    (a first draft recounted from the raw dataset and got 32 where the timing page
    says 29 -- the difference was its primary-source inclusion rule)."""
    import build_early_decisions
    rows = build_early_decisions.collect(YEAR)
    early = sum(1 for r in rows if r["delta"] < 0)
    on = sum(1 for r in rows if r["delta"] == 0)
    late = sum(1 for r in rows if r["delta"] > 0)
    biggest = None
    for r in rows:
        if r["delta"] < 0 and (biggest is None or -r["delta"] > biggest[0]):
            biggest = (-r["delta"], r.get("drug") or r["ticker"], r["actual"])
    return len(rows), early, on, late, biggest


def main():
    t = io.open(PAGE, encoding="utf-8", errors="replace").read()
    n, early, on, late, biggest = timing_split()
    today = dt.date.today()
    stamp = f'{["","January","February","March","April","May","June","July","August","September","October","November","December"][today.month]} {today.day}, {today.year}'

    p4 = ""
    if n:
        p4 = (f"<p>Of the {n} FDA decisions in {YEAR} on this site with both a sourced "
              f"goal date and a sourced action date, {early} came before the goal date, "
              f"{on} landed on it, and {late} came after.")
        if biggest:
            p4 += (f" The largest early margin was {biggest[0]} days "
                   f"({esc(biggest[1])}, {pretty(biggest[2])}).")
        p4 += (' Full record: <a class="lit" href="/research/fda-decision-timing">'
               "FDA decision timing</a>.</p>")

    block = (
        "<!--EXPLAINER:BEGIN-->"
        '<div class="explainer" style="max-width:76ch;color:var(--mut2);'
        'font-size:14.5px;line-height:1.62;margin:10px 0 6px">'
        "<p>A PDUFA date is the FDA's target date to complete review of a drug "
        "application, set under the Prescription Drug User Fee Act. It is a goal, "
        "not a promise: the agency can act before the date, on it, or after it.</p>"
        "<p>A standard review carries a 10-month goal from the FDA's acceptance of "
        "the application; a priority review carries a 6-month goal. If the sponsor "
        "submits a major amendment during review, the FDA can extend the goal date "
        "by 3 months.</p>"
        "<p>The FDA does not publish an official, forward-looking PDUFA calendar. "
        f"Every date on this page comes from a company filing, press release or FDA "
        f"notice, and each row links its source.</p>"
        + p4 +
        "<p>On or around the goal date the FDA typically either approves the "
        "application or issues a Complete Response Letter explaining what stands in "
        "the way of approval. Decided rows below state the outcome in words and "
        "link the decision record.</p>"
        "</div>"
        f'<h2 style="font-size:16px;margin:18px 0 4px">Upcoming FDA PDUFA dates, '
        f"updated {stamp}</h2>"
        "<!--EXPLAINER:END-->"
    )

    if "<!--EXPLAINER:BEGIN-->" in t:
        t2 = re.sub(r"<!--EXPLAINER:BEGIN-->[\s\S]*?<!--EXPLAINER:END-->", block, t)
    else:
        anchor = "<!--LEDE:END-->"
        if anchor not in t:
            print("calendar explainer: LEDE:END marker missing, nothing written")
            return 1
        t2 = t.replace(anchor, anchor + block, 1)
    if t2 != t:
        io.open(PAGE, "w", encoding="utf-8").write(t2)
        print(f"calendar explainer: written (n={n}, early={early}, on={on}, "
              f"late={late})")
    else:
        print("calendar explainer: unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
