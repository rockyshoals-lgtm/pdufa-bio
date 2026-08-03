# -*- coding: utf-8 -*-
"""add_decision_chart.py -- inject a run-up -> decision-day reaction chart into a decision page.

Builds an SVG from REAL Polygon daily closes spanning ~8 weeks before the FDA decision through today:
the run-up is drawn neutral, the segment AFTER the decision day is colored green/red (the reaction),
and the decision day itself is marked with a gold dot + dashed line. A caption states the day-of move.
If Polygon has no data for the ticker (e.g. some ADRs), the page keeps its honest "no chart" note.

Idempotent: the block carries id="reaction-chart" and is replaced (not duplicated) on re-run.

    python add_decision_chart.py --ticker OTLK --date 2026-07-24 [--days-before 55]
"""
import argparse, json, os, re, time
import datetime as dt
import urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
TODAY = dt.date.today()
NOCACHE = ('<p class="sub" style="font-size:13px">Daily price history for this ticker is not yet in '
           'our chart cache, so no run-up chart is shown for this decision (we do not estimate or '
           'fabricate price data).</p>')


def load_key():
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"), os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ.get("POLYGON_API_KEY")


def poly_daily(key, t, start, end):
    url = (f"https://api.polygon.io/v2/aggs/ticker/{t}/range/1/day/{start}/{end}"
           f"?adjusted=true&sort=asc&limit=300&apiKey={key}")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                rows = (json.loads(r.read().decode("utf-8", "replace")) or {}).get("results") or []
                return [(dt.datetime.fromtimestamp(x["t"] / 1000, dt.timezone.utc).date().isoformat(), x["c"])
                        for x in rows if x.get("c") is not None and x.get("t") is not None]
        except urllib.error.HTTPError as e:
            if e.code in (429,) or e.code >= 500:
                time.sleep(2 ** attempt); continue
            return []
        except Exception:
            time.sleep(1)
    return []


def build_chart(dated, decision_date):
    if len(dated) < 3:
        return None
    ds = [d for d, _ in dated]; cs = [c for _, c in dated]
    W, H, PAD = 340, 92, 6
    lo, hi = min(cs), max(cs); rng = (hi - lo) or 1.0; n = len(cs)
    X = lambda i: round(PAD + i * (W - 2 * PAD) / (n - 1), 1)
    Y = lambda c: round(H - PAD - (c - lo) / rng * (H - 2 * PAD), 1)
    di = next((i for i, d in enumerate(ds) if d >= decision_date), n - 1)
    move = (cs[di] / cs[di - 1] - 1) * 100.0 if (di > 0 and ds[di] == decision_date) else None
    pre = " ".join(f"{X(i)},{Y(c)}" for i, c in enumerate(cs[:di + 1]))
    post = " ".join(f"{X(i)},{Y(c)}" for i, c in enumerate(cs) if i >= di)
    rc = "#46d17f" if (move is None or move >= 0) else "#ff7a72"
    svg = (f'<svg width="100%" viewBox="0 0 {W} {H}" preserveAspectRatio="none" '
           f'style="display:block;height:96px;max-width:{W}px">'
           f'<line x1="{X(di)}" y1="{PAD}" x2="{X(di)}" y2="{H - PAD}" stroke="#e3ba5e" '
           f'stroke-width="1" stroke-dasharray="3 3" opacity="0.7"/>'
           f'<polyline points="{pre}" fill="none" stroke="#9db4d6" stroke-width="1.6"/>'
           f'<polyline points="{post}" fill="none" stroke="{rc}" stroke-width="2"/>'
           f'<circle cx="{X(di)}" cy="{Y(cs[di])}" r="3.2" fill="#e3ba5e" stroke="#02060d" stroke-width="0.8"/>'
           f'</svg>')
    dhuman = dt.date.fromisoformat(decision_date).strftime("%b %-d %Y") if os.name != "nt" \
        else dt.date.fromisoformat(decision_date).strftime("%b %d %Y")
    mv = ""
    if move is not None:
        mv = (f' Day-of move: <b style="color:{rc}">{"+" if move >= 0 else ""}{move:.0f}%</b>'
              f' (decision-day close vs prior close).')
    cap = (f'<p class="note" style="margin-top:10px">Gray = run-up into the FDA decision; '
           f'gold dot &amp; dashed line = the decision day ({dhuman}); colored line = the day-of '
           f'reaction and after.{mv} Daily closes via Polygon. Not a prediction.</p>')
    return (f'<div class="card" id="reaction-chart"><div style="font-size:12px;color:#94a9c9;'
            f'margin-bottom:6px">Run-up &amp; decision-day reaction</div>{svg}{cap}</div>')


def inject(path, block):
    html = open(path, encoding="utf-8").read()
    if 'id="reaction-chart"' in html:
        html = re.sub(r'<div class="card" id="reaction-chart">.*?</div>\s*</div>',
                      block, html, count=1, flags=re.S)
    elif NOCACHE in html:
        html = html.replace(NOCACHE, block, 1)
    else:
        html = html.replace("<h2>Key facts</h2>", block + "<h2>Key facts</h2>", 1)
    open(path, "w", encoding="utf-8").write(html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--date", required=True)             # YYYY-MM-DD decision date
    ap.add_argument("--days-before", type=int, default=55)
    a = ap.parse_args()
    page = os.path.join(SITE, "fda-decision", f"{a.ticker}-{a.date}", "index.html")
    if not os.path.exists(page):
        raise SystemExit(f"decision page not found: {page}")
    key = load_key()
    if not key:
        raise SystemExit("no POLYGON_API_KEY -> leaving the honest no-chart note in place")
    start = (dt.date.fromisoformat(a.date) - dt.timedelta(days=a.days_before)).isoformat()
    dated = poly_daily(key, a.ticker, start, TODAY.isoformat())
    block = build_chart(dated, a.date)
    if not block:
        print(f"no Polygon data for {a.ticker} -> keeping no-chart note (nothing fabricated)")
        return
    inject(page, block)
    print(f"injected reaction chart into {os.path.relpath(page, SITE)} ({len(dated)} daily closes)")


if __name__ == "__main__":
    main()
