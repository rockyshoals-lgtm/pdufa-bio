#!/usr/bin/env python3
"""
conference_miner.py — WHO IS PRESENTING AT A DATED CONGRESS? Local, EDGAR-based, ~2-4 min.

WHY THIS EXISTS (2026-08-29)
----------------------------
Conference presentations are the single strongest catalyst class we track: abstract acceptance
is implicit peer review plus company self-selection (90.2% positive vs 76.7% baseline in the
March study). And they are the main source of GOLD dates — a congress agenda is published,
public, and checkable, unlike "2H 2026" guidance prose.

Until today our only source for presenter rows was BiopharmaCatalyst's export — a file David
downloads by hand, currently a week stale. This miner replaces that dependency with EDGAR:
companies ANNOUNCE their presentations in 8-K/6-K press releases weeks ahead ("to present
Phase 2 data at ESMO 2026"). Same two-stage architecture that works in readout_scan:

  stage 1  EDGAR FTS, short adjacency-safe fragments, time-sliced newest-first
  stage 2  fetch the doc, run conference_presentations.extract() on the full text —
           the alias table finds the congress, conf_registry.json supplies the DATE
           (the filing almost never states it), pres-type comes from the prose

HONESTY RULES (inherited, non-negotiable)
  - a date only earns precision "day" when the registry has OBSERVED that year's congress
    or can project it confidently; date_basis says which. We never fabricate a date.
  - past presentations are dropped by extract()'s backstop: a future date is only legitimate
    when the filing says the company WILL present.
  - facts only: conference, date, oral/poster, abstract number. No scores. The Conference
    Overlay v1.0 weighting scheme is RETIRED/REFUTED — do not reintroduce it here.

OUTPUT  conference_presenters.csv — one row per (ticker, conference, year):
  ticker, conference, catalyst_date, date_precision, date_basis, pres_type, abstract,
  days_to, filed, form, company, phrases, url

Downstream: readout_gold_dates.py ingests this and tiers observed-day rows GOLD
(EDGAR/conference:XXXX) — the same trust class as BPC's conference column, but from our
own pipeline, fresh every run. Not investment advice.
"""
import collections
import csv
import datetime as dt
import os
import re
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Reuse the proven EDGAR machinery (rate-limited _get, sliced walk) and the proven
# conference brain. Import, don't copy — one implementation, one set of bugfixes.
from readout_scan import ua, _get, walk, ARCHIVES, BIO_SIC          # noqa: E402
import conference_presentations as CP                                # noqa: E402

# ---------------------------------------------------------------------------- phrases
# Short, adjacency-safe fragments (the AMLX/KLRS lesson: EDGAR FTS matches quoted phrases
# by ADJACENCY — "to present data at ESMO" does not match "to present at"). These are the
# universal stubs companies actually use in presentation PRs.
PRESENT_PHRASES = [
    "to present at",                 # broad but forms-filtered to 8-K/6-K
    "will present at",
    "to be presented at",
    "will be presented at",
    "oral presentation at",
    "poster presentation at",
    "late-breaking",
    "accepted for presentation",
    "abstract accepted",
    "presentations at the",
    "to present data",
    "poster presentations at",
    "upcoming medical conferences",
]

TAG_RX = re.compile(r"<[^>]+>")
WS_RX = re.compile(r"\s+")


def doc_text(v, agent):
    cik = str(int(v["cik"]))
    url = f"{ARCHIVES}/{cik}/{v['accn'].replace('-', '')}/{v['doc']}"
    raw = _get(url, agent)
    if not raw:
        return "", url
    try:
        t = raw.decode("utf-8", errors="replace")
    except Exception:
        return "", url
    return WS_RX.sub(" ", TAG_RX.sub(" ", t)), url


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60,
                    help="lookback window (presentation PRs land 2-8 weeks ahead)")
    ap.add_argument("--step", type=int, default=7)
    ap.add_argument("--max-fetch", type=int, default=120,
                    help="doc fetch cap; bio-SIC + armed names are fetched first")
    ap.add_argument("--out", default="conference_presenters.csv")
    a = ap.parse_args()
    agent = ua()
    today = dt.date.today()
    registry = CP.load_registry()

    print("=" * 92)
    print(f"  CONFERENCE PRESENTER MINER — last {a.days}d in {a.step}d slices")
    print("=" * 92)
    print(f"  {len(PRESENT_PHRASES)} presenter phrases; date comes from conf_registry.json "
          f"({sum(1 for v in registry.values() if '2026' in (v.get('dates') or {}))} "
          f"congresses with an observed 2026 date)\n")

    hits, calls = walk(PRESENT_PHRASES, a.days, a.step, agent, "CONF")
    print(f"\n  {len(hits)} candidate filings from {calls} FTS calls")

    # armed names first, then bio SIC, then the rest — the fetch cap should never starve
    # the names we already care about.
    try:
        import json
        armed = set((json.load(open(os.path.join(HERE, "Momentum Scanner",
                                                 "armed_watchlist.json"),
                                    encoding="utf-8", errors="replace"))
                     .get("armed") or {}).keys())
    except Exception:
        armed = set()

    def prio(v):
        return (0 if v["ticker"] in armed else
                1 if any(s in BIO_SIC for s in v["sics"]) else 2, v["filed"])

    ordered = sorted(hits.values(), key=prio)[:a.max_fetch]
    print(f"  fetching {len(ordered)} docs "
          f"({sum(1 for v in ordered if v['ticker'] in armed)} armed, "
          f"{sum(1 for v in ordered if any(s in BIO_SIC for s in v['sics']))} bio-SIC) ...")

    best = {}                       # (ticker, conference, year) -> row
    fetched = 0
    for v in ordered:
        text, url = doc_text(v, agent)
        fetched += 1
        time.sleep(0.11)
        if not text:
            continue
        try:
            filed_dt = dt.date.fromisoformat(v["filed"])
        except Exception:
            filed_dt = None
        ev = CP.extract(text, filed_dt=filed_dt, registry=registry)
        if not ev:
            continue
        iso = ev["catalyst_date"]
        # forward only: this file feeds a PRELOAD calendar, not a history
        chk = iso if len(iso) == 10 else iso + "-28"
        try:
            if dt.date.fromisoformat(chk) < today:
                continue
        except Exception:
            continue
        k = (v["ticker"], ev["conference"], ev["year"])
        row = {
            "ticker": v["ticker"], "conference": ev["conference"],
            "catalyst_date": iso, "date_precision": ev["date_precision"],
            "date_basis": ev["date_basis"], "pres_type": ev.get("pres_type") or "",
            "abstract": ev.get("abstract") or "",
            "days_to": (dt.date.fromisoformat(chk) - today).days,
            "filed": v["filed"], "form": v["form"], "company": v["company"],
            "phrases": " | ".join(sorted(v["phrases"])), "url": url,
        }
        # keep the NEWEST filing per event; oral beats poster beats unknown on a tie,
        # because the more specific row is the more useful one
        old = best.get(k)
        rank = {"oral": 0, "late-breaking": 0, "poster": 1}.get(row["pres_type"], 2)
        orank = {"oral": 0, "late-breaking": 0, "poster": 1}.get((old or {}).get("pres_type", ""), 2)
        if old is None or (row["filed"], -rank) > (old["filed"], -orank):
            best[k] = row
        if fetched % 25 == 0:
            print(f"    {fetched}/{len(ordered)} fetched, {len(best)} presenter events")

    out = sorted(best.values(), key=lambda r: (r["catalyst_date"], r["ticker"]))
    dst = os.path.join(HERE, a.out)
    cols = ["ticker", "conference", "catalyst_date", "date_precision", "date_basis",
            "pres_type", "abstract", "days_to", "filed", "form", "company", "phrases", "url"]
    # lock-resistant write (the Excel lesson: last night's whole chain wrote to _new files
    # because the .bat had auto-opened the CSVs)
    tmp = dst + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    try:
        os.replace(tmp, dst)
    except PermissionError:
        dst = dst.replace(".csv", "_new.csv")
        os.replace(tmp, dst)
        print(f"  [warn] {a.out} is LOCKED (close it) -> wrote {os.path.basename(dst)}")

    pc = collections.Counter(r["date_precision"] for r in out)
    bc = collections.Counter(r["date_basis"] for r in out)
    tc = collections.Counter(r["pres_type"] or "(unknown)" for r in out)
    print(f"\n  {len(out)} upcoming presenter events -> {os.path.basename(dst)}")
    print(f"  precision: {dict(pc)}   basis: {dict(bc)}   type: {dict(tc)}")

    print("\n" + "=" * 92)
    print("  UPCOMING PRESENTERS (next 90 days — an OBSERVED day-precision row is a GOLD date)")
    print("=" * 92)
    print(f"  {'date':<12}{'in':>4}  {'tkr':<7}{'conf':<10}{'type':<14}{'basis':<11}company")
    for r in out:
        if r["days_to"] <= 90:
            print(f"  {r['catalyst_date']:<12}{r['days_to']:>3}d  {r['ticker']:<7}"
                  f"{r['conference']:<10}{(r['pres_type'] or '-'):<14}"
                  f"{r['date_basis']:<11}{r['company'][:34]}")
    print("\n  Dates come from the congress agenda (registry), never from the filing prose.")
    print("  Informational only — not investment advice.")


if __name__ == "__main__":
    main()
