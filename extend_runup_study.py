# -*- coding: utf-8 -*-
"""extend_runup_study.py -- add every newly-decided PDUFA to the run-up dataset.

The run-up study is the site's proprietary asset: 1,705 PDUFA events with real daily price behaviour
from T-90 into the decision. It had gone stale at PDUFA date 2026-02-21 while the decisions archive
kept growing -- 122 decided PDUFAs (118 of them 2026) were missing, including every July approval.
Every decision we publish and never fold back into the study is data the moat does not compound.

This reads the decisions archive (the canonical published record), finds what the study lacks, pulls
daily bars from Polygon, and computes the same metrics with the same conventions as the existing rows:

  eve_date    last trading day strictly before the decision date
  eve_price   close on eve_date
  runup_Nd    PERCENT return from the close N trading days before eve -> eve close
  post_Nd     PERCENT return from eve close -> close N trading days after
  T-A_T-B     FRACTION return from A trading days before eve -> B trading days before eve
              (kept as a fraction because that is how the existing 1,705 rows store it)
  vol_ratio   decision-day volume / mean volume over the 30 sessions before eve

Rows are appended, never rewritten, and a row is skipped unless Polygon returns enough history to
compute it honestly -- a partial row would silently corrupt the study's aggregates.

    python extend_runup_study.py [--dry-run] [--limit N]
"""
import argparse, csv, json, os, re, sys, time
import datetime as dt
import urllib.request, urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
DECISIONS = os.path.join(SITE, "decisions", "index.html")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")


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


def bars(t, start, end):
    """[(date, close, volume)] ascending."""
    url = (f"https://api.polygon.io/v2/aggs/ticker/{t}/range/1/day/{start}/{end}"
           f"?adjusted=true&sort=asc&limit=50000&apiKey={KEY}")
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                rows = (json.loads(r.read().decode()) or {}).get("results") or []
                return [(dt.datetime.fromtimestamp(x["t"] / 1000, dt.timezone.utc).date().isoformat(),
                         x["c"], x.get("v") or 0) for x in rows if x.get("c")]
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** i); continue
            return []
        except Exception:
            time.sleep(0.8)
    return []


def mcap_tier(mcap):
    if not mcap:
        return ""
    m = float(mcap)
    if m < 50e6:
        return "Nano (<$50M)"
    if m < 300e6:
        return "Micro ($50M-$300M)"
    if m < 2e9:
        return "Small ($300M-$2B)"
    if m < 10e9:
        return "Mid ($2B-$10B)"
    return "Large (>$10B)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    existing = list(csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")))
    cols = list(existing[0].keys())
    have = {(r["ticker"], r["pdufa_date"][:10]) for r in existing}

    # canonical published decisions + their outcome
    html = open(DECISIONS, encoding="utf-8", errors="replace").read()
    dec = {}
    for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', html):
        tk, d = m.group(1), m.group(2)
        tail = html[m.end():m.end() + 260].lower()
        oc = "CRL" if ("crl" in tail or "complete response" in tail) else "APPROVAL"
        dec.setdefault((tk, d), oc)

    # drug / company / mcap context from the API dataset where we have it
    meta = {}
    try:
        src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
        arr, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
        for r in arr:
            if r.get("t"):
                meta.setdefault(r["t"], r)
    except Exception:
        pass

    todo = sorted([k for k in dec if k not in have], key=lambda x: x[1])
    if a.limit:
        todo = todo[:a.limit]
    print(f"study rows: {len(existing)}  (through {max(r['pdufa_date'][:10] for r in existing)})")
    print(f"archive decisions: {len(dec)}  |  MISSING from study: {len(todo)}")
    if not todo:
        print("nothing to add."); return

    added, skipped = [], []
    for n, (tk, d) in enumerate(todo, 1):
        pd = dt.date.fromisoformat(d)
        b = bars(tk, (pd - dt.timedelta(days=200)).isoformat(),
                 (pd + dt.timedelta(days=20)).isoformat())
        if len(b) < 95:
            skipped.append((tk, d, f"only {len(b)} bars")); continue
        dates = [x[0] for x in b]; closes = [x[1] for x in b]; vols = [x[2] for x in b]
        # eve = last session strictly before the decision date
        eve_i = None
        for i, dd in enumerate(dates):
            if dd < d:
                eve_i = i
            else:
                break
        if eve_i is None or eve_i < 92 or eve_i + 1 >= len(closes):
            skipped.append((tk, d, "insufficient window around eve")); continue
        eve_p = closes[eve_i]

        def pct(back):
            j = eve_i - back
            return (eve_p / closes[j] - 1) * 100 if j >= 0 and closes[j] else ""

        def post(fwd):
            j = eve_i + fwd
            return (closes[j] / eve_p - 1) * 100 if j < len(closes) and eve_p else ""

        def frac(a_back, b_back):
            ia, ib = eve_i - a_back, eve_i - b_back
            return (closes[ib] / closes[ia] - 1) if ia >= 0 and ib >= 0 and closes[ia] else ""

        base = [v for v in vols[max(0, eve_i - 30):eve_i] if v]
        dec_vol = vols[eve_i + 1] if eve_i + 1 < len(vols) else vols[eve_i]
        vr = (dec_vol / (sum(base) / len(base))) if base else ""

        m = meta.get(tk, {})
        row = {c: "" for c in cols}
        row.update({
            "ticker": tk, "company": m.get("company", "") or "", "asset": m.get("name", "") or "",
            "indication": ((m.get("_d") or {}).get("indication") or "") if isinstance(m.get("_d"), dict) else "",
            "pdufa_date": d, "outcome": dec[(tk, d)],
            "outcome_bin": "1" if dec[(tk, d)] == "APPROVAL" else "0",
            "eve_price": eve_p, "eve_date": dates[eve_i],
            "runup_30d": pct(30), "runup_21d": pct(21), "runup_14d": pct(14),
            "runup_7d": pct(7), "runup_5d": pct(5), "runup_3d": pct(3),
            "post_1d": post(1), "post_2d": post(2), "post_5d": post(5),
            "vol_ratio": vr,
            "mcap_tier": mcap_tier(((m.get("_d") or {}).get("market_cap_usd")) if isinstance(m.get("_d"), dict) else None),
            "cache_key": f"{tk}_{d.replace('-', '')}",
            "T-90_T-7": frac(90, 7), "T-90_T-3": frac(90, 3), "T-90_T-1": frac(90, 1),
            "T-60_T-7": frac(60, 7), "T-60_T-3": frac(60, 3), "T-60_T-1": frac(60, 1),
            "T-45_T-7": frac(45, 7), "T-45_T-3": frac(45, 3), "T-45_T-1": frac(45, 1),
            "T-25_T-7": frac(25, 7), "T-25_T-3": frac(25, 3), "T-25_T-1": frac(25, 1),
        })
        added.append(row)
        if n % 20 == 0:
            print(f"  {n}/{len(todo)}  ({len(added)} computed, {len(skipped)} skipped)")
        time.sleep(0.09)

    print(f"\ncomputed {len(added)} new rows | skipped {len(skipped)} (no usable price history)")
    for s in skipped[:12]:
        print(f"   skip {s[0]:6s} {s[1]}  {s[2]}")
    if skipped[12:]:
        print(f"   ... and {len(skipped)-12} more")
    if added:
        yr = {}
        for r in added:
            yr[r["pdufa_date"][:4]] = yr.get(r["pdufa_date"][:4], 0) + 1
        print("  new rows by year:", dict(sorted(yr.items())))
        print(f"  study would go {len(existing)} -> {len(existing)+len(added)} rows, "
              f"through {max(r['pdufa_date'] for r in added)}")

    if a.dry_run:
        print("\nDRY RUN -- not written."); return
    if not added:
        return
    import shutil
    shutil.copyfile(CSVF, CSVF + ".bak_extend")
    with open(CSVF, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        allrows = existing + added
        allrows.sort(key=lambda r: str(r.get("pdufa_date") or ""))
        w.writerows(allrows)
    print(f"\nwrote {CSVF} ({len(existing)+len(added)} rows; backup .bak_extend)")


if __name__ == "__main__":
    main()
