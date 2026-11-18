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
# RULE 1 (audit 2026-10-13): the build runs after midnight UTC; countdowns and 'today' are Eastern.
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
from site_dates import eastern_today as _eastern_today
TODAY = _eastern_today()
GRACE_DAYS = 10   # keep a just-passed, unresolved PDUFA visible this long ("awaiting decision")
COH = {"Nano": "8.0%", "Micro": "4.6%", "Small": "3.6%", "Mid": "2.2%", "Large": "1.0%", "": "3.6%"}  # 1,827-event vintage
# 2026-10-22: the chips were typed in at the 1,827-event vintage and never moved; at 1,879 events Mid is 2.1%, not 2.2%.
# They now come from runup_study_stats.json (cohort_abs_move, median ABS decision-day move by tier) every build. A row
# with no cap tier keeps the Small figure, as before.
try:
    _cs = json.load(open(os.path.join(HERE, "runup_study_stats.json"), encoding="utf-8")).get("cohort_abs_move") or {}
    for _k, _v in _cs.items():
        _tier = _k.split(" ")[0]
        if _tier in COH and _v.get("median_abs_pct") is not None:
            COH[_tier] = f"{float(_v['median_abs_pct']):.1f}%"
    COH[""] = COH["Small"]
except Exception:  # noqa: BLE001  -- a missing stats file keeps the last typed values
    pass


def load_key():
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"), os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ.get("FMP_API_KEY")   # 2026-11-13: prices come from price_source (FMP)


def poly_closes(key, t, days=95):
    """Closes ascending. 2026-11-10: price_source (FMP primary, Polygon fallback); the key argument is unused."""
    return [c for _, c in poly_daily(key, t, days)]


def poly_daily(key, t, days=95):
    """[(iso_date, close)] ascending; [] when no feed has the ticker. Keeps the date so a decision day can be
    located and marked on the sparkline. 2026-11-10: price_source (FMP primary, Polygon fallback)."""
    import price_source
    return price_source.closes(t, (TODAY - dt.timedelta(days=days)).isoformat(), TODAY.isoformat())


def sparkline_reaction(dated, disclosed, after_close=False):
    """64x20 run-up polyline with a GOLD dot on the reaction day. Returns (svg, move_pct_or_None, reaction_day).

    2026-11-18 (design red team, change 2): the move used to be read only on the page's own date, so SMMT's CRL,
    announced on a Sunday (Nov 15), showed no move at all, and a decision dated by the FDA a day before it was
    public was measured on a day the market could not have known. The reaction day is now the first trading day
    ON OR AFTER the disclosure, or strictly AFTER it when the news came after the close (NVO-2026-03-26: "Announced
    2026-03-26, after the close"; that day's close is before the news). The move is its close against the previous
    close. The gold dot sits on the reaction day, and is left off when that day is not in the price series yet."""
    if len(dated) < 2:
        return "", None, None
    win = dated[-44:] if len(dated) > 44 else dated
    ds = [d for d, _ in win]; cs = [c for _, c in win]
    lo, hi = min(cs), max(cs); rng = (hi - lo) or 1.0; n = len(cs)
    X = lambda i: round(i * 64 / (n - 1), 1)
    Y = lambda c: round(19 - (c - lo) / rng * 18, 1)
    pts = " ".join(f"{X(i)},{Y(c)}" for i, c in enumerate(cs))
    color = "#46d17f" if cs[-1] >= cs[0] else "#ff7a72"
    after = (lambda d: d > disclosed) if after_close else (lambda d: d >= disclosed)
    alld = [d for d, _ in dated]; allc = [c for _, c in dated]
    move = day = None
    j = next((k for k, d in enumerate(alld) if after(d)), None)
    if j is not None and j > 0 and allc[j - 1] and \
            (dt.date.fromisoformat(alld[j]) - dt.date.fromisoformat(disclosed)).days <= 5:
        move, day = (allc[j] / allc[j - 1] - 1) * 100.0, alld[j]
    dot = ""
    if day in ds:
        di = ds.index(day)
        dot = f'<circle cx="{X(di)}" cy="{Y(cs[di])}" r="2.4" fill="#e3ba5e" stroke="#02060d" stroke-width="0.6"/>'
    svg = (f'<svg class="spk" width="64" height="20" viewBox="0 0 64 20" style="flex:0 0 auto" aria-hidden="true">'
           f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.4"/>{dot}</svg>')
    return svg, move, day


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

    def tokens(name):
        """Identity tokens of a drug name: lowercased runs of 4+ alphanumerics.

        'Oveporexton (TAK-861-2001)' and 'ORZEYFUL (oveporexton)' share {oveporexton} -> same
        drug. 'MK-6240' and 'Camzyos (mavacamten)' share nothing -> different drugs."""
        return {w for w in re.findall(r"[a-z0-9]{4,}", str(name or "").lower())}

    def resolved(tk, gdate, gdrug):
        """Is this upcoming catalyst already decided?

        The original rule resolved by TICKER alone: any approval within 270 days killed every
        upcoming catalyst the company had. For serial filers that deleted live events -- LNTH's
        Aug 13 MK-6240 PDUFA vanished because Lantheus had a March approval of a DIFFERENT drug,
        and BMY's iberdomide vanished behind Camzyos. The 270-day reach exists for one real case:
        the same drug approved ahead of its goal date (TAK's oveporexton, approved Aug 5 against a
        Sep 30 goal), so the reach stays but now requires the DRUG to match. Without names to
        compare on either side, only a tight window resolves -- deleting a live catalyst is the
        worse failure, and the decided-sweep will catch a true resolution within a day anyway.
        """
        g = dt.date.fromisoformat(gdate)
        gtok = tokens(gdrug)
        for t, d, outcome, ddrug in decisions:
            if t != tk:
                continue
            gap = (dt.date.fromisoformat(d) - g).days
            dtok = tokens(ddrug)
            same = bool(gtok & dtok)
            known = bool(gtok) and bool(dtok)
            if outcome == "crl":
                if abs(gap) <= 14 and (same or not known):
                    return True
            else:
                if same and gap >= -270:           # same drug approved, even well ahead of goal
                    return True
                if not known and abs(gap) <= 7:    # nameless: only a same-event date slip
                    return True
        return False

    cats = [c for c in slate["catalysts"] if c.get("ticker") and c.get("date")
            and str(c["date"])[:10] >= grace
            and not resolved(c["ticker"].upper(), str(c["date"])[:10],
                             c.get("drug") or c.get("drug_name") or "")]
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
        tail = html[m.end():m.end() + 200]
        low = tail.lower()
        outcome = "crl" if ("crl" in low or "complete response" in low) else "ap"
        # The drug text after the outcome marker, for identity matching in resolved().
        dm = re.search(r"(?:Approved|CRL)\s*:?\s*(.{0,90})", re.sub(r"<[^>]+>", " ", tail))
        out.append((tk, date, outcome, dm.group(1) if dm else ""))
    out.sort(key=lambda r: r[1], reverse=True)
    # collapse the same decision double-listed on both its real date and its PDUFA goal date
    # (e.g. UNCY 06-29 & 06-30): same ticker within a week -> keep only the newest
    dedup = []
    for tk, date, outcome, drug in out:
        if any(t == tk and abs((dt.date.fromisoformat(date) - dt.date.fromisoformat(d)).days) <= 7
               for t, d, _, _ in dedup):
            continue
        dedup.append((tk, date, outcome, drug))
    return dedup


def link_for(tk):
    if os.path.exists(os.path.join(SITE, "pdufa", tk, "index.html")):
        return f"/pdufa/{tk}"
    if os.path.exists(os.path.join(SITE, "ticker", tk, "index.html")):
        return f"/ticker/{tk}"
    return "/calendar"


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _dataset_rows():
    try:
        src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
        return json.loads(src[src.index("["):src.rindex("]") + 1])
    except Exception:  # noqa: BLE001
        return []


def _drug_tokens(name):
    """Identity tokens of a drug name (load_slate's tokens(): lowercased runs of 4+ alphanumerics)."""
    return {w for w in re.findall(r"[a-z0-9]{4,}", str(name or "").lower())}


def window_of(tk, date, rows, drug=""):
    """Design red team 2026-11-18 (change 1). The slate stores every goal as a day, so a month-precision goal
    (REGN cemdisiran, "Nov 2026") was baked as "PDUFA 2026-11-30, 12 days" and the client hydrator kept counting
    down to a day nobody stated. Returns the window label when the dataset holds this goal only as a month,
    quarter or year; None when it holds it as a day, since a stated day stays a day.

    The goal is found by drug identity first (the same tokens load_slate matches decisions on), whatever its status:
    precision belongs to the goal, so a goal the dataset already marks Decided, but which the decisions archive does
    not list yet, keeps its window rather than falling back to the slate's storage day. Matching only by "this ticker
    has a window containing the date" let one drug's window swallow another drug's exact day (RHHBY's Gazyva "Dec
    2026" over giredestrant's Nov 30 if the slate date drifted)."""
    from site_windows import is_day, is_withdrawn, window_label, window_span
    cands = [r for r in rows if r.get("t") == tk and r.get("type") == "PDUFA" and r.get("d")
             and not is_withdrawn(r)]
    if not cands:
        return None

    def span(r):
        s, e = window_span(r)
        return (s or str(r.get("d"))[:10]), (e or str(r.get("d"))[:10])

    def dist(r):
        s, e = span(r)
        if s <= date <= e:
            return 0
        a = dt.date.fromisoformat(date)
        return min(abs((dt.date.fromisoformat(s) - a).days), abs((dt.date.fromisoformat(e) - a).days))

    gtok = _drug_tokens(drug)
    same = [r for r in cands if gtok and gtok & _drug_tokens(r.get("name"))]
    if same:
        best = min(same, key=lambda r: (-len(gtok & _drug_tokens(r.get("name"))), dist(r), str(r.get("d"))))
        if dist(best) > 92:           # nothing of this drug near the slate date: no basis to coarsen it
            return None
        return None if is_day(best) else window_label(best)
    # No name to match on: a day row of this ticker on the date keeps the day; otherwise only a single window row
    # that contains the date may coarsen it.
    if any(is_day(r) and str(r.get("d"))[:10] == date for r in cands):
        return None
    wins = [r for r in cands if not is_day(r) and dist(r) == 0]
    return window_label(wins[0]) if len(wins) == 1 else None


def render_upcoming(cats, key):
    rows = []
    ds = _dataset_rows()
    for c in cats:
        tk, cap = c["ticker"], c.get("cap", "")
        date = str(c["date"])[:10]
        win = window_of(tk, date, ds, c.get("drug") or c.get("drug_name") or "")
        if win:
            # No countdown: the box shows the window, and "PDUFA window ..." is not a day the hydrator can match.
            parts = win.split(" ", 1)
            big, small = (parts[0], parts[1]) if len(parts) == 2 else (win, "window")
            label = f"PDUFA window {win}"
            if win.lower() == "not announced":      # the sponsor states no goal date at all
                big, small, label = "TBA", "date", "PDUFA date not announced"
            drug = esc(c.get("drug") or c.get("name") or tk)
            rows.append(
                f'<a class="row" href="{link_for(tk)}"><span class="cd"><b>{esc(big)}</b>'
                f'<i>{esc(small)}</i></span>'
                f'<span class="mid"><span class="tk">{esc(tk)} <em class="cap">{esc(cap)}</em></span>'
                f'<span class="dg">{drug} · {esc(label)}</span></span>{sparkline(poly_closes(key, tk))}'
                f'<span class="coh">{COH.get(cap, "±3%")}<i>cohort</i></span></a>')
            continue
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


def _page_kv(tk, page_date):
    p = os.path.join(SITE, "fda-decision", f"{tk}-{page_date}", "index.html")
    return open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else ""


def fda_day(tk, page_date):
    """(day, known) for /fda-decision/{tk}-{page_date}. day is the FDA's own action day: the dataset's
    fda_action_date, else the decision page's key facts ("FDA decision date"). When neither holds one (the page says
    "not found in a public FDA record"), day is the page date and known is False: the card then says "announced"."""
    u = f"/fda-decision/{tk}-{page_date}"
    try:
        from calendar_decided_rows_once import action_dates
        fad = action_dates().get(u)
    except Exception:  # noqa: BLE001
        fad = None
    if fad:
        return fad, True
    doc = _page_kv(tk, page_date)
    m = re.search(r'<div class="kv"><span>FDA decision date</span><b>(\d{4}-\d{2}-\d{2})</b>', doc)
    if m:
        return m.group(1), True
    m = re.search(r'<!--FDAREC:BEGIN-->.*?<b>FDA record of the action:</b> the FDA [a-z ]+? on <b>([A-Z][a-z]+ \d{1,2}, '
                  r'\d{4})</b>, per <a href="https://www\.(?:accessdata\.)?fda\.gov/', doc, re.S)
    if m:
        return dt.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat(), True
    return page_date, False


def disclosure(tk, page_date):
    """(day the decision was made public, after the close?) from the page's own "Announced" row, else the page date."""
    m = re.search(r'<div class="kv"><span>Announced</span><b>(\d{4}-\d{2}-\d{2})([^<]*)</b>', _page_kv(tk, page_date))
    if not m:
        return page_date, False
    return m.group(1), "after the close" in m.group(2).lower()


def _md(iso):
    x = dt.date.fromisoformat(iso)
    return f"{x.strftime('%b')} {x.day}"


DECIDED_NOTE = ('<p class="decn" style="margin:8px 0 0;font-size:11.5px;line-height:1.45;color:var(--mut2,#94a9c9)">'
                "Dates are the FDA's action day; a date marked announced has no public FDA record of its own. The move "
                "is the close on the first trading day after the decision was made public (the same day if it came "
                "before the close), against the close before it.</p>")


def render_decided(decs, key):
    cards = []
    acts = {(tk, date): fda_day(tk, date) for tk, date, _o, _d in decs}
    for tk, date, outcome, _drug in sorted(decs, key=lambda r: (acts[(r[0], r[1])][0], r[1]), reverse=True):
        cls = "dec ap" if outcome == "ap" else "dec cr"   # CSS styles CRL cards via .dec.cr
        icon = "✓" if outcome == "ap" else "✕"
        word = "Approved" if outcome == "ap" else "CRL"
        act, known = acts[(tk, date)]
        pub, after_close = disclosure(tk, date)
        spk, move, rday = sparkline_reaction(poly_daily(key, tk), pub, after_close)   # gold dot: reaction day
        mv = ""
        why = (f"FDA action {_md(act)}" + (f", made public {_md(pub)}" if pub != act else "") if known else
               f"Announced {_md(pub)}; no public FDA record of the action day")
        if after_close:
            why += " after the close"
        if move is not None:
            r = round(move)
            mc = "#46d17f" if r > 0 else ("#ff7a72" if r < 0 else "#94a9c9")
            mv = f' · <b style="color:{mc}">{"+" if r > 0 else ""}{r}%</b>'
            why += f"; move {'+' if r > 0 else ''}{r}% on {_md(rday)}, close against the previous close"
        shown = act if known else f"{date} announced"
        cards.append(
            f'<a class="{cls}" href="/fda-decision/{tk}-{date}" title="{esc(why)}"><span class="di">{icon}</span>'
            f'<span class="dt">{esc(tk)}</span>{spk}<span class="dd">{shown} · {word}{mv}</span></a>')
    return "".join(cards) + (DECIDED_NOTE if cards else "")


def _ua_eastern_date(ua):
    """'ua' is a UTC ISO stamp ('2026-11-09T04:05:00Z'). Its first 10 chars are the UTC date, which
    after 20:00 ET is already tomorrow: on 2026-11-08 at 23:30 ET the badge read 'Data through Nov 9'.
    The site's calendar date is Eastern (CLAUDE.md rule 1), so convert before taking the date."""
    s = str(ua or "")
    if len(s) < 10:
        return ""
    try:
        from site_dates import _ET
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=dt.timezone.utc)
        return t.astimezone(_ET).date().isoformat()
    except Exception:
        return s[:10]


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
        if r.get("type") != "PDUFA" or r.get("st") in ("Decided", "Withdrawn"):
            continue
        ua = _ua_eastern_date(r.get("ua")); d = str(r.get("d") or "")[:10]
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
    key = load_key() or "price_source"   # 2026-11-10: prices come from price_source (FMP); no Polygon key needed

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
