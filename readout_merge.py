"""readout_merge.py — unify EDGAR guidance + CT.gov dates into ONE tradeable readout calendar.

The 10:24 run left two files that don't talk to each other:
    readout_forward.csv   EDGAR "the company SAID a readout is coming"  (vague dates + smart money)
    ctgov_readouts.csv    CT.gov "the trial's data LOCKS on <date>"     (specific dates)
29 names appear in both, and several DISAGREE in a way that matters:
    CANF  EDGAR "Q4 2026"  vs  CT.gov 2026-07-15 (-3d, data pending NOW)
    RFL   EDGAR "2H 2026"  vs  CT.gov 2026-07-02 (-16d, overdue)
That gap is signal. This merges them into readout_calendar.csv — one row per ticker, the most
specific date we have, the EDGAR window beside it, a confidence tag, an imminence tag, a
DISAGREE flag when the two sources are far apart, and the smart-money columns. Sorted by
imminence so "data pending now" is at the top.

HONEST FRAMING (unchanged): CT.gov primary completion dates are ESTIMATES that slip; a locked
trial can report weeks later; EDGAR guidance is a plan companies miss. A readout is +3% on
average, 1 in 8 pops >=15%. This is a WATCHLIST with the best dates we can assemble, not a
prediction. Verify against IR. Not investment advice.
"""
import csv
import datetime as dt
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SM_COLS = ["sm_signal", "sm_cp_ratio", "sm_unusual_x", "sm_dp_lean", "sm_dp_prem", "sm_gex_sign",
           "sm_implied_date", "sm_implied_conf"]


def load(p):
    """Read the FRESHEST of {name.csv, name_new.csv}. When a CSV is open/locked, the upstream
    step falls back to a `_new.csv` sibling (lock-resistant write). Without this, the merge would
    silently consume the STALE main file and quietly undo the fresh run. Pick whichever is newer.
    """
    base = os.path.join(HERE, p)
    alt = os.path.splitext(base)[0] + "_new.csv"
    cands = [c for c in (base, alt) if os.path.exists(c)]
    if not cands:
        return []
    best = max(cands, key=os.path.getmtime)
    return list(csv.DictReader(open(best, encoding="utf-8-sig")))


def edgar_window_start(w):
    """A vague EDGAR window -> its expected-midpoint date, so we can sort/compare with CT.gov.
    Reuses the same logic family as readout_scan; kept local to avoid a cross-import."""
    s = (w or "").lower().strip()
    m = re.search(r"20(2\d|3\d)", s)
    if not m:
        return None
    yr = int(m.group(0))
    if re.search(r"\bq1\b|first quarter|early", s): mo = 2
    elif re.search(r"\bq2\b|second quarter", s): mo = 5
    elif re.search(r"\bq3\b|third quarter", s): mo = 8
    elif re.search(r"\bq4\b|fourth quarter", s): mo = 11
    elif re.search(r"\b1h\b|first half", s): mo = 3
    elif re.search(r"\b2h\b|second half|2nd half|mid", s): mo = 9
    elif re.search(r"\blate\b", s): mo = 11
    else: mo = 6
    try:
        return dt.date(yr, mo, 15)
    except ValueError:
        return None


def imminence(days):
    """The tradeable zone is +/-30 days of TODAY, not 'most overdue'. A trial whose primary
    completion was 4 months ago has almost certainly reported already — it is LESS actionable
    than one locking this week. So the buckets peak at ~now and DECAY in both directions, and
    deep-overdue is pushed to the bottom as 'likely already reported'."""
    if days is None:
        return "UNDATED"
    # NOTE: JUST REPORTED is handled BEFORE this function (it out-ranks every date bucket) — a
    # filing reporting data today is the morning gapper regardless of any future PCD.
    if -30 <= days < 0:
        return "DATA PENDING NOW"
    if 0 <= days <= 21:
        return "IMMINENT (<=3wk)"
    if 21 < days <= 60:
        return "SOON (<=60d)"
    if -90 <= days < -30:
        return "RECENTLY LOCKED (PR may be out)"
    if 60 < days <= 120:
        return "NEAR (<=120d)"
    if days > 120:
        return "LATER"
    return "STALE (likely reported)"          # days < -90


def main():
    fwd = {r["ticker"].upper(): r for r in load("readout_forward.csv") if r.get("ticker")}
    ctg = {r["ticker"].upper(): r for r in load("ctgov_readouts.csv") if r.get("ticker")}
    today = dt.date.today()
    tickers = sorted(set(fwd) | set(ctg))

    rows = []
    for t in tickers:
        e = fwd.get(t, {})
        c = ctg.get(t, {})
        ew = (e.get("window") or "").strip()
        cpcd = (c.get("pcd") or "").strip()
        try:
            cdays = int(c["days_to_pcd"]) if c.get("days_to_pcd") not in (None, "") else None
        except ValueError:
            cdays = None

        # BEST date: prefer the specific CT.gov date; fall back to the EDGAR window.
        if cpcd:
            best_date, date_src, days = cpcd, "CTGOV", cdays
        elif ew:
            best_date, date_src, days = ew, "EDGAR", None
            es = edgar_window_start(ew)
            if es:
                days = (es - today).days
        else:
            best_date, date_src, days = "", "", None

        # THE KLRS LESSON — did the EDGAR filing REPORT data (not just guide to it)? If so it
        # out-ranks every future date: that name gapped this morning. (Column absent on pre-fix
        # CSVs -> treated as no.)
        just_reported = (e.get("just_reported") or "").strip().upper() == "YES"
        result_hit = (e.get("result_hit") or "").strip()
        imm = "🔥 JUST REPORTED (data out)" if just_reported else imminence(days)

        # confidence: in BOTH sources = highest
        conf = "BOTH" if (t in fwd and t in ctg and (ew or cpcd)) else \
               ("CTGOV" if t in ctg else "EDGAR")

        # DISAGREE: EDGAR window midpoint vs CT.gov date, > ~100 days apart
        disagree = ""
        es = edgar_window_start(ew)
        cpcd_d = None
        if cpcd:
            try:
                cpcd_d = dt.date(*map(int, cpcd.split("-")))
            except Exception:
                cpcd_d = None
        if es and cpcd_d and abs((es - cpcd_d).days) > 100:
            disagree = f"EDGAR~{es.isoformat()} vs CTgov {cpcd}"

        row = {
            "ticker": t,
            "best_date": best_date,
            "date_source": date_src,
            "days_to": days if days is not None else "",
            "imminence": imm,
            "just_reported": "YES" if just_reported else "",
            "result_hit": result_hit[:120],
            "confidence": conf,
            "edgar_window": ew,
            "ctgov_pcd": cpcd,
            "phase": (c.get("phase") or "").strip(),
            "status": (c.get("status") or "").strip(),
            "nct": (c.get("nct") or "").strip(),
            "disagree": disagree,
            "company": (e.get("company") or c.get("company") or "")[:40],
        }
        for col in SM_COLS:
            row[col] = e.get(col, "")
        rows.append(row)

    # peak at NOW, decay both ways; stale/undated at the bottom. Within a bucket, closest to
    # today (smallest |days|) first.
    order = {"🔥 JUST REPORTED (data out)": -1, "DATA PENDING NOW": 0, "IMMINENT (<=3wk)": 1,
             "SOON (<=60d)": 2, "RECENTLY LOCKED (PR may be out)": 3, "NEAR (<=120d)": 4,
             "LATER": 5, "STALE (likely reported)": 6, "UNDATED": 7}

    def sortkey(r):
        d = r["days_to"]
        d = d if isinstance(d, int) else 99999
        return (order.get(r["imminence"], 9), abs(d))
    rows.sort(key=sortkey)

    dst = os.path.join(HERE, "readout_calendar.csv")
    cols = ["ticker", "best_date", "date_source", "days_to", "imminence", "just_reported",
            "result_hit", "confidence", "edgar_window", "ctgov_pcd", "phase", "status", "nct",
            "disagree", "company"] + SM_COLS
    # lock-resistant write (Documents is OneDrive-synced)
    import time as _t
    tmp = dst + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    ok = False
    for a in range(5):
        try:
            os.replace(tmp, dst)
            ok = True
            break
        except PermissionError:
            _t.sleep(1.2 * (a + 1))
    if not ok:
        dst = os.path.splitext(dst)[0] + "_new.csv"
        os.replace(tmp, dst)
        print(f"[merge] readout_calendar.csv LOCKED (close it) -> wrote {os.path.basename(dst)}")

    print("=" * 96)
    print(f"  READOUT CALENDAR — {len(rows)} names, most-specific date, sorted by imminence")
    print("=" * 96)
    print(f"  {'tkr':<6}{'best date':<13}{'src':<7}{'in':>6}  {'imminence':<30}"
          f"{'conf':<6}{'sm':<8}")
    print("  " + "-" * 92)
    for r in rows[:45]:
        d = f"{r['days_to']}d" if r["days_to"] != "" else ""
        flag = "  !DISAGREE" if r["disagree"] else ""
        print(f"  {r['ticker']:<6}{r['best_date'][:12]:<13}{r['date_source']:<7}{d:>6}  "
              f"{r['imminence']:<30}{r['confidence']:<6}{r.get('sm_signal',''):<8}{flag}")
    dis = [r for r in rows if r["disagree"]]
    print(f"\n  {len([r for r in rows if r['confidence']=='BOTH'])} highest-confidence (BOTH "
          f"sources) · {len(dis)} EDGAR/CTgov date DISAGREEMENTS (the interesting ones):")
    for r in dis[:12]:
        print(f"    {r['ticker']:<6} {r['disagree']}")
    print("\n  CT.gov dates are estimates; a locked trial can report weeks later; EDGAR is a plan.")
    print("  Not investment advice.")


if __name__ == "__main__":
    main()
