# -*- coding: utf-8 -*-
"""sls_coc_baserate.py -- measure how often a biotech change-of-control severance amendment is
actually followed by the company disappearing (acquisition/going-private/delisting).

Retail read SELLAS's June 24 2026 Item 5.02 amendment as "deal prep." That is a testable claim, and
the honest way to test it is a BASE RATE, not anecdotes: how many comparable biotechs file the same
kind of amendment in a year, and what share of them stop trading independently afterwards?

Method
  1. EDGAR full-text search 8-K filings for change-of-control severance language over a window.
  2. Keep pharma/biotech filers only (SIC 2834 pharmaceutical, 2836 biological products,
     8731 commercial physical & biological research).
  3. Deduplicate to one row per company (earliest qualifying filing).
  4. For each ticker, ask the market-data API whether it still returns a live quote. A ticker that no
     longer quotes is a PROXY for "no longer independent" -- acquisition, going-private, or delisting.

Honest limits (stated on the page too): a dead ticker is NOT proof of acquisition -- bankruptcy,
reverse merger, ticker change and exchange delisting all produce the same signature, so this number
is an UPPER BOUND on the acquisition rate, not the acquisition rate itself. It is still the right
order-of-magnitude answer to "does this filing mean a buyout is coming?"

    python sls_coc_baserate.py [--days 365]
"""
import argparse, json, os, re, sys, time
import datetime as dt
import urllib.parse, urllib.request, urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.environ.get("SEC_USER_AGENT", "David Moody rockyshoals@gmail.com")
FTS = "https://efts.sec.gov/LATEST/search-index"
TODAY = dt.date.today()
BIO_SIC = {"2834", "2836", "8731"}
PHRASES = [
    "severance and change of control letter agreement",
    "change of control severance agreement",
    "change in control severance agreement",
    "amended and restated severance and change of control",
    "severance and change in control agreement",
    "change in control severance benefits",
    "change of control severance benefits",
    "executive severance and change in control",
    "executive severance plan",
    "change in control and severance",
    "change of control and severance",
    "severance and change of control agreement",
]
TICK = re.compile(r'\(([A-Z][A-Z.\-]{0,5})\)')


def load_key():
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"), os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ.get("FMP_API_KEY")


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(min(2 ** i, 15)); continue
            return None
        except Exception:
            time.sleep(0.6 * (i + 1))
    return None


def fts(phrase, start, end):
    q = urllib.parse.urlencode({"q": f'"{phrase}"', "startdt": start, "enddt": end, "forms": "8-K"})
    raw = get(f"{FTS}?{q}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=365)
    a = ap.parse_args()
    key = load_key()

    start_win = TODAY - dt.timedelta(days=a.days)
    print("=" * 96)
    print(f"  CHANGE-OF-CONTROL AMENDMENT BASE RATE  |  8-K filings {start_win} .. {TODAY}")
    print("  biotech/pharma filers only (SIC 2834 / 2836 / 8731)")
    print("=" * 96)

    firms, calls, all_hits, bio_hits = {}, 0, 0, 0
    step = 30
    i = 0
    slices = []
    while i < a.days:
        b = TODAY - dt.timedelta(days=min(i + step, a.days))
        e = TODAY - dt.timedelta(days=i)
        slices.append((b.isoformat(), e.isoformat()))
        i += step

    for ph in PHRASES:
        for (s, e) in slices:
            j = fts(ph, s, e)
            calls += 1
            if not j:
                continue
            for h in (j.get("hits", {}) or {}).get("hits", []) or []:
                src = h.get("_source", {}) or {}
                all_hits += 1
                sics = set(str(x) for x in (src.get("sics") or []))
                if not (sics & BIO_SIC):
                    continue
                bio_hits += 1
                names = " ".join(src.get("display_names", []) or [])
                mt = TICK.search(names)
                if not mt:
                    continue
                tk = mt.group(1)
                fd = src.get("file_date", "")
                if tk not in firms or fd < firms[tk]["filed"]:
                    firms[tk] = {"filed": fd, "name": names.split("(")[0].strip()}
            time.sleep(0.11)

    print(f"  {calls} full-text queries -> {all_hits} total 8-K hits, {bio_hits} from biotech/pharma "
          f"filers -> {len(firms)} distinct biotech/pharma companies\n")

    # Is the ticker still trading? (proxy for "still independent")
    alive, dead, unknown = [], [], []
    if key:
        tks = sorted(firms)
        for n, tk in enumerate(tks):
            raw = get(f"https://financialmodelingprep.com/stable/quote?symbol={tk}&apikey={key}")
            ok = None
            if raw:
                try:
                    d = json.loads(raw)
                    ok = bool(d) and isinstance(d, list) and d and d[0].get("price") is not None
                except Exception:
                    ok = None
            (alive if ok else (dead if ok is False else unknown)).append(tk)
            time.sleep(0.12)
            if (n + 1) % 25 == 0:
                print(f"    quote-check {n+1}/{len(tks)}")
    else:
        print("  (no FMP_API_KEY -> skipping the still-trading check)")

    tot = len(alive) + len(dead)
    print("\n" + "=" * 96)
    print("  RESULT")
    print("=" * 96)
    print(f"  biotech/pharma companies filing a comparable CoC amendment : {len(firms)}")
    print(f"  still quoting today (independent)                          : {len(alive)}")
    print(f"  no longer quoting (acquired / private / delisted)          : {len(dead)}")
    if tot:
        print(f"  -> upper-bound 'no longer independent' rate                : {100*len(dead)/tot:.1f}%")
    if unknown:
        print(f"  indeterminate quote lookups                               : {len(unknown)}")
    print("\n  A dead ticker is an UPPER BOUND on acquisition: bankruptcy, reverse merger, ticker")
    print("  change and delisting produce the same signature. Not investment advice.")

    json.dump({"window_days": a.days, "as_of": TODAY.isoformat(), "firms": firms,
               "alive": alive, "dead": dead, "unknown": unknown},
              open(os.path.join(HERE, "_sls_coc_baserate.json"), "w"), indent=1)
    print(f"\n  wrote _sls_coc_baserate.json")


if __name__ == "__main__":
    main()
