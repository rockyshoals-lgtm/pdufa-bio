# -*- coding: utf-8 -*-
"""CI guard: a conference page's "Key dates" are the organiser's own, as read, and nothing else.

WHY (2026-11-28): "asco 2027" sat at Bing position 7.5 with 0 clicks while Copilot cited asco.org for the
same question. People searching a meeting months ahead want its calendar: when abstracts are due, when the
titles post, when the embargo lifts. conferences.json now carries that calendar (key_dates) for the editions
where the organiser's "Dates to Know" page was read, and build_conference_pages.py / build_conference_faq.py
render it. A wrong date here is worse than none, so this holds:

  1. every key_dates list names its source on the organiser's own host and the day it was read;
  2. every entry with an exact date (iso) says that same day in its own words; an entry the organiser gave
     only as part of a month ("Late May 2027") carries no iso and no day number;
  3. no key date falls after the meeting ends, and the "meeting" entry is the meeting's own start;
  4. the live page shows every entry, and its FAQ answers the release question where there is one;
  5. a conference without key_dates shows no Key dates section.

Plants (each must FAIL): PLANT=iso (one exact date moved a day), PLANT=render (the section dropped from a page).

    python tests/test_conference_key_dates.py
"""
import datetime as dt
import html
import io
import json
import os
import re
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
MONF = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
        "November", "December"]
KINDS = {"submission_open", "submission_deadline", "lba_deadline", "notify", "titles", "embargo", "release",
         "meeting"}


def slug(code):
    return code.replace(" ", "-")


def host(u):
    h = urlparse(u).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def test_conference_key_dates():
    plant = os.environ.get("PLANT", "")
    confs = json.load(io.open(os.path.join(HERE, "conferences.json"), encoding="utf-8"))["conferences"]
    with_kd = [c for c in confs if c.get("key_dates")]
    assert with_kd, "no conference carries key_dates; the guard has nothing to hold"
    if plant == "iso":
        k = next(k for k in with_kd[0]["key_dates"] if k.get("iso") and k["kind"] != "meeting")
        k["iso"] = (dt.date.fromisoformat(k["iso"]) + dt.timedelta(days=1)).isoformat()
    bad = []
    for c in with_kd:
        tag = f'{c["code"]} {c["start"][:4]}'
        src = c.get("key_dates_source") or ""
        if not src or host(src) != host(c.get("source") or ""):
            bad.append(f"{tag}: key_dates_source {src!r} is not on the organiser's host ({c.get('source')})")
        try:
            dt.date.fromisoformat(c.get("key_dates_read") or "")
        except ValueError:
            bad.append(f"{tag}: key_dates_read {c.get('key_dates_read')!r} is not a date")
        for k in c["key_dates"]:
            when, what, iso, kind = k.get("when") or "", k.get("what") or "", k.get("iso"), k.get("kind")
            if not when or not what or kind not in KINDS:
                bad.append(f"{tag}: incomplete entry {k}")
                continue
            if iso:
                d = dt.date.fromisoformat(iso)
                said = re.match(rf"^{MONF[d.month - 1]} {d.day}\b(?:-\d+)?, {d.year}\b", when)
                if not said:
                    bad.append(f"{tag}: {what!r} says {when!r} but carries {iso}")
                if iso > c["end"]:
                    bad.append(f"{tag}: {what!r} ({iso}) falls after the meeting ends ({c['end']})")
                if kind == "meeting" and iso != c["start"]:
                    bad.append(f"{tag}: the meeting entry ({iso}) is not the meeting's start ({c['start']})")
            elif re.search(r"\b\d{1,2},? 20\d\d\b", when):
                bad.append(f"{tag}: {when!r} names a day but carries no iso")

        page = os.path.join(SITE, "conference", slug(c["code"]), "index.html")
        if not os.path.exists(page):
            continue                                     # a past edition with no page of its own
        doc = html.unescape(io.open(page, encoding="utf-8", errors="replace").read())
        if plant == "render" and c is with_kd[0]:
            doc = doc.replace(f"Key dates for {tag}", "")
        if f"Key dates for {tag}" not in doc:
            bad.append(f"/conference/{slug(c['code'])}: no Key dates section")
        else:
            for k in c["key_dates"]:
                if k["when"] not in doc:
                    bad.append(f"/conference/{slug(c['code'])}: key date {k['when']!r} not shown")
        if any(k["kind"] == "release" for k in c["key_dates"]) and f"When are {tag} abstracts released?" not in doc:
            bad.append(f"/conference/{slug(c['code'])}: FAQ does not answer when abstracts are released")

    for c in confs:
        if c.get("key_dates"):
            continue
        page = os.path.join(SITE, "conference", slug(c["code"]), "index.html")
        if os.path.exists(page) and "Key dates for " in io.open(page, encoding="utf-8", errors="replace").read():
            if not any(x.get("key_dates") and x["code"] == c["code"] for x in confs):
                bad.append(f"/conference/{slug(c['code'])}: shows Key dates with none in conferences.json")
    assert not bad, "conference key dates:\n  " + "\n  ".join(bad)


if __name__ == "__main__":
    test_conference_key_dates()
    print("OK")
