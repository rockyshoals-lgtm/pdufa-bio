# -*- coding: utf-8 -*-
"""verify_decisions.py -- replace price-inference with primary sources, event by event.

Owner decision 2026-08-12: 'I'd rather not infer approval/CRL from the stock's reaction because
sometimes that doesn't pan out.' He is right, and the site already knows it -- the false SELLAS
CRL was exactly a price-inference that panned wrong, and every price-only page has carried an
'Unverified record' banner since. This script does the verification those banners promise.

For each of the 307 price-only decision pages (ticker + date, joined to the ODIN research
dataset for drug name, company and claimed outcome):

  1. Drugs@FDA via openFDA: search the drug's brand/generic names; an approval (submission
     status AP) dated within the window is primary evidence of approval. Source URL: the
     official Drugs@FDA application page.
  2. SEC EDGAR full-text search: 8-K/PR filings in a +/-14-day window from the right CIK
     mentioning 'complete response letter' (CRL evidence) or approval language. Source URL:
     the filing itself.

Nothing is upgraded without a source URL a reader can open. Outcomes are recorded as:
  verified_approved / verified_crl  -- evidence agrees with the price-inferred claim
  CONTRADICTION                     -- evidence disagrees; reported loudly, page gets the truth
  unverified                        -- no evidence found; the honest banner stays

Everything cached in _decision_verification_cache.json (openFDA + EDGAR responses) and results
written to _decision_verification.json for the page-upgrade pass.

    python verify_decisions.py [--limit N] [--only TICKER-DATE]
"""
import argparse, csv, datetime as dt, glob, json, os, re, sys, time, urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CACHE_P = os.path.join(HERE, "_decision_verification_cache.json")
OUT_P = os.path.join(HERE, "_decision_verification.json")
ODIN_CSV = os.path.join(HERE, "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv")
UA = {"User-Agent": "pdufa.bio research rockyshoals@gmail.com"}

CACHE = json.load(open(CACHE_P, encoding="utf-8")) if os.path.exists(CACHE_P) else {}


def fetch(url, tag, throttle):
    if url in CACHE:
        return CACHE[url]
    time.sleep(throttle)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        data = {"_error": str(e)[:200]}
    CACHE[url] = data
    return data


def save_cache():
    json.dump(CACHE, open(CACHE_P, "w", encoding="utf-8"))


def name_tokens(asset):
    """Candidate search names: brand word(s) before any paren + the paren generic."""
    s = re.sub(r"\s+", " ", str(asset or "")).strip()
    out = []
    lead = re.split(r"[(–-]| - ", s)[0].strip()
    if lead:
        out.append(lead)
        if " " in lead:                       # also try just the first word (brand)
            out.append(lead.split()[0])
    for inner in re.findall(r"\(([^()]{3,60})\)", s):
        inner = re.sub(r"\b(?:the|a|an)\b", "", inner).strip()
        if re.search(r"[a-z]", inner) and not inner.isupper():
            out.append(re.split(r"[,;]", inner)[0].strip())
    seen, res = set(), []
    for x in out:
        x = x.strip(" .,-")
        if len(x) >= 4 and x.lower() not in seen:
            seen.add(x.lower())
            res.append(x)
    return res[:4]


def openfda_approval(names, date, window=10):
    """An AP-status submission dated within window days of `date`, searched by name."""
    d0 = dt.date.fromisoformat(date)
    for nm in names:
        q = urllib.parse.quote(f'"{nm}"')
        url = (f"https://api.fda.gov/drug/drugsfda.json?search="
               f"(openfda.brand_name:{q}+OR+openfda.generic_name:{q}"
               f"+OR+products.brand_name:{q})&limit=20")
        j = fetch(url, "openfda", 0.35)
        for res in j.get("results", []):
            appl = res.get("application_number", "")
            for sub in res.get("submissions", []) or []:
                if sub.get("submission_status") != "AP":
                    continue
                sd = str(sub.get("submission_status_date", ""))
                if len(sd) == 8:
                    sd_iso = f"{sd[:4]}-{sd[4:6]}-{sd[6:8]}"
                    try:
                        if abs((dt.date.fromisoformat(sd_iso) - d0).days) <= window:
                            num = re.sub(r"[^0-9]", "", appl)
                            return {
                                "kind": "approval",
                                "matched_name": nm,
                                "appl_no": appl,
                                "approval_date": sd_iso,
                                "source_url": ("https://www.accessdata.fda.gov/scripts/cder/"
                                               f"daf/index.cfm?event=overview.process&ApplNo={num}"),
                                "source_label": f"Drugs@FDA, application {appl}, "
                                                f"action date {sd_iso}"}
                    except ValueError:
                        pass
    return None


_CIK = {}
def cik_for(ticker):
    global _CIK
    if not _CIK:
        j = fetch("https://www.sec.gov/files/company_tickers.json", "sec", 0.4)
        for v in j.values():
            if isinstance(v, dict):
                _CIK[str(v.get("ticker", "")).upper()] = int(v.get("cik_str", 0))
    return _CIK.get(ticker.upper())


def edgar_search(ticker, date, phrase, window=14):
    cik = cik_for(ticker)
    if not cik:
        return None
    d0 = dt.date.fromisoformat(date)
    start = (d0 - dt.timedelta(days=2)).isoformat()
    end = (d0 + dt.timedelta(days=window)).isoformat()
    q = urllib.parse.quote(f'"{phrase}"')
    # 8-K/6-K only: event-driven filings dated to the event. A 10-Q or annual report mentioning
    # 'complete response letter' is usually describing SOME CRL in the company's history, not
    # this one -- the first run produced two false contradictions exactly this way.
    url = (f"https://efts.sec.gov/LATEST/search-index?q={q}"
           f"&dateRange=custom&startdt={start}&enddt={end}&forms=8-K,6-K&ciks={cik:010d}")
    j = fetch(url, "sec", 0.45)
    hits = (j.get("hits", {}) or {}).get("hits", []) or []
    for h in hits:
        src = h.get("_source", {}) or {}
        acc = str(src.get("adsh", ""))
        fdate = str(src.get("file_date", ""))
        if not acc:
            continue
        doc_id = str(h.get("_id", ""))          # "accession:filename"
        fname = doc_id.split(":", 1)[1] if ":" in doc_id else ""
        accn = acc.replace("-", "")
        url_doc = (f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn}/{fname}"
                   if fname else
                   f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik:010d}")
        return {"kind": "filing", "phrase": phrase, "filing_date": fdate,
                "accession": acc, "source_url": url_doc,
                "source_label": f"SEC filing {acc} of {fdate} containing '{phrase}'"}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--recent-days", type=int, default=0,
                    help="only events decided within N days of today -- the daily CI mode. "
                         "New decisions get source-checked while their 8-K is days old, and "
                         "recent unverified ones are retried as filings land; the deep "
                         "backlog is left to deliberate full runs.")
    a = ap.parse_args()

    odin = _load_join(ODIN_CSV, HERE)

    targets = []
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = open(p, encoding="utf-8", errors="replace").read()
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]+)-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        if "price-only" in doc:
            claimed = ("approval" if "consistent with approval" in doc
                       else "crl" if "consistent with a CRL" in doc else "unknown")
            targets.append((slug, m.group(1), m.group(2), claimed))
            continue
        # second backlog (2026-08-12): older pages that ASSERT an outcome in their title but
        # link no external document at all -- asserted, source unshown. Same verification.
        ext = [u for u in re.findall(r'href="(https?://[^"]+)"', doc)
               if "pdufa.bio" not in u]
        if not ext:
            t = re.search(r"<span>Outcome</span><b[^>]*>([^<]+)</b>", doc)
            if t:
                oc = t.group(1).strip().lower()
                claimed = ("approval" if "approv" in oc
                           else "crl" if "crl" in oc or "complete response" in oc
                           else "unknown")
                if claimed != "unknown":
                    targets.append((slug, m.group(1), m.group(2), claimed))
    if a.only:
        targets = [t for t in targets if t[0] == a.only]
    if a.recent_days:
        cutoff = (dt.date.today() - dt.timedelta(days=a.recent_days)).isoformat()
        targets = [t for t in targets if t[2] >= cutoff]
        print(f"recent mode: {len(targets)} event(s) since {cutoff}")
        # bust cached EMPTY EDGAR answers for the window: an 8-K that landed yesterday must be
        # seen today, and a cached miss would hide it forever
        purge = [u for u, resp in CACHE.items()
                 if "efts.sec.gov" in u and f"startdt={cutoff[:4]}" <= u
                 and re.search(r"startdt=(\d{4}-\d{2}-\d{2})", u)
                 and re.search(r"startdt=(\d{4}-\d{2}-\d{2})", u).group(1) >= cutoff
                 and not ((resp.get("hits") or {}).get("hits")
                          if isinstance(resp, dict) else None)]
        for u in purge:
            del CACHE[u]
        if purge:
            print(f"recent mode: {len(purge)} cached empty EDGAR response(s) purged for retry")
    if a.limit:
        targets = targets[:a.limit]

    prev = json.load(open(OUT_P, encoding="utf-8")) if os.path.exists(OUT_P) else {}
    results = prev.get("results", {})
    n_done = 0
    for slug, tk, date, claimed in targets:
        if slug in results and results[slug].get("status") != "unverified":
            continue
        row = odin.get((tk, date), {})
        asset = row.get("asset", "")
        names = name_tokens(asset)
        ev_appr = openfda_approval(names, date) if names else None
        ev_crl = edgar_search(tk, date, "complete response letter")
        # approval evidence from EDGAR too (covers biologics openFDA may miss)
        ev_appr_sec = None
        if not ev_appr and not ev_crl:
            ev_appr_sec = edgar_search(tk, date, "FDA approval") \
                or edgar_search(tk, date, "approval of")

        if ev_appr or (ev_appr_sec and claimed == "approval"):
            ev = ev_appr or ev_appr_sec
            status = ("verified_approved" if claimed in ("approval", "unknown")
                      else "CONTRADICTION")
        elif ev_crl:
            status = "verified_crl" if claimed in ("crl", "unknown") else "CONTRADICTION"
            ev = ev_crl
        else:
            status, ev = "unverified", None

        results[slug] = {"ticker": tk, "date": date, "asset": asset,
                         "claimed": claimed, "status": status, "evidence": ev}
        n_done += 1
        flag = "!!" if status == "CONTRADICTION" else "ok" if ev else ".."
        print(f"  [{flag}] {slug:22s} claimed={claimed:8s} -> {status}"
              + (f"  ({ev['source_label'][:60]})" if ev else ""))
        if n_done % 20 == 0:
            save_cache()
            json.dump({"as_of": dt.date.today().isoformat(), "results": results},
                      open(OUT_P, "w", encoding="utf-8"), indent=1)

    save_cache()
    json.dump({"as_of": dt.date.today().isoformat(), "results": results},
              open(OUT_P, "w", encoding="utf-8"), indent=1)
    from collections import Counter
    c = Counter(v["status"] for v in results.values())
    print("\nsummary:", dict(c))
    return 0




def _load_join(path_full, here):
    """(ticker, date) -> row with asset/indication. Full ODIN csv on the workstation, the
    committed slim extract in CI, empty if neither -- never a crash (2026-08-14: four daily
    rebuilds died on the missing workstation-only csv)."""
    import csv as _csv, os as _os
    slim = _os.path.join(here, "_decisions_join_slim.csv")
    src = path_full if _os.path.exists(path_full) else (slim if _os.path.exists(slim) else None)
    if src is None:
        print("  [warn] no drug-name join available (neither ODIN csv nor slim extract); "
              "name-based matching disabled this run")
        return {}
    with open(src, encoding="utf-8", errors="replace") as f:
        return {(str(r["ticker"]).upper(), str(r["catalyst_date"])[:10]): r
                for r in _csv.DictReader(f)}

if __name__ == "__main__":
    sys.exit(main())
