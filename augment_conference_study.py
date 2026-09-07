# -*- coding: utf-8 -*-
"""Bring /research/conference-runup up to the 09-06d spec, on its existing URL.

The red team asked for "/research/conference-runups" as a real study page. A real study
page already exists at /research/conference-runup (by year, whole path, by tier, by
conference, corrections, method) -- so this adds what it lacked rather than splitting
authority across two URLs: the anchor caveat VERBATIM near the top, a distribution table
(quartiles, event day, days after, small-cap tail shares) with n at every cell and real
<caption>s, the "not a forecast" sentence, and a CC BY 4.0 CSV of the 1,425 rows with
the public columns. A redirect covers the plural URL.

All numbers via conference_runup_facts (one source), marker-bounded (CSTUDYX), idempotent.
"""
import csv
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "research", "conference-runup", "index.html")
CSV_OUT = os.path.join(SITE, "research", "conference-runup", "conference-runup-study.csv")
sys.path.insert(0, HERE)
import conference_runup_facts as crf  # noqa: E402

B, E = "<!--CSTUDYX:BEGIN-->", "<!--CSTUDYX:END-->"
PUBLIC_COLS = ["ticker", "company", "conf", "year", "cap_tier_pit", "runup_30d",
               "runup_20d", "runup_10d", "runup_5d", "event_day", "post_5d", "post_10d"]


def write_csv():
    rows = list(csv.DictReader(io.open(crf.CSVF, encoding="utf-8-sig", errors="replace")))
    with io.open(CSV_OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write("# pdufa.bio conference run-up study, 1,425 presentations 2017-2026. "
                 "License: CC BY 4.0. Tier column is point-in-time market cap. Returns in "
                 "percent, anchored on the meeting start date. Not investment advice.\n")
        w = csv.DictWriter(fh, fieldnames=PUBLIC_COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in PUBLIC_COLS})
    return len(rows)


def main():
    f = crf.load()
    fmt = crf._fmt
    q = f["quartiles"]
    o = f["overall"]
    tails = f["tails"].get("small_caps_30d", {})
    n_csv = write_csv()

    def row(label, key):
        d = q[key]
        pu = o.get(key, {}).get("pct_up")
        return (f"<tr><td>{label}</td><td>{d['n']:,}</td><td>{fmt(d['p25'])}</td>"
                f"<td><b>{fmt(d['p50'])}</b></td><td>{fmt(d['p75'])}</td>"
                f"<td>{pu if pu is not None else ''}%</td></tr>")

    dist = "".join([row("30 trading days before", "runup_30d"),
                    row("10 trading days before", "runup_10d"),
                    row("Presentation day", "event_day"),
                    row("5 trading days after", "post_5d"),
                    row("10 trading days after", "post_10d")])
    tail_sent = ""
    if tails:
        tail_sent = (f"<p>Among nano, micro and small-cap presenters (n={tails['n']}, "
                     f"point-in-time tiers), {tails['pct_up_25']}% rose 25% or more in the 30 "
                     f"trading days before the meeting and {tails['pct_down_25']}% fell 25% or "
                     f"more. That is the distribution; it carries no verb.</p>")

    block = (
        f"{B}"
        f'<div style="background:#0c1d38;border:1px solid #f0c86a;border-radius:12px;'
        f'padding:13px 15px;margin:14px 0"><b style="color:#f0c86a">Read this first</b>'
        f'<div style="color:#9db3d4;font-size:13.5px;margin-top:6px;line-height:1.65">'
        f"Every figure on this page is {crf.ANCHOR_CAVEAT}. Until a second computation "
        f"anchored on abstract release exists, no sentence here implies that presenting "
        f"caused the move. {crf.NOT_FORECAST} {crf.SELECTION_CAVEAT}</div></div>"
        f"<h2>Distribution: before, on the day, and after</h2>"
        f"<table><caption>Share-price move around a presentation across all {f['n']:,} "
        f"presentations, 2017 to 2026: quartiles, median and share rising, by window. "
        f"Anchored on the meeting start date.</caption>"
        f"<tr><th>Window</th><th>n</th><th>25th pct</th><th>Median</th><th>75th pct</th>"
        f"<th>Rose</th></tr>{dist}</table>"
        f"{tail_sent}"
        f'<p>The {n_csv:,} underlying rows are downloadable: <a class="lit" '
        f'href="/research/conference-runup/conference-runup-study.csv">conference-runup-study.csv</a> '
        f"(CC BY 4.0; ticker, meeting, year, point-in-time tier, and each window's return).</p>"
        f"{E}")

    doc = io.open(PAGE, encoding="utf-8", errors="replace").read()
    if B in doc:
        new = doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
    else:
        m = re.search(r"</h1>(?:\s*<!--FRESH:BEGIN-->[\s\S]*?<!--FRESH:END-->)?", doc)
        if not m:
            print("conference study: no h1 anchor")
            return 1
        new = doc[:m.end()] + block + doc[m.end():]
    if new != doc:
        io.open(PAGE, "w", encoding="utf-8").write(new)
        print(f"conference study augmented (CSV {n_csv:,} rows, anchor caveat verbatim)")
    else:
        print("conference study unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
