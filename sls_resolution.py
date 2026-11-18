# -*- coding: utf-8 -*-
"""sls_resolution.py -- what SELLAS has announced about REGAL since the /sls pages were written.

The /sls hub and /research/sls-deep-dive were written while REGAL waited for its 80th event, and
their prose makes a claim of ABSENCE ("as of <date>, the 80th event has not been announced").
check_sls_filings.py advanced that date by checking EDGAR only, and SELLAS announced the 80th event
in a GlobeNewswire release on Oct 28, 2026 without a material EDGAR filing, so the pages went on
saying "Not yet" for three weeks, through the Nov 17 topline (red team 2026-11-17).

The announcements live in _sls_verified_through.json under "event80" and "topline", each with the
date, the release URL and the company's own words. When they are present, resolve() rewrites the
absence sentences into what was announced, and adds an update box at the top. Nothing here is
inferred: every figure is quoted from the release it cites.
"""
import datetime as dt
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "_sls_verified_through.json")
MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def state():
    try:
        return json.load(io.open(STATE, encoding="utf-8"))
    except Exception:
        return {}


def pretty(iso):
    return f"{MON[int(iso[5:7])]} {int(iso[8:10])}, {iso[:4]}"


def update_box(st):
    e, t = st.get("event80") or {}, st.get("topline") or {}
    if not e:
        return ""
    parts = [f'<b>{pretty(e["date"])}:</b> SELLAS announced that REGAL reached its 80th event '
             f'(<a href="{e["url"]}">release</a>: &ldquo;{e["quote"]}&rdquo;).']
    if t:
        parts.append(f'<b>{pretty(t["date"])}:</b> SELLAS reported REGAL topline results '
                     f'(<a href="{t["url"]}">release</a>): &ldquo;{t["quote"]}&rdquo; These are the '
                     f'company&#x27;s figures; the full data have not been presented.')
    for x in st.get("since") or []:
        parts.append(f'<b>{pretty(x["date"])}:</b> {x["text"]} (<a href="{x["url"]}">release</a>).')
    return ('<div class="card" style="border-color:#e3ba5e"><h3 style="margin-top:0">Update: the 80th event '
            'has been reached and REGAL has read out</h3>' + "".join(f"<p>{p}</p>" for p in parts) +
            '<p class="note">Sections below that discuss the wait for the 80th event are kept as the record of '
            'what was disclosed before it; the pace arithmetic is historical.</p></div>')


def resolve(html, page):
    """Rewrite the pre-80th-event absence claims. `page` is 'hub' or 'deepdive'."""
    st = state()
    e = st.get("event80")
    if not e:
        return html
    when = pretty(e["date"])
    t = st.get("topline") or {}
    top = f"reported topline on {pretty(t['date'])}" if t else "the final analysis is under way"
    reps = [
        ('<div class="big" style="color:var(--gold)">Not yet</div><div class="note">company says it will announce it</div>',
         f'<div class="big" style="color:#46d17f">Yes</div><div class="note">{when} &middot; {top}</div>'),
        ("a Phase 3 survival trial sitting two deaths from its final analysis",
         f"a Phase 3 survival trial that reached its 80th event on {when} and {top}"),
        ("the 80th event has not been announced. This is",
         f"the 80th event was announced on {when}, later than every one of these windows. This is"),
        ("it is unannounced, ", f"it was announced on {when}, "),
        ("SELLAS has not announced the 80th event. The company has said it will\nannounce the 80th event when it occurs.",
         f"SELLAS announced the 80th event on {when}."),
        ("as of {VERIFIED_TXT} it has not been announced, ", f"it was announced on {when}, "),
        ("it has not been announced, ", f"it was announced on {when}, "),
    ]
    days = (dt.date.fromisoformat(e["date"]) - dt.date.fromisoformat(st.get("as_of") or "2026-05-11")).days
    rx = [
        (r"As of\s*<b>[^<]+</b>, <b>\d+ days</b> after that as-of date: the 80th event has not been announced\.",
         f"The 80th event was announced on <b>{when}</b>, <b>{days} days</b> after that as-of date and later than all three."),
        (r"As of\s*<b>[^<]+</b>:\s*\d+ days\s+after the 78-event as-of date: SELLAS has not announced the 80th event\. "
         r"The company has said it will\s+announce the 80th event when it occurs\.",
         f"SELLAS announced the 80th event on <b>{when}</b>, {days} days after the 78-event as-of date."),
        (r"as of [A-Z][a-z]{2} \d{1,2}, \d{4},? it (?:is unannounced|has not been announced), \d+ days past the 78-event as-of date",
         f"it was announced on {when}, {days} days after the 78-event as-of date"),
        (r'<div class="big">78 / 80</div><div class="note">as of May 11, 2026 &middot; \d+d ago</div>',
         f'<div class="big">80 / 80</div><div class="note">reached {when} (78 as of May 11, 2026)</div>'),
    ]
    for a, b in rx:
        html = re.sub(a, b, html)
    for a, b in reps:
        html = html.replace(a, b)
    box = update_box(st)
    if box and "Update: the 80th event" not in html:
        anchor = '<div class="grid4">' if page == "hub" else "<h2>"
        i = html.find(anchor)
        if i >= 0:
            html = html[:i] + box + html[i:]
    return html



def main():
    """Apply to the built pages in place (CI runs this after the SLS builders, whether or not they ran)."""
    site = os.path.join(HERE, "pdufa_site_src")
    n = 0
    for rel, page in (("sls/index.html", "hub"), ("research/sls-deep-dive/index.html", "deepdive")):
        p = os.path.join(site, rel)
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8").read()
        new = resolve(doc, page)
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
            n += 1
        left = [w for w in ABSENCE if w in new]
        print(f"{rel}: {'updated' if new != doc else 'unchanged'}" + (f"; STILL SAYS {left}" if left else ""))
    return 0


ABSENCE = ("has not been announced", "has not announced the 80th", "is unannounced", ">Not yet<",
           "two deaths from its final analysis")

if __name__ == "__main__":
    sys.exit(main())
