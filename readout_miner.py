# -*- coding: utf-8 -*-
"""readout_miner.py -- resilient readout-date miner. ONLY real readouts, never enrolling trials.

The problem with the old CT.gov pass: it kept every RECRUITING / ENROLLING_BY_INVITATION trial, so
names that are still ACCRUING patients (GLMD, TCRX, TTRX, CANF, OCGN, SLS, ...) showed up with a
"primary completion date" that is a soft estimate months out and slips constantly. Those are NOT
readouts -- the data is not coming until enrollment finishes.

A trial only produces an imminent, tradeable readout once ENROLLMENT IS DONE. In ClinicalTrials.gov
that is exactly two statuses:
    ACTIVE_NOT_RECRUITING  = enrollment closed, patients on-study, data locking -> readout coming
    COMPLETED              = primary completion reached -> data out or imminent
Everything else -- RECRUITING, NOT_YET_RECRUITING, ENROLLING_BY_INVITATION, SUSPENDED, TERMINATED,
WITHDRAWN, UNKNOWN -- is rejected by default. (Pass --include-recruiting to also emit a clearly
separated WATCH list of recruiting names, off by default.)

Resilience (this run must never die on one bad ticker or a console-encoding quirk):
  * UTF-8 stdout, ASCII-only status markers (no emoji -> no cp1252 crash like the old readout_scan)
  * per-ticker try/except with an error tally; one failure never aborts the run
  * HTTP retry w/ exponential backoff incl. 429 rate-limit handling
  * server-side status + date filtering (smaller, more reliable responses)
  * checkpoint: partial CSV flushed every 25 tickers, so a kill keeps progress
  * lock-resistant atomic write (falls back to *_new.csv if the CSV is open in Excel/OneDrive)

Honest limits: CT.gov primary-completion dates are ESTIMATES ([EST]) and can slip; a locked trial can
report weeks after the date. Verify against IR. Not investment advice.

    python readout_miner.py [--fwd-months 12] [--overdue-days 120] [--include-recruiting]
"""
import argparse, csv, json, os, re, sys, time
import datetime as dt
import urllib.parse, urllib.request, urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.environ.get("SEC_USER_AGENT", "David Moody rockyshoals@gmail.com")
TICKER_MAP_CACHE = os.path.join(HERE, "bpc_data", "_edgar_ticker_map.json")
OUT = os.path.join(HERE, "readout_miner.csv")
COLS = ["ticker", "pcd", "pcd_type", "days_to_pcd", "bucket", "status", "phase", "enroll",
        "enroll_type", "nct", "company", "title"]

# The ONLY statuses where enrollment is finished -> a readout is actually coming.
READOUT_STATUS = {"ACTIVE_NOT_RECRUITING", "COMPLETED"}
ENROLLING_STATUS = {"RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"}
DEAD_STATUS = {"WITHDRAWN", "TERMINATED", "SUSPENDED", "UNKNOWN", "NO_LONGER_AVAILABLE"}


def log(msg=""):
    print(msg, flush=True)


def _get(url, tries=5):
    """GET with exponential backoff; handles 429/5xx. Returns text or None."""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(min(2 ** i, 20)); continue
            return None
        except Exception:
            time.sleep(0.5 * (i + 1))
    return None


def ticker_to_company():
    try:
        if os.path.exists(TICKER_MAP_CACHE) and (time.time() - os.path.getmtime(TICKER_MAP_CACHE)) < 7 * 86400:
            return json.load(open(TICKER_MAP_CACHE))
    except Exception:
        pass
    raw = _get("https://www.sec.gov/files/company_tickers.json")
    m = {}
    if raw:
        try:
            for v in json.loads(raw).values():
                t = (v.get("ticker") or "").upper()
                if t:
                    m[t] = v.get("title", "")
            os.makedirs(os.path.dirname(TICKER_MAP_CACHE), exist_ok=True)
            json.dump(m, open(TICKER_MAP_CACHE, "w"))
        except Exception:
            pass
    return m


def sponsor_query(name):
    """Company title -> CT.gov sponsor term. Drop only the trailing legal suffix; keep the
    descriptive words (so 'Tarsus Pharmaceuticals, Inc.' stays 'Tarsus Pharmaceuticals', not the
    Turkish 'Tarsus University')."""
    n = (name or "").split(",")[0].strip()
    for suf in (" Inc.", " Inc", " Corporation", " Corp.", " Corp", " Ltd.", " Ltd", " plc",
                " N.V.", " S.A.", " AG", " SE", " LLC", " Limited", " Co.", " Holdings"):
        if n.endswith(suf):
            n = n[:-len(suf)].strip()
    return n or (name or "")


_ACADEMIC = ("university", "hospital", "institute", "college", "medical center", "clinic",
             "foundation", "national ", "ministry", "health system", "cancer center", "school of")


def sponsor_ok(lead_name, company):
    ld = (lead_name or "").lower()
    if not ld:
        return False
    comp_l = (company or "").lower()
    company_is_academic = any(a in comp_l for a in _ACADEMIC)
    if not company_is_academic and any(a in ld for a in _ACADEMIC):
        return False
    toks = [w for w in re.findall(r"[a-z]+", comp_l)
            if len(w) > 2 and w not in ("the", "inc", "corp", "ltd", "group", "holdings")]
    key = toks[0] if toks else ""
    return bool(key) and key in ld


def parse_pcd(s):
    if not s:
        return None
    p = s.split("-")
    try:
        if len(p) == 3:
            return dt.date(int(p[0]), int(p[1]), int(p[2]))
        if len(p) == 2:
            y, m = int(p[0]), int(p[1])
            last = [31, 29 if y % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
            return dt.date(y, m, last)
        return dt.date(int(p[0]), 12, 31)
    except Exception:
        return None


def ctgov_studies(sponsor, include_recruiting):
    """Query CT.gov v2 by sponsor, filtered SERVER-SIDE to enrollment-complete statuses."""
    statuses = list(READOUT_STATUS) + (list(ENROLLING_STATUS) if include_recruiting else [])
    q = urllib.parse.quote(sponsor)
    url = (f"https://clinicaltrials.gov/api/v2/studies?query.spons={q}"
           f"&filter.overallStatus={','.join(statuses)}"
           f"&fields=NCTId,BriefTitle,Phase,OverallStatus,PrimaryCompletionDate,"
           f"PrimaryCompletionDateType,LeadSponsorName,EnrollmentCount,EnrollmentType&pageSize=50")
    raw = _get(url)
    if not raw:
        return None  # None = query failed (distinct from empty result)
    try:
        return json.loads(raw).get("studies", [])
    except Exception:
        return None


def classify(status, pcd, today):
    d = (pcd - today).days
    if status == "COMPLETED":
        return "REPORTED/IMMINENT" if d <= 14 else "COMPLETES SOON"
    # ACTIVE_NOT_RECRUITING
    if d < 0:
        return "DATA PENDING (lock passed)"
    if d <= 60:
        return "SOON (<=60d)"
    if d <= 180:
        return "UPCOMING (<=6mo)"
    return "SCHEDULED (>6mo)"


def load_universe():
    tks, sources = set(), {}
    def add(t, src):
        t = (t or "").strip().upper()
        if t and t.isascii() and re.fullmatch(r"[A-Z.\-]{1,6}", t):
            tks.add(t); sources.setdefault(t, src)
    for p, src in ((os.path.join(HERE, "readout_watchlist.txt"), "watchlist"),
                   (os.path.join(HERE, "catalysts_out", "universe_effective.txt"), "universe")):
        if os.path.exists(p):
            for ln in open(p, encoding="utf-8", errors="ignore"):
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    add(ln.split(",")[0].split()[0], src)
    p = os.path.join(HERE, "readout_forward.csv")
    if os.path.exists(p):
        try:
            for r in csv.DictReader(open(p, encoding="utf-8-sig")):
                add(r.get("ticker"), "forward")
        except Exception:
            pass
    return sorted(tks), sources


def write_csv(rows, dst):
    tmp = dst + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    for attempt in range(5):
        try:
            os.replace(tmp, dst); return dst
        except PermissionError:
            time.sleep(1.2 * (attempt + 1))
    alt = os.path.splitext(dst)[0] + "_new.csv"
    os.replace(tmp, alt)
    log(f"  [lock] {os.path.basename(dst)} was open/locked -> wrote {os.path.basename(alt)} instead.")
    return alt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fwd-months", type=int, default=12)
    ap.add_argument("--overdue-days", type=int, default=120)
    ap.add_argument("--include-recruiting", action="store_true",
                    help="also emit a separate WATCH list of still-enrolling names (default: off)")
    ap.add_argument("--limit", type=int, default=0, help="cap tickers scanned (0 = all; for quick runs)")
    a = ap.parse_args()

    today = dt.date.today()
    lo, hi = today - dt.timedelta(days=a.overdue_days), today + dt.timedelta(days=a.fwd_months * 31)
    tks, _ = load_universe()
    if a.limit:
        tks = tks[:a.limit]
    tmap = ticker_to_company()

    log("=" * 90)
    log(f"  READOUT MINER  {dt.datetime.now():%Y-%m-%d %H:%M}  |  {len(tks)} tickers  |  "
        f"PCD window {lo} .. {hi}")
    log("  keeping ONLY enrollment-complete trials (ACTIVE_NOT_RECRUITING, COMPLETED); "
        "recruiting/enrolling REJECTED" + (" (but listed as WATCH)" if a.include_recruiting else ""))
    log("=" * 90)

    out, watch = [], []
    stats = {"no_company": 0, "query_fail": 0, "rejected_enrolling": 0, "rejected_dead": 0,
             "rejected_window": 0, "rejected_phase": 0, "rejected_sponsor": 0, "errors": 0}
    for i, tk in enumerate(tks):
        try:
            company = tmap.get(tk)
            if not company:
                stats["no_company"] += 1
                continue
            studies = ctgov_studies(sponsor_query(company), a.include_recruiting)
            if studies is None:
                stats["query_fail"] += 1
                continue
            best, best_watch = None, None
            for s in studies:
                ps = s.get("protocolSection", {})
                sm = ps.get("statusModule", {})
                status = sm.get("overallStatus", "")
                lead = (ps.get("sponsorCollaboratorsModule", {}) or {}).get("leadSponsor", {}).get("name", "")
                if not sponsor_ok(lead, company):
                    stats["rejected_sponsor"] += 1; continue
                pcd = parse_pcd((sm.get("primaryCompletionDateStruct", {}) or {}).get("date", ""))
                if not pcd or not (lo <= pcd <= hi):
                    stats["rejected_window"] += 1; continue
                phases = ",".join(ps.get("designModule", {}).get("phases", []) or [])
                if not any(p in phases for p in ("PHASE1", "PHASE2", "PHASE3")):
                    stats["rejected_phase"] += 1; continue
                enr = (ps.get("designModule", {}).get("enrollmentInfo", {}) or {})
                rec = {
                    "ticker": tk, "company": company, "pcd": pcd.isoformat(),
                    "pcd_type": (sm.get("primaryCompletionDateStruct", {}) or {}).get("type", ""),
                    "status": status, "phase": phases,
                    "enroll": enr.get("count", ""), "enroll_type": enr.get("type", ""),
                    "nct": ps.get("identificationModule", {}).get("nctId", ""),
                    "title": (ps.get("identificationModule", {}).get("briefTitle", "") or "")[:70],
                    "days_to_pcd": (pcd - today).days,
                    "bucket": classify(status, pcd, today),
                }
                if status in READOUT_STATUS:
                    if best is None or abs(rec["days_to_pcd"]) < abs(best["days_to_pcd"]):
                        best = rec
                elif status in ENROLLING_STATUS:
                    stats["rejected_enrolling"] += 1
                    rec["bucket"] = "WATCH (still enrolling)"
                    if best_watch is None or abs(rec["days_to_pcd"]) < abs(best_watch["days_to_pcd"]):
                        best_watch = rec
                else:
                    stats["rejected_dead"] += 1
            if best:
                out.append(best)
            elif best_watch:
                watch.append(best_watch)
        except Exception as e:
            stats["errors"] += 1
            log(f"  [warn] {tk}: {type(e).__name__}: {e}")
        if (i + 1) % 25 == 0:
            log(f"  {i+1}/{len(tks)}  ({len(out)} readouts kept, {stats['rejected_enrolling']} enrolling rejected)")
            write_csv(sorted(out, key=lambda r: r["pcd"]), OUT)  # checkpoint
        time.sleep(0.05)

    out.sort(key=lambda r: r["pcd"])
    dst = write_csv(out, OUT)

    log("\n" + "=" * 90)
    log(f"  {len(out)} READOUTS (enrollment complete) -> {os.path.basename(dst)}")
    log("=" * 90)
    log(f"  {'tkr':<6}{'PCD':<12}{'in':>6}  {'status':<22}{'phase':<14}{'bucket':<26}{'nct':<12}")
    log("  " + "-" * 86)
    for r in out:
        est = "~" if str(r["pcd_type"]).upper().startswith("EST") else " "
        log(f"  {r['ticker']:<6}{est}{r['pcd']:<11}{r['days_to_pcd']:>5}d  "
            f"{r['status'][:21]:<22}{r['phase'][:13]:<14}{r['bucket']:<26}{r['nct']:<12}")

    if a.include_recruiting and watch:
        watch.sort(key=lambda r: r["pcd"])
        log(f"\n  WATCH -- {len(watch)} still-enrolling names (NOT readouts; date unreliable):")
        for r in watch:
            log(f"    {r['ticker']:<6} {r['pcd']:<11} {r['status']:<24} {r['nct']}")

    log("\n  filter tally: " + "  ".join(f"{k}={v}" for k, v in stats.items() if v))
    log(f"  kept {len(out)} readouts | rejected {stats['rejected_enrolling']} enrolling, "
        f"{stats['rejected_dead']} dead/unknown, {stats['rejected_window']} out-of-window.")
    log("  ~ = estimated PCD (slips). Data can print weeks after the lock. Verify vs IR. Not investment advice.")


if __name__ == "__main__":
    main()
