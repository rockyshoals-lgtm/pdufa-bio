# -*- coding: utf-8 -*-
"""CI guard: every open date we publish is stated, at its precision, in the source words we quote.

WHY (red team 2026-11-17, David: "build our moat here too as the most accurate")
pdufa.bio prints a date and, next to it, the sponsor's own sentence. The two can drift apart without
anything looking wrong: a goal date moves and the quote is not replaced, a readout is re-keyed to a
conference and the quote is an abstract title, a quarter row is keyed to the wrong quarter. On
2026-11-17 (Eastern), 17 of 291 open rows failed this check (CAPR with no quote at all; four ASH/ESMO rows
whose quote was a poster title with no date; NVO rows with no goal date). A reader can verify a
date only when the quoted words state it, so this is the invariant:

  1. Every open PDUFA row (Upcoming / Under review) and every company-Guided readout whose window has
     not ended carries an http(s) source_url and a quote (`_d.source_quote` for PDUFA rows,
     `_d.guidance_text` for readouts).
  2. The quote (plus `_d.date_quote`, the verbatim date words when the quoted sentence is a title)
     states the row's date at the row's precision (date_quote_match.quote_states_date:
     day -> month+day, month -> month, quarter -> Qn+year, half -> Hn+year, year -> year;
     "this year"/"next year" read against the source's own date). A readout keyed to a conference
     window also passes when the quote names that conference and the conference falls in the window.
  3. A guided readout's `d` is the end of its `guided_window` (a quarter row ends on the quarter's
     last day), so the date we sort and count by is the one the company stated.
  4. A PDUFA row whose goal date the sponsor has not announced says so (`_d.goal_date: "not
     announced"`) and is exempt, because there is no date to state.

Exceptions live in _date_quote_ack.json, each with a reason and an `until` date no more than 30 days
out. An expired exception fails the build, so nothing is excused for good.

    python tests/test_quote_states_date.py
"""
import calendar
import datetime as dt
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from date_quote_match import norm, quote_states_date, states_month  # noqa: E402

DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
ACK = os.path.join(HERE, "_date_quote_ack.json")
MAX_ACK_DAYS = 30


def eastern_today():
    try:
        from site_dates import eastern_today as et
        return et()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=5)).date()


def load_rows(path=DATASET):
    src = io.open(path, encoding="utf-8").read()
    return json.loads(src[src.index("["):src.rindex("]") + 1])


def window_bounds(gw):
    """guided_window -> (start, end) dates, or None if the format is unknown."""
    gw = (gw or "").strip()
    m = re.fullmatch(r"(\d{4})", gw)
    if m:
        y = int(m.group(1))
        return dt.date(y, 1, 1), dt.date(y, 12, 31)
    m = re.fullmatch(r"(\d{4})-H([12])", gw)
    if m:
        y, h = int(m.group(1)), int(m.group(2))
        return (dt.date(y, 1, 1), dt.date(y, 6, 30)) if h == 1 else (dt.date(y, 7, 1), dt.date(y, 12, 31))
    m = re.fullmatch(r"(\d{4})-Q([1-4])", gw)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        em = q * 3
        return dt.date(y, em - 2, 1), dt.date(y, em, calendar.monthrange(y, em)[1])
    m = re.fullmatch(r"(\d{4})-(\d{2})", gw)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return dt.date(y, mo, 1), dt.date(y, mo, calendar.monthrange(y, mo)[1])
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})", gw)
    if m:
        d = dt.date.fromisoformat(m.group(1))
        return d, d
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})", gw)
    if m:
        return dt.date.fromisoformat(m.group(1)), dt.date.fromisoformat(m.group(2))
    return None


def conferences(rows):
    out = []
    for r in rows:
        if r.get("type") != "Conference":
            continue
        names = {norm(r.get("t") or ""), norm(r.get("name") or "")}
        names = {n for n in names if len(n) >= 3}
        try:
            out.append((names, dt.date.fromisoformat(r["d"])))
        except Exception:
            pass
    return out


def names_conference_in_window(quote, start, end, confs):
    q = norm(quote)
    for names, d in confs:
        if not (start - dt.timedelta(days=3) <= d <= end):
            continue
        for n in names:
            if re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", q):
                years = set(re.findall(r"\b(20\d\d)\b", q))
                if not years or str(d.year) in years:
                    return True
    return False


def source_date(d):
    for k in ("guided_filed", "source_date"):
        v = d.get(k)
        if v and re.match(r"\d{4}-\d{2}-\d{2}", str(v)):
            return str(v)[:10]
    m = re.search(r"(20\d\d-\d\d-\d\d)", str(d.get("source") or ""))
    return m.group(1) if m else None


def check(rows, today, acks):
    fails = []
    confs = conferences(rows)
    for r in rows:
        d = r.get("_d") or {}
        typ, st = r.get("type"), r.get("st")
        if typ == "PDUFA" and st in ("Upcoming", "Under review"):
            if str(d.get("goal_date") or "").lower() == "not announced":
                continue
            quote, prec = d.get("source_quote"), r.get("dp")
        elif typ == "Readout" and st == "Guided":
            if r.get("d", "") < today.isoformat():
                continue  # past windows: test_guided_readouts_current owns them
            # date_quote: the sponsor's verbatim words that carry the date when the descriptive
            # guidance_text does not (a poster title next to a session time in the same release).
            quote = " ... ".join(x for x in (d.get("guidance_text"), d.get("date_quote")) if x)
            prec = d.get("guided_precision") or r.get("dp")
        else:
            continue
        rid = r.get("id")
        why = []
        if not re.match(r"https?://", str(d.get("source_url") or "")):
            why.append("no http(s) source_url")
        if not (quote or "").strip():
            why.append("no quoted source words")
        elif typ == "Readout" and prec == "window":
            wb = window_bounds(d.get("guided_window"))
            if not wb:
                why.append(f"unreadable guided_window {d.get('guided_window')!r}")
            elif not (states_month(norm(quote), wb[1]) or names_conference_in_window(quote, wb[0], wb[1], confs)
                      or quote_states_date(quote, wb[0].isoformat(), "day")
                      or (wb[0].year < wb[1].year and all(re.search(rf"\b{y}\b", quote)
                                                          for y in range(wb[0].year, wb[1].year + 1)))):
                why.append(f"quote names neither the dates nor a conference inside {d.get('guided_window')}")
        elif not quote_states_date(quote, r["d"], prec, source_date(d)):
            why.append(f"quote does not state {r['d']} at {prec} precision")
        if typ == "Readout":
            wb = window_bounds(d.get("guided_window"))
            if wb and wb[1].isoformat() != r.get("d"):
                why.append(f"d {r.get('d')} is not the end of guided_window {d.get('guided_window')} ({wb[1]})")
        if not why:
            continue
        a = acks.get(rid)
        if a:
            try:
                until = dt.date.fromisoformat(a.get("until", ""))
            except Exception:
                until = None
            if until and today <= until <= today + dt.timedelta(days=MAX_ACK_DAYS) and (a.get("why") or "").strip():
                continue
            why.append(f"exception in _date_quote_ack.json is expired or malformed (until={a.get('until')!r})")
        fails.append(f"{rid} [{r.get('t')}] {r.get('d')}: " + "; ".join(why))
    return fails


def load_acks():
    if not os.path.exists(ACK):
        return {}
    j = json.load(io.open(ACK, encoding="utf-8"))
    return {a["id"]: a for a in j.get("acks", [])}


def self_test():
    """Planted rows: each must fail, and each fixed twin must pass."""
    t = dt.date(2026, 11, 18)
    base = [{"id": "c", "type": "Conference", "t": "ASH", "name": "American Society of Hematology Annual Meeting",
             "d": "2026-12-12"}]
    bad = [
        {"id": "p1", "t": "X", "type": "PDUFA", "st": "Upcoming", "d": "2026-12-30", "dp": "day",
         "_d": {"source_url": "https://sec.gov/x", "source_quote": "PDUFA target action date of December 3, 2026"}},
        {"id": "p2", "t": "X", "type": "PDUFA", "st": "Upcoming", "d": "2026-12-30", "dp": "day",
         "_d": {"source_url": "https://sec.gov/x", "source_quote": ""}},
        {"id": "r1", "t": "Y", "type": "Readout", "st": "Guided", "d": "2027-03-31", "dp": "quarter",
         "_d": {"source_url": "https://x", "guidance_text": "topline data in the fourth quarter of 2026",
                "guided_precision": "quarter", "guided_window": "2027-Q1"}},
        {"id": "r2", "t": "Y", "type": "Readout", "st": "Guided", "d": "2026-12-14", "dp": "day",
         "_d": {"source_url": "https://x", "guidance_text": "final OS results will be presented",
                "guided_precision": "day", "guided_window": "2026-12-14"}},
        {"id": "r3", "t": "Y", "type": "Readout", "st": "Guided", "d": "2027-12-31", "dp": "year",
         "_d": {"source_url": "https://x", "guidance_text": "data expected in the first half of 2027",
                "guided_precision": "half", "guided_window": "2027-H1"}},
        {"id": "r4", "t": "Y", "type": "Readout", "st": "Guided", "d": "2027-12-31", "dp": "quarter",
         "_d": {"source_url": "https://x", "guidance_text": "Two readouts anticipated in 2027: A in the first half "
                "and B in the third quarter.", "guided_precision": "quarter", "guided_window": "2027-Q4"}},
        {"id": "r5", "t": "Y", "type": "Readout", "st": "Guided", "d": "2027-06-30", "dp": "half",
         "_d": {"source_url": "https://x", "guidance_text": "efficacy data expected to follow in H2 2027.",
                "guided_precision": "half", "guided_window": "2027-H1"}},
    ]
    good = [
        {"id": "g1", "t": "X", "type": "PDUFA", "st": "Upcoming", "d": "2026-12-30", "dp": "day",
         "_d": {"source_url": "https://sec.gov/x", "source_quote": "a PDUFA target action date of December 30, 2026"}},
        {"id": "g2", "t": "Y", "type": "Readout", "st": "Guided", "d": "2027-12-31", "dp": "year",
         "_d": {"source_url": "https://x", "guidance_text": "results expected by the end of next year",
                "guided_precision": "year", "guided_window": "2027", "guided_filed": "2026-11-05"}},
        {"id": "g3", "t": "Y", "type": "Readout", "st": "Guided", "d": "2026-12-15", "dp": "month",
         "_d": {"source_url": "https://x", "guidance_text": "new clinical data at ASH 2026",
                "guided_precision": "window", "guided_window": "2026-12-12..2026-12-15"}},
        {"id": "g4", "t": "Y", "type": "Readout", "st": "Guided", "d": "2027-06-30", "dp": "year",
         "_d": {"source_url": "https://x", "guidance_text": "Data Expected in 1H27",
                "guided_precision": "half", "guided_window": "2027-H1"}},
        {"id": "g5", "t": "N", "type": "PDUFA", "st": "Under review", "d": "2026-12-31", "dp": "month",
         "_d": {"source_url": "https://sec.gov/x", "source_quote": "launch in early 2027", "goal_date": "not announced"}},
        {"id": "g6", "t": "Y", "type": "Readout", "st": "Guided", "d": "2027-12-31", "dp": "quarter",
         "_d": {"source_url": "https://x", "guidance_text": "Two Phase 2 readouts anticipated in 2027: A in the second "
                "half and, for the first time, guidance for B in the fourth quarter.",
                "guided_precision": "quarter", "guided_window": "2027-Q4"}},
        {"id": "g7", "t": "Y", "type": "Readout", "st": "Guided", "d": "2027-06-30", "dp": "half",
         "_d": {"source_url": "https://x", "guidance_text": "efficacy data expected to follow in H1 and H2 2027.",
                "guided_precision": "half", "guided_window": "2027-H1"}},
        {"id": "g8", "t": "Y", "type": "Readout", "st": "Guided", "d": "2027-12-31", "dp": "half",
         "_d": {"source_url": "https://x", "guidance_text": "initial data in the 2nd half of 2027.",
                "guided_precision": "half", "guided_window": "2027-H2"}},
    ]
    f_bad = check(base + bad, t, {})
    f_good = check(base + good, t, {})
    ok = len(f_bad) == len(bad) and not f_good
    expired = check(base + bad[:1], t, {"p1": {"id": "p1", "why": "x", "until": "2026-11-01"}})
    long_ack = check(base + bad[:1], t, {"p1": {"id": "p1", "why": "x", "until": "2027-06-01"}})
    ok = ok and len(expired) == 1 and len(long_ack) == 1
    if not ok:
        print("SELF-TEST FAILED: the rule no longer catches planted defects")
        print("  bad ->", f_bad)
        print("  good ->", f_good)
    return ok


def main():
    if not self_test():
        return 1
    rows = load_rows()
    fails = check(rows, eastern_today(), load_acks())
    if fails:
        print(f"FAIL: {len(fails)} open date(s) not stated by the source words we quote "
              f"(fix the row or quote, or add a dated exception to _date_quote_ack.json):")
        for f in fails[:60]:
            print("   " + f)
        return 1
    print("OK -- every open PDUFA and guided readout date is stated, at its precision, in the quoted source words.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
