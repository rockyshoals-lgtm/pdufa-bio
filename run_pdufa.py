#!/usr/bin/env python3
"""
pdufa.bio — autonomous run wrapper (the engine the 5x/day scheduler calls).

One entry point that, on each trading-day run:
  1. crawls all sources (catalyst_crawler.py --fmp --options)
  2. runs the freshness guard (flags companies that have reported since we last parsed)
  3. runs the integrity audit (publish-readiness verdict)
and then logs everything, writes a machine-readable status file, and ALERTS you if a
run failed or the data isn't publish-ready — so you always KNOW the state, and a bad run
never silently replaces good data.

Design principles:
  - Failure-tolerant: a single stage failing is captured, not fatal; if the *crawl* fails,
    the previous data is left untouched (better stale-but-known than half-written).
  - Trading-day aware: skips weekends and US market holidays (override with --force).
  - Idempotent: safe to fire 5x/day; multiple-instance guard is on the OS scheduler side.

Edit the CONFIG block for your machine, then point Task Scheduler / cron at:
    python run_pdufa.py
"""
import os, sys, re, json, subprocess, datetime as dt, urllib.request

# ----------------------------- CONFIG (edit for your machine) -----------------------------
BASE       = r"C:\Users\dcmoo\Documents\Python\9realms"          # working directory
PY         = sys.executable
CRAWLER    = os.path.join(BASE, "catalyst_crawler.py")
FRESHNESS  = os.path.join(BASE, "freshness_check.py")
AUDIT      = os.path.join(BASE, "data_audit.py")
UNIVERSE   = os.path.join(BASE, "your_universe.txt")
BPC        = r"C:\Users\dcmoo\Documents\Python\fda_2026-05-30.xlsx"   # latest BioPharmaCatalyst export
OUTDIR     = os.path.join(BASE, "catalysts_out")
PUBLIC_CSV = os.path.join(OUTDIR, "catalysts_public.csv")
RUNS       = os.path.join(BASE, "runs")
STAGE_TIMEOUT = 3600                                              # seconds per stage
ALERT_WEBHOOK = os.environ.get("PDUFA_ALERT_WEBHOOK", "")         # optional Slack/Discord/Teams incoming webhook
# Keys (FMP_API_KEY / ORATS_API_KEY / UW_API_KEY) must exist in THIS process's environment —
# set them as persistent USER/SYSTEM environment variables so the scheduled task inherits them.

# NYSE market holidays 2026 — not trading days, skip.
HOLIDAYS = {"2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25","2026-06-19",
            "2026-07-03","2026-09-07","2026-11-26","2026-12-25",
            "2027-01-01","2027-01-18","2027-02-15","2027-03-26","2027-05-31","2027-06-18",
            "2027-07-05","2027-09-06","2027-11-25","2027-12-24"}

# ------------------------------------------------------------------------------------------
def is_trading_day(d):
    return d.weekday() < 5 and d.isoformat() not in HOLIDAYS

def run_stage(name, cmd):
    """Run a stage. Never raises — returns (ok, captured_output_tail)."""
    try:
        p = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=STAGE_TIMEOUT)
        return p.returncode == 0, ((p.stdout or "") + (p.stderr or ""))[-4000:]
    except subprocess.TimeoutExpired:
        return False, f"{name} TIMED OUT after {STAGE_TIMEOUT}s"
    except Exception as e:
        return False, f"{name} crashed: {e}"

def grep_num(text, pat, cast=int, default=None):
    m = re.search(pat, text)
    try: return cast(m.group(1)) if m else default
    except Exception: return default

def alert(msg):
    print("ALERT:", msg)
    if not ALERT_WEBHOOK: return
    try:
        body = json.dumps({"text": msg}).encode()
        req = urllib.request.Request(ALERT_WEBHOOK, data=body, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print("  (webhook failed:", e, ")")

def write_status(start, verdict, status, loglines, stamp):
    os.makedirs(RUNS, exist_ok=True)
    status = {"run": stamp, "started": start.isoformat(), "verdict": verdict,
              "finished": dt.datetime.now().isoformat(), **status}
    json.dump(status, open(os.path.join(RUNS, "status.json"), "w"), indent=2)   # latest
    with open(os.path.join(RUNS, f"run_{stamp}.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(loglines))
    return status

def main():
    force = "--force" in sys.argv
    start = dt.datetime.now()
    stamp = start.strftime("%Y-%m-%d_%H-%M-%S")
    log = []
    def L(s): log.append(str(s)); print(s)

    L(f"================ pdufa.bio run {stamp} (local time) ================")
    if not is_trading_day(start.date()) and not force:
        L("Not a trading day (weekend/holiday) — skipping. Use --force to override.")
        write_status(start, "skipped", {}, log, stamp); return

    status = {}

    # 1) CRAWL ------------------------------------------------------------------
    L("[1/3] crawling all sources ...")
    ok, out = run_stage("crawl", [PY, CRAWLER, "--tickers", UNIVERSE, "--bpc", BPC,
                                  "--fmp", "--options", "--out", OUTDIR])
    status["crawl"] = "ok" if ok else "FAILED"
    L(out)
    if not ok:
        L(">> Crawl FAILED — leaving previous data unchanged (stale-but-known beats half-written).")
        alert(f"pdufa.bio crawl FAILED at {stamp}. Data was NOT updated — check runs/run_{stamp}.log")
        write_status(start, "crawl_failed", status, log, stamp); return

    # 2) FRESHNESS GUARD --------------------------------------------------------
    L("[2/3] freshness guard ...")
    ok, out = run_stage("freshness", [PY, FRESHNESS, PUBLIC_CSV])
    status["freshness"] = "ok" if ok else "FAILED"
    status["stale_financials"] = grep_num(out, r"STALE financials[^:]*:\s*(\d+)")
    L(out)

    # 3) INTEGRITY AUDIT --------------------------------------------------------
    L("[3/3] integrity audit ...")
    ok, out = run_stage("audit", [PY, AUDIT, PUBLIC_CSV])
    status["audit"] = "ok" if ok else "FAILED"
    status["integrity_score"] = grep_num(out, r"integrity score:\s*([\d.]+)", float)
    status["blockers"] = grep_num(out, r"(\d+)\s*HIGH")
    status["publish_ready"] = "PUBLISH-READY" in out
    L(out)

    # VERDICT + ALERT -----------------------------------------------------------
    problems = []
    if status.get("blockers"): problems.append(f"{status['blockers']} blocker(s)")
    if status.get("stale_financials"): problems.append(f"{status['stale_financials']} stale financials")
    if status["freshness"] != "ok" or status["audit"] != "ok": problems.append("a stage failed")
    if not status.get("publish_ready", False) or problems:
        alert(f"pdufa.bio {stamp}: score {status.get('integrity_score')}, " + ", ".join(problems or ["not publish-ready"]) + " — review before publish.")
    else:
        L(">> publish-ready, no problems flagged.")

    final = write_status(start, "ok", status, log, stamp)
    L("================ done: " + json.dumps({k: final[k] for k in ('integrity_score','blockers','stale_financials','publish_ready') if k in final}) + " ================")

if __name__ == "__main__":
    main()
