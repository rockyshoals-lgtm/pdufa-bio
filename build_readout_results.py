# -*- coding: utf-8 -*-
"""build_readout_results.py -- keep /readouts current AND auto-log readout stock reactions.

Two jobs, run every day by the autonomous engine:

 1) PRUNE: drop month / quarter / half-year sections whose window is already in the past (so June &
    July stop showing once we're past them). Pure date logic on the section labels -- format-agnostic.

 2) LOG (hybrid): for every readout whose estimated window has elapsed, auto-log the stock's move over
    that window from Polygon daily closes and render a "Recently reported" results block at the top of
    the page. Readouts are ESTIMATED month windows, not confirmed dated events, so this is explicitly
    labelled the market's move over the window -- NOT a claim the trial read out that day or succeeded.
    A confirmed exact date + outcome (added via the review sweep) later upgrades an entry to a precise
    day-of reaction; nothing here is invented.

Idempotent: the results block is delimited by <!--/readout-results--> and replaced in place.

    python build_readout_results.py [--dry-run]
"""
import argparse, json, os, re, time
import datetime as dt
import urllib.request, urllib.error

SITE = "pdufa_site_src"
PAGE = os.path.join(SITE, "readouts", "index.html")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = dt.date.today()
MON = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}
MON3 = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
BLOCK = re.compile(r'<div class="mhead">([^<]+)</div><div class="grid">.*?(?=<div class="mhead">|<div class="note"|$)', re.S)


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
    if not key:
        return []
    url = (f"https://api.polygon.io/v2/aggs/ticker/{t}/range/1/day/{start}/{end}"
           f"?adjusted=true&sort=asc&limit=200&apiKey={key}")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                rows = (json.loads(r.read().decode("utf-8", "replace")) or {}).get("results") or []
                return [x["c"] for x in rows if x.get("c") is not None]
        except urllib.error.HTTPError as e:
            if e.code in (429,) or e.code >= 500:
                time.sleep(2 ** attempt); continue
            return []
        except Exception:
            time.sleep(1)
    return []


def label_is_past(label):
    """True if a section label ('June 2026', 'Q2 2026 (est.)', 'H1 2026 (est.)') is fully in the past."""
    s = label.replace("(est.)", "").strip()
    m = re.match(r'^([A-Za-z]+)\s+(\d{4})$', s)
    if m and m.group(1) in MON:
        y, mo = int(m.group(2)), MON[m.group(1)]
        return (y, mo) < (TODAY.year, TODAY.month)
    m = re.match(r'^Q([1-4])\s+(\d{4})$', s)
    if m:
        y, endm = int(m.group(2)), int(m.group(1)) * 3
        return (y, endm) < (TODAY.year, TODAY.month)
    m = re.match(r'^H([12])\s+(\d{4})$', s)
    if m:
        y, endm = int(m.group(2)), int(m.group(1)) * 6
        return (y, endm) < (TODAY.year, TODAY.month)
    return False


def prune(html):
    dropped = []
    def repl(m):
        if label_is_past(m.group(1)):
            dropped.append(m.group(1).strip()); return ""
        return m.group(0)
    return BLOCK.sub(repl, html), dropped


def load_past_readouts():
    src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    arr, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    cur = TODAY.strftime("%Y-%m")
    out = []
    for r in arr:
        if r.get("type") != "Readout" or not r.get("t"):
            continue
        ym = (r.get("dm") or str(r.get("d") or "")[:7])
        if not re.match(r'^\d{4}-\d{2}$', ym) or ym >= cur:
            continue  # only fully-elapsed month windows
        out.append({"t": r["t"], "ym": ym, "name": r.get("name") or r["t"], "url": r.get("url") or ""})
    out.sort(key=lambda x: x["ym"], reverse=True)
    return out


def spark(closes):
    cs = closes[-46:] if len(closes) > 46 else closes
    if len(cs) < 2:
        return "", None
    lo, hi = min(cs), max(cs); rng = (hi - lo) or 1.0; n = len(cs)
    pts = " ".join(f"{round(i*72/(n-1),1)},{round(19-(c-lo)/rng*18,1)}" for i, c in enumerate(cs))
    move = (cs[-1] / cs[0] - 1) * 100.0 if cs[0] else None
    color = "#46d17f" if (move is None or move >= 0) else "#ff7a72"
    svg = (f'<svg width="72" height="20" viewBox="0 0 72 20" style="flex:0 0 auto">'
           f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.4"/></svg>')
    return svg, move


def window_bounds(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    start = dt.date(y, m, 1)
    end = (dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(days=1))
    return (start - dt.timedelta(days=6)).isoformat(), min(end + dt.timedelta(days=6), TODAY).isoformat()


def esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_section(readouts, key, limit):
    rows = []
    for r in readouts[:limit]:
        s, e = window_bounds(r["ym"])
        svg, move = spark(poly_daily(key, r["t"], s, e))
        win = f"{MON3[int(r['ym'][5:7]) - 1]} {r['ym'][:4]}"
        if move is None:
            mv = '<div style="margin-left:auto;color:#7c93b6;font-size:12px">no price data</div>'
        else:
            col = "#46d17f" if move >= 0 else "#ff7a72"
            mv = f'<div style="margin-left:auto;font-weight:800;color:{col}">{"+" if move>=0 else ""}{move:.0f}%</div>'
        href = esc(r["url"] or "#")
        rows.append(
            f'<a class="row" href="{href}" rel="nofollow" style="display:flex;align-items:center;gap:12px">'
            f'<div style="min-width:150px"><div class="t">{esc(r["t"])} &middot; {win}</div>'
            f'<div class="d">{esc(r["name"])[:60]}</div></div>{svg}{mv}</a>')
    if not rows:
        return ""
    return ('<div id="readout-results">'
            '<div class="mhead" style="color:#46d17f">Recently reported &mdash; stock move over the estimated readout window</div>'
            '<div class="note" style="margin:-2px 0 8px">Auto-logged: each stock\'s price move across its '
            'estimated readout window (Polygon daily closes). These are estimated month windows, so the exact '
            'announcement date and clinical outcome are not yet verified &mdash; this shows the market\'s move '
            'over the window, not a statement about trial success. '
            '<a href="/methodology" style="color:#e3ba5e">Methodology</a>.</div>'
            f'<div class="grid">{"".join(rows)}</div></div><!--/readout-results-->')


def inject(html, section):
    if not section:
        return html
    if "<!--/readout-results-->" in html:
        return re.sub(r'<div id="readout-results">.*?<!--/readout-results-->', section, html, count=1, flags=re.S)
    i = html.find('<div class="mhead">')
    if i < 0:
        return html
    return html[:i] + section + html[i:]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=40); a = ap.parse_args()
    html = open(PAGE, encoding="utf-8", errors="replace").read().replace("\x00", "")
    html, dropped = prune(html)
    key = load_key()
    readouts = load_past_readouts()
    section = build_section(readouts, key, a.limit)
    html = inject(html, section)
    print(f"pruned past sections: {dropped or 'none'}")
    print(f"logged {min(len(readouts), a.limit)} readout window-moves (of {len(readouts)} past) "
          f"| polygon={'yes' if key else 'NO KEY'}")
    if a.dry_run:
        print("DRY RUN -- not written."); return
    open(PAGE, "w", encoding="utf-8").write(html)
    print("wrote /readouts.")


if __name__ == "__main__":
    main()
