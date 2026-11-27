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


def fetch_prs(tk, key, since=None, limit=100, pages=6):
    # 2026-11-27: without from/to, FMP's press-release search returns only the last few months (Karyopharm: 7
    # releases, ending Aug 27), so a topline announced earlier in the year (XPORT-EC-042, Jul 30 2026) was never
    # seen and the row was marked "no topline". Ask for the whole span back to the earliest window, page by page.
    out = []
    for page in range(pages):
        q = {"symbols": tk, "limit": limit, "page": page, "apikey": key, "to": TODAY.isoformat()}
        if since:
            q["from"] = since
        req = urllib.request.Request(FMP_PR + "?" + urllib.parse.urlencode(q), headers={"User-Agent": "pdufa.bio builder"})
        try:
            rows = json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            return out or None
        got = [x for x in (rows if isinstance(rows, list) else []) if isinstance(x, dict)]
        for x in got:
            title = str(x.get("title") or "")
            body = re.sub(r"<[^>]+>", " ", str(x.get("text") or x.get("content") or ""))[:3000]
            pub = str(x.get("publishedDate") or x.get("date") or "")[:10]
            out.append((title, body, pub, x.get("url") or x.get("link") or ""))
        if len(got) < limit:
            break
        time.sleep(0.2)
    seen, uniq = set(), []
    for t in out:
        if (t[0], t[2]) not in seen:
            seen.add((t[0], t[2]))
            uniq.append(t)
    return uniq


# words of a registry title that say nothing about which disease the trial is in
GENERIC = set("""randomized randomised placebo controlled multicenter multicentre multi center double blind blinded
open label single arm patients participants subjects adults adult pediatric evaluate evaluating assess assessing
efficacy safety tolerability pharmacokinetics pharmacodynamics study trial phase versus compared combination therapy
treatment treated previously advanced recurrent relapsed refractory maintenance systemic standard physician physicians
choice agent single after before first second line moderate severe moderately severely active chronic acute
investigate investigating determine dose escalation expansion cohort monotherapy alone global international
cancer cancers carcinoma tumors tumours tumor tumour solid disease diseases syndrome disorder metastatic malignant
malignancies malignancy neoplasms positive negative results primary endpoint topline announces wildtype""".split())


def phases(text):
    out = set()
    for a, b in re.findall(r"phase\s*(\d)(?:\s*/\s*(\d))?", str(text or ""), re.I):
        out.add(int(a))
        if b:
            out.add(int(b))
    return out


def disease_words(row):
    blk = (row.get("_d") or {}).get("nct_id")
    blk = blk if isinstance(blk, dict) else {}
    t = " ".join(str(blk.get(k) or "") for k in ("title", "brief_title"))
    return {w for w in re.findall(r"[a-z]{6,}", t.lower()) if w not in GENERIC}


def match_release(row, prs, toks, start, multi):
    """The first release (newest first) in prs that reports this row's results, as (title, date, url), or None."""
    d = row.get("_d") or {}
    hit = None
    dz = disease_words(row) - {t.lower() for t in toks}
    tph = phases(((d.get("nct_id") or {}) if isinstance(d.get("nct_id"), dict) else {}).get("title"))
    for title, body, pub, url in prs:
        if pub and pub < start:
            continue
        if not RESULTS.search(title) or FUTURE.search(title) or FOLLOWUP.search(title):
            continue
        if not any(re.search(r"\b" + re.escape(t) + r"\b", title, re.I) for t in toks):
            # 2026-11-27: a topline headline often names the trial and the disease, not the drug ("Topline
            # Results from Phase 3 XPORT-EC-042 Trial in Endometrial Cancer"). Accept it only when the release
            # body names the drug, the headline names the disease of this row's registry trial, and any phase
            # the headline states is this trial's phase.
            if not any(re.search(r"\b" + re.escape(t) + r"\b", body, re.I) for t in toks):
                continue
            if not dz or not (dz & set(re.findall(r"[a-z]{6,}", title.lower()))):
                continue
            hph = phases(title)
            if hph and tph and not (hph & tph):
                continue
        elif dz and not (dz & set(re.findall(r"[a-z]{6,}", (title + " " + body).lower()))):
            # 2026-11-27 replay on 45 sponsors: "Positive Results from its ... Phase 2 Trial of Onvansertib in
            # First-Line RAS-Mutated mCRC" must not resolve an onvansertib PANCREATIC trial. A headline that names
            # the drug still has to share a disease word with this trial's registry title in its headline or text.
            continue
        if multi:
            tn = re.search(r"\b([A-Z][A-Za-z0-9-]{3,}(?:-\d+)?)\b", str(row.get("name") or ""))
            if not (tn and tn.group(1).lower() in body.lower()):
                continue
        hit = (title, pub, url)
        break
    return hit


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
        if res.get("state") == "sponsor_release" or res.get("reviewed"):
            n_skip += 1
            continue                                  # a found release is kept; never downgraded. A resolution
            #                                           checked by hand (reviewed=<date>, e.g. a release for the
            #                                           right trial, or the company stopping it) is never
            #                                           re-matched by headline (2026-11-17 stale-window check).
        if not key:
            rp = reg.get("results_first_submitted")
            if rp and not res:
                d["resolution"] = {"state": "results_posted_registry", "date": rp, "checked": TODAY.isoformat(),
                                   "searched": "ClinicalTrials.gov results section"}
                n_reg += 1
            continue
        if r["t"] not in cache:
            first = min(x for x in (past_window(z) for z in by_tk[r["t"]]) if x)
            since = (dt.date(int(first[:4]), int(first[5:7]), 1) - dt.timedelta(days=45)).isoformat()
            cache[r["t"]] = fetch_prs(r["t"], key, since=since)
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
        hit = match_release(r, prs, toks, start, multi)
        if hit:
            d["resolution"] = {"state": "sponsor_release", "date": hit[1], "headline": hit[0][:200], "url": hit[2],
                               "checked": TODAY.isoformat(),
                               "basis": "sponsor press-release headline with results language that names the drug, or "
                                        "names this trial's disease while its text names the drug; outcome not "
                                        "summarised here"}
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
