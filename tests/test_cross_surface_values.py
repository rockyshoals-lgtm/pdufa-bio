# -*- coding: utf-8 -*-
"""CI guard: a value that appears on more than one surface must be the SAME on all of them.

Audit 2026-09-14, ORDER item 5, and the auditor's own framing: "Items 1 to 4 are four instances
of one thing ... this is the third week running that a correct dataset change has failed to
reach a rendered page." The four were:

  A  the 2026 decision-timing statistic: /calendar and /learn said 30/18/9/3 while
     /research/fda-decision-timing -- the study BOTH of them link to as the citation -- still
     said 27/15/9/3. Following our own source link made us look wrong.
  B  twelve event pages kept "Dec 31 2026" in their <title> after the calendar had dropped it.
  C  /fda-decision/BAYRY-2026-09-09 published "82 Days Early" against a goal date the same page
     said was never sourced.
  D  build-info.json named a past-dated event as next, with next_days: -3.

EVERY ASSERTION HERE IS ON RENDERED OUTPUT, not on source data, because that is where all four
defects lived. The dataset was right in all four cases.

Four invariants:
  1. TIMING STATISTIC -- the n / early / on-day / late quadruple must be identical everywhere it
     is stated.
  2. GOAL-DATE WINDOW -- no /pdufa page may state a day for a row whose dataset precision is not
     "day"; the label it renders must equal site_windows.window_label for that row.
  3. EARLINESS -- no page may render "N days early" for a row where site_windows.earliness_allowed
     is False.
  4. NEXT POINTER -- build-info.json must never publish a negative next_days.

    python tests/test_cross_surface_values.py
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from site_windows import earliness_allowed, window_label  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
STOP = {"pdufa", "date", "and", "the"}


def text(p):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ",
                                      io.open(p, encoding="utf-8", errors="replace").read()))


def raw(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def toks(s):
    return {w for w in re.findall(r"[a-z][a-z0-9]{2,}", str(s or "").lower())
            if w not in STOP}


def load_rows():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
                  encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    return rows


def main():
    rows = load_rows()
    fail = 0

    # ---- 1. the timing statistic, as RENDERED text on every surface that states it ----
    pat = re.compile(r"(\d+)\s+(?:sourced\s+)?(?:2026\s+)?(?:FDA\s+)?decisions?[^.]{0,120}?"
                     r"(\d+)\s+came\s+before[^.]{0,40}?(\d+)\s+landed on it,?\s*and\s+(\d+)\s+"
                     r"came after", re.I)
    seen = {}
    for rel in ("research/fda-decision-timing", "calendar", "learn/what-is-a-pdufa-date"):
        p = os.path.join(SITE, rel, "index.html")
        if not os.path.exists(p):
            continue
        m = pat.search(text(p))
        if m:
            seen["/" + rel] = tuple(int(x) for x in m.groups())
    if len(set(seen.values())) > 1:
        print("  FAIL the 2026 decision-timing statistic differs between surfaces:")
        for k, v in sorted(seen.items()):
            print(f"        {k:<34} n={v[0]} early={v[1]} on={v[2]} late={v[3]}")
        print("        These pages cite each other. A reader who follows our own link to check "
              "a number must find the same number. Re-run build_early_decisions.py, then "
              "inject_calendar_explainer.py and sync_learn_timing.py.")
        fail += 1

    # ---- 2. no event page may state a day the dataset does not hold ----
    nonday = {}
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st") or "").lower() == "decided":
            continue
        if str(r.get("dp") or "day") == "day":
            continue
        nonday.setdefault(str(r.get("t") or "").upper(), []).append(r)

    for p in sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        tk = slug.split("-")[0].upper()
        cands = nonday.get(tk)
        if not cands:
            continue
        doc = raw(p)
        m = re.search(r"<span>FDA PDUFA target date</span><b>([^<]+)</b>", doc)
        if not m:
            continue
        shown = m.group(1).strip()
        part = slug[len(tk):].lstrip("-")
        st = toks(part.replace("-", " "))
        hits = [c for c in cands if (not st) or (st & toks(c.get("name")))]
        if len(hits) != 1:
            continue
        want = window_label(hits[0])
        if re.match(r"^\d{4}-\d{2}-\d{2}$", shown):
            print(f"  FAIL /pdufa/{slug}: states the day {shown}, but the dataset holds this row "
                  f"at {hits[0].get('dp')} precision ({want}). The calendar was corrected and "
                  f"this page was not. Run fix_event_page_windows.py.")
            fail += 1
        elif shown != want:
            print(f"  FAIL /pdufa/{slug}: renders {shown!r}; site_windows.window_label says "
                  f"{want!r}. One owner formats a window.")
            fail += 1

    # ---- 3. no earliness figure without a sourced day-precision goal ----
    allowed = {}
    for r in rows:
        if r.get("type") == "PDUFA" and str(r.get("st") or "").lower() == "decided":
            allowed[(str(r.get("t") or "").upper(), str(r.get("dcd") or "")[:10])] = \
                earliness_allowed(r)
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"^([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        key = (m.group(1), m.group(2))
        if allowed.get(key, True):
            continue
        doc = text(p)
        hit = re.search(r"\b\d+\s+[Dd]ays?\s+[Ee]arly\b|\b\d+\s+days before its\b", doc)
        if hit:
            print(f"  FAIL /fda-decision/{slug}: renders {hit.group(0)!r}, but this row's goal "
                  f"date is not a sourced day. An unsourced goal rounded to a late date "
                  f"manufactures the largest possible earliness. Run rewrite_decision_snippets.py.")
            fail += 1
    for p in sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        tk = slug.split("-")[0].upper()
        doc = text(p)
        hit = re.search(r"(\d+) days before its ([A-Z][a-z]+ \d{1,2}, \d{4}) goal date", doc)
        if not hit:
            continue
        bad = [k for k, v in allowed.items() if k[0] == tk and not v]
        if bad:
            print(f"  FAIL /pdufa/{slug}: renders '{hit.group(0)}' for a ticker whose decided "
                  f"row has no sourced day-precision goal. Run mark_event_pages_decided.py.")
            fail += 1

    # ---- 4. the next pointer is never a negative countdown ----
    bi = os.path.join(SITE, "build-info.json")
    if os.path.exists(bi):
        j = json.loads(io.open(bi, encoding="utf-8").read())
        nd = j.get("next_days")
        if isinstance(nd, int) and nd < 0:
            print(f"  FAIL build-info.json publishes next_days={nd}. A decision cannot be a "
                  f"negative number of days away. A past-dated undecided event is 'awaiting': "
                  f"keep it as next, set next_status and clamp next_days to 0.")
            fail += 1

    if fail:
        print(f"\n{fail} cross-surface disagreement(s). The dataset being right is not the same "
              f"as the site being right. DO NOT PUBLISH.")
        return 1
    print(f"OK -- timing statistic agrees on {len(seen)} surface(s) {sorted(set(seen.values()))}; "
          f"no event page states a day the dataset withdrew; no unsourced earliness rendered; "
          f"next_days not negative.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
