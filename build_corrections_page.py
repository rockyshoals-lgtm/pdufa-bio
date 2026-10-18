# -*- coding: utf-8 -*-
"""build_corrections_page.py -- /corrections: every correction to a published fact, dated, linked (audit 2026-10-18, order 2).

Source: _corrections.json (append-only; new entries are added there and this page follows). Newest first.
Each entry states the page, what was published, what it says now, and the primary record the fix was read from.
The page shell matches build_fda_letters_hub.py; nav, footer, breadcrumbs and OG tags come from the normalisers.

    python build_corrections_page.py
"""
import datetime as dt
import html
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
BASE = "https://www.pdufa.bio"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
       "November", "December"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month]} {d.day}, {d.year}"


def main():
    data = json.load(io.open(os.path.join(HERE, "_corrections.json"), encoding="utf-8"))
    ents = sorted(data["entries"], key=lambda e: e["date"], reverse=True)
    n = len(ents) + len(data.get("legacy") or [])
    first = min([e["date"] for e in ents] + [e["date"] for e in (data.get("legacy") or [])])
    last = ents[0]["date"]
    title = f"Corrections: {n} published facts fixed, dated and sourced | pdufa.bio"
    desc = (f"Every correction to a published fact on pdufa.bio: {n} dated entries since {pretty(first)}, each with the "
            f"page, what it said, what it says now, and its source.")
    assert len(desc) <= 158, len(desc)
    sys.path.insert(0, HERE)
    from site_dates import eastern_today
    stamp = pretty(eastern_today().isoformat())
    CSS = ("*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,"
           "BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.55}a{color:#6fb6ff;"
           "text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:960px;margin:0 auto;padding:22px 18px 60px}"
           ".top{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;padding-bottom:12px}"
           ".brand{font-size:19px;font-weight:800}.brand b{color:#e3ba5e}.nav a{color:#a7bcd9;font-size:13px;margin-left:14px}"
           "h1{font-size:27px;line-height:1.18;margin:10px 0 6px}h1 .g{color:#e3ba5e}h2{font-size:18px;color:#e3ba5e;margin:26px 0 8px}"
           ".sub{color:#a7bcd9;font-size:15px;margin:6px 0 14px;max-width:80ch}.c{border:1px solid #1a3358;border-radius:10px;"
           "padding:12px 14px;margin:10px 0;background:#0c1d38}.c .d{color:#e3ba5e;font-size:12.5px;font-weight:700;"
           "text-transform:uppercase;letter-spacing:.4px}.c p{margin:5px 0;font-size:14px;color:#cfe0f5}.c .k{color:#a7bcd9}"
           ".c .s{font-size:12.5px;color:#94a9c9}")
    NAV = ('<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a>'
           '<div class="nav"><!--NAVC:BEGIN--><!--NAVC:END--></div></div>')
    body = [f'<div style="font-size:12px;color:#94a9c9;margin:16px 0 4px"><a href="/" style="color:#94a9c9">Home</a> '
            f'&rsaquo; Corrections</div>'
            f'<h1>Corrections: <span class="g">{n} published facts fixed, each dated and sourced</span></h1>'
            f'<div class="sub">pdufa.bio publishes FDA decision dates from the FDA&#x27;s own record and goal dates from '
            f'sponsor filings. When a published fact turns out to be wrong, the fix is listed here with the page, what it '
            f'said, what it says now, and the record it was corrected from. {n} entries from {pretty(first)} to '
            f'{pretty(last)}, newest first, updated {stamp}. The <a href="/changelog">changelog</a> lists feature '
            f'changes; this page lists only corrections to facts.</div>']
    for e in ents:
        pg = e["page"]
        body.append(f'<div class="c"><div class="d">{pretty(e["date"])} &middot; <a href="{esc(pg)}">{esc(pg)}</a></div>'
                    f'<p><span class="k">Was:</span> {esc(e["was"])}</p>'
                    f'<p><span class="k">Now:</span> {esc(e["now"])}</p>'
                    f'<p class="s">Source: {esc(e["source"])}</p></div>')
    leg = sorted(data.get("legacy") or [], key=lambda e: e["date"], reverse=True)
    if leg:
        body.append(f'<h2>Earlier log, July to September 2026 ({len(leg)} entries)</h2>'
                    '<div class="sub">The corrections log as it stood before the dated format above: every material error '
                    'found in our own published numbers, what caused it and what changed, including bug reports we rejected '
                    'and why.</div>')
        for e in leg:
            body.append(f'<div class="c"><div class="d">{pretty(e["date"])} &middot; {esc(e["where"])}</div>'
                        f'<p><b>{esc(e["title"])}</b></p><p>{esc(e["text"])}</p></div>')
    body.append('<h2>How corrections happen</h2><div class="sub">Guards run on every rebuild (every decision page must name '
                'the same product as its row, every calendar row must be backed by the data, every FDA date must come from an '
                'FDA record). An audit re-reads the site against primary sources most days. A finding either passes '
                '(nothing changes) or lands here with its fix. A Complete Response Letter is never called a rejection, and '
                'no early or late margin is stated unless both the goal date and the FDA action date come from documents that '
                'state them.</div>')
    ld = json.dumps({"@context": "https://schema.org", "@type": "WebPage", "name": title.replace(" | pdufa.bio", ""),
                     "url": f"{BASE}/corrections", "description": desc,
                     "isPartOf": {"@type": "WebSite", "name": "pdufa.bio", "url": BASE + "/"}}, separators=(",", ":"))
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
           f'initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}">'
           f'<link rel="canonical" href="{BASE}/corrections"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">'
           f'<script type="application/ld+json">{ld}</script><style>{CSS}</style></head><body><div class="wrap">{NAV}'
           + "".join(body) + "</div></body></html>")
    out = os.path.join(SITE, "corrections", "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cur = io.open(out, encoding="utf-8").read() if os.path.exists(out) else ""
    if cur != doc:
        io.open(out, "w", encoding="utf-8").write(doc)
    print(f"/corrections: {n} entries ({first} to {last})" + ("" if cur != doc else " (unchanged)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
