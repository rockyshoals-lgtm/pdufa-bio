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
import unicodedata
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


EARLY_LEADS = os.path.join(HERE, "_readout_early_leads.json")
EARLY_WORDS = re.compile(r"\b(?:top-?line|results?|data|met|missed|achieved|did\s+not\s+meet|primary\s+endpoint)\b", re.I)


def future_estimate(row):
    """An Estimated readout whose registry window is still ahead and has no recorded outcome."""
    if row.get("type") != "Readout" or str(row.get("st") or "") != "Estimated":
        return False
    if past_window(row) or ((row.get("_d") or {}).get("resolution") or {}).get("state"):
        return False
    blk = (row.get("_d") or {}).get("nct_id")
    return isinstance(blk, dict) and str(blk.get("nct") or "").upper().startswith("NCT")


def future_guided(row, today):
    """2026-11-27: a company-guided readout whose window is still open or ahead and has no recorded outcome. The early
    pass looked only at registry estimates; a "Q4 2026" row whose topline came out in October stayed "upcoming"
    until the quarter closed."""
    if row.get("type") != "Readout" or str(row.get("st") or "") != "Guided":
        return False
    if row.get("dp") == "day" or ((row.get("_d") or {}).get("resolution") or {}).get("state"):
        return False
    return str(row.get("d") or "") >= today.isoformat()


def _as_trial(row):
    """A guided row has no registry record; its indication and trial name stand in for the registry title, so the
    headline must still share a disease word with it (see match_release)."""
    d = row.get("_d") or {}
    if isinstance(d.get("nct_id"), dict) and d["nct_id"].get("title"):
        return row
    t = " ".join(str(d.get(k) or "") for k in ("indication", "trial"))
    return {**row, "_d": {**d, "nct_id": {"title": t}}}


def _fold(text):
    """Lower-case ASCII ("Sjögren's" -> "sjogren's"), so an accented disease name still matches a headline."""
    return unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()


# all-caps headline words that are conferences, agencies or terms, not trial names
NOT_TRIALS = set("""PHASE FDA EMA NMPA PMDA CHMP NICE ASCO ESMO AACR SABCS EULAR AASLD EASL EADV AAAAI CTAD AAIC
ISTH IDWEEK ACTRIMS ECTRIMS DDW UEGW ERS CHEST ESC AHA ACC ASN ASGCT WCLC JPM NASDAQ NYSE TSX AIM ADR CEO CFO
NASH MASH COVID HIV AIDS CAR STAT TRUE FALSE DATA""".split())


def _trial_names(text):
    """Trial acronyms (ECLIPSE 2, EMBRACE, BROADEN2) in a row's trial field or a headline, as (word, number)."""
    out = set()
    for w, n in re.findall(r"\b([A-Z]{4,})(?:[\s-]?(\d{1,2})\b)?", str(text or "")):
        if w not in NOT_TRIALS:
            out.add((w, n or ""))
    return out


def _guided_headline_ok(row, title):
    """2026-11-27 first wide run: 9 guided-row leads, none real. A guided row has no registry record, so its
    headline match rests on the company's own words: the headline must name the row's disease (Kymera's BROADEN2
    atopic dermatitis topline is not its BREADTH asthma readout; BMS's POETYK SLE results are not POETYK SjS), and a
    headline that names a trial must name this row's trial (Vir's ECLIPSE 1 is not ECLIPSE 2 or 3; Helus's APPROACH
    is not EMBRACE)."""
    d = row.get("_d") or {}
    ind = {w for w in re.findall(r"[a-z]{4,}", _fold(d.get("indication"))) if w not in GENERIC}
    head = set(re.findall(r"[a-z]{4,}", _fold(title)))
    mine, named = _trial_names(d.get("trial")), _trial_names(title)
    if mine and named:
        if not any((w, n) in named or (not n and any(x[0] == w for x in named)) for w, n in mine):
            return False
    # Naming this row's trial stands in for naming the disease only when the name is the whole trial: POETYK
    # SjS-1's family word POETYK is shared with BMS's POETYK SLE-1 and SLE-2.
    trial = str(d.get("trial") or "")
    whole = {(w, n) for w, n in mine if n or not re.search(re.escape(w) + r"\s+[A-Za-z]{2,}-?\d", trial)}
    return bool(ind & head) or any((w, n) in named or (not n and any(x[0] == w for x in named)) for w, n in whole)


def early_leads(rows, key, cache, fetch=None, today=None):
    """2026-11-27: the pass above only looks for a sponsor release once a registry window has PASSED. Humacyte
    reported V012's primary endpoint at a prespecified interim on Jun 10, 2026 and MediciNova reported MN-001's
    topline on Sep 28, 2026, while /readouts still listed both as upcoming (windows Jun 2027 and Dec 2026). This pass
    runs the same headline match over the last ~13 months of releases for every Estimated row whose window is still
    ahead, and writes each hit to _readout_early_leads.json as a LEAD for a person to verify against the release and
    the registry. It never changes a row: an early headline is as often an interim or a different part of the trial
    (a Phase 1 stage, a dose-selection cut) as the readout itself. Guard: tests/test_resolver_finds_trial_headlines.py."""
    fetch = fetch or fetch_prs
    today = today or TODAY
    since = (today - dt.timedelta(days=400)).isoformat()
    todo = [r for r in rows if future_estimate(r) or future_guided(r, today)]
    by_tk = {}
    for r in todo:
        by_tk.setdefault(r["t"], []).append(r)
    leads = []
    for r in todo:
        ck = ("early", r["t"])
        if ck not in cache:
            cache[ck] = fetch(r["t"], key, since=since, pages=3)
            time.sleep(0.2)
        prs = cache[ck]
        toks = drug_tokens(r)
        if not prs or not toks:
            continue
        multi = len([x for x in by_tk[r["t"]] if drug_tokens(x)[:1] == toks[:1]]) > 1
        # A lead needs a results word in its headline: the first run (Nov 27) listed "Pivotal Trial ... Underway"
        # and "Reaches Full Enrollment in Pivotal Phase 3 Trial", which the passed-window match tolerates only
        # because a passed window has nothing else to be.
        start, cand = since, [p for p in prs if EARLY_WORDS.search(p[0])]
        if r.get("st") == "Guided":
            if not (r.get("_d") or {}).get("indication"):
                continue
            # A release from before the company guided this readout as still to come cannot be it, and neither can
            # the guiding release itself: Pharming's and ProMIS's quarterly releases that set the timing, Beam's
            # BEACON topline and AbbVie's INTREPID topline that each guided a LATER, fuller readout (Nov 27 run).
            filed = str((r.get("_d") or {}).get("guided_filed") or "")[:10]
            cand = [p for p in cand if (not filed or str(p[2] or "") > filed) and _guided_headline_ok(r, p[0])]
            start = max(since, filed)
        hit = match_release(_as_trial(r), cand, toks, start, multi)
        if hit:
            blk = (r["_d"].get("nct_id") if isinstance(r["_d"].get("nct_id"), dict) else None) or {}
            leads.append({"id": r["id"], "t": r["t"], "st": r.get("st"), "nct": blk.get("nct"),
                          "window": (r["_d"].get("guided_label") if r.get("st") == "Guided" else None)
                          or r.get("dm") or str(r.get("d"))[:7],
                          "headline": hit[0][:200], "date": hit[1], "url": hit[2], "found": today.isoformat()})
    out = {"_note": "Leads only, never published: a sponsor headline with results language for a trial whose "
                    "registry or company-guided window is still open. Verify the release is this trial's readout (not an interim, "
                    "a different stage or a different trial) before a row is changed. Written by "
                    "resolve_past_readouts.py.", "checked": today.isoformat(), "rows_checked": len(todo),
           "leads": leads}
    io.open(EARLY_LEADS, "w", encoding="utf-8").write(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"early-release leads: {len(leads)} of {len(todo)} future-window estimated/guided rows (see _readout_early_leads.json)")
    for x in leads:
        print(f"  LEAD {x['id']}: {x['date']} {x['headline'][:120]}")
    return leads


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--no-early", action="store_true", help="skip the early-release lead pass")
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
    if not a.dry_run:
        io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    # 2026-11-27: the lead pass now covers ~300 sponsors (guided rows too), so it runs AFTER the dataset is written:
    # a slow FMP day that hits the step's time limit loses only the leads, never the passed-window findings.
    if key and not a.no_early:
        early_leads(rows, key, cache)
    if a.dry_run:
        print("--dry-run: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
