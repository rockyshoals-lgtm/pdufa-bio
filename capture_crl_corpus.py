# -*- coding: utf-8 -*-
"""Dated capture of the FDA CRL release (openFDA transparency/crl) -- a time series, not a file.

Moat audit 09-20b item 3. Two hand-made snapshots existed (2026-06-22: 439 letters; 2026-08-29:
458) and that pair is already a "CRLs released per period" series by construction. This makes
the capture routine: page the endpoint, compare with the newest snapshot on disk, and

  * if the release CHANGED (total or last_updated), write CRL_corpus_openFDA_<today>.json in the
    same shape as the hand-made ones (meta + results) so build_crl_hub / link_crl_letters pick it
    up through newest_corpus();
  * always append one row to _crl_capture_series.json: checked date, openFDA last_updated, total,
    since-approved, not-approved, and whether a snapshot was written. That file is the series
    "/crl" can chart and the auditor asked for.

Network failure is not a build failure: the newest snapshot on disk stays authoritative.

    python capture_crl_corpus.py [--force]
"""
import argparse
import datetime as dt
import glob
import io
import json
import os
import re
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SERIES = os.path.join(HERE, "_crl_capture_series.json")
API = "https://api.fda.gov/transparency/crl.json"
UA = {"User-Agent": "pdufa.bio corpus capture (contact via site)"}


def newest_corpus():
    """Path of the newest CRL_corpus_openFDA_YYYY-MM-DD.json on disk (by the date in the name)."""
    files = glob.glob(os.path.join(HERE, "CRL_corpus_openFDA_????-??-??.json"))
    files = [f for f in files if re.search(r"CRL_corpus_openFDA_\d{4}-\d{2}-\d{2}\.json$", f)]
    return max(files, key=lambda f: re.search(r"(\d{4}-\d{2}-\d{2})\.json$", f).group(1)) if files else None


def fetch(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60)
    return json.loads(r.read().decode("utf-8", "replace"))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    today = dt.date.today().isoformat()
    cur = newest_corpus()
    cur_meta = {}
    if cur:
        try:
            cur_meta = json.load(io.open(cur, encoding="utf-8")).get("meta") or {}
        except Exception:
            cur_meta = {}
    cur_total = int(((cur_meta.get("results") or {}).get("total")) or 0)
    cur_upd = str(cur_meta.get("last_updated") or "")

    try:
        head = fetch(API + "?limit=1")
    except Exception as e:
        print(f"capture: openFDA unreachable ({e}); newest snapshot stays authoritative: {os.path.basename(cur) if cur else 'none'}")
        return 0
    meta = head.get("meta") or {}
    total = int(((meta.get("results") or {}).get("total")) or 0)
    upd = str(meta.get("last_updated") or "")
    try:
        cnt = fetch(API + "?count=approval_status").get("results") or []
        counts = {c.get("term"): int(c.get("count") or 0) for c in cnt}
    except Exception:
        counts = {}
    ap_n, un_n = counts.get("Approved"), counts.get("Unapproved")
    # openFDA's last_updated is not monotonic (the 08-29 snapshot says 2026-08-26; the live API
    # said 2026-08-13 on 09-20 for the identical record set), so "changed" is decided on the
    # RECORDS: page the release (five requests) and compare the set of (file, date, status).
    results = []
    skip = 0
    while skip < total:
        page = fetch(f"{API}?limit=100&skip={skip}")
        results.extend(page.get("results") or [])
        skip += 100
        time.sleep(0.3)
    def keyset(recs):
        return sorted((str(r.get("file_name")), str(r.get("letter_date")), str(r.get("approval_status"))) for r in recs)
    cur_keys = []
    if cur:
        try:
            cur_keys = keyset(json.load(io.open(cur, encoding="utf-8")).get("results") or [])
        except Exception:
            cur_keys = []
    changed = a.force or (len(results) == total and keyset(results) != cur_keys)
    written = None
    if changed and total > 0:
        if len(results) != total:
            print(f"capture: paged {len(results)} of {total}; not writing a partial snapshot")
        else:
            out = os.path.join(HERE, f"CRL_corpus_openFDA_{today}.json")
            meta_out = dict(meta); meta_out["results"] = {"skip": 0, "limit": total, "total": total}
            io.open(out, "w", encoding="utf-8").write(json.dumps({"meta": meta_out, "results": results}, ensure_ascii=False))
            written = os.path.basename(out)
            print(f"capture: release changed ({cur_total} -> {total}, last_updated {cur_upd} -> {upd}); wrote {written}")
    else:
        print(f"capture: unchanged ({total} records, same file/date/status set as {os.path.basename(cur) if cur else 'none'}; openFDA last_updated {upd})")

    try:
        series = json.load(io.open(SERIES, encoding="utf-8"))
    except Exception:
        series = {"_what": "One row per check of openFDA transparency/crl: the FDA's CRL release as a time series. "
                           "total/approved/unapproved are openFDA's own counts (approval_status). A snapshot file is "
                           "written only when the release changed.", "rows": []}
    series["rows"] = [r for r in series["rows"] if r.get("checked") != today]
    series["rows"].append({"checked": today, "last_updated": upd, "total": total, "approved": ap_n,
                           "unapproved": un_n, "snapshot": written})
    series["rows"].sort(key=lambda r: r["checked"])
    io.open(SERIES, "w", encoding="utf-8").write(json.dumps(series, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
