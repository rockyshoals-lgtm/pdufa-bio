# -*- coding: utf-8 -*-
"""add_t120_baseline.py -- compute a uniform T-120 baseline for every event in the run-up study.

Why: /runup-by-year was historically produced by a separate pipeline that measured run-up from a
T-120 baseline. That pipeline's source files died in March 2026, so the page was rebuilt off the
master study, which stores a T-90 baseline. Same site, two different baselines. This makes T-120 the
single baseline everywhere by computing it directly from Polygon daily closes for all events.

Adds four columns to pdufa_runup_bifrost_v2.csv, all FRACTIONS (matching the existing T-A_T-B
convention in that file):

    T-120_T-1     return from 120 trading days before eve -> eve close (the full pre-decision drift)
    T-120_T-7     same, measured to 7 sessions before the decision
    T-120_T-3     same, measured to 3 sessions before the decision
    T-120_peak    return from the T-120 close to the HIGHEST close anywhere in T-120..T-1
                  (how much was on the table for someone who sold at the top of the run-up)

"eve" is the last trading session strictly before the decision date, identical to how every other
column in this file is computed. A row is left blank rather than filled with a partial window: an
event without 120 sessions of prior history is genuinely unmeasurable on this basis, and writing a
short-window number would silently bias the aggregates toward newly-listed companies.

Bars are cached in runup_t120_cache.json so reruns cost nothing.

    python add_t120_baseline.py [--dry-run] [--limit N] [--workers N]
"""
import argparse, csv, json, os, sys, threading, time
import datetime as dt
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
CACHE = os.path.join(HERE, "runup_t120_cache.json")
# Small, committed: keys we have already proven cannot be measured (company not listed long
# enough). Without it CI would re-query Polygon for the same 71 dead ends every single night.
SHORT = os.path.join(HERE, "runup_t120_short.json")

NEW_COLS = ["T-120_T-1", "T-120_T-7", "T-120_T-3", "T-120_peak"]


def load_key():
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"), os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ.get("POLYGON_API_KEY")


KEY = load_key()
_lock = threading.Lock()


def bars(t, start, end):
    """[(date, close)] ascending, split-adjusted."""
    url = (f"https://api.polygon.io/v2/aggs/ticker/{t}/range/1/day/{start}/{end}"
           f"?adjusted=true&sort=asc&limit=50000&apiKey={KEY}")
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                rows = (json.loads(r.read().decode()) or {}).get("results") or []
                return [[dt.datetime.fromtimestamp(x["t"] / 1000, dt.timezone.utc).date().isoformat(),
                         x["c"]] for x in rows if x.get("c")]
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(1.5 * (i + 1)); continue
            return []
        except Exception:
            time.sleep(0.8)
    return []


def compute(b, decision_date):
    """-> dict of the four fractions, or {} if the window is not fully available."""
    if not b:
        return {}
    dates = [x[0] for x in b]
    closes = [x[1] for x in b]
    eve_i = None
    for i, dd in enumerate(dates):
        if dd < decision_date:
            eve_i = i
        else:
            break
    if eve_i is None or eve_i < 120:
        return {}
    base = closes[eve_i - 120]
    if not base:
        return {}
    out = {}
    for lbl, back in (("T-120_T-1", 0), ("T-120_T-7", 7), ("T-120_T-3", 3)):
        j = eve_i - back
        if j >= 0 and closes[j]:
            out[lbl] = closes[j] / base - 1
    window = [c for c in closes[eve_i - 120:eve_i + 1] if c]
    if window:
        out["T-120_peak"] = max(window) / base - 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--all", action="store_true",
                    help="recompute every row from scratch instead of only the missing ones")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")))
    cols = list(rows[0].keys())
    print(f"study rows: {len(rows):,}")

    cache = {}
    if os.path.exists(CACHE):
        try:
            cache = json.load(open(CACHE, encoding="utf-8"))
            print(f"cache: {len(cache):,} series")
        except Exception:
            cache = {}

    # Incremental by default. The bar cache is 9 MB of local convenience and is NOT committed, so
    # in CI it starts empty; refetching all 1,827 series every night would be pointless when the
    # answers are already sitting in the CSV. Only rows with no T-120 value are fetched, minus the
    # ones already proven to lack 120 sessions of history (they would be retried forever otherwise).
    short = set()
    if os.path.exists(SHORT):
        try:
            short = set(json.load(open(SHORT, encoding="utf-8")))
        except Exception:
            short = set()

    todo = []
    for r in rows:
        d = (r.get("pdufa_date") or "")[:10]
        tk = (r.get("ticker") or "").strip().upper()
        if len(d) != 10 or not tk:
            continue
        k = f"{tk}|{d}"
        if not a.all and (r.get("T-120_T-1") or "").strip():
            continue                      # already computed
        if not a.all and k in short:
            continue                      # known to lack the window; do not retry nightly
        if k not in cache:
            todo.append((tk, d, k))
    if a.limit:
        todo = todo[:a.limit]
    print(f"need bars for {len(todo):,} event(s)  "
          f"({len(short):,} known short-history, skipped)")

    done = [0]

    def save_cache():
        """Atomic: a run killed mid-write must never leave a truncated cache behind.
        (It did exactly that once -- a half-written JSON failed to parse on the next run and
        silently discarded 1,312 already-fetched series.)"""
        tmp = CACHE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        os.replace(tmp, CACHE)

    def fetch(job):
        tk, d, k = job
        pd = dt.date.fromisoformat(d)
        b = bars(tk, (pd - dt.timedelta(days=330)).isoformat(),
                 (pd + dt.timedelta(days=10)).isoformat())
        with _lock:
            cache[k] = b
            done[0] += 1
            if done[0] % 100 == 0:
                print(f"  {done[0]:,}/{len(todo):,}", flush=True)
                save_cache()          # checkpoint, so a timeout costs at most 100 fetches

    if todo:
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            list(ex.map(fetch, todo))
        save_cache()
        print(f"cached {len(cache):,} series -> {os.path.basename(CACHE)}")

    filled, missing, new = 0, 0, 0
    for r in rows:
        d = (r.get("pdufa_date") or "")[:10]
        tk = (r.get("ticker") or "").strip().upper()
        k = f"{tk}|{d}"
        had = bool((r.get("T-120_T-1") or "").strip())
        if had and not a.all:
            filled += 1
            continue                      # never recompute a value we already have
        vals = compute(cache.get(k) or [], d) if len(d) == 10 else {}
        if vals:
            filled += 1
            new += 1
            for c in NEW_COLS:
                v = vals.get(c)
                r[c] = f"{v:.6f}" if v is not None else ""
        else:
            missing += 1
            if k in cache:
                short.add(k)              # asked Polygon, window genuinely not there
            for c in NEW_COLS:
                r.setdefault(c, "")

    for c in NEW_COLS:
        if c not in cols:
            cols.append(c)

    print(f"\nT-120 present for {filled:,} events ({new:,} newly computed this run); "
          f"{missing:,} lack 120 sessions of prior history")
    if a.dry_run:
        print("DRY RUN -- csv not written."); return
    json.dump(sorted(short), open(SHORT, "w", encoding="utf-8"), indent=0)

    bak = CSVF + ".bak_t120"
    if not os.path.exists(bak):
        import shutil; shutil.copy2(CSVF, bak)
        print(f"backup -> {os.path.basename(bak)}")
    with open(CSVF, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {os.path.basename(CSVF)} ({len(rows):,} rows x {len(cols)} cols)")


if __name__ == "__main__":
    main()
