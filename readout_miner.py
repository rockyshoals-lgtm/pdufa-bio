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
TODAY = dt.date.today()
COLS = ["ticker", "best_date", "date_source", "confidence", "guided_date", "guided_precision",
        "guided_form", "guided_filed", "pcd", "pcd_type", "days_to_pcd", "bucket", "status",
        "phase", "enroll", "enroll_type", "nct", "company", "title"]

# The ONLY statuses where enrollment is finished -> a readout is actually coming.
# ---------------------------------------------------------------- EDGAR guidance source
# Readout DATES are usually announced by the company, not posted to ClinicalTrials.gov. CT.gov gives
# you the trial's data-lock estimate; EDGAR gives you what the company actually GUIDED ("topline data
# expected in Q4 2026"). Press releases for US issuers are filed as 8-K exhibits and for foreign
# issuers as 6-K, and guidance is repeated in 10-Q/10-K MD&A and in registration statements -- so all
# of those are searched, not just 8-K/6-K.
FTS = "https://efts.sec.gov/LATEST/search-index"
EDGAR_FORMS = "8-K,6-K,10-Q,10-K,20-F,S-1,424B4,424B5"
GUIDE_PHRASES = [
    "topline data expected", "topline results expected", "data expected in", "data are expected",
    "results are expected", "results expected in", "readout expected", "readout anticipated",
    "results anticipated", "data anticipated in", "expects to report topline",
    "expect to report topline", "plans to report topline", "on track to report",
    "anticipate reporting", "initial data expected", "interim analysis expected",
    "primary endpoint data expected", "expects to announce topline", "data readout expected",
    "proof-of-concept data expected", "topline readout",
]
# Date expressions companies actually use, most specific first -> (normalized date, precision)
MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September",
     "October", "November", "December"], 1)}

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


def _eom(y, m):
    return dt.date(y, m, [31, 29 if y % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])


def parse_guided_date(text):
    """Pull the guided readout date out of company language.
    Returns (iso_date, precision) or (None, None). Dates are normalized to the END of the guided
    window (a 'Q4 2026' readout is not promised on Oct 1), and the precision is recorded so nothing
    is presented as more exact than the company actually said."""
    t = (text or "").lower()
    y_now = TODAY.year
    # explicit month + year -> month precision
    m = re.search(r'\b(' + "|".join(MONTHS) + r')\s+(20\d{2})\b', t)
    if m:
        y, mo = int(m.group(2)), MONTHS[m.group(1)]
        return _eom(y, mo).isoformat(), "month"
    # quarter -- companies write "Q4 2026", "4Q 2026", "fourth quarter of 2026"
    m = re.search(r'\b(?:q\s?([1-4])\s*(20\d{2})|([1-4])q\s*(20\d{2})'
                  r'|([1-4])(?:st|nd|rd|th)\s+quarter\s+(?:of\s+)?(20\d{2})'
                  r'|(first|second|third|fourth)\s+quarter\s+(?:of\s+)?(20\d{2}))\b', t)
    if m:
        if m.group(1):
            q, y = int(m.group(1)), int(m.group(2))
        elif m.group(3):
            q, y = int(m.group(3)), int(m.group(4))
        elif m.group(5):
            q, y = int(m.group(5)), int(m.group(6))
        else:
            q = {"first": 1, "second": 2, "third": 3, "fourth": 4}[m.group(7)]; y = int(m.group(8))
        return _eom(y, q * 3).isoformat(), "quarter"
    # half / mid / year-end
    m = re.search(r'\b(?:([12])h\s*(20\d{2})|(first|second)\s+half\s+(?:of\s+)?(20\d{2}))\b', t)
    if m:
        if m.group(1):
            h, y = int(m.group(1)), int(m.group(2))
        else:
            h = 1 if m.group(3) == "first" else 2; y = int(m.group(4))
        return _eom(y, h * 6).isoformat(), "half"
    m = re.search(r'\bmid[-\s]?(20\d{2})\b', t)
    if m:
        return _eom(int(m.group(1)), 6).isoformat(), "half"
    m = re.search(r'\b(?:year[-\s]?end|end of)\s+(20\d{2})\b', t)
    if m:
        return _eom(int(m.group(1)), 12).isoformat(), "half"
    m = re.search(r'\b(early|late)\s+(20\d{2})\b', t)
    if m:
        y = int(m.group(2))
        return (_eom(y, 3) if m.group(1) == "early" else _eom(y, 12)).isoformat(), "half"
    # bare year ("topline data expected in 2027") -> year precision, end of year
    m = re.search(r'\bin\s+(20\d{2})\b', t)
    if m:
        y = int(m.group(1))
        if TODAY.year <= y <= TODAY.year + 3:
            return _eom(y, 12).isoformat(), "year"
    return None, None


def _fts(phrase, start, end, frm=0):
    q = urllib.parse.urlencode({"q": f'"{phrase}"', "startdt": start, "enddt": end,
                                "forms": EDGAR_FORMS, "from": frm})
    raw = _get(f"{FTS}?{q}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


TICK = re.compile(r'\(([A-Z][A-Z.\-]{0,5})\)')


ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
TAG = re.compile(r"<[^>]+>")


def _doc_text(cik, adsh, fname):
    url = f"{ARCHIVES}/{str(cik).lstrip('0')}/{adsh.replace('-', '')}/{fname}"
    raw = _get(url, tries=3)
    if not raw:
        return ""
    return re.sub(r"\s+", " ", TAG.sub(" ", raw))


def edgar_guidance(days, max_docs=150, verbose=True):
    """{TICKER: {...}} of company-GUIDED readout dates, mined from EDGAR full text.

    Two stages, because EDGAR's search API returns NO highlight snippets -- the guided date only
    exists inside the filing itself:
      1. full-text search each guidance phrase across the window -> candidate filings (+ ticker)
      2. fetch the filing and read the sentence around the phrase -> parse the guided date

    Filings are deduped and the newest are fetched first, so the doc budget is spent on current
    guidance rather than stale repeats."""
    step = 30
    slices, i = [], 0
    while i < days:
        b = TODAY - dt.timedelta(days=min(i + step, days))
        e = TODAY - dt.timedelta(days=i)
        slices.append((b.isoformat(), e.isoformat()))
        i += step

    cands, calls = {}, 0
    for ph in GUIDE_PHRASES:
        for (a, b) in slices:
            j = _fts(ph, a, b)
            calls += 1
            if not j:
                continue
            for h in (j.get("hits", {}) or {}).get("hits", []) or []:
                src = h.get("_source", {}) or {}
                mt = TICK.search(" ".join(src.get("display_names", []) or []))
                if not mt:
                    continue
                _id = h.get("_id", "")
                if ":" not in _id:
                    continue
                adsh, fname = _id.split(":", 1)
                key = (mt.group(1), adsh, fname)
                rec = cands.setdefault(key, {"phrases": set(), "form": src.get("file_type", ""),
                                             "filed": src.get("file_date", ""),
                                             "cik": (src.get("ciks") or [""])[0]})
                rec["phrases"].add(ph)
            time.sleep(0.11)          # SEC fair-use pacing

    ordered = sorted(cands.items(), key=lambda kv: kv[1]["filed"] or "", reverse=True)[:max_docs]
    out, parsed, fetched = {}, 0, 0
    for (tk, adsh, fname), meta in ordered:
        txt = _doc_text(meta["cik"], adsh, fname)
        fetched += 1
        if not txt:
            continue
        low = txt.lower()
        best = None
        for ph in meta["phrases"]:
            pos = 0
            while True:
                k = low.find(ph, pos)
                if k < 0:
                    break
                snip = txt[max(0, k - 200): k + 260]
                d, prec = parse_guided_date(snip)
                if d and d >= TODAY.isoformat() and (best is None or d < best[0]):
                    best = (d, prec, ph, snip)
                pos = k + len(ph)
        if best:
            parsed += 1
            prev = out.get(tk)
            if prev is None or best[0] < prev["guided_date"]:
                out[tk] = {"guided_date": best[0], "guided_precision": best[1], "phrase": best[2],
                           "form": meta["form"], "filed": meta["filed"], "adsh": adsh}
        time.sleep(0.09)
    if verbose:
        log(f"  EDGAR: {calls} full-text queries over {days}d across [{EDGAR_FORMS}] -> "
            f"{len(cands)} candidate filings; fetched {fetched}, parsed a forward date from {parsed}; "
            f"{len(out)} tickers with company-guided dates")
    return out


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
    ap.add_argument("--source", choices=["both", "ctgov", "edgar"], default="both",
                    help="which date sources to use (default both)")
    ap.add_argument("--edgar-days", type=int, default=180,
                    help="how far back to full-text search EDGAR for guided readout dates")
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

    # ---- merge in the EDGAR company-guided dates -------------------------------------------
    guided = {}
    if a.source in ("both", "edgar"):
        log("")
        guided = edgar_guidance(a.edgar_days)

    by_tk = {r["ticker"]: r for r in out}
    for tk, g in guided.items():
        r = by_tk.get(tk)
        if r:
            r.update({"guided_date": g["guided_date"], "guided_precision": g["guided_precision"],
                      "guided_form": g["form"], "guided_filed": g["filed"]})
        elif a.source in ("both", "edgar"):
            # Company guided a readout but CT.gov shows no enrollment-complete trial. Still a real
            # readout date -- this is the SLS/"never in CT.gov" case the whole upgrade exists for.
            by_tk[tk] = {"ticker": tk, "company": tmap.get(tk, ""), "pcd": "", "pcd_type": "",
                         "days_to_pcd": "", "status": "", "phase": "", "enroll": "",
                         "enroll_type": "", "nct": "", "title": "",
                         "bucket": "GUIDED (company statement)",
                         "guided_date": g["guided_date"], "guided_precision": g["guided_precision"],
                         "guided_form": g["form"], "guided_filed": g["filed"]}

    merged = list(by_tk.values())
    for r in merged:
        gd, pcd = r.get("guided_date") or "", r.get("pcd") or ""
        if gd and pcd:
            r["date_source"], r["confidence"] = "BOTH", "high"
            # prefer the company's own guidance; it is what the market trades
            r["best_date"] = gd
        elif gd:
            r["date_source"], r["confidence"], r["best_date"] = "EDGAR", "medium", gd
        else:
            r["date_source"], r["confidence"], r["best_date"] = "CTGOV", "medium", pcd
    merged.sort(key=lambda r: (r.get("best_date") or "9999"))
    out = merged
    dst = write_csv(out, OUT)

    nboth = sum(1 for r in out if r["date_source"] == "BOTH")
    nedgar = sum(1 for r in out if r["date_source"] == "EDGAR")
    nctg = sum(1 for r in out if r["date_source"] == "CTGOV")
    log("\n" + "=" * 100)
    log(f"  {len(out)} READOUT DATES -> {os.path.basename(dst)}   "
        f"[BOTH sources {nboth} | EDGAR-guided {nedgar} | CT.gov only {nctg}]")
    log("=" * 100)
    log(f"  {'tkr':<6}{'best date':<12}{'src':<7}{'conf':<8}{'guided':<12}{'prec':<9}"
        f"{'status':<22}{'bucket':<26}")
    log("  " + "-" * 96)
    for r in out:
        log(f"  {r['ticker']:<6}{(r.get('best_date') or '')[:10]:<12}{r['date_source']:<7}"
            f"{r['confidence']:<8}{(r.get('guided_date') or '-')[:10]:<12}"
            f"{(r.get('guided_precision') or '-'):<9}{(r.get('status') or '-')[:21]:<22}"
            f"{r.get('bucket',''):<26}")

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
