# -*- coding: utf-8 -*-
"""test_calendar_feed.py -- the public .ics must parse, and must never invent a date.

/calendar.ics is the one artefact that leaves our site and lives inside someone's calendar app,
next to their real appointments. Two things can go wrong there and neither is visible from our pages:

  1. A malformed feed. Calendar clients do not report errors usefully; they drop events or refuse
     the subscription silently. Unfolded long lines (RFC 5545 caps content lines at 75 octets) are
     the classic cause.
  2. A fabricated date. 328 of our 418 events are guided only to a month or quarter. Rendering one
     of those as a single day would put a guess in a calendar app where it is indistinguishable
     from a confirmed FDA action date. That is the most consequential way this site could mislead
     someone, because it survives outside our pages and outside our disclaimers.

So: every month-precision event must span its month, every quarter event its quarter, and only
day-precision events may occupy a single day.

    python tests/test_calendar_feed.py
"""
import datetime as dt, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
ICS = os.path.join(SITE, "calendar.ics")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")


def parse_events(raw):
    """Minimal VEVENT reader with RFC 5545 unfolding. Deliberately dependency-free."""
    text = raw.replace("\r\n ", "").replace("\r\n\t", "")
    out, cur = [], None
    for line in text.split("\r\n"):
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            if cur is not None:
                out.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            k, v = line.split(":", 1)
            cur[k.split(";")[0].upper()] = v
    return out


def main():
    if not os.path.exists(ICS):
        print("FAIL: pdufa_site_src/calendar.ics does not exist")
        sys.exit(1)

    raw = open(ICS, encoding="utf-8", newline="").read()
    ok = True

    # 1. structure
    if not raw.startswith("BEGIN:VCALENDAR") or "END:VCALENDAR" not in raw:
        ok = False
        print("FAIL: not a well-formed VCALENDAR")

    long_lines = [ln for ln in raw.split("\r\n") if len(ln.encode("utf-8")) > 75]
    if long_lines:
        ok = False
        print(f"FAIL: {len(long_lines)} content line(s) exceed the RFC 5545 75-octet limit.")
        print("   Clients silently drop or mangle events when lines are not folded.")
        print(f"   e.g. {long_lines[0][:90]}...")
    else:
        print("  PASS: all content lines within the 75-octet fold limit")

    events = parse_events(raw)
    print(f"parsed {len(events):,} VEVENT(s)")
    if not events:
        print("FAIL: feed contains no events")
        sys.exit(1)

    for req in ("UID", "DTSTART", "SUMMARY"):
        missing = [e for e in events if not e.get(req)]
        if missing:
            ok = False
            print(f"FAIL: {len(missing)} event(s) missing {req}")

    uids = [e.get("UID") for e in events]
    if len(set(uids)) != len(uids):
        ok = False
        print(f"FAIL: duplicate UIDs ({len(uids) - len(set(uids))}). Clients will collapse events.")
    else:
        print("  PASS: every UID unique")

    # 2. the one that matters: precision must survive into the feed
    rows = []
    if os.path.exists(DATASET):
        m = re.search(r"export default (\[.*\])",
                      open(DATASET, encoding="utf-8", errors="replace").read(), re.S)
        if m:
            rows = json.loads(m.group(1))
    prec = {}
    for r in rows:
        if r.get("id"):
            prec[str(r["id"])] = r.get("dp")

    def d(s):
        return dt.date(int(s[0:4]), int(s[4:6]), int(s[6:8]))

    bad, checked = [], 0
    for e in events:
        uid = (e.get("UID") or "").split("@")[0]
        dp = prec.get(uid)
        if not dp or not e.get("DTEND"):
            continue
        try:
            span = (d(e["DTEND"]) - d(e["DTSTART"])).days
        except Exception:
            continue
        checked += 1
        if dp == "day" and span != 1:
            bad.append((uid, dp, span))
        elif dp == "month" and not (28 <= span <= 31):
            bad.append((uid, dp, span))
        elif dp == "quarter" and not (89 <= span <= 92):
            bad.append((uid, dp, span))

    if bad:
        ok = False
        print(f"\nFAIL: {len(bad)} event(s) whose calendar span contradicts their stated precision:")
        for uid, dp, span in bad[:10]:
            print(f"   {uid}  precision={dp}  span={span}d")
        print("   A month-precision event rendered as one day is a fabricated date sitting in "
              "someone's calendar next to real appointments.")
    else:
        print(f"  PASS: all {checked:,} matched events span exactly their stated precision")

    # 3. the feed should send readers to us, not to our sources
    urls = re.findall(r"^URL:(\S+)", raw.replace("\r\n ", ""), re.M)
    offsite = [u for u in urls if "pdufa.bio" not in u]
    if offsite:
        ok = False
        print(f"\nFAIL: {len(offsite)} event URL(s) point off-site, e.g. {offsite[0][:60]}")
        print("   Primary sources belong in DESCRIPTION; the click should land on our page.")
    else:
        print(f"  PASS: all {len(urls):,} event links point to pdufa.bio")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
