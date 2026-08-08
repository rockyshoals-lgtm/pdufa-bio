#!/usr/bin/env python3
"""
pdufa.bio — pre-publication data-integrity audit.

Runs after a crawl and grades the dataset against the classes of error that
quietly destroy trust: stale calendars, unsourced catalysts, impossible
financials, self-contradictions in our own dilution logic, and conflicts.

It does not "fix" anything silently. It produces a severity-ranked report and
a publish-readiness verdict (HIGH issues are launch blockers) so a human can
decide. Corrections already made by the crawler are surfaced as a transparency
log — the same spirit as showing your work.

Usage:
    python data_audit.py [catalysts_public.csv]   ->  writes integrity_report.json
"""
import sys, json, datetime as dt
import pandas as pd, numpy as np

TODAY = dt.date(2026, 6, 1)                       # crawl date; swap for dt.date.today() in prod
HORIZON_DAYS = 730                                # nothing should sit further out than this
FRESH_HOURS = 36                                  # last_checked SLA
PATH = sys.argv[1] if len(sys.argv) > 1 else "catalysts_public.csv"

d = pd.read_csv(PATH, dtype=str)
def f(x):
    try: return float(x)
    except: return np.nan
def date(x):
    try: return dt.date.fromisoformat(str(x)[:10])
    except: return None
def has(x):
    return not (x is None or (isinstance(x, float) and np.isnan(x)) or str(x).strip() in ("", "nan", "None"))

findings = []   # each: dict(check, severity, title, rows=[{ticker,date,detail}])
def add(check, severity, title, rows):
    if rows: findings.append(dict(check=check, severity=severity, title=title, rows=rows))

# ---- HIGH: decisions that have already passed but still sit on the calendar ----
rows = []
for _, r in d.iterrows():
    dd = date(r["catalyst_date"])
    if r["date_precision"] == "day" and dd and dd < TODAY and r["catalyst_type"] in ("PDUFA", "AdComm", "Submission"):
        rows.append(dict(ticker=r["ticker"], date=r["catalyst_date"],
                         detail=f"{r['catalyst_type']} date passed {(TODAY-dd).days}d ago — must be resolved/removed or its outcome captured"))
add("past_due_decision", "HIGH", "Day-precision decision dates that have already passed", rows)

# ---- HIGH: a PDUFA/AdComm still listed though an FDA outcome (approval/CRL) is on record ----
outc = d[d["catalyst_type"].isin(["Approval", "CRL"])][["ticker", "catalyst_type", "catalyst_date"]]
outc_tk = set(outc["ticker"])
rows = []
for _, r in d.iterrows():
    if r["catalyst_type"] in ("PDUFA", "AdComm") and r["ticker"] in outc_tk:
        o = outc[outc["ticker"] == r["ticker"]].iloc[0]
        rows.append(dict(ticker=r["ticker"], date=r["catalyst_date"],
                         detail=f"{r['catalyst_type']} still listed but {o['catalyst_type']} on record ({o['catalyst_date']}) — resolve or remove"))
add("outcome_on_record", "HIGH", "Catalyst still listed despite a known FDA outcome", rows)

# ---- HIGH: market cap below cash on hand — financially implausible, smells stale ----
rows = []
for _, r in d.iterrows():
    mc, cash = f(r["market_cap"]), f(r["cash"])
    if mc > 0 and cash > 0 and mc < cash:
        rows.append(dict(ticker=r["ticker"], date=r["catalyst_date"],
                         detail=f"cap ${mc/1e6:.0f}M < cash ${cash/1e6:.0f}M — verify: genuine sub-cash valuation or stale share count"))
add("below_cash", "INFO", "Trading below cash on hand — surfaced signal (real sub-cash vs stale cap)", rows)

# ---- HIGH: a catalyst with no primary source is not publishable ----
rows = []
for _, r in d.iterrows():
    if not has(r.get("source_url")) and not has(r.get("urls")):
        rows.append(dict(ticker=r["ticker"], date=r["catalyst_date"],
                         detail=f"{r['catalyst_type']} has no source_url — unsourced, cannot publish under provenance rule"))
add("missing_source", "HIGH", "Catalysts with no primary-source link", rows)

# ---- MED: same ticker + type carrying conflicting dates ----
d["_drug"] = d["drug"].fillna("").astype(str).str.strip()
rows = []
for (tk, ty, dg), g in d[d["_drug"] != ""].groupby(["ticker", "catalyst_type", "_drug"]):
    ds = sorted(set(x for x in g["catalyst_date"].dropna().astype(str) if x.strip()))
    if len(ds) > 1:
        rows.append(dict(ticker=tk, date=" / ".join(ds),
                         detail=f"{ty} for {dg}: {len(ds)} different dates — true conflict, reconcile"))
add("date_conflict", "MED", "Same drug + catalyst type carrying conflicting dates", rows)

# ---- MED: our own dilution logic contradicting itself ----
rows = []
for _, r in d.iterrows():
    re_, dd = date(r.get("runway_end")), date(r["catalyst_date"])
    if re_ and dd and re_ < dd and not has(r.get("dilution_risk")):
        rows.append(dict(ticker=r["ticker"], date=r["catalyst_date"],
                         detail=f"runway ends {r['runway_end']} before catalyst {r['catalyst_date']} but no dilution flag set — should be HIGH"))
add("dilution_inconsistent", "MED", "Runway ends before catalyst yet no dilution flag", rows)

# ---- MED: warrant / non-common tickers riding along ----
rows = [dict(ticker=r["ticker"], date=r["catalyst_date"], detail=str(r["data_flags"]))
        for _, r in d.iterrows() if has(r.get("data_flags")) and "warrant" in str(r["data_flags"]).lower()]
add("warrant_ticker", "MED", "Warrant / non-common tickers flagged", rows)

# ---- LOW: dates absurdly far beyond the horizon ----
rows = []
for _, r in d.iterrows():
    dd = date(r["catalyst_date"])
    if dd and (dd - TODAY).days > HORIZON_DAYS:
        rows.append(dict(ticker=r["ticker"], date=r["catalyst_date"], detail=f"{(dd-TODAY).days}d out — beyond {HORIZON_DAYS}d horizon, verify it's real"))
add("beyond_horizon", "LOW", "Catalyst dates beyond the coverage horizon", rows)

# ---- LOW: low-confidence rows the reader should treat gently ----
rows = [dict(ticker=r["ticker"], date=r["catalyst_date"], detail=f"confidence {r['confidence']} ({r['catalyst_type']})")
        for _, r in d.iterrows() if 0 < f(r.get("confidence")) < 0.4]
add("low_confidence", "LOW", "Low-confidence catalysts (conf < 0.50)", rows)

# ---- INFO: corrections the crawler already made — the transparency log ----
corr = [dict(ticker=r["ticker"], date=r["catalyst_date"], detail=str(r["data_flags"]))
        for _, r in d.iterrows() if has(r.get("data_flags")) and "corrected" in str(r["data_flags"]).lower()]
corr += [dict(ticker=r["ticker"], date=r["catalyst_date"], detail=str(r.get("change_detail") or "correction"))
         for _, r in d.iterrows() if str(r.get("change_type")) == "correction"]

# ---- freshness ----
stale_fresh = False
try:
    lc = pd.to_datetime(d["last_checked"].dropna().iloc[0])
    now_utc = pd.Timestamp.now("UTC")
    age_h = (now_utc - (lc.tz_localize("UTC") if lc.tzinfo is None else lc)).total_seconds()/3600
    stale_fresh = age_h > FRESH_HOURS
except Exception:
    age_h = None

# ---- aggregate ----
sev_counts = {"HIGH": 0, "MED": 0, "LOW": 0, "INFO": 0}
for fnd in findings:
    sev_counts[fnd["severity"]] += len(fnd["rows"])
blockers = sev_counts["HIGH"]
score = max(0, 100 - 8*sev_counts["HIGH"] - 2*sev_counts["MED"] - 0.5*sev_counts["LOW"])  # INFO does not penalize

report = dict(
    generated=dt.datetime.now(dt.timezone.utc).isoformat(),
    dataset=PATH, rows=len(d), tickers=int(d["ticker"].nunique()),
    integrity_score=round(score, 1),
    publish_ready=(blockers == 0),
    blockers=blockers,
    severity_counts=sev_counts,
    data_age_hours=(round(age_h,1) if age_h is not None else None),
    freshness_ok=(not stale_fresh),
    corrections_this_run=corr,
    findings=findings,
)
out = PATH.rsplit("/",1)[0]+"/integrity_report.json" if "/" in PATH else "integrity_report.json"
json.dump(report, open(out, "w"), indent=2)

# ---- console summary ----
print(f"\n{'='*64}\n  DATA-INTEGRITY AUDIT — {PATH}\n{'='*64}")
print(f"  {len(d)} rows / {d['ticker'].nunique()} tickers   integrity score: {score:.0f}/100")
print(f"  verdict: {'PUBLISH-READY ✓' if blockers==0 else f'NOT READY — {blockers} blocker(s) to clear'}")
print(f"  data age: {age_h:.1f}h ({'fresh' if not stale_fresh else 'STALE > %dh'%FRESH_HOURS})" if age_h is not None else "  data age: n/a")
print(f"  issues: {sev_counts['HIGH']} HIGH · {sev_counts['MED']} MED · {sev_counts['LOW']} LOW   ·   {sev_counts['INFO']} INFO signals")
if corr: print(f"  corrections logged this run: {len(corr)}")
for fnd in sorted(findings, key=lambda x: {"HIGH":0,"MED":1,"LOW":2,"INFO":3}[x["severity"]]):
    print(f"\n  [{fnd['severity']}] {fnd['title']}  ({len(fnd['rows'])})")
    for row in fnd["rows"][:6]:
        print(f"      {row['ticker']:7s} {str(row['date'])[:21]:21s} {row['detail']}")
    if len(fnd["rows"]) > 6: print(f"      … +{len(fnd['rows'])-6} more (see integrity_report.json)")
print(f"\n  full report -> {out}\n")
