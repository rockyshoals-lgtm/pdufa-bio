# -*- coding: utf-8 -*-
"""build_guided_readouts.py -- put the company-guided readouts at the top of /readouts.

/readouts opened by saying every date on it is "an estimated primary-completion window from
ClinicalTrials.gov". That was true when CT.gov was the only source. It is no longer true: 57 rows
are dates the company itself stated in an SEC filing, which is a different and much stronger claim,
and burying them among trial-registry estimates throws away the best data on the page.

This injects a "Company-guided" section above the estimates, between markers so it can be
regenerated without duplicating. Each row shows the program, the company, the precision the company
actually used (a quarter is rendered "Q3 2026", never a fabricated day) and links to the filing.

Run after build_readout_results.py.

    python build_guided_readouts.py [--dry-run]
"""
import argparse, datetime as dt, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "readouts", "index.html")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
BEGIN, END = "<!--GUIDED:BEGIN-->", "<!--GUIDED:END-->"


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def label(d, prec):
    """Render the date at the precision the company actually gave. Printing 'Dec 31' for guidance
    that said 'Q4' invents a day and is exactly what the watchlist split exists to prevent."""
    y, m = int(d[:4]), int(d[5:7])
    if prec == "quarter":
        return f"Q{(m - 1) // 3 + 1} {y}"
    if prec == "month":
        return dt.date(y, m, 1).strftime("%b %Y")
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    arr, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    # Confirmed outcomes: a guided row whose result is in shows "Reported <date>" linking the
    # company release, instead of sitting in the list as if still ahead.
    try:
        _conf = {c.get("id"): c for c in json.load(
            open(os.path.join(HERE, "readout_reported_manual.json"), encoding="utf-8")
        ).get("reported", [])}
    except Exception:
        _conf = {}
    for r in arr:
        c = _conf.get(r.get("id"))
        if c:
            r["_reported"] = c
    today = dt.date.today().isoformat()
    rows = [r for r in arr
            if r.get("type") == "Readout" and r.get("st") == "Guided" and (r.get("d") or "") >= today]
    rows.sort(key=lambda r: (r["d"], r["t"]))
    print(f"company-guided readouts: {len(rows)}")
    if not rows:
        return

    trs = []
    for r in rows:
        d = r["_d"] or {}
        prog = d.get("program") or re.sub(r"\s+readout$", "", r.get("name") or "")
        url = r.get("url") or ""
        srcbit = (f'<a href="{esc(url)}" rel="nofollow">{esc(d.get("guided_form") or "SEC filing")}'
                  f' {esc(d.get("guided_filed") or "")}</a>') if url.startswith("http") else "&mdash;"
        ev = ('<span class="pill" style="background:rgba(240,200,106,.12);color:#f0c86a;'
              'border:1px solid #6b5a2f">event-driven</span>') if d.get("event_driven") else ""
        rep = r.get("_reported")
        date_cell = esc(label(r["d"], r.get("dp")))
        if rep:
            oc = str(rep.get("outcome", "")).lower()
            col = "#46d17f" if oc == "positive" else "#ff7a72" if oc == "negative" else "#9db3d4"
            mv = rep.get("day_move_pct")
            mvtxt = (f' {"+" if (mv or 0) >= 0 else ""}{mv:.1f}% day-of' if mv is not None else "")
            date_cell = (f'<span style="color:{col};font-weight:700">&#10003; Reported '
                         f'{esc(rep.get("reported_date", ""))}</span>'
                         f'<div style="font-size:11px;color:{col}">{esc(oc)}{mvtxt} &middot; '
                         f'<a href="{esc(rep.get("source_url") or "#")}" rel="nofollow" '
                         f'style="color:{col}">company release</a></div>')
        trs.append(
            f'<tr><td class="dt">{date_cell}</td>'
            f'<td class="tk"><a href="/ticker/{esc(r["t"])}">{esc(r["t"])}</a></td>'
            f'<td>{esc(prog)} {ev}</td>'
            f'<td class="co">{esc((r.get("company") or "")[:38])}</td>'
            f'<td class="sr">{srcbit}</td></tr>')

    block = (
        BEGIN +
        '<style>.gtbl{width:100%;border-collapse:collapse;font-size:13.5px}'
        '.gtbl th{text-align:left;color:#f0c86a;font-size:11px;text-transform:uppercase;'
        'letter-spacing:.4px;padding:8px 8px;border-bottom:1px solid #294d80}'
        '.gtbl td{padding:8px;border-bottom:1px solid #1e3a63;color:#9db3d4;vertical-align:top}'
        '.gtbl td.dt{color:#eef4fc;font-weight:700;white-space:nowrap}'
        '.gtbl td.tk a{color:#6fb6ff;font-weight:700}'
        '.gtbl td.co{color:#7c93b6}.gtbl td.sr{white-space:nowrap;font-size:12px}'
        '.gtbl td.sr a{color:#6fb6ff}'
        '.pill{display:inline-block;font-size:10px;font-weight:700;padding:1px 6px;border-radius:20px}'
        '</style>'
        '<div class="mhead" style="color:#f0c86a;margin-top:22px">Company-guided readouts</div>'
        f'<p style="color:#9db3d4;font-size:14.5px;line-height:1.6">These {len(rows)} dates are not '
        'trial-registry estimates. Each one is timing the company itself stated in an SEC filing, '
        'and each row links to that filing so you can read the sentence it came from. Dates are shown '
        'at the precision the company used: a quarter stays a quarter rather than being rendered as '
        'a specific day it never named. Guidance that was vaguer than a quarter is not on this page '
        'at all.</p>'
        '<div class="card"><table class="gtbl">'
        '<tr><th>Guided</th><th>Ticker</th><th>Program</th><th>Company</th><th>Source</th></tr>'
        + "".join(trs) +
        '</table></div>' + END)

    html = open(PAGE, encoding="utf-8", errors="replace").read()
    if BEGIN in html and END in html:
        html = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda m: block, html, flags=re.S)
    else:
        # the page uses div.mhead, not <h2>; anchor on the "Recently reported" block
        anchor = (re.search(r'<div id="readout-results">', html)
                  or re.search(r'<div class="mhead"', html))
        if not anchor:
            print("could not find an insertion point"); return
        html = html[:anchor.start()] + block + html[anchor.start():]

    if a.dry_run:
        print("DRY RUN -- not written."); return
    open(PAGE, "w", encoding="utf-8").write(html)
    print(f"injected {len(rows)} guided readout(s) into /readouts")


if __name__ == "__main__":
    main()
