# -*- coding: utf-8 -*-
"""build_weekly_decisions.py -- /fda-approval-decisions-this-week: the week's FDA decisions, decided and pending, dated.

Audit 2026-10-08 item 4 / 2026-10-10 item 7: "fda approval decision biotech" drew 250 Bing impressions at 0 clicks;
the answer box was compiled from aggregators and stale. No page of ours was titled for the query. This page is
rebuilt daily for the current Monday-to-Sunday week (Eastern): every tracked application the FDA decided this
week (by the FDA's action day where we hold it), every application withdrawn this week, every goal date still
ahead this week, and next week's dates. Facts from the dataset only; each row links its page.

Reuses build_today_page's shell (CSS, nav, helpers). Facts only; not investment advice.

    python build_weekly_decisions.py
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_today_page as T  # noqa: E402
from site_dates import eastern_today  # noqa: E402

SITE = T.SITE
BASE = "https://www.pdufa.bio"
PATH = "fda-approval-decisions-this-week"
esc, pretty, _cdn = T.esc, T.pretty, T._cdn
MON3 = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def short(d):
    return f"{MON3[d.month]} {d.day}"



def fda_record_rows(start_iso, end_iso, rows, esc, pretty):
    """Section HTML listing decision-class Drugs@FDA approvals in the range that no tracked dataset row covers
    (audit 2026-10-14: an answer to "what did the FDA approve this week" built from us was incomplete). Where
    pdufa.bio has a decision page for the action (a /fda-decision/{TK}-{date} page within 3 days whose title
    names the brand) the row links it; otherwise it links the FDA's letter or Drugs@FDA record."""
    import datetime as _dt
    import glob as _glob
    import re as _re
    import fda_week_actions as F
    acts, fetched = F.actions(start_iso, end_iso)
    extra = sorted(F.not_on_calendar(acts, rows), key=lambda x: (x["date"], x["brand"]))
    if not extra:
        return "", 0, []
    site = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdufa_site_src", "fda-decision")
    pages = []
    for p in _glob.glob(os.path.join(site, "*", "index.html")):
        slug = os.path.basename(os.path.dirname(p))
        m = _re.match(r"[A-Z]{1,6}-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        try:
            t = _re.search(r"<title>(.*?)</title>", io.open(p, encoding="utf-8", errors="replace").read(), _re.S)
        except OSError:
            continue
        pages.append((slug, m.group(1), (t.group(1) if t else "").lower()))
    out = []
    for x in extra:
        what = x["brand"] or x["ingredient"] or x["app"]
        kind = ("new application" if x["type"] == "ORIG" else "new indication (efficacy supplement)")
        first = (x["brand"] or x["ingredient"]).lower().split()[0] if (x["brand"] or x["ingredient"]) else ""
        ours = next((s for s, d, t in pages if first and first in t
                     and abs((_dt.date.fromisoformat(d) - _dt.date.fromisoformat(x["date"])).days) <= 3), None)
        href = f"/fda-decision/{ours}" if ours else (x["letter"] or x["overview"])
        rel = "" if ours else ' rel="nofollow noopener"'
        src_word = "our decision page" if ours else ("FDA approval letter" if x["letter"] else "Drugs@FDA record")
        out.append(f'<a class="row" href="{esc(href)}"{rel}><div class="t">{esc(pretty(x["date"]))} &middot; '
                   f'{esc(what)} <span style="color:#46d17f;font-weight:700">&#10003; Approved</span></div>'
                   f'<div class="d">{esc(x["sponsor"].title())} &middot; {esc(x["app"][:3] + " " + x["app"][3:])}'
                   f'{(" S-" + x["number"]) if x["type"] == "SUPPL" else ""} &middot; {esc(kind)}'
                   f'{" &middot; " + esc(x["ingredient"].lower()) if x["ingredient"] and x["brand"] else ""}'
                   f' &middot; {src_word}</div></a>')
    note = ('<p class="sub" style="margin:-2px 0 8px">Original NDA/BLA approvals and new-indication supplements recorded in '
            'Drugs@FDA (openFDA) that are not goal dates on our calendar, by the FDA&#x27;s own action date. openFDA posts '
            'records a few days after the action, and CBER products (vaccines, cell and gene therapies) are not in '
            'Drugs@FDA.</p>')
    return note + '<div class="grid">' + "".join(out) + "</div>", len(extra), extra


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    today = eastern_today()
    mon = today - dt.timedelta(days=today.weekday())
    sun = mon + dt.timedelta(days=6)
    nmon, nsun = mon + dt.timedelta(days=7), sun + dt.timedelta(days=7)
    wk = lambda d, a, b: a.isoformat() <= str(d)[:10] <= b.isoformat()  # noqa: E731
    pd = [r for r in rows if r.get("type") == "PDUFA"]

    def act_day(r):
        return str((r.get("_d") or {}).get("fda_action_date") or r.get("dcd") or "")[:10]
    decided = sorted((r for r in pd if str(r.get("st") or "").lower() == "decided" and wk(act_day(r), mon, sun)),
                     key=act_day, reverse=True)
    withdrawn = [r for r in pd if str(r.get("st") or "").lower() == "withdrawn"
                 and wk((r.get("_d") or {}).get("withdrawn_date") or "", mon, sun)]
    pending = sorted((r for r in pd if str(r.get("st") or "").lower() not in ("decided", "withdrawn")
                      and r.get("dp") == "day" and wk(r.get("d"), mon, sun) and str(r.get("d")) >= today.isoformat()),
                     key=lambda r: str(r.get("d")))
    passed = [r for r in pd if str(r.get("st") or "").lower() not in ("decided", "withdrawn")
              and r.get("dp") == "day" and wk(r.get("d"), mon, sun) and str(r.get("d")) < today.isoformat()]
    nxt = sorted((r for r in pd if str(r.get("st") or "").lower() not in ("decided", "withdrawn")
                  and r.get("dp") == "day" and wk(r.get("d"), nmon, nsun)), key=lambda r: str(r.get("d")))

    def dec_row(r):
        tk, d = esc(r.get("t")), str(r.get("dcd") or act_day(r))
        oc = str(r.get("oc") or "Decided")
        col, icon = ("#7ee2a0", "&#10003;") if oc == "Approved" else ("#ff8a8a", "&#10007;")
        fad = act_day(r)
        when = pretty(fad) + (f" (announced {pretty(d)})" if fad and d != fad else "")
        return (f'<a class="row" href="/fda-decision/{tk}-{d}"><div class="t">{tk} &middot; {esc(when)} '
                f'<span style="color:{col};font-weight:700">{icon} {esc(oc)}</span></div>'
                f'<div class="d">{esc(_cdn(r.get("name")))}</div></a>')

    def up_row(r, label):
        tk, d = esc(r.get("t")), str(r.get("d"))
        return (f'<a class="row" href="{esc(str(r.get("url") or "/pdufa/" + tk))}"><div class="t">{tk} &middot; {pretty(d)} '
                f'<span style="color:#e3ba5e">{label}</span></div><div class="d">{esc(_cdn(r.get("name")))}</div></a>')

    def wd_row(r):
        tk = esc(r.get("t")); x = r.get("_d") or {}
        return (f'<a class="row" href="{esc(str(r.get("url") or "/calendar"))}"><div class="t">{tk} &middot; {pretty(x.get("withdrawn_date"))} '
                f'<span style="color:#ffce85;font-weight:700">Withdrawn</span></div>'
                f'<div class="d">{esc(_cdn(r.get("name")))}, before its {pretty(r.get("d"))} goal date</div></a>')

    span = f"{short(mon)} to {short(sun)}, {sun.year}"
    title = f"FDA approval decisions this week: {span} | pdufa.bio"
    n_dec, n_pend = len(decided), len(pending)
    desc = (f"FDA decisions on tracked drug applications, week of {span}: {n_dec} decided"
            + ((" (" + ", ".join(str(r.get("t")) + " " + str(r.get("oc")) for r in decided[:3]) + ")") if decided else "")
            + f", {n_pend} goal date{'s' if n_pend != 1 else ''} still ahead. Dated by FDA record.")
    if len(desc) > 158:
        desc = (f"FDA decisions on tracked drug applications, week of {span}: {n_dec} decided, "
                f"{n_pend} goal date{'s' if n_pend != 1 else ''} still ahead. Dated by FDA record.")
    lede = (f"In the week of {span}, the FDA decided {n_dec} tracked application{'s' if n_dec != 1 else ''}"
            + ("" if not decided else ": " + "; ".join(
                f"{r.get('t')} {_cdn(r.get('name'))} ({r.get('oc')}, {pretty(act_day(r))})" for r in decided))
            + f". {n_pend} goal date{'s' if n_pend != 1 else ''} remain{'s' if n_pend == 1 else ''} this week"
            + (": " + "; ".join(f"{r.get('t')} {_cdn(r.get('name'))} ({pretty(r.get('d'))})" for r in pending) if pending else "")
            + f". As of {pretty(today.isoformat())} (Eastern). Dates come from FDA records and company filings; "
              f"no approval odds, no predictions.")
    body = [f'<div class="bc"><a href="/">Home</a> &rsaquo; <a href="/decisions">FDA Decisions</a> &rsaquo; This week</div>',
            f'<h1>FDA approval decisions this week: <span class="g">{esc(span)}</span></h1>',
            f'<p class="sub">{esc(lede)}</p>',
            f'<h2>Decided this week ({n_dec})</h2><div class="grid">' + ("".join(dec_row(r) for r in decided) or
            '<p class="sub">No tracked application has an FDA decision recorded this week yet.</p>') + '</div>']
    rec_html, n_rec, rec = fda_record_rows(mon.isoformat(), sun.isoformat(), rows, esc, pretty)
    if n_rec:
        body.append(f'<h2>Other FDA approvals recorded this week ({n_rec})</h2>' + rec_html)
    if withdrawn:
        body.append(f'<h2>Withdrawn this week ({len(withdrawn)})</h2><div class="grid">' + "".join(wd_row(r) for r in withdrawn) + "</div>")
    body.append(f'<h2>Still ahead this week ({n_pend})</h2><div class="grid">'
                + ("".join(up_row(r, "goal date" if str(r.get("d")) != today.isoformat() else "today") for r in pending) or
                   '<p class="sub">No further goal dates fall in this week.</p>') + "</div>")
    if passed:
        body.append(f'<h2>Goal date passed, no decision published ({len(passed)})</h2><div class="grid">'
                    + "".join(up_row(r, "awaiting") for r in passed) + "</div>")
    body.append(f'<h2>Next week ({short(nmon)} to {short(nsun)})</h2><div class="grid">'
                + ("".join(up_row(r, "goal date") for r in nxt) or '<p class="sub">No day-dated goal date falls next week.</p>') + "</div>")
    body.append('<p class="sub">Every FDA decision date on pdufa.bio comes from the FDA&#x27;s own record where one is held, '
                'otherwise from the sponsor&#x27;s announcement, and the page says which. See <a href="/fda-decisions-today">today</a>, '
                '<a href="/fda-this-month">this month</a>, the <a href="/calendar">full PDUFA calendar</a> and '
                '<a href="/fda-approval-letters">every FDA approval letter</a>. Informational only; not investment advice.</p>')
    faq = [("Which drugs did the FDA approve this week?",
            (f"In the week of {span} the FDA decided {n_dec} tracked application{'s' if n_dec != 1 else ''}"
             + (": " + "; ".join(f"{r.get('t')} {_cdn(r.get('name'))} ({r.get('oc')}, {pretty(act_day(r))})" for r in decided) if decided else "")
             + f", as of {pretty(today.isoformat())}."
             + (f" Drugs@FDA also records {n_rec} decision-class approval{'s' if n_rec != 1 else ''} this week on applications "
                f"not on our calendar: " + "; ".join(f"{x['brand'] or x['ingredient']} ({x['sponsor'].title()}, {pretty(x['date'])})" for x in rec) + "."
                if n_rec else ""))),
           ("Which FDA decisions are still due this week?",
            (f"{n_pend} goal date{'s' if n_pend != 1 else ''}: " + "; ".join(f"{r.get('t')} {_cdn(r.get('name'))} on {pretty(r.get('d'))}" for r in pending)
             if pending else "No further goal dates fall in this week.") + " A goal date is the FDA's target, not a promise of a decision that day."),
           ("Where do these dates come from?",
            "From the FDA's approval letters, Drugs@FDA and FDA notices for decisions, and from SEC filings and company releases for goal dates. Each row links its page and source.")]
    faq_ld = ('<script type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@type": "FAQPage", "url": f"{BASE}/{PATH}",
         "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
        separators=(",", ":")) + "</script>")
    body.append("<h2>Questions</h2>" + "".join(f"<h3>{esc(q)}</h3><p class=\"sub\">{esc(a)}</p>" for q, a in faq))
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title>'
           f'<meta name="description" content="{esc(desc)}"><link rel="canonical" href="{BASE}/{PATH}">'
           f'<meta name="robots" content="index,follow,max-image-preview:large"><meta name="theme-color" content="#02060d">'
           f'<meta property="og:type" content="website"><meta property="og:site_name" content="pdufa.bio">'
           f'<meta property="og:url" content="{BASE}/{PATH}"><meta property="og:title" content="{esc(title)}">'
           f'<meta property="og:description" content="{esc(desc)}">{faq_ld}'
           f'<style>{T.CSS}</style></head><body><div class="wrap">{T.NAV}' + "".join(body) + "</div></body></html>")
    out = os.path.join(SITE, PATH, "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(doc)
    print(f"/{PATH}: week {mon}..{sun}; decided {n_dec}, withdrawn {len(withdrawn)}, pending {n_pend}, passed {len(passed)}, next week {len(nxt)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
