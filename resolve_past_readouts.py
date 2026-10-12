# -*- coding: utf-8 -*-
"""resolve_past_readouts.py -- every readout whose window has passed says what we found and when we looked.

Audit 2026-10-11 section 2c: 72 rows said "Window passed" with no outcome and no date on which we last
checked. That is the readouts equivalent of a stale pending decision: current-looking, sourced, and not
resolved. This runs daily and records, on each past-window Estimated/Guided row, ONE of:

  _d.resolution.state = "sponsor_release"   the sponsor's own results headline for this drug, dated and
                                            linked (matched on the headline: drug token + results language,
                                            not a scheduling or follow-up headline; trial name in the body
                                            when the drug spans several rows). No outcome is summarised:
                                            that stays the human path (readout_reported_manual.json).
  _d.resolution.state = "no_topline"        nothing found in the sponsor's press releases (FMP, counted) and
                                            no results on ClinicalTrials.gov, checked on `checked`.
  (terminated rows)                         already carried as _d.registry.overall_status and served as
                                            "Terminated per registry"; this script leaves them alone.

Without an FMP key the press-release search cannot run, so NOTHING is claimed about sponsor releases: the
script only records registry results-posted dates. The API (api/v1/_lib.mjs) serves these as
"Sponsor release {date}" / "No topline as of {date}"; /readouts prints them per row. Facts only. RULE 1: all
dates are the sponsor's own calendar dates; `checked` is the Eastern build date.

    python resolve_past_readouts.py [--dry-run] [--limit N]
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
TODAY = eastern_today()
CUR = TODAY.strftime("%Y-%m")
FMP_PR = "https://financialmodelingprep.com/stable/news/press-releases"

RESULTS = re.compile(
    r"\b(?:top-?line|primary\s+endpoint|pivotal\s+(?:phase\s*3\s+)?(?:trial|study|data|results)|"
    r"(?:positive|negative|mixed)\s+(?:top-?line\s+)?(?:results|data)|"
    r"(?:met|missed|achieved|did\s+not\s+meet)\s+(?:its\s+)?(?:the\s+)?primary|"
    r"statistically\s+significant\s+(?:improvement|reduction|benefit)|"
    r"announces?\s+(?:positive\s+|negative\s+|)(?:results|data)\s+from)", re.I)
FUTURE = re.compile(r"\bto\s+(?:report|announce|present|host)\b", re.I)
FOLLOWUP = re.compile(r"\b(?:\d+-year|\d+-month|long-?term|follow-?up|real-?world|post-?hoc|subgroup|"
                      r"extension\s+(?:study|data)|durability)\b", re.I)
STOP = {"placebo", "readout", "phase", "topline", "clinical", "study", "trial", "plus", "with", "and", "the",
        "cell", "cells", "tablets", "oral", "injection", "treated", "human", "low", "dose", "high"}


def drug_tokens(row):
    d = row.get("_d") or {}
    cands = [str(d.get("program") or ""), str(row.get("name") or "")]
    toks = []
    for c in cands:
        for part in re.split(r"[;,/()]| and | plus | readout| topline| Phase", c):
            w = part.strip().split()
            if not w:
                continue
            tok = re.sub(r"[^A-Za-z0-9-]", "", w[0])
            if len(tok) >= 4 and tok.lower() not in STOP and not re.match(r"^\d+$", tok):
                toks.append(tok)
    out = []
    for t in toks:
        if t.lower() not in [o.lower() for o in out]:
            out.append(t)
    return out[:2]


def past_window(row):
    if row.get("type") != "Readout" or str(row.get("st") or "") not in ("Estimated", "Guided"):
        return None
    ym = str(row.get("d") or "")[:7]
    if not re.match(r"^\d{4}-\d{2}$", ym):
        ym = str(row.get("dm") or "")
    if not re.match(r"^\d{4}-\d{2}$", ym) or ym >= CUR:
        return None
    return ym


def fetch_prs(tk, key, limit=60):
    url = FMP_PR + "?" + urllib.parse.urlencode({"symbols": tk, "limit": limit, "apikey": key})
    req = urllib.request.Request(url, headers={"User-Agent": "pdufa.bio builder"})
    try:
        rows = json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    out = []
    for x in rows if isinstance(rows, list) else []:
        if not isinstance(x, dict):
            continue
        title = str(x.get("title") or "")
        body = re.sub(r"<[^>]+>", " ", str(x.get("text") or x.get("content") or ""))[:3000]
        pub = str(x.get("publishedDate") or x.get("date") or "")[:10]
        out.append((title, body, pub, x.get("url") or x.get("link") or ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=400)
    a = ap.parse_args()
    key = os.environ.get("FMP_API_KEY", "").strip()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    todo = [(r, past_window(r)) for r in rows]
    todo = [(r, ym) for r, ym in todo if ym][: a.limit]
    print(f"{len(todo)} past-window readout rows; FMP key {'present' if key else 'ABSENT (registry-only pass)'}")
    by_tk = {}
    for r, ym in todo:
        by_tk.setdefault(r["t"], []).append(r)
    cache = {}
    n_rel = n_none = n_reg = n_skip = 0
    for r, ym in todo:
        d = r.setdefault("_d", {})
        reg = d.get("registry") or {}
        if str(reg.get("overall_status") or "").upper() in ("TERMINATED", "WITHDRAWN", "SUSPENDED"):
            n_skip += 1
            continue
        res = d.get("resolution") or {}
        if res.get("state") == "sponsor_release":
            n_skip += 1
            continue                                  # a found release is kept; never downgraded
        if not key:
            rp = reg.get("results_first_submitted")
            if rp and not res:
                d["resolution"] = {"state": "results_posted_registry", "date": rp, "checked": TODAY.isoformat(),
                                   "searched": "ClinicalTrials.gov results section"}
                n_reg += 1
            continue
        if r["t"] not in cache:
            cache[r["t"]] = fetch_prs(r["t"], key)
            time.sleep(0.2)
        prs = cache[r["t"]]
        if prs is None:
            continue                                  # fetch failed: claim nothing
        toks = drug_tokens(r)
        if not toks:
            continue                                  # nothing to match a headline on: claim nothing
        y, m = int(ym[:4]), int(ym[5:7])
        start = (dt.date(y, m, 1) - dt.timedelta(days=45)).isoformat()
        multi = len([x for x in by_tk[r["t"]] if drug_tokens(x)[:1] == toks[:1]]) > 1
        hit = None
        for title, body, pub, url in prs:
            if pub and pub < start:
                continue
            if not any(re.search(r"\b" + re.escape(t) + r"\b", title, re.I) for t in toks):
                continue
            if not RESULTS.search(title) or FUTURE.search(title) or FOLLOWUP.search(title):
                continue
            if multi:
                trial = str(d.get("program") or "")
                tn = re.search(r"\b([A-Z][A-Za-z0-9-]{3,}(?:-\d+)?)\b", str(r.get("name") or ""))
                if not (tn and tn.group(1).lower() in body.lower()):
                    continue
            hit = (title, pub, url)
            break
        if hit:
            d["resolution"] = {"state": "sponsor_release", "date": hit[1], "headline": hit[0][:200], "url": hit[2],
                               "checked": TODAY.isoformat(),
                               "basis": "sponsor press-release headline naming the drug with results language; "
                                        "outcome not summarised here"}
            n_rel += 1
        else:
            d["resolution"] = {"state": "no_topline", "checked": TODAY.isoformat(),
                               "searched": f"{len(prs)} sponsor press releases (FMP) through {TODAY.isoformat()}"
                                           + ("; ClinicalTrials.gov " + str(reg.get("checked")) if reg.get("checked") else "")}
            if reg.get("results_first_submitted"):
                d["resolution"]["registry_results_posted"] = reg.get("results_first_submitted")
            n_none += 1
    print(f"sponsor release found {n_rel}; no topline as of today {n_none}; registry results-posted only {n_reg}; "
          f"terminated/kept {n_skip}")
    if a.dry_run:
        print("--dry-run: nothing written")
        return 0
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
