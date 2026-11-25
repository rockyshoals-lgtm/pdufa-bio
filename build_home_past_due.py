# -*- coding: utf-8 -*-
"""Home page "Past their goal date" box: every PDUFA goal date that has passed with no FDA decision on record.

David, 2026-11-25: "add a past due box on the home page for pdufas that missed their date so it stays current and
accurate". Before this, a goal date that passed without a decision stayed in "Next FDA decisions" as "0 due" for ten
days (build_home_board.GRACE_DAYS) and then left the home page altogether, though the application was still pending.

One rule, shared with the event pages (mark_goal_date_passed.py) and the API (/api/v1 calls such a row "Awaiting"):
a dataset PDUFA row is past due when it is still open (Upcoming, Awaiting or Under review), its goal is a stated date
(not "not announced") and the whole stated period has ended before today, Eastern: the day itself for a day, the
last day of the month or quarter for a month or quarter goal. A row the dataset holds as Decided or Withdrawn is never
past due; it leaves the box on the run that records its decision.

When the sponsor has said, with a source, that the FDA will not act by the date (_goal_date_passed.json, hand-verified,
e.g. Savara on 2026-11-20), the row says so and links that source. Otherwise it says only that no decision is on
record as of today, which is what the event page says too. NRXP's KETAFREE in that ledger is an ANDA with a GDUFA goal
date, not a PDUFA date, and has no PDUFA row, so it is not listed here.

Marker-bounded (<!--PASTDUE:BEGIN/END-->), placed at the top of the home page's side column, above "Recently
decided". Idempotent. build_home_board.py leaves these rows out of "Next FDA decisions" so no goal shows twice.
tests/test_home_past_due.py recomputes the list from the dataset and fails on any row missing, extra or stale.

    python build_home_past_due.py [--dry-run]
"""
import argparse
import calendar
import datetime as dt
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402  (RULE 1: a goal date passes at midnight Eastern)

SITE = os.path.join(HERE, "pdufa_site_src")
HOME = os.path.join(SITE, "index.html")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
LEDGER = os.path.join(HERE, "_goal_date_passed.json")
B, E = "<!--PASTDUE:BEGIN-->", "<!--PASTDUE:END-->"
OPEN = ("upcoming", "awaiting", "under review")
MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
         "November", "December"]


def _rows():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    return rows


def _ledger():
    try:
        return {e["slug"]: e for e in json.load(io.open(LEDGER, encoding="utf-8")).get("passed", [])}
    except Exception:  # noqa: BLE001
        return {}


def period_end(d, dp):
    """Last day of the stated goal period: the day, or the end of its month, quarter or year."""
    dp = str(dp or "day").lower()
    if dp == "month":
        return d.replace(day=calendar.monthrange(d.year, d.month)[1])
    if dp == "quarter":
        m = ((d.month - 1) // 3 + 1) * 3
        return dt.date(d.year, m, calendar.monthrange(d.year, m)[1])
    if dp == "year":
        return dt.date(d.year, 12, 31)
    return d


def goal_words(d, dp):
    dp = str(dp or "day").lower()
    if dp == "month":
        return f"{MONTH[d.month]} {d.year}"
    if dp == "quarter":
        return f"Q{(d.month - 1) // 3 + 1} {d.year}"
    if dp == "year":
        return str(d.year)
    return f"{MON[d.month]} {d.day}, {d.year}"


def short_day(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month]} {d.day}"


def drug_of(r):
    """The event page's own "Drug / candidate" fact, else the dataset name without its trial suffix."""
    u = str(r.get("url") or "")
    p = os.path.join(SITE, u.strip("/"), "index.html") if u.startswith("/pdufa/") else ""
    if p and os.path.exists(p):
        m = re.search(r'<div class="kv"><span>Drug / candidate</span><b>([^<]{1,160})</b>',
                      io.open(p, encoding="utf-8", errors="replace").read())
        if m:
            return html.unescape(m.group(1)).strip()
    return re.sub(r"\s+-\s+\(.*$", "", str(r.get("name") or r.get("t") or "")).strip()


def past_due(today=None, rows=None):
    """[{t, url, slug, drug, goal, dp, goal_words, miss_date, miss_text, source, source_label}], oldest goal first."""
    today = today or eastern_today()
    rows = rows if rows is not None else _rows()
    led = _ledger()
    out = []
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st") or "").lower() not in OPEN:
            continue
        if str((r.get("_d") or {}).get("goal_date") or "").lower() == "not announced":
            continue
        try:
            d = dt.date.fromisoformat(str(r.get("d") or "")[:10])
        except ValueError:
            continue
        if period_end(d, r.get("dp")) >= today:
            continue
        u = str(r.get("url") or "")
        slug = u.split("/")[2] if u.startswith("/pdufa/") and u.count("/") >= 2 else ""
        e = led.get(slug, {})
        out.append({"t": str(r.get("t") or "").upper(), "url": u, "slug": slug, "drug": drug_of(r),
                    "goal": d.isoformat(), "dp": str(r.get("dp") or "day"), "goal_words": goal_words(d, r.get("dp")),
                    "miss_date": e.get("announced_miss_date") or "", "miss_text": e.get("announced_miss_text") or "",
                    "source": e.get("source") or "", "source_label": e.get("source_label") or ""})
    out.sort(key=lambda x: (x["goal"], x["t"]))
    return out


def keys(today=None):
    """(ticker, goal day) of every past-due row, for build_home_board.py to keep them out of Next FDA decisions."""
    return {(x["t"], x["goal"]) for x in past_due(today)}


STYLE = ('<style id="pastdue-css">.pdue{border-color:rgba(227,186,94,.45)}.pdue .pdl{display:flex;flex-direction:column;'
         'gap:7px;margin-top:12px}.pdue .pdr{display:block;padding:8px 10px;border-radius:10px;border:1px solid '
         'var(--line);transition:.15s;color:inherit;text-decoration:none}.pdue .pdr:hover{background:var(--cardh)}'
         '.pdue .pdh{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.pdue .pdh .dt{font-weight:800;'
         'font-size:14px}.pdue .pdh .dnm{font-size:12px;color:var(--mut);min-width:0}.pdue .pdg{display:block;'
         'font-size:11.5px;color:#e3ba5e;margin-top:3px}.pdue .pds{display:block;font-size:11.5px;line-height:1.45;'
         'color:var(--mut2);margin-top:2px}.pdue .pdn{margin:10px 0 0;font-size:11.5px;line-height:1.45;'
         'color:var(--mut2,#94a9c9)}</style>')


def render(items, today):
    day = f"{MONTH[today.month]} {today.day}, {today.year}"
    if not items:
        body = (f'<p class="pdn" style="margin-top:12px">No PDUFA goal date on the calendar has passed without a '
                f'decision on record, as of {day} (Eastern).</p>')
    else:
        rows = []
        for x in items:
            if x["miss_date"] and x["miss_text"]:
                status = (f"On {short_day(x['miss_date'])}, the sponsor said the FDA would not act by the goal date"
                          + ("; the review is ongoing" if "ongoing" in x["miss_text"].lower() else "")
                          + f". No decision on record as of {short_day(today.isoformat())}.")
            else:
                status = f"No FDA decision or sponsor announcement on record as of {short_day(today.isoformat())}."
            rows.append(
                f'<a class="pdr" href="{html.escape(x["url"])}"><span class="pdh"><span class="dt">{html.escape(x["t"])}'
                f'</span><span class="dnm">{html.escape(x["drug"])}</span></span>'
                f'<span class="pdg">PDUFA goal {html.escape(x["goal_words"])} passed</span>'
                f'<span class="pds">{html.escape(status)}</span></a>')
        body = (f'<div class="pdl">{"".join(rows)}</div><p class="pdn">Goal dates that have passed with no FDA '
                f'decision on record, as of {day} (Eastern). A row leaves this box when its decision is published; '
                f'each links the event page and its sources.</p>')
    return (f'{B}{STYLE}<div class="panel pdue"><div class="sec"><h2>Past their goal date</h2>'
            f'<a href="/calendar">Calendar →</a></div>{body}</div>{E}')


def place(doc, block):
    if B in doc and E in doc:
        return doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
    i = doc.find("<aside>")
    if i < 0:
        raise SystemExit("home: no <aside> to hold the past-due box")
    return doc[:i + len("<aside>")] + block + doc[i + len("<aside>"):]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = eastern_today()
    items = past_due(today)
    doc = io.open(HOME, encoding="utf-8").read()
    new = place(doc, render(items, today))
    for x in items:
        print(f"  past due: {x['t']:<6} goal {x['goal_words']:<14} {x['drug'][:40]}"
              + ("  [sponsor said FDA would miss]" if x["miss_date"] else ""))
    print(f"home past-due box: {len(items)} row(s) as of {today} (Eastern); " + ("changed" if new != doc else "unchanged")
          + (" [dry run]" if a.dry_run else ""))
    if new != doc and not a.dry_run:
        io.open(HOME, "w", encoding="utf-8").write(new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
