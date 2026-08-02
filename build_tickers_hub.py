# -*- coding: utf-8 -*-
"""build_tickers_hub.py -- the /tickers A-Z index (SEO playbook B2).

The problem: /ticker/* is the largest URL group on the site (208 pages, ~40% of the sitemap) and it is
effectively ORPHANED -- measured internal links to it were homepage 1, /calendar 0, /decisions 0,
/screener 0. Those pages are reachable essentially only via the sitemap, and a sitemap is a hint, not
an endorsement: it confers no link equity. That is textbook "Discovered - currently not indexed," which
is the bucket holding 478 of this site's pages.

This builds a real hub with server-rendered <a href> anchors to every ticker page, grouped A-Z, each
row carrying what the site actually knows about that ticker (upcoming catalysts / decision history) so
the page is genuinely useful rather than a bare link dump.

    python build_tickers_hub.py [--dry-run]
"""
import argparse, json, os, re, sys
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
TICKER_DIR = os.path.join(SITE, "ticker")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
DECISIONS = os.path.join(SITE, "decisions", "index.html")
OUT = os.path.join(SITE, "tickers")
TODAY = dt.date.today()

NAV = ('<nav><a href="/calendar">Calendar</a><a href="/conferences">Conferences</a>'
       '<a href="/adcomm">AdComm</a><a href="/decisions">Decisions</a>'
       '<a href="/runup-by-year">Run-up</a><a href="/readouts">Readouts</a>'
       '<a href="/screener">Screener</a><a href="/sls" style="color:#46d17f;font-weight:700">SLS</a>'
       '<a class="pro" href="/pricing" style="color:var(--gold)">Pro</a></nav>')


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    tickers = sorted(d for d in os.listdir(TICKER_DIR)
                     if os.path.isdir(os.path.join(TICKER_DIR, d))
                     and os.path.exists(os.path.join(TICKER_DIR, d, "index.html")))

    # what do we know about each ticker?
    src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    arr, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    upcoming, company = {}, {}
    for r in arr:
        t = r.get("t")
        if not t:
            continue
        if r.get("company"):
            company.setdefault(t, r["company"])
        d = str(r.get("d") or "")[:10]
        if r.get("st") not in ("Decided",) and d >= TODAY.isoformat():
            cur = upcoming.get(t)
            if cur is None or d < cur[0]:
                upcoming[t] = (d, r.get("type") or "", r.get("name") or "")

    dec_count = {}
    if os.path.exists(DECISIONS):
        html = open(DECISIONS, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', html):
            dec_count[m.group(1)] = dec_count.get(m.group(1), 0) + 1

    groups = {}
    for t in tickers:
        groups.setdefault(t[0].upper(), []).append(t)

    with_up = sum(1 for t in tickers if t in upcoming)
    with_hist = sum(1 for t in tickers if t in dec_count)

    # jump bar
    letters = sorted(groups)
    jump = "".join(f'<a href="#{L}" class="jl">{L}</a>' for L in letters)

    body = []
    for L in letters:
        rows = []
        for t in groups[L]:
            up = upcoming.get(t)
            n = dec_count.get(t, 0)
            bits = []
            if up:
                bits.append(f'<b style="color:var(--gold)">{up[1] or "Catalyst"} {up[0]}</b>'
                            + (f' &middot; {esc(up[2])[:40]}' if up[2] else ""))
            if n:
                bits.append(f'{n} decision{"s" if n != 1 else ""} on record')
            if not bits:
                bits.append("no catalyst on record")
            rows.append(
                f'<a class="trow" href="/ticker/{t}"><span class="tk">{t}</span>'
                f'<span class="tm"><span class="cn">{esc(company.get(t, ""))[:44]}</span>'
                f'<span class="dd">{" &middot; ".join(bits)}</span></span></a>')
        body.append(f'<h2 id="{L}">{L}</h2><div class="grid">{"".join(rows)}</div>')

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="index,follow,max-image-preview:large">
<title>All Biotech Tickers We Track (A&ndash;Z) &mdash; FDA Catalysts by Company | pdufa.bio</title>
<meta name="description" content="Every biotech and pharma ticker tracked by pdufa.bio, A to Z ({len(tickers)} companies) &mdash; with each company's next FDA catalyst and how many FDA decisions we have on record. Free, no login.">
<link rel="canonical" href="https://www.pdufa.bio/tickers"><meta name="theme-color" content="#060b14">
<meta property="og:type" content="website"><meta property="og:title" content="All biotech tickers we track (A&ndash;Z)"><meta property="og:url" content="https://www.pdufa.bio/tickers">
<style>*{{box-sizing:border-box}}
:root{{--bg:#060b14;--card:#0e1c33;--cardh:#132745;--line:#1e3a63;--line2:#294d80;--gold:#f0c86a;--ink:#eef4fc;--mut:#9db3d4;--mut2:#7c93b6;--green:#46d17f}}
html,body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.55}}
a{{color:inherit;text-decoration:none}}
header.site{{position:sticky;top:0;z-index:20;backdrop-filter:blur(10px);background:rgba(6,11,20,.85);border-bottom:1px solid var(--line)}}
.hd{{max-width:1120px;margin:0 auto;padding:12px 22px;display:flex;align-items:center;justify-content:space-between;gap:16px}}
.hd .brand{{font-size:20px;font-weight:800;letter-spacing:-.4px}}.hd .brand b{{color:var(--gold)}}
.hd nav{{display:flex;gap:2px;flex-wrap:wrap}}.hd nav a{{font-size:13.5px;color:var(--mut);padding:7px 10px;border-radius:8px}}.hd nav a:hover{{color:var(--ink);background:var(--card)}}
.wrap{{max-width:1120px;margin:0 auto;padding:22px 22px 70px}}
.bc{{font-size:12px;color:var(--mut2);margin:2px 0 10px}}.bc a{{color:var(--mut2)}}
h1{{font-size:31px;line-height:1.14;font-weight:800;letter-spacing:-.6px;margin:6px 0 8px}}h1 .g{{color:var(--gold)}}
.sub{{font-size:15.5px;color:var(--mut);margin:0 0 14px;max-width:780px}}
h2{{font-size:17px;color:var(--gold);margin:26px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px;scroll-margin-top:70px}}
.jump{{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 4px}}
.jl{{display:inline-block;min-width:30px;text-align:center;font-weight:800;font-size:13px;color:var(--mut);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 8px}}
.jl:hover{{color:var(--ink);border-color:var(--gold)}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}}
@media(max-width:900px){{.grid{{grid-template-columns:1fr 1fr}}}}
@media(max-width:600px){{.grid{{grid-template-columns:1fr}}h1{{font-size:25px}}.hd nav{{display:none}}}}
.trow{{display:flex;gap:11px;align-items:flex-start;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}}
.trow:hover{{background:var(--cardh);border-color:var(--gold)}}
.tk{{flex:0 0 auto;min-width:54px;font-weight:800;color:var(--gold);font-size:14px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}
.tm{{min-width:0}}.cn{{display:block;font-size:13px;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.dd{{display:block;font-size:11.5px;color:var(--mut);margin-top:2px}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0}}
@media(max-width:600px){{.stats{{grid-template-columns:1fr}}}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px}}
.big{{font-size:25px;font-weight:800;letter-spacing:-.5px}}
.note{{font-size:12px;color:var(--mut2);line-height:1.6}}
.legal{{border-top:1px solid var(--line);margin-top:36px;padding-top:16px;font-size:11.5px;color:#8aa0bf;line-height:1.6}}
</style><link rel="icon" type="image/svg+xml" href="/favicon.svg"></head><body>
<header class="site"><div class="hd"><a class="brand" href="/">pdufa<b>.bio</b></a>{NAV}</div></header>
<main class="wrap">
<div class="bc"><a href="/">Home</a> &rsaquo; All tickers</div>
<h1>Every ticker we <span class="g">track</span> &mdash; A to Z</h1>
<p class="sub">All {len(tickers)} biotech and pharma companies covered by pdufa.bio, with each company's next
FDA catalyst and the number of FDA decisions we hold on record for it. Every calendar date and outcome on this
site is sourced to a primary FDA, SEC or company filing. Free, no login.</p>
<div class="stats">
  <div class="stat"><div class="note">Companies tracked</div><div class="big">{len(tickers)}</div></div>
  <div class="stat"><div class="note">With an upcoming catalyst</div><div class="big" style="color:var(--gold)">{with_up}</div></div>
  <div class="stat"><div class="note">With decision history</div><div class="big" style="color:var(--green)">{with_hist}</div></div>
</div>
<div class="jump">{jump}</div>
{"".join(body)}
<p class="note" style="margin-top:26px">Looking for something specific? Try the
<a href="/calendar" style="color:#6fb6ff">PDUFA calendar</a>,
<a href="/decisions" style="color:#6fb6ff">decision archive</a>,
<a href="/readouts" style="color:#6fb6ff">readout calendar</a>,
<a href="/adcomm" style="color:#6fb6ff">AdComm calendar</a>, or the free
<a href="/developers" style="color:#6fb6ff">API</a>.</p>
<div class="legal"><a href="/about" style="color:#8aa0bf">About</a> &middot; <a href="/corrections" style="color:#8aa0bf">Corrections</a> &middot; <a href="/methodology" style="color:#8aa0bf">Methodology</a> &middot; <a href="/developers" style="color:#8aa0bf">API</a><br><br>
<b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an independent service.
<b>Informational and educational only &mdash; not investment advice.</b> Verify every date and outcome against
primary FDA / SEC / company filings. &copy; 2026 pdufa.bio</div>
</main><script src="/cmdk.js" defer></script></body></html>"""

    print(f"/tickers: {len(tickers)} tickers, {len(letters)} letter groups, "
          f"{with_up} with upcoming catalyst, {with_hist} with decision history")
    if a.dry_run:
        print("DRY RUN -- not written."); return
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)
    print(f"wrote tickers/index.html ({len(html)} bytes, {len(tickers)} server-rendered anchors)")


if __name__ == "__main__":
    main()
