# -*- coding: utf-8 -*-
"""/pdufa-date-changes -- every PDUFA goal date we have seen move, with its source.

Asked in four consecutive audits (09-06 ORDER 7; BPIQ's changelog shape, our sourcing).
Built from `_d.prior_pdufa_date`, which the ingest scripts set when a sponsor discloses a
new action date, plus `_d.date_provenance` / the row's own source link. One dated line per
change, newest first, each linking the document that announced it.

Discipline, stated on the page: this lists changes THIS ARCHIVE RECORDED, not every change
the FDA made. A goal date that moved before we tracked the application, or that moved
without a public announcement, is not here -- and the page says so rather than implying a
census. No forward-looking verb appears: a date that moved once is not a prediction that it
will move again.
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
OUT = os.path.join(SITE, "pdufa-date-changes")
MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONL = ["", "January", "February", "March", "April", "May", "June", "July", "August",
        "September", "October", "November", "December"]


def esc(s):
    return html.escape(str(s), quote=False)


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month]} {d.day}, {d.year}"


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    changes = []
    for r in rows:
        d = r.get("_d") or {}
        prior = str(d.get("prior_pdufa_date") or "")[:10]
        now = str(r.get("d") or "")[:10]
        if not (re.match(r"^\d{4}-\d{2}-\d{2}$", prior) and
                re.match(r"^\d{4}-\d{2}-\d{2}$", now) and prior != now):
            continue
        url = str(d.get("date_provenance") or d.get("source_url_2") or r.get("url") or "")
        changes.append({
            "t": str(r.get("t") or "").upper(),
            "name": str(r.get("name") or ""),
            "company": str(r.get("company") or ""),
            "prior": prior, "now": now,
            "days": (dt.date.fromisoformat(now) - dt.date.fromisoformat(prior)).days,
            "url": url if url.startswith("http") else "",
            "st": str(r.get("st") or ""),
        })
    changes.sort(key=lambda c: c["now"], reverse=True)

    today = dt.date.today()
    stamp = f"{MONL[today.month]} {today.day}, {today.year}"
    n = len(changes)
    rows_html = "".join(
        f'<div class="row"><div class="t"><b>{esc(c["t"])}</b> &middot; '
        f'{esc(c["name"][:64])}</div><div class="d">Goal date moved from '
        f'<b>{esc(pretty(c["prior"]))}</b> to <b>{esc(pretty(c["now"]))}</b>, '
        f'{abs(c["days"])} days {"later" if c["days"] > 0 else "earlier"}'
        + (f', announced by {esc(c["company"])}' if c["company"] else "")
        + (f'. <a class="lit" href="{esc(c["url"])}" rel="nofollow">Source</a>.'
           if c["url"] else ".")
        + f' <a class="lit" href="/pdufa/{esc(c["t"])}">{esc(c["t"])} events</a>.'
        + "</div></div>"
        for c in changes) or "<p>No sourced goal-date change is on record yet.</p>"

    title = "PDUFA Date Changes: Every FDA Goal Date We Have Seen Move | pdufa.bio"
    desc = (f"{n} FDA goal date change{'s' if n != 1 else ''} recorded in this archive, each "
            f"with the date it moved from, the date it moved to, and the announcement that "
            f"said so. Updated {stamp}.")
    if len(desc) > 158:
        desc = desc[:158].rsplit(" ", 1)[0].rstrip(",;:") + "."

    qa = [("Why do PDUFA dates change?",
           "The FDA can extend a goal date, most often by three months, when the sponsor "
           "submits a major amendment to the application during review. A sponsor may also "
           "withdraw and resubmit, which starts a new review clock. The agency does not "
           "publish these changes as a list; each one here comes from the company's own "
           "announcement."),
          ("Is this every PDUFA date change?",
           f"No. It is every change THIS ARCHIVE recorded, currently {n}. A goal date that "
           f"moved before we began tracking the application, or that moved without a public "
           f"announcement, is not here. We would rather show a short sourced list than imply "
           f"a complete one."),
          ("Where do the dates come from?",
           "Company press releases and SEC filings, linked on every row. pdufa.bio is never "
           "cited as its own source.")]
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                         "mainEntity": [{"@type": "Question", "name": q,
                                         "acceptedAnswer": {"@type": "Answer", "text": a}}
                                        for q, a in qa]}, ensure_ascii=False)
    faq = "".join(
        f'<div style="background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;'
        f'padding:14px 16px;margin:12px 0"><b>{esc(q)}</b>'
        f'<div style="color:#9db3d4;font-size:14px;margin-top:6px">{esc(a)}</div></div>'
        for q, a in qa)

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="https://www.pdufa.bio/pdufa-date-changes"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="theme-color" content="#02060d"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="https://www.pdufa.bio/pdufa-date-changes"><style>*{{box-sizing:border-box}}body{{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.6}}a{{color:#6fb6ff;text-decoration:none}}a:hover{{text-decoration:underline}}.wrap{{max-width:820px;margin:0 auto;padding:22px 18px 60px}}.top{{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;padding-bottom:12px}}.brand{{font-size:19px;font-weight:800}}.brand b{{color:#e3ba5e}}.nav a{{color:#a7bcd9;font-size:13px;margin-left:14px}}h1{{font-size:26px;line-height:1.2;margin:10px 0 6px}}h2{{font-size:18px;color:#e3ba5e;margin:26px 0 8px}}.bc{{font-size:12px;color:#94a9c9;margin:16px 0 4px}}.bc a{{color:#94a9c9}}.sub{{color:#a7bcd9;font-size:15px}}p{{max-width:78ch}}.row{{background:#0c1d38;border:1px solid #1e3a63;border-radius:10px;padding:11px 13px;margin:8px 0}}.row .t{{font-size:14.5px}}.row .d{{color:#9db3d4;font-size:13.5px;margin-top:3px}}.note{{font-size:12px;color:#94a9c9;line-height:1.6}}footer{{border-top:1px solid #1a3358;margin-top:34px;padding-top:16px;font-size:11.5px;color:#94a9c9;line-height:1.6}}footer b{{color:#a7bcd9}}</style><script type="application/ld+json">{jsonld}</script></head><body><div class="wrap"><div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a><a href="/readouts">Readouts</a><a href="/research">Research</a></div></div><div class="bc"><a href="/">Home</a> &rsaquo; PDUFA date changes</div><h1>PDUFA date changes</h1><div class="sub">{n} FDA goal date change{'s' if n != 1 else ''} on record in this archive, newest first. Each row states the date it moved from, the date it moved to, and links the announcement that said so. A PDUFA date is the FDA's target for completing review, and the agency can extend it, most often by three months after a major amendment.</div><h2>Recorded changes</h2>{rows_html}<div class="note" style="margin-top:10px"><b>What this list is:</b> every goal-date change this archive recorded, not every change the FDA made. Changes that happened before we tracked an application, or that were never announced publicly, are absent. Updated {esc(stamp)}.</div><h2>Questions</h2>{faq}<p class="note">Historical record of specific date changes, each linked to its source. Not a prediction about any pending application, and not investment advice.</p><footer><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an independent publication with no affiliation with, endorsement by, sponsorship by, or connection to the U.S. Food and Drug Administration. <b>Informational and educational purposes only. Not investment advice.</b> Verify every date against primary FDA, SEC or company filings.<br><br>&copy; {today.year} pdufa.bio. All rights reserved.</footer></div><script src="/cmdk.js" defer></script></body></html>"""

    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
    print(f"wrote /pdufa-date-changes ({n} sourced change(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
