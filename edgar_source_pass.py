# -*- coding: utf-8 -*-
"""EDGAR source pass (task #77, audit 09-15 ORDER 4 back-fill).

For every upcoming PDUFA row with no `_d.source_url`: search EDGAR full-text for the row's stated
date (day rows: "Month D, YYYY"; month/quarter rows: the window phrase) together with "PDUFA",
restricted to the sponsor's own filings where the ticker resolves to a CIK; fetch the best hit;
confirm the date string sits within 400 characters of "PDUFA" or "target action date" in the
document text; and only then write `source`, `source_url` and `source_quote` on the row.

Nothing is written on a search hit alone. A row that cannot be confirmed is listed at the end as
UNSOURCED with what was tried, so the precision downgrade decision is made by a person.

    python edgar_source_pass.py [--dry-run] [--only TICKER,...]
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
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September",
       "October", "November", "December"]
QTR = {1: "first quarter", 2: "second quarter", 3: "third quarter", 4: "fourth quarter"}


def http(url, timeout=40):
    for i in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except Exception as e:  # noqa: BLE001
            if i == 2:
                raise
            time.sleep(1.5 * (i + 1))


def efts(q, forms, start, end, entity=None):
    u = (f"https://efts.sec.gov/LATEST/search-index?q={urllib.parse.quote(q)}&forms={forms}"
         f"&dateRange=custom&startdt={start}&enddt={end}")
    if entity:
        u += f"&ciks={entity}"
    return json.loads(http(u))["hits"]["hits"]


_TICKERS = {}


def ticker_cik(tk):
    if not _TICKERS:
        try:
            j = json.loads(http("https://www.sec.gov/files/company_tickers.json"))
            for v in j.values():
                _TICKERS[str(v.get("ticker", "")).upper()] = str(v["cik_str"]).zfill(10)
        except Exception:
            _TICKERS["__failed__"] = ""
    return _TICKERS.get(tk.upper()) or None


def clean(html):
    return re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", html)))


def phrases(r):
    d = dt.date.fromisoformat(r["d"])
    dp = r.get("dp") or "day"
    if dp == "day":
        return [f"{MON[d.month]} {d.day}, {d.year}", f"{MON[d.month]} {d.day} {d.year}"], "day"
    if dp == "month":
        return [f"{MON[d.month]} {d.year}", f"{MON[d.month]} of {d.year}"], "month"
    if dp == "quarter":
        q = (d.month - 1) // 3 + 1
        return [f"{QTR[q]} of {d.year}", f"{QTR[q]} {d.year}", f"Q{q} {d.year}", f"{q}Q{str(d.year)[2:]}"], "quarter"
    return [f"{d.year}"], "year"


def confirm(text, phr):
    """Return a quote if the phrase sits near PDUFA / target action date."""
    for p in phr:
        for m in re.finditer(re.escape(p), text, re.I):
            win = text[max(0, m.start() - 400): m.end() + 400]
            if re.search(r"PDUFA|target action date|goal date|action date", win, re.I):
                s = text[max(0, m.start() - 220): m.end() + 120]
                return s.strip()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    only = {t.strip().upper() for t in a.only.split(",") if t.strip()}

    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    todo = [r for r in rows if r.get("type") == "PDUFA" and r.get("st") == "Upcoming"
            and not (r.get("_d") or {}).get("source_url") and (not only or r["t"].upper() in only)]
    print(f"{len(todo)} upcoming PDUFA row(s) without source_url\n")
    sourced, unsourced = [], []
    end = dt.date.today().isoformat()
    for r in todo:
        tk = r["t"].upper()
        phr, kind = phrases(r)
        cik = ticker_cik(tk)
        drug = re.split(r"[\s(\-]", str(r.get("name") or ""), maxsplit=1)[0]
        tried = []
        hit_url = quote = None
        queries = [f'"{phr[0]}" "PDUFA"']
        if drug and len(drug) > 3:
            queries.append(f'"{phr[0]}" "{drug}"')
        for q in queries:
            try:
                hits = efts(q, "8-K,10-Q,10-K,6-K,20-F", "2025-06-01", end, entity=cik)
            except Exception as e:  # noqa: BLE001
                tried.append(f"{q}: search error {e}")
                continue
            tried.append(f"{q}: {len(hits)} hit(s){' (CIK-restricted)' if cik else ''}")
            for h in hits[:6]:
                s = h["_source"]
                adsh, fn = h["_id"].split(":", 1)
                m = re.search(r"CIK (\d+)", s["display_names"][0])
                if not m:
                    continue
                # THE FILER MUST BE THE SPONSOR (or the row's CIK). The dry run matched
                # Nuvalent's November 27 to BridgeBio's 8-K (same date, other company), Roche's
                # November 30 to Cogent's, Bayer's "December 2026" to Vanda's. A date near "PDUFA"
                # in someone else's filing is not a source.
                filer = s["display_names"][0].split("  (")[0].lower()
                ctoks = {w for w in re.findall(r"[a-z]{4,}", str(r.get("company") or "").lower())
                         if w not in ("inc", "corp", "company", "holdings", "pharmaceuticals", "pharma",
                                      "therapeutics", "biosciences", "limited", "group", "plc", "sciences",
                                      "medicines", "biotherapeutics")}
                same_cik = cik and m.group(1).zfill(10) == cik
                if not same_cik and not any(w in filer for w in ctoks):
                    tried.append(f"  {s['display_names'][0][:30]}: not the sponsor's filing")
                    continue
                url = f"https://www.sec.gov/Archives/edgar/data/{int(m.group(1))}/{adsh.replace('-', '')}/{fn}"
                try:
                    text = clean(http(url).decode("utf-8", "replace"))
                except Exception as e:  # noqa: BLE001
                    tried.append(f"  fetch {url[-40:]}: {e}")
                    continue
                qt = confirm(text, phr)
                if qt:
                    hit_url, quote = url, qt
                    form, fdate = s.get("form"), s.get("file_date")
                    label = f"{s['display_names'][0].split('  (')[0]} {form} {fdate}"
                    break
                tried.append(f"  {url[-50:]}: phrase not near PDUFA")
            if hit_url:
                break
            time.sleep(0.4)
        if hit_url:
            sourced.append((r["id"], hit_url, label, quote))
            print(f"SOURCED  {r['id']:<30} {kind:<7} {label}\n         {hit_url}\n         \"{quote[:200]}\"\n")
            if not a.dry_run:
                dd = r.setdefault("_d", {})
                dd["source"] = label
                dd["source_url"] = hit_url
                dd["source_quote"] = quote[:400]
        else:
            unsourced.append((r["id"], kind, tried))
            print(f"UNSOURCED {r['id']:<30} {kind:<7} {r.get('name')}")
            for t in tried:
                print(f"         {t}")
            print()
        time.sleep(0.5)
    if not a.dry_run and sourced:
        io.open(DATASET, "w", encoding="utf-8").write(
            src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    print(f"\n{len(sourced)} sourced, {len(unsourced)} unsourced" + ("   (--dry-run)" if a.dry_run else ""))
    json.dump({"sourced": sourced, "unsourced": unsourced, "run": dt.datetime.now().isoformat()},
              io.open(os.path.join(HERE, "_edgar_source_pass_result.json"), "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
