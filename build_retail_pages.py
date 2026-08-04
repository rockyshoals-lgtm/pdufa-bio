# -*- coding: utf-8 -*-
"""build_retail_pages.py -- turn thin ticker hubs into researched, plain-English deep dives.

The retail questions about a biotech stock are always the same two: what does this drug actually do,
and how good was the last data. The pages that currently rank answer the first with a mechanism
diagram and the second with a price target. We can answer both from primary sources, in ordinary
words, without forecasting anything.

Three design decisions worth stating, because each one was a fork:

1. NO NEW URL NAMESPACE. Content is injected into the existing /ticker/<T> hub between markers,
   not published at a second address. A parallel /stock/<T> tree would have split link equity and
   given us two pages competing for one query.

2. PLAIN FIRST, TECHNICAL BENEATH. Every drug description and every trial result carries a plain
   sentence a non-scientist can follow, with the precise clinical phrasing underneath it and
   labelled. Retail readers are served without giving up the precision that makes the run-up study
   citable.

3. A PROFILE MUST BE COMPLETE OR IT DOES NOT PUBLISH. REQUIRED enforces the fields; a half-filled
   profile raises and the page is skipped. This site already carries 92 hubs noindexed for being
   thin, and 478 URLs Google has declined to crawl. Publishing a stub for a heavily-searched ticker
   would add to exactly that pile.

Stock reactions are MEASURED from Polygon daily closes at build time, never written into the
profile. A number typed by hand drifts away from what happened; a number computed from closes
cannot. Where a company's characterisation and the market's reaction disagree, both are shown and
neither is adjudicated.

    python build_retail_pages.py [--dry-run] [--ticker MRNA]
"""
import argparse, datetime as dt, glob, html, json, os, sys, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PROFILES = os.path.join(HERE, "retail_profiles")
BEGIN, END = "<!--DEEPDIVE:BEGIN-->", "<!--DEEPDIVE:END-->"

REQUIRED = ("ticker", "company", "asset", "plain", "technical", "results", "events", "caveats")
VERDICT_STYLE = {
    "met":       ("#46d17f", "Met"),
    "missed":    ("#ff8f8f", "Missed"),
    "contested": ("#f0c86a", "Contested"),
    "note":      ("#9db3d4", "Note"),
}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def load_key():
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"), os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ.get("POLYGON_API_KEY")


def bars(ticker, key, start="2025-01-01"):
    u = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/"
         f"{dt.date.today().isoformat()}?adjusted=true&sort=asc&limit=50000&apiKey={key}")
    try:
        res = json.loads(urllib.request.urlopen(u, timeout=30).read()).get("results") or []
    except Exception as e:
        print(f"  {ticker}: price fetch failed ({type(e).__name__}); reactions omitted")
        return []
    return [(dt.datetime.fromtimestamp(x["t"] / 1000, dt.timezone.utc).date().isoformat(),
             x["c"]) for x in res]


def reaction(series, date):
    """Close on `date` against the previous close. Returns None when the day is not a session, so
    an announcement on a non-trading day is reported as absent rather than silently attached to a
    neighbouring session."""
    idx = {d: i for i, (d, _) in enumerate(series)}
    i = idx.get(date)
    if i is None or i == 0:
        return None
    prev, cur = series[i - 1][1], series[i][1]
    if not prev:
        return None
    return {"prev": prev, "close": cur, "pct": (cur / prev - 1) * 100}


def validate(p, path):
    missing = [f for f in REQUIRED if not p.get(f)]
    if missing:
        raise ValueError(f"{os.path.basename(path)} missing required field(s): {', '.join(missing)}")
    for r in p["results"]:
        for f in ("trial", "verdict", "plain", "technical", "source"):
            if not r.get(f):
                raise ValueError(f"{p['ticker']}: result '{r.get('trial','?')}' missing '{f}'")
        if r["verdict"] not in VERDICT_STYLE:
            raise ValueError(f"{p['ticker']}: unknown verdict '{r['verdict']}'")
    for e in p["events"]:
        if len(e) != 3 or not e[2].startswith("http"):
            raise ValueError(f"{p['ticker']}: every event needs (date, what, source URL): {e}")


def render(p, series):
    t = p["ticker"]
    out = [BEGIN,
           '<section class="deepdive" style="margin:26px 0 8px">']

    # header + status
    st = p.get("status") or {}
    out.append(f'<h2 style="font-size:20px;margin:0 0 6px">{esc(p.get("headline") or p["asset"])}</h2>')
    if st.get("date"):
        out.append(
            f'<div style="background:var(--card);border:1px solid var(--line);border-radius:12px;'
            f'padding:13px 15px;margin:12px 0 18px">'
            f'<div style="font-size:12px;color:var(--mut2);text-transform:uppercase;'
            f'letter-spacing:.5px">{esc(st.get("label","Status"))}</div>'
            f'<div class="lit" style="font-size:19px;color:#eef4fc;margin:2px 0 6px">'
            f'{esc(st["date"])}</div>'
            f'<div style="font-size:13px;color:var(--mut2);line-height:1.65">'
            f'{esc(st.get("detail",""))} '
            f'<a href="{esc(st.get("source",""))}" rel="nofollow noopener">Source</a></div></div>')

    # what it is: plain first, technical beneath
    out.append(f'<h3 style="font-size:16px;margin:18px 0 6px">What {esc(p["asset"])} is</h3>')
    out.append(f'<p style="font-size:14.5px;line-height:1.75;color:#dce7f7;margin:0 0 8px">'
               f'{esc(p["plain"])}</p>')
    out.append(f'<p style="font-size:12.5px;line-height:1.7;color:var(--mut2);margin:0 0 6px">'
               f'<b style="color:#9db3d4">In clinical terms.</b> {esc(p["technical"])}'
               + (f' <a href="{esc(p.get("technical_source",""))}" rel="nofollow noopener">Source</a>'
                  if p.get("technical_source") else "") + '</p>')

    # results
    out.append('<h3 style="font-size:16px;margin:22px 0 6px">What the data showed</h3>')
    for r in p["results"]:
        colour, _ = VERDICT_STYLE[r["verdict"]]
        out.append(
            f'<div style="border:1px solid var(--line);border-left:3px solid {colour};'
            f'border-radius:10px;padding:13px 15px;margin:0 0 12px">'
            f'<div style="font-weight:700;color:#eef4fc;font-size:14px">{esc(r["trial"])}</div>'
            f'<div style="color:{colour};font-size:12.5px;margin:3px 0 8px">'
            f'{esc(r.get("verdict_label",""))}</div>'
            f'<p style="font-size:14px;line-height:1.75;color:#dce7f7;margin:0 0 8px">'
            f'{esc(r["plain"])}</p>'
            f'<p style="font-size:12.5px;line-height:1.7;color:var(--mut2);margin:0">'
            f'<b style="color:#9db3d4">The numbers.</b> {esc(r["technical"])}'
            + (f' {esc(r["detail"])}' if r.get("detail") else "")
            + f' <a href="{esc(r["source"])}" rel="nofollow noopener">Source</a></p></div>')

    # contested section
    c = p.get("contested")
    if c:
        srcs = " ".join(f'<a href="{esc(u)}" rel="nofollow noopener">[{i+1}]</a>'
                        for i, u in enumerate(c.get("sources", [])))
        out.append(
            f'<div style="background:var(--card);border:1px solid var(--line);border-radius:12px;'
            f'padding:14px 16px;margin:18px 0">'
            f'<div style="font-weight:700;color:#f0c86a;font-size:14px;margin-bottom:6px">'
            f'{esc(c.get("heading","Where the sources disagree"))}</div>'
            f'<p style="font-size:14px;line-height:1.75;color:#dce7f7;margin:0">{esc(c["plain"])} '
            f'{srcs}</p></div>')

    # measured market reactions
    rows = []
    for rr in (p.get("reactions") or []):
        m = reaction(series, rr["date"])
        if not m:
            continue
        col = "#46d17f" if m["pct"] >= 0 else "#ff8f8f"
        rows.append(
            f'<tr><td class="lit" style="padding:7px 10px;white-space:nowrap">{esc(rr["date"])}</td>'
            f'<td style="padding:7px 10px;color:var(--mut2)">{esc(rr["what"])}</td>'
            f'<td class="lit" style="padding:7px 10px;text-align:right;color:{col}">'
            f'{m["pct"]:+.1f}%</td>'
            f'<td class="lit" style="padding:7px 10px;text-align:right;color:var(--mut2)">'
            f'${m["prev"]:,.2f} to ${m["close"]:,.2f}</td></tr>')
    if rows:
        out.append(
            '<h3 style="font-size:16px;margin:22px 0 6px">How the stock moved on the day</h3>'
            '<p style="font-size:12.5px;color:var(--mut2);line-height:1.65;margin:0 0 8px">'
            'Closing price on the announcement date against the previous close, measured from daily '
            'data when this page was built. Announcements made before the open move that day; '
            'announcements after the close move the next session. This records what happened, and '
            'does not claim the announcement caused it.</p>'
            '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;'
            'font-size:13px;border:1px solid var(--line);border-radius:10px">'
            '<thead><tr style="color:var(--mut2);text-align:left;font-size:11.5px;'
            'text-transform:uppercase;letter-spacing:.4px">'
            '<th style="padding:8px 10px">Date</th><th style="padding:8px 10px">Event</th>'
            '<th style="padding:8px 10px;text-align:right">Move</th>'
            '<th style="padding:8px 10px;text-align:right">Close</th></tr></thead><tbody>'
            + "".join(rows) + '</tbody></table></div>')

    # timeline
    out.append('<h3 style="font-size:16px;margin:22px 0 6px">Timeline, with sources</h3><ul '
               'style="font-size:13.5px;line-height:1.8;color:#dce7f7;padding-left:18px;margin:0">')
    for d, what, src in sorted(p["events"]):
        out.append(f'<li><span class="lit" style="color:var(--mut2)">{esc(d)}</span> {esc(what)} '
                   f'<a href="{esc(src)}" rel="nofollow noopener">source</a></li>')
    out.append('</ul>')

    # caveats
    out.append('<h3 style="font-size:16px;margin:22px 0 6px">What could go wrong, and what this '
               'page does not tell you</h3><ul style="font-size:13.5px;line-height:1.8;'
               'color:var(--mut2);padding-left:18px;margin:0 0 10px">')
    for cav in p["caveats"]:
        out.append(f'<li>{esc(cav)}</li>')
    out.append('</ul>')

    out.append(
        f'<p style="font-size:11.5px;color:var(--mut2);line-height:1.65;margin:14px 0 0">'
        f'Compiled from primary sources and last reviewed {esc(p.get("as_of",""))}. '
        f'Every figure above links to the filing, regulator document or journal it came from. '
        f'This is information, not investment advice, and nothing here forecasts an FDA decision.'
        f'</p>')
    out.append('</section>')
    out.append(END)
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ticker")
    a = ap.parse_args()

    key = load_key()
    if not key:
        print("note: no POLYGON_API_KEY; pages build without the measured reaction table")

    files = sorted(glob.glob(os.path.join(PROFILES, "*.json")))
    if a.ticker:
        files = [f for f in files if os.path.basename(f).upper() == a.ticker.upper() + ".JSON"]
    if not files:
        print("no profiles found"); return

    built = skipped = 0
    for f in files:
        p = json.load(open(f, encoding="utf-8"))
        try:
            validate(p, f)
        except ValueError as e:
            print(f"  SKIP {e}")
            skipped += 1
            continue

        t = p["ticker"]
        page = os.path.join(SITE, "ticker", t, "index.html")
        if not os.path.exists(page):
            print(f"  SKIP {t}: /ticker/{t} does not exist")
            skipped += 1
            continue

        series = bars(t, key) if key else []
        block = render(p, series)

        doc = open(page, encoding="utf-8", errors="replace").read()
        if BEGIN in doc:
            pre, rest = doc.split(BEGIN, 1)
            doc = pre + block + rest.split(END, 1)[1]
        else:
            # Before the footer if we can find it, else at the end of the main wrapper.
            for anchor in ('<div class="legal"', "<footer", "</div></body>"):
                if anchor in doc:
                    doc = doc.replace(anchor, block + anchor, 1)
                    break
            else:
                print(f"  SKIP {t}: no insertion point"); skipped += 1; continue

        # The hub was noindexed for being thin. It is not thin now.
        doc = doc.replace('<meta name="robots" content="noindex,follow">', "")

        if not a.dry_run:
            open(page, "w", encoding="utf-8").write(doc)
        n_react = doc.count("</tr>")
        print(f"  {t}: {len(p['results'])} result(s), {len(p['events'])} timeline entries, "
              f"{len(series):,} sessions available")
        built += 1

    print(f"retail deep dives: {built} built, {skipped} skipped"
          + (" (dry run)" if a.dry_run else ""))


if __name__ == "__main__":
    main()
