# -*- coding: utf-8 -*-
"""build_today_page.py -- /fda-decisions-today: what the FDA decided, freshly.

WHY (red team 2026-09-01, Part 4): a "today" query family emerged on BOTH Bing surfaces
before any page existed for it -- "fda approvals today pdufa" at 13.33% web CTR (position
3.77) and 28.57% AI-citation share. Demand proven on two independent surfaces, zero
competition. The audit proposed /today; that path is occupied by the legacy noindexed app
rewrite in vercel.json, so the page lives at /fda-decisions-today (the audit's alternate)
and nothing in the frozen nav changes -- in-page links carry it.

Honesty rules:
  - "today" is stated as an explicit as-of date, never implied;
  - on a day with no decision the page SAYS no decision was published today, then shows
    the most recent ones -- an empty day is a fact, not a gap to paper over;
  - every decision links its decision page (which carries the primary source);
  - upcoming rows come from the same dataset as the calendar, so the two cannot disagree.

Runs in CI daily after the decision fan-out; being date-driven, its content genuinely
changes every day, which is exactly the freshness signal the SERP already rewards us for.
"""
import datetime as dt
import html
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
BASE = "https://www.pdufa.bio"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August",
       "September", "October", "November", "December"]


def esc(s):
    return html.escape(str(s or "").strip())


def pretty(iso):
    try:
        d = dt.date.fromisoformat(str(iso)[:10])
        return f"{MON[d.month]} {d.day}, {d.year}"
    except Exception:
        return str(iso or "")


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    today = dt.date.today()
    tiso = today.isoformat()

    dec = [r for r in rows if r.get("type") == "PDUFA"
           and str(r.get("st", "")).lower() == "decided" and r.get("dcd")]
    dec.sort(key=lambda r: str(r.get("dcd")), reverse=True)
    dec_today = [r for r in dec if str(r.get("dcd")) == tiso]
    week_ago = (today - dt.timedelta(days=7)).isoformat()
    dec_week = [r for r in dec if week_ago <= str(r.get("dcd")) <= tiso]
    recent = dec[:8]

    up = [r for r in rows if r.get("type") == "PDUFA"
          and str(r.get("st", "")).lower() != "decided"
          and r.get("dp") == "day" and str(r.get("d", "")) >= tiso]
    up.sort(key=lambda r: str(r.get("d")))
    up_next = up[:8]

    def dec_row(r):
        tk, d = esc(r.get("t")), str(r.get("dcd"))
        oc = str(r.get("oc") or "Decided")
        col, icon = ("#7ee2a0", "&#10003;") if oc == "Approved" else ("#ff8a8a", "&#10007;")
        return (f'<a class="row" href="/fda-decision/{tk}-{d}">'
                f'<div class="t">{tk} &middot; {pretty(d)} '
                f'<span style="color:{col};font-weight:700">{icon} {esc(oc)}</span></div>'
                f'<div class="d">{esc(str(r.get("name"))[:80])}</div></a>')

    def up_row(r):
        tk, d = esc(r.get("t")), str(r.get("d"))
        days = (dt.date.fromisoformat(d) - today).days
        when = "today" if days == 0 else ("tomorrow" if days == 1 else f"in {days} days")
        return (f'<a class="row" href="/pdufa/{tk}">'
                f'<div class="t">{tk} &middot; {pretty(d)} <span style="color:#e3ba5e">'
                f'{when}</span></div>'
                f'<div class="d">{esc(str(r.get("name"))[:80])}</div></a>')

    if dec_today:
        lede = (f"The FDA decided {len(dec_today)} tracked application"
                f"{'s' if len(dec_today) != 1 else ''} today, {pretty(tiso)}: "
                + "; ".join(f"{r.get('t')} ({r.get('oc')})" for r in dec_today)
                + ". Each links its decision page and primary source below.")
    else:
        newest = dec[0] if dec else None
        lede = (f"No FDA decision on a tracked application has been published today, "
                f"{pretty(tiso)}. The most recent was "
                + (f"{newest.get('t')}'s {str(newest.get('name'))[:40]} "
                   f"({newest.get('oc')}) on {pretty(newest.get('dcd'))}. " if newest else "")
                + "Decisions from the past week and the next scheduled dates are below.")

    nxt = up_next[0] if up_next else None
    qa = [("What did the FDA approve today?",
           lede),
          ("When is the next FDA decision?",
           (f"The next scheduled PDUFA date is {nxt.get('t')}'s "
            f"{str(nxt.get('name'))[:50]} on {pretty(nxt.get('d'))}."
            if nxt else "No day-precision PDUFA date is currently scheduled.")
           + " The FDA can act before a goal date; in this archive's sourced 2026 "
             "decisions, more came early than late."),
          ("How current is this page?",
           f"Rebuilt {pretty(tiso)} from the same dataset that drives the calendar and "
           f"the decisions archive; every decision links the FDA notice, SEC filing or "
           f"company release it came from.")]
    faq_ld = ('<script type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@type": "FAQPage",
         "url": f"{BASE}/fda-decisions-today",
         "mainEntity": [{"@type": "Question", "name": q,
                         "acceptedAnswer": {"@type": "Answer", "text": a}}
                        for q, a in qa]}, separators=(",", ":")) + "</script>")

    CSS = ("*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;"
           "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,"
           "Arial,sans-serif;line-height:1.55}a{color:#6fb6ff;text-decoration:none}"
           "a:hover{text-decoration:underline}.wrap{max-width:820px;margin:0 auto;"
           "padding:22px 18px 60px}.top{display:flex;align-items:center;"
           "justify-content:space-between;border-bottom:1px solid #1a3358;"
           "padding-bottom:12px}.brand{font-size:19px;font-weight:800}"
           ".brand b{color:#e3ba5e}.nav a{color:#a7bcd9;font-size:13px;margin-left:14px}"
           "h1{font-size:27px;line-height:1.18;margin:10px 0 6px}h1 .g{color:#e3ba5e}"
           "h2{font-size:18px;color:#e3ba5e;margin:26px 0 8px}"
           ".sub{color:#a7bcd9;font-size:15px;margin:6px 0 14px}"
           ".grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}"
           "@media(max-width:560px){.grid{grid-template-columns:1fr}}"
           ".row{display:block;background:#0c1d38;border:1px solid #1a3358;"
           "border-radius:10px;padding:11px 13px;color:#f2f6fc}"
           ".row:hover{border-color:#2a496f;text-decoration:none}.row .t{font-weight:800}"
           ".row .d{font-size:12.5px;color:#a7bcd9}"
           "footer{border-top:1px solid #1a3358;margin-top:34px;padding-top:16px;"
           "font-size:11.5px;color:#94a9c9;line-height:1.6}footer b{color:#a7bcd9}")

    NAV = ('<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a>'
           '<div class="nav"><!--NAVC:BEGIN--><!--NAVC:END--></div></div>')

    title = "FDA Decisions Today: PDUFA Approvals & CRLs, Updated Daily | pdufa.bio"
    desc = (f"What the FDA decided today and this week, with primary sources, plus the "
            f"next scheduled PDUFA dates. Updated daily; as of {pretty(tiso)}.")

    body = [f'<div class="bc" style="font-size:12px;color:#94a9c9;margin:16px 0 4px">'
            f'<a href="/" style="color:#94a9c9">Home</a> &rsaquo; FDA decisions today</div>'
            f'<h1>FDA decisions <span class="g">today</span></h1>'
            f'<div class="sub">{esc(lede)}</div>']
    if dec_today:
        body.append(f'<h2>Decided today ({len(dec_today)})</h2><div class="grid">'
                    + "".join(dec_row(r) for r in dec_today) + "</div>")
    if dec_week:
        label = "This week" if dec_today else "Decided in the past week"
        shown = [r for r in dec_week if r not in dec_today]
        if shown:
            body.append(f'<h2>{label} ({len(shown)})</h2><div class="grid">'
                        + "".join(dec_row(r) for r in shown) + "</div>")
    if not dec_week and recent:
        body.append(f'<h2>Most recent decisions</h2><div class="grid">'
                    + "".join(dec_row(r) for r in recent) + "</div>")
    if up_next:
        body.append(f'<h2>Next scheduled PDUFA dates</h2><div class="grid">'
                    + "".join(up_row(r) for r in up_next) + "</div>")
    body.append('<p><a href="/calendar">Every upcoming FDA decision date on the 2026 '
                'PDUFA calendar</a> &middot; <a href="/decisions">the full decisions '
                'archive</a></p>')

    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1,'
           f'viewport-fit=cover"><title>{esc(title)}</title>'
           f'<meta name="description" content="{esc(desc)}">'
           f'<link rel="canonical" href="{BASE}/fda-decisions-today">'
           f'<meta name="robots" content="index,follow,max-image-preview:large">'
           f'<meta name="theme-color" content="#02060d">'
           f'<meta property="og:type" content="website">'
           f'<meta property="og:site_name" content="pdufa.bio">'
           f'<meta property="og:url" content="{BASE}/fda-decisions-today">'
           f'<meta property="og:title" content="{esc(title)}">'
           f'<meta property="og:description" content="{esc(desc)}">{faq_ld}'
           f'<style>{CSS}</style></head><body><div class="wrap">{NAV}'
           + "".join(body) + "</div></body></html>")

    out = os.path.join(SITE, "fda-decisions-today", "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(doc)
    print(f"/fda-decisions-today: {len(dec_today)} today, {len(dec_week)} this week, "
          f"{len(up_next)} next scheduled; as of {tiso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
