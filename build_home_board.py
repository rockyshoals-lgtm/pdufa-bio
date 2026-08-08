# -*- coding: utf-8 -*-
"""build_home_board.py -- regenerate the homepage's two live board sections from DATA, every run.

Replaces the hand-maintained (and fragile) homepage board with a real generator, so it is always:
  * SORTED  -- "Next FDA decisions" in true date order (a corrected date like CAPR 07-29->08-22
               moves to its right slot automatically instead of sitting where it was).
  * PROMOTED -- "Recently decided" rebuilt from the decisions archive, newest first, so an approval
               (MNKD) always appears without a manual edit.
  * CHARTED -- every tile gets a real run-up sparkline built from Polygon daily closes (this is what
               gives MNKD's decided tile a graph like the others).

Countdowns stay hydrator-driven (baked value is a placeholder the browser recomputes). Links go to
/pdufa/{T} when that page exists, else the /ticker/{T} hub, else /calendar -- never a 404.

Idempotent, backs up index.html first. Run standalone or from the hourly task.

    python build_home_board.py [--upcoming 8] [--decided 10] [--dry-run]
"""
import argparse, json, os, re, sys, time
import datetime as dt
import urllib.parse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
HOME = os.path.join(SITE, "index.html")
API = os.path.join(SITE, "api", "data.js")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
DECISIONS = os.path.join(SITE, "decisions", "index.html")
MON3 = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
TODAY = dt.date.today()
GRACE_DAYS = 10   # keep a just-passed, unresolved PDUFA visible this long ("awaiting decision")
COH = {"Nano": "8.0%", "Micro": "4.6%", "Small": "3.6%", "Mid": "2.2%", "Large": "1.0%", "": "3.6%"}  # median ABS decision-day move, recomputed from the 1,827-event study


def load_key():
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"), os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ.get("POLYGON_API_KEY")


def poly_closes(key, t, days=95):
    if not key:
        return []
    start = (TODAY - dt.timedelta(days=days)).isoformat()
    url = (f"https://api.polygon.io/v2/aggs/ticker/{t}/range/1/day/{start}/{TODAY.isoformat()}"
           f"?adjusted=true&sort=asc&limit=120&apiKey={key}")
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


def poly_daily(key, t, days=95):
    """[(iso_date, close)] ascending; [] on any failure / no key. Same source as poly_closes but
    keeps the date so a decision day can be located and marked on the sparkline."""
    if not key:
        return []
    start = (TODAY - dt.timedelta(days=days)).isoformat()
    url = (f"https://api.polygon.io/v2/aggs/ticker/{t}/range/1/day/{start}/{TODAY.isoformat()}"
           f"?adjusted=true&sort=asc&limit=200&apiKey={key}")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                rows = (json.loads(r.read().decode("utf-8", "replace")) or {}).get("results") or []
                out = []
                for x in rows:
                    c, ts = x.get("c"), x.get("t")
                    if c is None or ts is None:
                        continue
                    out.append((dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc).date().isoformat(), c))
                return out
        except urllib.error.HTTPError as e:
            if e.code in (429,) or e.code >= 500:
                time.sleep(2 ** attempt); continue
            return []
        except Exception:
            time.sleep(1)
    return []


def sparkline_reaction(dated, decision_date):
    """64x20 run-up polyline with a GOLD dot on the decision day, so the day-of reaction is visible.
    Returns (svg, day_of_move_pct_or_None). Move = decision-day close vs the prior trading close."""
    if len(dated) < 2:
        return "", None
    win = dated[-44:] if len(dated) > 44 else dated
    ds = [d for d, _ in win]; cs = [c for _, c in win]
    lo, hi = min(cs), max(cs); rng = (hi - lo) or 1.0; n = len(cs)
    X = lambda i: round(i * 64 / (n - 1), 1)
    Y = lambda c: round(19 - (c - lo) / rng * 18, 1)
    pts = " ".join(f"{X(i)},{Y(c)}" for i, c in enumerate(cs))
    color = "#46d17f" if cs[-1] >= cs[0] else "#ff7a72"
    di = next((i for i, d in enumerate(ds) if d >= decision_date), n - 1)  # first day on/after decision
    alld = [d for d, _ in dated]; allc = [c for _, c in dated]
    move = None
    if decision_date in alld:
        j = alld.index(decision_date)
        if j > 0 and allc[j - 1]:
            move = (allc[j] / allc[j - 1] - 1) * 100.0
    dot = f'<circle cx="{X(di)}" cy="{Y(cs[di])}" r="2.4" fill="#e3ba5e" stroke="#02060d" stroke-width="0.6"/>'
    svg = (f'<svg class="spk" width="64" height="20" viewBox="0 0 64 20" style="flex:0 0 auto">'
           f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.4"/>{dot}</svg>')
    return svg, move


def sparkline(closes):
    """A 64x20 polyline from closes; green if it ended up over the window, red if down. Empty -> ''."""
    cs = closes[-44:] if len(closes) > 44 else closes
    if len(cs) < 2:
        return ""
    lo, hi = min(cs), max(cs)
    rng = (hi - lo) or 1.0
    n = len(cs)
    pts = " ".join(f"{round(i * 64 / (n - 1), 1)},{round(19 - (c - lo) / rng * 18, 1)}" for i, c in enumerate(cs))
    color = "#46d17f" if cs[-1] >= cs[0] else "#ff7a72"
    return (f'<svg class="spk" width="64" height="20" viewBox="0 0 64 20" style="flex:0 0 auto">'
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.4"/></svg>')


def load_slate():
    src = open(API, encoding="utf-8").read()
    i = src.find("const SLATE=")
    slate, _ = json.JSONDecoder().raw_decode(src[i + len("const SLATE="):])
    # Keep a catalyst whose PDUFA date just passed but has no confirmed outcome yet: FDA/company
    # announcements often lag the goal date by a day or two (and foreign filers like Otsuka aren't
    # caught by our SEC decided-sweep). Without this grace window such a catalyst vanishes silently
    # the morning after its date -- dropped from Upcoming, not yet in Decided. It shows as "awaiting".
    grace = (TODAY - dt.timedelta(days=GRACE_DAYS)).isoformat()

    # Resolve a slate row against the archive by TICKER and a date window, not by exact date.
    #
    # This was keyed on (ticker, date), matching the slate's PDUFA GOAL date against the archive's
    # ACTUAL decision date. Those are only the same when the FDA acts precisely on its goal date.
    # Replimune's goal was 2026-08-02 and the approval came 2026-08-06, so the keys never matched:
    # REPL appeared under "Next FDA decisions" as "0 due" AND under "Recently decided" as approved,
    # on the same screen. Moderna was excluded correctly only by the accident of the FDA acting on
    # the exact day.
    #
    # The asymmetry is the same one the calendar marker needs. An APPROVAL ends the application, so
    # it resolves a goal date whenever it lands, before or after. A CRL is why a later goal date
    # exists at all, because the company resubmits and the FDA starts a new clock, so a CRL only
    # resolves a goal date it is close to. Treating them alike would delete a live, pending catalyst
    # from the board on the strength of last cycle's rejection.
    decisions = load_decisions()

    def resolved(tk, gdate):
        g = dt.date.fromisoformat(gdate)
        for t, d, outcome in decisions:
            if t != tk:
                continue
            gap = (dt.date.fromisoformat(d) - g).days
            if outcome == "crl":
                if abs(gap) <= 14:                 # this cycle's rejection
                    return True
            elif gap >= -270:                      # an approval, whenever it landed
                return True
        return False

    cats = [c for c in slate["catalysts"] if c.get("ticker") and c.get("date")
            and str(c["date"])[:10] >= grace
            and not resolved(c["ticker"].upper(), str(c["date"])[:10])]
    # collapse accidental duplicates on (ticker, date); keep the richest drug name so the board
    # never shows the same catalyst twice even if the slate has a stray dupe
    best = {}
    for c in cats:
        k = (c["ticker"].upper(), str(c["date"])[:10])
        if k not in best or len(str(c.get("drug") or "")) > len(str(best[k].get("drug") or "")):
            best[k] = c
    return sorted(best.values(), key=lambda c: str(c["date"])[:10])


def load_decisions():
    if not os.path.exists(DECISIONS):
        return []
    html = open(DECISIONS, encoding="utf-8").read()
    seen, out = set(), []
    for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', html):
        tk, date = m.group(1), m.group(2)
        if (tk, date) in seen:
            continue
        seen.add((tk, date))
        tail = html[m.end():m.end() + 160].lower()
        outcome = "crl" if ("crl" in tail or "complete response" in tail) else "ap"
        out.append((tk, date, outcome))
    out.sort(key=lambda r: r[1], reverse=True)
    # collapse the same decision double-listed on both its real date and its PDUFA goal date
    # (e.g. UNCY 06-29 & 06-30): same ticker within a week -> keep only the newest
    dedup = []
    for tk, date, outcome in out:
        if any(t == tk and abs((dt.date.fromisoformat(date) - dt.date.fromisoformat(d)).days) <= 7
               for t, d, _ in dedup):
            continue
        dedup.append((tk, date, outcome))
    return dedup


def link_for(tk):
    if os.path.exists(os.path.join(SITE, "pdufa", tk, "index.html")):
        return f"/pdufa/{tk}"
    if os.path.exists(os.path.join(SITE, "ticker", tk, "index.html")):
        return f"/ticker/{tk}"
    return "/calendar"


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_upcoming(cats, key):
    rows = []
    for c in cats:
        tk, cap = c["ticker"], c.get("cap", "")
        date = str(c["date"])[:10]
        d = (TODAY - dt.date.fromisoformat(date)).days * -1
        # A PDUFA date that has passed with no outcome posted yet must not render as "-1 days".
        # The client hydrator already rewrote this to "0 due" at view time, but the BAKED html is
        # what crawlers index and what a reader sees before JS runs, and "-1 days" reads as a bug.
        cd_n, cd_u = (str(d), "days" if d != 1 else "day") if d > 0 else \
                     ("0", "today" if d == 0 else "due")
        drug = esc(c.get("drug") or c.get("name") or tk)
        spk = sparkline(poly_closes(key, tk))
        rows.append(
            f'<a class="row" href="{link_for(tk)}"><span class="cd"><b>{cd_n}</b>'
            f'<i>{cd_u}</i></span>'
            f'<span class="mid"><span class="tk">{esc(tk)} <em class="cap">{esc(cap)}</em></span>'
            f'<span class="dg">{drug} · PDUFA {date}</span></span>{spk}'
            f'<span class="coh">{COH.get(cap, "±3%")}<i>cohort</i></span></a>')
    return "".join(rows)


def render_decided(decs, key):
    cards = []
    for tk, date, outcome in decs:
        cls = "dec ap" if outcome == "ap" else "dec cr"   # CSS styles CRL cards via .dec.cr
        icon = "✓" if outcome == "ap" else "✕"
        word = "Approved" if outcome == "ap" else "CRL"
        spk, move = sparkline_reaction(poly_daily(key, tk), date)   # gold dot marks the decision day
        mv = ""
        if move is not None:
            mc = "#46d17f" if move >= 0 else "#ff7a72"
            mv = f' · <b style="color:{mc}">{"+" if move >= 0 else ""}{move:.0f}%</b>'
        cards.append(
            f'<a class="{cls}" href="/fda-decision/{tk}-{date}"><span class="di">{icon}</span>'
            f'<span class="dt">{esc(tk)}</span>{spk}<span class="dd">{date} · {word}{mv}</span></a>')
    return "".join(cards)


def freshness_label():
    """Server-side twin of the homepage freshness JS: MODE of updated_at over FORWARD PDUFA rows.
    Bakes 'Data through {date}' into the HTML so a non-JS crawler sees the real currency, not the
    'free, no login' fallback. Returns (label, age_days) or (None, None)."""
    try:
        src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
        arr, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    except Exception:
        return None, None
    tISO = TODAY.isoformat(); counts = {}
    for r in arr:
        if r.get("type") != "PDUFA" or r.get("st") == "Decided":
            continue
        ua = str(r.get("ua") or "")[:10]; d = str(r.get("d") or "")[:10]
        if not ua or d < tISO:
            continue
        counts[ua] = counts.get(ua, 0) + 1
    if not counts:
        return None, None
    best = max(counts, key=counts.get)
    y, m, dd = (int(x) for x in best.split("-"))
    age = (TODAY - dt.date(y, m, dd)).days
    return f"Data through {MON3[m - 1]} {dd} · free, no login", age


def stamp_freshness(html):
    label, age = freshness_label()
    if not label:
        return html
    html = re.sub(r'(<span id="fresh">).*?(</span>)', lambda m: m.group(1) + label + m.group(2),
                  html, count=1, flags=re.S)
    if age is not None and age > 7:  # never overstate currency: dim the dot server-side too
        html = html.replace('<span class="dot"></span><span id="fresh">',
                            '<span class="dot" style="background:#e3ba5e;box-shadow:none"></span><span id="fresh">', 1)
    return html


def stamp_study_size(html):
    """The homepage headline stat "N events in the run-up study" was a hardcoded literal, so it
    drifted every time the study grew (it read 1,754 while the study held 1,827). Drive it from
    runup_study_stats.json, the same file every other published run-up figure comes from."""
    f = os.path.join(HERE, "runup_study_stats.json")
    if not os.path.exists(f):
        return html
    n = json.load(open(f, encoding="utf-8")).get("n_events")
    if not n:
        return html
    new, k = re.subn(r'(<b>)[\d,]+(</b><span>events in the run-up study</span>)',
                     lambda m: m.group(1) + f"{n:,}" + m.group(2), html, count=1)
    if k:
        print(f"  run-up study stat -> {n:,} events")
    return new


def replace_block(html, open_tag, inner):
    i = html.find(open_tag)
    if i < 0:
        raise SystemExit(f"container {open_tag!r} not found in index.html")
    j = html.find("</div>", i + len(open_tag))
    return html[:i + len(open_tag)] + inner + html[j:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upcoming", type=int, default=8)
    ap.add_argument("--decided", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    key = load_key()

    cats = load_slate()[:a.upcoming]
    decs = load_decisions()[:a.decided]
    print(f"upcoming: {len(cats)} (sorted by date)  |  decided: {len(decs)} (newest first)  |  "
          f"polygon={'yes' if key else 'NO KEY -> no sparklines'}")
    for c in cats:
        print(f"  next  {c['ticker']:6s} {str(c['date'])[:10]}  {(c.get('drug') or '')[:30]}")

    html = open(HOME, encoding="utf-8").read()
    html = replace_block(html, '<div class="list">', render_upcoming(cats, key))
    html = replace_block(html, '<div class="decs">', render_decided(decs, key))
    html = stamp_study_size(html)  # keep the headline study count from drifting
    html = stamp_freshness(html)   # server-render the "Data through {date}" badge for non-JS crawlers

    if a.dry_run:
        print("\nDRY RUN -- not written.")
        return
    open(HOME + ".bak_board", "w", encoding="utf-8").write(open(HOME, encoding="utf-8").read())
    open(HOME, "w", encoding="utf-8").write(html)
    print(f"\nrewrote homepage board (backup: index.html.bak_board).")


if __name__ == "__main__":
    main()
