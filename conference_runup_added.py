# -*- coding: utf-8 -*-
"""conference_runup_added.py -- publish the red-teamed company-release conference rows BESIDE the study, not in it.

David approved adding these rows to the published study on 2026-11-27. The study page carries a rule this site wrote
after the July 2026 revert: "never change the sampling frame and the published number in the same step. If the
universe changes, publish old and new side by side with the recall figure, and say why they differ." These rows come
from a different frame (companies' own releases for tickers we track, and older presentations named in SEC filings,
which skew small-cap), so they go on the study page in their own section, with the curated headline unchanged, the
two samples side by side. No combined figure is shown: the page says a new frame does not feed the study until a
recall figure exists, and none exists for this frame yet; the section says so.

ROWS: _conference_runup_additions.json (meetings from 2026-06-05) and _conference_runup_backfill.json (earlier
meetings the study left out). Each is anchored on the presenting company's own release reporting data from the
meeting (anchor_basis) and re-checked against the current rules on every rebuild by the scripts that write them.
Only rows whose windows have closed ("complete") with all seven windows numeric are shown; a pending row joins when
its window closes, and a row held as "check" never joins. A row whose (ticker, meeting code, year) the study already
holds is left out, and so is a row whose ticker has a study row labelled UNKNOWN (meeting not verified) within
NEAR_DAYS of its anchor, since that may be the same presentation; no presentation is counted twice.

TIER: point-in-time FMP market cap on the trading day before the anchor (d_minus_1), the study's thresholds, cached in
_conference_runup_mcap.json so each row is priced once. Without an FMP key a tier stays blank and is counted as
unknown.

WRITES: pdufa_site_src/research/conference-runup/conference-runup-company-releases.csv (CC BY 4.0, one row per
presentation with its release URL) and the CSTUDYADD block on the study page, right after the CSTUDYX block.
Guard: tests/test_conference_runup_added.py.

    python conference_runup_added.py
"""
import csv
import datetime as dt
import io
import json
import os
import re
import statistics as st
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
STUDY = os.path.join(HERE, "conf_study", "conference_runup_PUBLISHED.csv")
CACHES = [os.path.join(HERE, "_conference_runup_additions.json"), os.path.join(HERE, "_conference_runup_backfill.json")]
MCAP = os.path.join(HERE, "_conference_runup_mcap.json")
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "research", "conference-runup", "index.html")
CSV_NAME = "conference-runup-company-releases.csv"
CSV_OUT = os.path.join(SITE, "research", "conference-runup", CSV_NAME)
WINDOWS = ("runup_30d", "runup_20d", "runup_10d", "runup_5d", "event_day", "post_5d", "post_10d")
SHOWN = (("runup_30d", "30 trading days before"), ("runup_10d", "10 trading days before"),
         ("event_day", "Anchor day and the next"), ("post_5d", "5 trading days after"),
         ("post_10d", "10 trading days after"))
TIERS = ("nano", "micro", "small", "mid", "large")
PUBLIC_COLS = ["ticker", "company", "conf", "conf_full", "year", "anchor", "anchor_basis", "release_url",
               "cap_tier_pit"] + list(WINDOWS)
B, E = "<!--CSTUDYADD:BEGIN-->", "<!--CSTUDYADD:END-->"
AFTER = "<!--CSTUDYX:END-->"
NEAR_DAYS = 45


def tier(m):
    if not m:
        return ""
    m = float(m)
    return "nano" if m < 50e6 else "micro" if m < 300e6 else "small" if m < 2e9 else "mid" if m < 10e9 else "large"


def num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def fmt(x):
    if x is None:
        return "n/a"
    return f"{x:+.2f}%".replace("-", "−") if abs(x) >= 0.005 else "0.00%"


def cache_rows(path):
    try:
        d = json.load(io.open(path, encoding="utf-8"))
        rows = d.get("rows") or {}
        rows = list(rows.values()) if isinstance(rows, dict) else list(rows)
        return [r for r in rows if isinstance(r, dict)]
    except Exception as e:  # noqa: BLE001
        print(f"  {os.path.basename(path)}: not read ({type(e).__name__}); no rows from it")
        return []


def day(s):
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def study_rows():
    return list(csv.DictReader(io.open(STUDY, encoding="utf-8-sig", errors="replace")))


def added_rows(study, lookup=None, mcap=None):
    """The rows to show, each with its tier; returns (rows, counts of what was left out, mcap cache)."""
    have = {(r["ticker"], r["conf"], str(r["year"])[:4]) for r in study}
    unknown = {}
    for r in study:
        if str(r.get("conf", "")).upper() == "UNKNOWN" and day(r.get("anchor")):
            unknown.setdefault(r["ticker"], []).append(day(r["anchor"]))
    mcap = dict(mcap or {})
    out, left, seen = [], {"window not closed or held": 0, "already in the study": 0, "duplicate": 0}, set()
    for path in CACHES:
        for r in sorted(cache_rows(path), key=lambda r: (r.get("anchor", ""), r.get("ticker", ""))):
            if not (r.get("status") == "complete" and r.get("ticker") and r.get("conf") and r.get("anchor")
                    and all(num(r.get(w)) is not None for w in WINDOWS)):
                left["window not closed or held"] += 1
                continue
            tcy = (r["ticker"], r["conf"], str(r.get("year", ""))[:4])
            a = day(r["anchor"])
            if tcy in have or (a and any(abs((a - u).days) <= NEAR_DAYS for u in unknown.get(r["ticker"], []))):
                left["already in the study"] += 1
                continue
            if tcy in seen:
                left["duplicate"] += 1
                continue
            seen.add(tcy)
            ck = f'{r["ticker"]}|{r.get("d_minus_1", "")}'
            if ck not in mcap and lookup and r.get("d_minus_1"):
                try:
                    v = lookup(r["ticker"], r["d_minus_1"])
                except Exception:  # noqa: BLE001
                    v = None
                if v:
                    mcap[ck] = v
            row = {c: r.get(c, "") for c in PUBLIC_COLS}
            row["year"] = str(r.get("year", ""))[:4]
            row["conf_full"] = re.sub(r"\b(\d{4}) \1$", r"\1", str(row["conf_full"]).strip())
            row["_from"] = "backfill" if "backfill" in os.path.basename(path) else "additions"
            row["cap_tier_pit"] = tier(mcap.get(ck))
            out.append(row)
    return out, left, mcap


def medians(rows):
    res = {}
    for w, _ in SHOWN:
        vals = [v for v in (num(r.get(w)) for r in rows) if v is not None]
        res[w] = {"n": len(vals), "median": round(st.median(vals), 2) if vals else None}
    return res


def mix(rows):
    c = {t: 0 for t in TIERS}
    for r in rows:
        if r.get("cap_tier_pit") in c:
            c[r["cap_tier_pit"]] += 1
    known = sum(c.values())
    return {"known": known, "unknown": len(rows) - known,
            "pct": {t: (round(100.0 * c[t] / known, 1) if known else None) for t in TIERS}}


def facts(study, added):
    return {"study_n": len(study), "added_n": len(added),
            "by_source": {"additions": sum(1 for r in added if r.get("_from") == "additions"),
                          "backfill": sum(1 for r in added if r.get("_from") == "backfill")},
            "years": sorted({r["year"] for r in added}),
            "study": medians(study), "added": medians(added),
            "mix_study": mix(study), "mix_added": mix(added)}


def write_csv(added):
    os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)
    with io.open(CSV_OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write("# pdufa.bio conference run-up study: company-release rows, kept apart from the curated study. "
                 "License: CC BY 4.0. Each row is anchored on the presenting company's own release that reported data "
                 "from the meeting (release_url). Returns in percent from the last close before the anchor; tier is "
                 "point-in-time market cap. Not investment advice.\n")
        w = csv.DictWriter(fh, fieldnames=PUBLIC_COLS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(added, key=lambda r: (r["anchor"], r["ticker"])):
            w.writerow(r)


def block(f):
    def pct(m, t):
        v = m["pct"][t]
        return "n/a" if v is None else f"{v:.1f}%"

    trs = "".join(
        f"<tr><td>{label}</td><td>{f['study'][w]['n']:,}</td><td>{fmt(f['study'][w]['median'])}</td>"
        f"<td>{f['added'][w]['n']:,}</td><td>{fmt(f['added'][w]['median'])}</td></tr>"
        for w, label in SHOWN)
    ms, ma = f["mix_study"], f["mix_added"]
    mix_rows = "".join(f"<tr><td>{t.capitalize()}</td><td>{pct(ms, t)}</td><td>{pct(ma, t)}</td></tr>" for t in TIERS)
    years = f["years"]
    span = f"{years[0]} to {years[-1]}" if len(years) > 1 else (years[0] if years else "")
    return (
        f"{B}"
        f"<h2>Company-release rows, kept apart from the study</h2>"
        f"<p>{f['added_n']:,} more presentations ({span}) are measured here, each anchored on the presenting "
        f"company's own release that reported data from the meeting, not on the date the study's rows use. {f['by_source']['additions']:,} are from "
        f"meetings ending on or after June 5, 2026 (the study's last row is June 4); {f['by_source']['backfill']:,} are earlier "
        f"presentations named in SEC filings that the study did not hold, each re-dated from the company's release. "
        f"A presentation the study already holds, or may hold under an unverified meeting label, is left out.</p>"
        f"<p>They are not in the {f['study_n']:,}-row figures above. This page's rule, written after the July 2026 "
        f"revert, is that a change of sampling frame is published beside the old figures, never folded into them in "
        f"the same step. These rows come from a different frame (releases for companies we track, and filings, which "
        f"skew to smaller companies), and no recall figure for that frame exists yet.</p>"
        f"<table><caption>Median share-price move, side by side: the study's rows and the company-release rows. "
        f"n is the number of rows with that window. No combined figure is given until a recall figure exists."
        f"</caption><tr><th>Window</th><th>Study n</th><th>Study median</th><th>Added n</th><th>Added median</th>"
        f"</tr>{trs}</table>"
        f"<table><caption>Point-in-time market-cap mix: share of rows with a known tier in each sample "
        f"(study {ms['known']:,} known, {ms['unknown']:,} unknown; added {ma['known']:,} known, "
        f"{ma['unknown']:,} unknown).</caption>"
        f"<tr><th>Tier</th><th>Study</th><th>Added</th></tr>{mix_rows}</table>"
        f'<p>The {f["added_n"]:,} rows, each with its release link, are downloadable: <a class="lit" '
        f'href="/research/conference-runup/{CSV_NAME}">{CSV_NAME}</a> (CC BY 4.0). This measures what happened; '
        f"it is not a forecast for any company.</p>"
        f"{E}")


def render(doc, html):
    if B in doc and E in doc.split(B, 1)[1]:
        return doc.split(B, 1)[0] + html + doc.split(B, 1)[1].split(E, 1)[1]
    if B in doc:
        return None
    if AFTER in doc:
        i = doc.index(AFTER) + len(AFTER)
        return doc[:i] + html + doc[i:]
    return None


def main(lookup=None):
    study = study_rows()
    try:
        mcap = json.load(io.open(MCAP, encoding="utf-8")) if os.path.exists(MCAP) else {}
        mcap = mcap if isinstance(mcap, dict) else {}
    except Exception:  # noqa: BLE001
        mcap = {}
    if lookup is None:
        try:
            from fmp_mcap import key, mcap_on  # noqa: E402
            lookup = mcap_on if key() else None
        except Exception:  # noqa: BLE001
            lookup = None
    added, left, mcap = added_rows(study, lookup, mcap)
    if lookup:
        io.open(MCAP, "w", encoding="utf-8").write(json.dumps(mcap, indent=0, sort_keys=True))
    if not added:
        doc = io.open(PAGE, encoding="utf-8", errors="replace").read()
        new = render(doc, "")
        if new is not None and new != doc:
            io.open(PAGE, "w", encoding="utf-8").write(new)
        if os.path.exists(CSV_OUT):
            os.remove(CSV_OUT)
        print("conference_runup_added: no complete company-release rows; section and CSV removed")
        return 0
    f = facts(study, added)
    write_csv(added)
    doc = io.open(PAGE, encoding="utf-8", errors="replace").read()
    new = render(doc, block(f))
    if new is None:
        print("conference_runup_added: the study page has no CSTUDYX block to follow (or a broken CSTUDYADD); "
              "nothing rendered")
        return 1
    if new != doc:
        io.open(PAGE, "w", encoding="utf-8").write(new)
    print(f"conference_runup_added: {f['added_n']} company-release rows beside the {f['study_n']:,}-row study "
          f"({f['mix_added']['known']} tiered); left out: " + ", ".join(f"{v} {k}" for k, v in left.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
