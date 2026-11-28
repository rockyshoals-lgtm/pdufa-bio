# -*- coding: utf-8 -*-
"""backfill_conference_runup.py -- conference run-up rows for presentations BEFORE 2026-06-05 that the published
study leaves out, re-dated by the same rule as the additions (cache only).

LEADS: conf_study/conference_backfill_leads_2026-11-27.csv lists 439 (ticker, meeting, year) presentations named in
SEC filings; conf_study/conference_backfill_leads_drive_2026-11-27.csv adds 43 presentations from the owner's
Drive conference files (4 ASCO 2026 on 2026-11-27, 39 more 2023-2026 on 2026-11-28), each confirmed by the company's own
release naming the meeting (each lead_source is that release). The lead files' own dates and prices are NOT used: its "anchor" was one calendar date per meeting edition
(conf_registry.json), not the filing's, and some of those dates were weeks off the meeting (AACR 2022 as March 8; the
meeting ran April 8-13). Each lead is only a pointer to look for the company's own release.

ANCHOR, ATTRIBUTION, PRICES: exactly extend_conference_runup.py's (imported, not copied): the Eastern publication date
of the company's earliest release whose headline names the meeting and reports data from it, published from 42 days
before the meeting opens to the day after it closes; the release must be the ticker's own; the study's window
arithmetic. A lead with no such release gets no row (it is not dated some other way).

MEETINGS: conferences.json, conf_study/meetings_extra.json and conf_study/meetings_past.json (past editions, each date
quoted from the organiser's own page). A lead whose edition has no organiser-dated entry gets no row.

Writes _conference_runup_backfill.json only. Nothing here is published: rows are folded into the study only after a
red team. Incremental: each lead is read once (again when RULES_VERSION changes). Guard:
tests/test_conference_runup_backfill.py.

    python backfill_conference_runup.py [--budget-min 8] [--price-min 3]
"""
import argparse, csv, datetime as dt, io, json, os, sys, time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extend_conference_runup as X  # noqa: E402
import fetch_earnings_dates as FE  # noqa: E402

LEADS = os.path.join(HERE, "conf_study", "conference_backfill_leads_2026-11-27.csv")
LEADS_DRIVE = os.path.join(HERE, "conf_study", "conference_backfill_leads_drive_2026-11-27.csv")
PAST = os.path.join(HERE, "conf_study", "meetings_past.json")
CACHE = os.path.join(HERE, "_conference_runup_backfill.json")
CUTOFF = "2026-06-05"     # the published study stops 2026-06-04; later rows belong to the additions
FIELDS = ("runup_30d", "runup_20d", "runup_10d", "runup_5d", "event_day", "post_5d", "post_10d")


def all_meetings():
    """Every organiser-dated meeting edition we hold, one per (code, year)."""
    rows = json.load(io.open(os.path.join(HERE, "conferences.json"), encoding="utf-8"))["conferences"]
    for f in (X.EXTRA, PAST):
        if os.path.exists(f):
            rows = rows + json.load(io.open(f, encoding="utf-8"))["meetings"]
    out, seen = [], set()
    for c in rows:
        if not (c.get("source") and c.get("start") and c.get("end")):
            continue
        k = (c["code"], c["start"][:4])
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out


def leads():
    out, seen = [], set()
    for f in (LEADS, LEADS_DRIVE):
        if os.path.exists(f):
            for r in csv.DictReader(io.open(f, encoding="utf-8-sig")):
                if lead_key(r) not in seen:
                    seen.add(lead_key(r))
                    out.append(r)
    return out


def lead_key(r):
    return f"{r['ticker'].strip().upper()}|{r['conf'].strip()}|{str(r['year']).strip()[:4]}"


def names():
    n = dict(FE.sec_names())
    n.update({k: v for k, v in FE.universe().items() if v and v != k})
    return n


def save(out):
    tmp = CACHE + ".tmp"
    io.open(tmp, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=0, sort_keys=True))
    os.replace(tmp, CACHE)


def owns(m, end_field="end"):
    """The backfill owns a meeting only if it ended before the cut-off; the additions read every later one."""
    return str(m.get(end_field) or "9999") < CUTOFF


def find_row(tk, name, m, ms, items, lead_source, today):
    """The row for this lead from the ticker's releases, or (None, reason). Earliest qualifying release only: if it
    cannot be stored so that it re-checks from what is kept, no later release stands in."""
    hi = (dt.date.fromisoformat(m["end"]) + dt.timedelta(days=X.LATE_DAYS)).isoformat()
    for it in sorted(items, key=lambda x: str(x.get("publishedDate") or "")):
        title, text = FE.clean(it.get("title")), FE.clean(it.get("text"))
        pub_et = str(it.get("publishedDate") or "")[:10]   # FMP timestamps are Eastern (CLAUDE.md rule 1)
        url = str(it.get("url") or "")
        if not (title and pub_et and url.startswith("https://")):
            continue
        if not (X._mlo(m) <= pub_et <= hi) or not X.anchors(title, m, ms) or not X.own(tk, name, title, text):
            continue
        if not X.early_ok(title, text[:X.EXCERPT], pub_et, m):
            continue                          # a notice of talks to come: a later release is the data
        code, yr = X.study_code(m["code"]), m["start"][:4]
        row = {"key": f"{tk}|{code}|{yr}", "ticker": tk, "company": name, "conf": code, "meeting_code": m["code"],
               "year": int(yr), "conf_full": f"{m['name']} {yr}", "meeting_start": m["start"],
               "meeting_end": m["end"], "meeting_source": m["source"], "anchor": pub_et,
               "anchor_basis": "earliest company release found reporting data from the meeting",
               "release_title": title, "release_url": url, "release_excerpt": text[:X.EXCERPT],
               "release_evidence": X.evidence(tk, name, text), "lead_source": lead_source,
               "status": "pending", "found": today}
        if X.passes(row, ms, name):
            return row, "found"
        return None, "earliest release not storable"
    return None, "no qualifying release"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-min", type=float, default=8.0)
    ap.add_argument("--price-min", type=float, default=3.0)
    a = ap.parse_args()
    key = os.environ.get("FMP_API_KEY", "")
    if not key:
        print("FMP_API_KEY not set; conference backfill not refreshed")
        return 0
    today = dt.date.today().isoformat()
    ms = all_meetings()
    mk = {(X.study_code(m["code"]), m["start"][:4]): m for m in ms}
    cache = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    same_rules = cache.get("rules_version") == X.RULES_VERSION
    done = cache.get("done", {}) if same_rules else {}
    nm = names()
    rows, dropped = {}, 0
    for r in cache.get("rows", []):
        if (str(r.get("anchor", "9999")) < CUTOFF and owns(r, "meeting_end")
                and X.passes(r, ms, r.get("company") or nm.get(r["ticker"], r["ticker"]))):
            rows[r["key"]] = r
        else:
            dropped += 1
            done.pop(r["key"], None)          # read again under the current rules
    pub = X.published_keys()
    todo = [r for r in leads() if lead_key(r) not in done]
    t0, read, failed = time.time(), 0, 0
    for ld in todo:
        if time.time() - t0 > a.budget_min * 60:
            print(f"conference backfill: read budget reached after {read} leads")
            break
        k = lead_key(ld)
        tk, conf, yr = k.split("|")
        if (tk, conf, yr) in pub:
            done[k] = "in the published study"
            continue
        m = mk.get((conf, yr))
        if m is None or m["start"] >= CUTOFF:
            done[k] = "no organiser-dated meeting before the cut-off"
            continue
        if not owns(m):
            # EULAR 2026 ran Jun 3-6: CGEM's first release came Jun 6, after the study stops, and failed the
            # backfill guard in run 576. extend_conference_runup reads every meeting ending on or after the cut-off.
            done[k] = "meeting runs past the cut-off; read by the additions"
            continue
        name = nm.get(tk, "")
        if not name or name == tk:
            done[k] = "no company name for the ticker"
            continue
        to = (dt.date.fromisoformat(m["end"]) + dt.timedelta(days=X.LATE_DAYS + 1)).isoformat()
        items = FE.fetch(tk, X._mlo(m), to, key)
        time.sleep(0.12)
        if items is None:
            failed += 1                       # read again next run
            continue
        read += 1
        row, why = find_row(tk, name, m, ms, items, ld.get("lead_source", ""), today)
        done[k] = why
        if row:
            rows[row["key"]] = row
    priced, t1 = 0, time.time()
    for r in sorted(rows.values(), key=lambda r: r.get("priced", "")):
        if time.time() - t1 > a.price_min * 60:
            print("conference backfill: price budget reached")
            break
        if r.get("status") == "complete":
            continue
        a0 = dt.date.fromisoformat(r["anchor"])
        s = X.prices(r["ticker"], (a0 - dt.timedelta(days=80)).isoformat(), key)
        time.sleep(0.12)
        w = X.window(s, r["anchor"]) if s else None
        if not w:
            continue
        r.update(w)
        vals = [w[f] for f in FIELDS if f in w]
        r["status"] = "complete" if len(vals) == 7 and all(X.RANGE[0] < v < X.RANGE[1] for v in vals) else "check"
        r["priced"] = today
        priced += 1
    out = {"about": "Conference run-up rows before 2026-06-05 that the published study leaves out, re-dated from the "
                    "companies' own releases by the additions' rule. Not published; folded in only after a red "
                    "team. See backfill_conference_runup.py.",
           "built": today, "rules_version": X.RULES_VERSION, "done": done,
           "rows": sorted(rows.values(), key=lambda r: (r["anchor"], r["ticker"]))}
    save(out)
    tally = {}
    for v in done.values():
        tally[v] = tally.get(v, 0) + 1
    print(f"conference backfill: read {read} leads ({failed} failed), {len(done)}/{len(leads())} settled; "
          f"{len(out['rows'])} rows, {sum(r['status'] == 'complete' for r in out['rows'])} priced ({priced} this run), "
          f"{dropped} dropped by the rules; " + ", ".join(f"{v}: {n}" for v, n in sorted(tally.items())))
    if read == 0 and todo and failed:
        print(f"::warning::conference backfill: no lead readable ({failed} failed)")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
