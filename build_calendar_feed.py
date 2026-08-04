# -*- coding: utf-8 -*-
"""build_calendar_feed.py -- a free, subscribable catalyst calendar at /calendar.ics.

There is already an .ics endpoint at /api/v1/calendar.ics, but it is deliberately gated behind the
Pro API tier. This writes a STATIC file instead, regenerated on every rebuild and served with no key,
so the paid API tiering is left completely untouched while readers get something they can subscribe
to once and forget.

The interesting problem is date precision. Only 91 of our ~419 events carry a real day; 271 are known
to a month and 57 to a quarter. The whole discipline of this site is that we never invent a day we
cannot source, and a calendar is the single easiest place to break that rule: dropping a
month-precision readout onto the 1st would put a fabricated date in someone's actual calendar app,
where it looks exactly as authoritative as a real PDUFA date.

So precision is preserved in the encoding rather than discarded:

    day      -> a one-day all-day event
    month    -> an all-day event spanning the whole month
    quarter  -> an all-day event spanning the whole quarter

A reader subscribing in Google or Apple Calendar sees a single square for a confirmed PDUFA date and
a bar across the window for an estimate. The imprecision becomes visible instead of hidden, and the
SUMMARY says which it is.

    python build_calendar_feed.py [--dry-run]
"""
import argparse, datetime as dt, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
STATS = os.path.join(HERE, "runup_study_stats.json")
OUT = os.path.join(SITE, "calendar.ics")

BASE = "https://www.pdufa.bio"
# Keep recent history in the feed: a subscriber looking back at last month's decisions is a feature.
BACKFILL_DAYS = 120

PRECISION_NOTE = {
    "day":     "Confirmed date.",
    "month":   "Company guidance or FDA action window is known to the month only; this entry spans "
               "the whole month rather than claiming a day.",
    "quarter": "Guidance is to the quarter only; this entry spans the quarter rather than claiming "
               "a day.",
}


def esc(s):
    """RFC 5545 text escaping. Order matters: backslash first or it double-escapes."""
    return (str(s or "").replace("\\", "\\\\").replace(";", r"\;")
            .replace(",", r"\,").replace("\n", r"\n"))


def fold(line):
    """RFC 5545 caps content lines at 75 octets; longer lines continue with a leading space.

    Real calendar clients do enforce this, and an unfolded long SUMMARY is a common reason a feed
    imports with missing or mangled events. Folding is done on encoded bytes, not characters, so a
    multi-byte character is never split down the middle.
    """
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        # 74 leaves room for the leading space on continuation lines
        if len(cur) + len(b) > (75 if not out else 74):
            out.append(cur.decode("utf-8"))
            cur = b""
        cur += b
    out.append(cur.decode("utf-8"))
    return ("\r\n ".join(out))


def load_rows():
    src = open(DATASET, encoding="utf-8", errors="replace").read()
    m = re.search(r"export default (\[.*\])", src, re.S)
    return json.loads(m.group(1)) if m else []


def window(d, dp):
    """(start_date, end_date_exclusive) for an all-day VEVENT, honouring the stated precision."""
    y, mo, day = int(d[0:4]), int(d[5:7]), int(d[8:10])
    start = dt.date(y, mo, day)
    if dp == "day":
        return start, start + dt.timedelta(days=1)
    if dp == "month":
        s = dt.date(y, mo, 1)
        e = dt.date(y + (mo == 12), (mo % 12) + 1, 1)
        return s, e
    if dp == "quarter":
        q0 = ((mo - 1) // 3) * 3 + 1
        s = dt.date(y, q0, 1)
        e = dt.date(y + (q0 + 3 > 12), ((q0 + 2) % 12) + 1, 1)
        return s, e
    return start, start + dt.timedelta(days=1)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = load_rows()
    today = dt.date.today()
    cutoff = today - dt.timedelta(days=BACKFILL_DAYS)

    stats = {}
    if os.path.exists(STATS):
        try:
            stats = json.load(open(STATS, encoding="utf-8"))
        except Exception:
            pass
    # One honest, sourced sentence carried on every PDUFA entry, so the feed teaches the study
    # rather than just listing dates.
    runup_note = ""
    if stats.get("T-120_peak_median_pct") is not None:
        runup_note = (f"Across {stats.get('n_events', 0):,} FDA decisions since "
                      f"{str(stats.get('date_min', ''))[:4]}, the median peak run-up from T-120 was "
                      f"{stats['T-120_peak_median_pct']:.1f}% and the median move from T-120 to the "
                      f"day before the decision was {stats.get('T-120_T-1_median_pct', 0):.1f}%. "
                      f"Past behaviour, not a forecast.")

    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0",
         "PRODID:-//pdufa.bio//catalyst calendar//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         "X-WR-CALNAME:pdufa.bio FDA catalysts",
         "X-WR-CALDESC:FDA PDUFA dates, advisory committees and clinical readouts. "
         "Entries spanning several days are estimates known only to that month or quarter.",
         "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H"]

    kept = skipped = 0
    by_prec = {}
    for e in rows:
        d, dp = e.get("d"), e.get("dp")
        if not d or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(d)):
            skipped += 1; continue
        try:
            s, end = window(d, dp)
        except Exception:
            skipped += 1; continue
        if end <= cutoff:
            skipped += 1; continue

        typ = e.get("type") or "Catalyst"
        tick = e.get("t") or ""
        name = e.get("name") or ""
        # Say the uncertainty in the title, because most calendar apps show only the title.
        prefix = "" if dp == "day" else "~"
        summary = f"{prefix}{tick} {typ}: {name}".strip()

        desc = [PRECISION_NOTE.get(dp, "")]
        if e.get("ta"):
            desc.append(f"Area: {e['ta']}.")
        if e.get("st"):
            desc.append(f"Status: {e['st']}.")
        if e.get("oc"):
            desc.append(f"Outcome: {e['oc']}.")
        if typ == "PDUFA" and runup_note:
            desc.append(runup_note)
        desc.append("Source: pdufa.bio. Informational only, not investment advice.")

        # A calendar entry's URL is the one thing a subscriber clicks. Many rows carry a
        # ClinicalTrials.gov or SEC link as their canonical source, and using that directly would
        # mean our own free calendar sends 242 of 418 readers straight off the site. So the click
        # goes to our page for the event, and the primary source is preserved in the description
        # where it still does its job of showing the claim is traceable.
        raw_url = str(e.get("url") or "")
        if raw_url.startswith("/"):
            url = BASE + raw_url
        else:
            if tick and os.path.isdir(os.path.join(SITE, "ticker", tick)):
                url = f"{BASE}/ticker/{tick}"
            elif typ == "Readout":
                url = f"{BASE}/readouts"
            else:
                url = f"{BASE}/calendar"
            if raw_url.startswith("http"):
                desc.insert(-1, f"Primary source: {raw_url}")

        L += ["BEGIN:VEVENT",
              f"UID:{esc(e.get('id') or (tick + d))}@pdufa.bio",
              f"DTSTAMP:{stamp}",
              f"DTSTART;VALUE=DATE:{s.strftime('%Y%m%d')}",
              f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
              f"SUMMARY:{esc(summary)}",
              f"DESCRIPTION:{esc(' '.join(x for x in desc if x))}",
              f"URL:{esc(url)}",
              "TRANSP:TRANSPARENT",          # do not make subscribers look busy all month
              "END:VEVENT"]
        kept += 1
        by_prec[dp] = by_prec.get(dp, 0) + 1

    L.append("END:VCALENDAR")
    ics = "\r\n".join(fold(x) for x in L) + "\r\n"

    print(f"calendar feed: {kept} event(s) kept, {skipped} skipped "
          f"(undated or older than {BACKFILL_DAYS}d)")
    for k in ("day", "month", "quarter"):
        if by_prec.get(k):
            shape = "single day" if k == "day" else f"spans the {k}"
            print(f"   {k:<8} {by_prec[k]:>4}   ({shape})")

    if a.dry_run:
        print("dry-run: not written"); return
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(ics)
    print(f"wrote {os.path.relpath(OUT, HERE)} ({len(ics):,} bytes)")

    inject_subscribe(kept, by_prec, stats)


SUB_BEGIN = "<!--SUBSCRIBE:BEGIN-->"
SUB_END = "<!--SUBSCRIBE:END-->"


def inject_subscribe(kept, by_prec, stats):
    """Put the subscribe box on /calendar, between markers so it is regenerated, not duplicated."""
    page = os.path.join(SITE, "calendar", "index.html")
    if not os.path.exists(page):
        print("  note: /calendar page not found; feed written but not linked"); return
    html = open(page, encoding="utf-8", errors="replace").read()

    exact = by_prec.get("day", 0)
    windowed = by_prec.get("month", 0) + by_prec.get("quarter", 0)
    peak = stats.get("T-120_peak_median_pct")
    n_ev = stats.get("n_events")
    cov = stats.get("t120_coverage_pct")

    runup_line = ""
    if peak is not None and n_ev:
        runup_line = (
            f'<div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--line);'
            f'font-size:12.5px;color:var(--mut2);line-height:1.65">'
            f'<b style="color:#eef4fc">Run-up context, measured from a uniform T-120 baseline.</b> '
            f'Across {n_ev:,} FDA decisions since {str(stats.get("date_min",""))[:4]}, the median '
            f'peak gain from 120 trading days out was '
            f'<b class="lit" style="color:#46d17f">{peak:.1f}%</b>, while the median move from '
            f'T-120 to the day before the decision was '
            f'<b class="lit">{stats.get("T-120_T-1_median_pct", 0):.1f}%</b>. '
            f'The gap between those two numbers is the point: most of the move happens before the '
            f'decision and is usually given back. '
            f'{cov:.0f}% of events have a full T-120 window; the rest are excluded rather than '
            f'back-filled. <a href="/runup-by-year">Full study</a>. '
            f'Past behaviour, not a forecast, and not investment advice.</div>')

    block = (
        f'{SUB_BEGIN}'
        f'<div class="subscribe" style="background:var(--card);border:1px solid var(--line);'
        f'border-radius:14px;padding:16px 18px;margin:14px 0 20px">'
        f'<div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;'
        f'justify-content:space-between">'
        f'<div><div style="font-family:\'Space Grotesk\',sans-serif;font-weight:700;'
        f'font-size:16px;color:#eef4fc">Put this calendar in your calendar</div>'
        f'<div style="font-size:12.5px;color:var(--mut2);margin-top:3px">'
        f'{kept:,} catalysts, refreshed daily. Free, and no account needed.</div></div>'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap">'
        f'<a href="webcal://www.pdufa.bio/calendar.ics" '
        f'style="display:inline-flex;align-items:center;min-height:40px;padding:9px 15px;'
        f'border-radius:10px;background:#46d17f;color:#04121f;font-weight:700;font-size:13.5px;'
        f'text-decoration:none">Subscribe</a>'
        f'<a href="/calendar.ics" download '
        f'style="display:inline-flex;align-items:center;min-height:40px;padding:9px 15px;'
        f'border-radius:10px;border:1px solid var(--line);color:#eef4fc;font-size:13.5px;'
        f'text-decoration:none">Download .ics</a></div></div>'
        f'<div style="font-size:12px;color:var(--mut2);margin-top:11px;line-height:1.6">'
        f'Subscribing keeps it current: new dates and changes arrive automatically. '
        f'<b style="color:#eef4fc">{exact:,}</b> entries have a confirmed date and appear on that '
        f'single day. <b style="color:#eef4fc">{windowed:,}</b> are guided only to a month or '
        f'quarter, so they span that whole window and are prefixed with '
        f'<span class="lit">~</span>. We do not place an estimate on a specific day, because in a '
        f'calendar app a guess looks exactly like a confirmed FDA date.</div>'
        f'{runup_line}</div>{SUB_END}')

    if SUB_BEGIN in html:
        html = re.sub(re.escape(SUB_BEGIN) + ".*?" + re.escape(SUB_END), lambda m: block,
                      html, flags=re.S)
    else:
        anchor = '<div class="hmap"'
        if anchor in html:
            html = html.replace(anchor, block + anchor, 1)
        else:
            print("  note: could not find an anchor on /calendar; box not inserted"); return

    open(page, "w", encoding="utf-8").write(html)
    print(f"  subscribe box on /calendar: {exact} exact-date, {windowed} windowed")


if __name__ == "__main__":
    main()
