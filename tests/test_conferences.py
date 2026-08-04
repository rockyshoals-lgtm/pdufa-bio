# -*- coding: utf-8 -*-
"""test_conferences.py -- the conference calendar must stay ahead of today, and stay sourced.

Two failure modes, both silent, both previously live:

  1. THE CALENDAR RUNS OUT. It listed 14 meetings ending 15 December 2026 and nothing beyond. A
     forward calendar does not announce its own expiry; it just quietly becomes a page about the
     past. This fails when fewer than MIN_FUTURE meetings remain ahead of today, or when the
     furthest one is less than MIN_HORIZON_DAYS away, so the gap is caught months before a reader
     notices.

  2. AN UNSOURCED DATE. Every row must carry the organiser URL it was verified against. A
     conference date lifted from an aggregator is exactly the kind of claim this site exists not to
     publish, and a wrong date propagates into the ICS feed and into people's calendars.

Also checks that presenter rows carry a filing or release URL, since a named company presenting is
a factual claim about that company.

    python tests/test_conferences.py
"""
import csv, datetime as dt, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "conferences.json")
MINED = os.path.join(HERE, "catalysts_out", "conference_presenters_mined.csv")
PAGE = os.path.join(HERE, "pdufa_site_src", "conferences", "index.html")

MIN_FUTURE = 12          # below this the calendar is thinning out
MIN_HORIZON_DAYS = 150   # the furthest meeting should be at least this far out


def main():
    if not os.path.exists(DATA):
        print("FAIL: conferences.json missing")
        sys.exit(1)

    data = json.load(open(DATA, encoding="utf-8"))
    confs = data.get("conferences") or []
    today = dt.date.today()
    ok = True

    future = [c for c in confs if c["end"] >= today.isoformat()]
    horizon = max((dt.date.fromisoformat(c["start"]) for c in future), default=today)
    days_out = (horizon - today).days

    print(f"{len(confs)} conferences on file, {len(future)} still ahead, "
          f"furthest starts in {days_out} days ({horizon})")

    if len(future) < MIN_FUTURE:
        ok = False
        print(f"\nFAIL: only {len(future)} conferences remain ahead of today (want {MIN_FUTURE}+).")
        print("   Add the next season's meetings to conferences.json, with organiser URLs.")
    else:
        print(f"  PASS: {len(future)} upcoming meetings")

    if days_out < MIN_HORIZON_DAYS:
        ok = False
        print(f"\nFAIL: the calendar only reaches {days_out} days out (want {MIN_HORIZON_DAYS}+).")
        print("   A forward calendar that runs out does not warn you, it just becomes a history "
              "page. Extend it now rather than after a reader notices.")
    else:
        print(f"  PASS: horizon {days_out} days")

    # every row sourced, dated sanely, and internally consistent
    bad = []
    for c in confs:
        for f in ("code", "name", "start", "end", "city", "focus", "source"):
            if not c.get(f):
                bad.append((c.get("code", "?"), f"missing {f}"))
        if not str(c.get("source", "")).startswith("http"):
            bad.append((c.get("code", "?"), "source is not a URL"))
        try:
            if dt.date.fromisoformat(c["end"]) < dt.date.fromisoformat(c["start"]):
                bad.append((c["code"], "ends before it starts"))
        except Exception:
            bad.append((c.get("code", "?"), "unparseable date"))

    if bad:
        ok = False
        print(f"\nFAIL: {len(bad)} conference row problem(s):")
        for code, why in bad[:12]:
            print(f"   {code}: {why}")
    else:
        print(f"  PASS: all {len(confs)} rows sourced to an organiser URL with sane dates")

    # presenters must be traceable
    if os.path.exists(MINED):
        rows = list(csv.DictReader(open(MINED, encoding="utf-8-sig", errors="replace")))
        unsourced = [r for r in rows if not str(r.get("filing_url", "")).startswith("http")]
        noname = [r for r in rows if not (r.get("ticker") or r.get("company"))]
        if unsourced or noname:
            ok = False
            print(f"\nFAIL: {len(unsourced)} mined presenter row(s) with no filing URL, "
                  f"{len(noname)} with no company.")
            print("   Naming a company as presenting is a factual claim and needs its filing.")
        else:
            print(f"  PASS: all {len(rows):,} mined presenter rows carry a filing URL")

    # the page must not re-introduce the promise it cannot keep
    if os.path.exists(PAGE):
        html = open(PAGE, encoding="utf-8", errors="replace").read()
        if re.search(r"\b0 presenters\b", html):
            ok = False
            print("\nFAIL: the page prints '0 presenters', which reads as 'no biotech is "
                  "presenting' when the truth is that the programme is not published yet.")
        else:
            print("  PASS: no bare '0 presenters' on the page")

    print("\n  PASS: conference calendar is current and sourced" if ok else "\n  see failures above")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
