# -*- coding: utf-8 -*-
"""bpc_compare.py -- live head-to-head against BioPharmCatalyst's API feed.

WHAT THIS IS FOR
BPC is the vendor whose spreadsheet we have been diffing by hand (compare_vs_bpc.py, run off
manual bpc_data/*.xlsx downloads). The API key makes that check live and daily.

WHAT THE KEY ACTUALLY BUYS (measured 2026-08-22, not assumed)
The /api/fda-calendar endpoint returns TEN rows and ignores every paging or filter parameter
tried -- per_page, limit, page, page_size, count, all, start_date/end_date, date_from/date_to,
stage, simplified_stage, fda_status_label. The response says last_page 1, total 10. So this is
a rolling "next ten catalysts" feed, not the full calendar. That is enough for the check that
matters most -- the most imminent events, where a wrong date is most costly -- but it CANNOT
answer "what does BPC have that we are missing" across the full calendar. This file says so
rather than implying wider coverage than the plan gives.

WHAT IT REPORTS
  AGREE      same ticker + drug, same date
  CONFLICT   same ticker + drug, DIFFERENT date -- verify against the primary source; our date
             carries a source_url, theirs does not
  MISSING    BPC lists it, we have no matching event -- a candidate gap to source independently
Their stage labels cover phase readouts and conference presentations as well as PDUFAs, so a
"missing" row is often a readout we track under a different shape; each is shown with enough
context to judge rather than auto-filed.

    python bpc_compare.py [--json out.json]
"""
import argparse, datetime as dt, json, os, re, sys, urllib.error, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
API = "https://www.biopharmcatalyst.com/api/fda-calendar"


def load_key():
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"),
              os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ.get("BPC_API_KEY")


def fetch(key):
    req = urllib.request.Request(API, headers={
        "X-API-KEY": key, "Accept": "application/json",
        "User-Agent": "pdufa.bio research rockyshoals@gmail.com"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.loads(r.read().decode("utf-8", "replace"))
    d = body.get("data", body)
    return (d.get("data", []) if isinstance(d, dict) else d), d


STOP = {"phase", "trial", "study", "readout", "data", "results", "topline", "presentation",
        "combination", "therapy", "injection", "tablets", "solution", "with", "plus"}


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]{4,}", str(s or "").lower()) if w not in STOP}


def load_ours():
    src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
               errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    key = load_key()
    if not key:
        print("SKIP: BPC_API_KEY not found in .env_master")
        return 0
    try:
        rows, meta = fetch(key)
    except urllib.error.HTTPError as e:
        print(f"SKIP: BPC API {e.code} -- {e.read(120).decode('utf-8','replace')[:100]}")
        return 0
    except Exception as e:
        print(f"SKIP: BPC API unreachable ({type(e).__name__})")
        return 0

    ours = load_ours()
    by_tk = {}
    for r in ours:
        by_tk.setdefault(str(r.get("t", "")).upper(), []).append(r)

    print("=" * 94)
    print(f"  BPC LIVE FEED vs OUR DATASET  |  {dt.date.today().isoformat()}")
    print(f"  feed returns {len(rows)} row(s) "
          f"(plan cap: total={meta.get('total')}, last_page={meta.get('last_page')}) "
          f"-- a rolling window, NOT the full calendar")
    print("=" * 94)

    agree, conflict, missing, other = [], [], [], []
    for b in rows:
        tk = str(b.get("company_ticker", "")).upper()
        drug = b.get("drug_name") or ""
        bdate = str(b.get("catalyst_date") or "")
        stage = b.get("next_catalyst_label") or b.get("label") or ""
        # Pick the BEST candidate, not the first. Sponsors carry several events for one drug --
        # CAPR has an AdComm AND a PDUFA for deramiocel, JAZZ a readout AND a PDUFA for Ziihera --
        # and taking the first drug-name hit reported both as "date conflicts" when we held the
        # matching row all along. Rank: same date beats a near date; a drug-name match beats a
        # date-only pairing.
        cands = by_tk.get(tk, [])
        dt_ = toks(drug)

        def rank(c):
            same_drug = bool(dt_ & toks(c.get("name")))
            cd = str(c.get("d", ""))
            try:
                gap = abs((dt.date.fromisoformat(cd) - dt.date.fromisoformat(bdate)).days)
            except Exception:
                gap = 9999
            return (0 if same_drug else 1, gap)

        scored = sorted((c for c in cands if (dt_ & toks(c.get("name")))
                         or str(c.get("d", "")) == bdate), key=rank)
        hit = scored[0] if scored else None
        rec = {"ticker": tk, "drug": drug, "bpc_date": bdate, "stage": stage,
               "bpc_note": (b.get("note") or "")[:160], "nct": b.get("clinical_trial_id")}
        if hit is None:
            missing.append(rec)
        else:
            rec["our_date"] = str(hit.get("d", ""))
            rec["our_name"] = hit.get("name")
            rec["our_type"] = hit.get("type")
            rec["our_status"] = hit.get("st")
            rec["our_precision"] = hit.get("dp")
            # A BPC "Conference Presentation" and our PDUFA for the same drug are DIFFERENT
            # events, not disagreeing dates. Only compare like with like.
            bpc_is_reg = "regulatory" in str(stage).lower() or "pdufa" in str(stage).lower()
            ours_is_reg = str(hit.get("type", "")).upper() == "PDUFA"
            if rec["our_date"] == bdate:
                agree.append(rec)
            elif bpc_is_reg != ours_is_reg:
                rec["why"] = f"different event types (BPC: {stage}; ours: {hit.get('type')})"
                other.append(rec)
            else:
                conflict.append(rec)

    def show(title, items, extra=lambda r: ""):
        print(f"\n{title}: {len(items)}")
        for r in items:
            print(f"   {r['ticker']:<6} {r['bpc_date']}  {str(r['drug'])[:34]:<34} "
                  f"{str(r['stage'])[:26]:<26}{extra(r)}")

    show("AGREE (same drug, same date)", agree,
         lambda r: f"  [{r['our_type']}/{r['our_status']}]")
    show("DATE CONFLICT -- verify against the primary source", conflict,
         lambda r: f"  ours={r['our_date']} ({r['our_type']}, {r['our_precision']})")
    show("SAME DRUG, DIFFERENT EVENT TYPE (not a disagreement)", other,
         lambda r: f"  ours={r['our_date']} ({r['our_type']})")
    show("BPC LISTS, WE HAVE NO MATCH (candidate gaps)", missing,
         lambda r: f"  {str(r['nct'] or '')[:12]}")

    if conflict:
        print("\n  Conflicts matter most: our dates carry a source_url, BPC's do not. Check the")
        print("  company release / SEC filing / FDA notice and fix whichever side is wrong.")
    print("\n  Coverage caveat: this feed is capped at 10 forward rows, so 'we have it and BPC")
    print("  does not' CANNOT be measured here -- only the reverse. Not investment advice.")

    if a.json:
        json.dump({"as_of": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "feed_rows": len(rows), "agree": agree, "conflict": conflict,
                   "missing": missing, "other": other}, open(a.json, "w", encoding="utf-8"), indent=1)
        print(f"\n  wrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
