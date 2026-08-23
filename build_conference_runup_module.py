# -*- coding: utf-8 -*-
"""build_conference_runup_module.py -- put our own run-up study on the conference pages.

The /conference/{CODE} pages listed dates and presenters and answered nothing about the thing a
reader actually wants to know: what has happened to biotech stocks around this meeting before.
We have measured that ourselves across 1,425 presentations (2017-2026) -- run-up over the 30/20/
10/5 trading days before, the event day, and the 5 and 10 days after -- so the pages can answer
it from our own data rather than repeating a vendor's summary.

WHAT GETS SHOWN, AND WHAT DOES NOT
  * A conference gets its own cohort numbers only when the study holds at least MIN_N events for
    it; otherwise the page shows the all-conference cohort and says so. A "typical run-up" from
    six events is not typical of anything.
  * Median leads. Biotech returns are fat-tailed; the mean is flattered by a handful of doubles,
    and quoting it alone would overstate the case.
  * Every number carries its n, and the block states in plain language that this is a historical
    distribution for a cohort of companies, not a prediction for any one of them, and not advice.

The pattern in the data is worth stating plainly because it is the opposite of the intuition:
stocks drift UP into these meetings and DOWN out of them, and the effect is strongest in the
smallest companies. The block says that, because a page that shows only the run-up would be
telling half the truth.

Idempotent via CRUN markers.

    python build_conference_runup_module.py [--dry-run]
"""
import argparse, glob, io, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
STATS = os.path.join(HERE, "_conference_runup_stats.json")
B, E = "<!--CRUN:BEGIN-->", "<!--CRUN:END-->"
TIERS = [("nano", "Nano (&lt;$50M)"), ("micro", "Micro ($50-300M)"),
         ("small", "Small ($300M-$2B)"), ("mid", "Mid ($2-10B)"), ("large", "Large (&gt;$10B)")]
LABELS = [("runup_30d", "30 days before"), ("runup_10d", "10 days before"),
          ("event_day", "Presentation day"), ("post_5d", "5 days after"),
          ("post_10d", "10 days after")]


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def cell(v):
    if v is None:
        return '<span style="color:#7c93b6">n/a</span>'
    col = "#46d17f" if v > 0 else ("#ff7a72" if v < 0 else "#9db3d4")
    return f'<b style="color:{col}">{v:+.2f}%</b>'


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(STATS):
        print("SKIP: run build_conference_runup_stats.py first")
        return 0
    S = json.load(io.open(STATS, encoding="utf-8"))
    overall, by_conf, by_cc = S["overall"], S["by_conference"], S["by_conference_cap"]

    done = 0
    for p in sorted(glob.glob(os.path.join(SITE, "conference", "*", "index.html"))):
        code = os.path.basename(os.path.dirname(p)).upper()
        own = by_conf.get(code)
        src = own or overall
        scope = (f"{code} presentations" if own else "all tracked conference presentations")
        n = src.get("runup_10d", {}).get("n") or src.get("runup_30d", {}).get("n") or 0

        rows = ""
        for key, label in LABELS:
            d = src.get(key, {})
            rows += (f'<div class="kv" style="display:flex;justify-content:space-between;'
                     f'gap:12px;font-size:14px;padding:7px 0;border-bottom:1px solid #14263f">'
                     f'<span style="color:#9db3d4">{label}</span>'
                     f'<span>{cell(d.get("median"))}'
                     + (f'<span style="color:#7c93b6;font-size:12px">'
                        f'&nbsp; {d["pct_up"]:.0f}% rose &middot; n={d["n"]}</span>'
                        if d else "") + '</span></div>')

        tier_rows = ""
        for t, tlabel in TIERS:
            d = by_cc.get(f"{code}|{t}")
            if not d:
                continue
            tier_rows += (f'<div class="kv" style="display:flex;justify-content:space-between;'
                          f'gap:12px;font-size:13.5px;padding:6px 0;border-bottom:1px solid '
                          f'#14263f"><span style="color:#9db3d4">{tlabel}</span><span>'
                          f'{cell(d.get("runup_10d", {}).get("median"))} into it &nbsp;&rarr;&nbsp; '
                          f'{cell(d.get("post_5d", {}).get("median"))} after'
                          f'<span style="color:#7c93b6;font-size:12px">&nbsp; n='
                          f'{d.get("runup_10d", {}).get("n", 0)}</span></span></div>')
        tier_block = ""
        if tier_rows:
            tier_block = ('<div style="margin-top:14px"><div style="font-size:13px;color:#f0c86a;'
                          'font-weight:700;margin-bottom:4px">By company size '
                          '(10-day run-up &rarr; 5 days after)</div>' + tier_rows + '</div>')

        block = (
            f'{B}<h2 style="font-size:18px;color:#f0c86a;margin:26px 0 8px">'
            f'How {esc(code)} stocks have traded historically</h2>'
            f'<div style="background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;'
            f'padding:14px 16px;margin:12px 0">'
            f'<div style="font-size:13.5px;color:#9db3d4;margin-bottom:8px">'
            f'Median share-price move around a presentation, measured across <b>{n}</b> '
            f'{esc(scope)} in our study (2017&ndash;2026)'
            + ("" if own else f", because our study holds fewer than {S['_min_n']} "
                              f"{esc(code)} events on their own") + '.</div>'
            + rows + tier_block +
            '<div style="font-size:12px;color:#7c93b6;margin-top:10px;line-height:1.6">'
            'Read the whole row, not just the first line: across this study stocks have drifted '
            '<b>up into</b> these meetings and <b>down out of</b> them, and the effect is '
            'largest in the smallest companies. Medians are shown because a handful of large '
            'moves pulls an average away from the typical case. '
            'This is a historical distribution for a cohort of companies &mdash; not a forecast '
            'for any single company, and not investment advice. '
            '<a href="/research" style="color:#f0c86a">Methodology and the full study</a>.'
            f'</div></div>{E}')

        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if B in doc:
            doc = re.sub(re.escape(B) + ".*?" + re.escape(E), lambda _: block, doc,
                         count=1, flags=re.S)
        else:
            i = doc.find("<!--CFAQ:BEGIN-->")          # sit above the FAQ when present
            if i < 0:
                i = doc.find("Not affiliated with or endorsed by the FDA")
                i = doc.rfind("<div", 0, i) if i > 0 else doc.rfind("</main>")
            if i < 0:
                continue
            doc = doc[:i] + block + doc[i:]
        if not a.dry_run:
            io.open(p, "w", encoding="utf-8").write(doc)
        done += 1
        print(f"  {code:8s} {'own cohort' if own else 'all-conference fallback'} "
              f"n={n}, {len([1 for t, _ in TIERS if f'{code}|{t}' in by_cc])} size tier(s)")

    print(f"run-up module on {done} conference page(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
