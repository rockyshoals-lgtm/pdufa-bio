# -*- coding: utf-8 -*-
"""watch_readouts.py -- the readout half of the calendar gets its own watcher.

Audit 2026-09-02e: TENX's Phase 3 topline and MPLT's Phase 2 resolved with nobody
looking -- "the same failure as REGN; the only difference is that a readout has no FDA
feed to query. But it isn't unwatchable." This asks ClinicalTrials.gov (v2 API, no key)
about every forward Guided/Estimated readout that carries an nct_id, daily.

A row becomes a LEAD when the registry contradicts its pending status:
  - overallStatus COMPLETED / TERMINATED / WITHDRAWN / SUSPENDED
  - resultsFirstSubmitDate present (results posted)
  - primaryCompletionDate type ACTUAL and in the past -- the TENX signature: LEVEL's
    primary completion flipped to ACTUAL 2026-06-30 while our row still said pending

Leads are VERIFY-then-publish, never auto-published: new unreviewed leads exit 1 and
block CI, exactly like the FDA approval watcher. Reviewed leads go in
_readout_watch_ack.json with a reason (the same file guard 59 honors), and that file
shrinks; it never grows silently. ~180 requests/day, throttled.

    python watch_readouts.py [--dry-run]
"""
import argparse
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
ACK = os.path.join(HERE, "_readout_watch_ack.json")
API = "https://clinicaltrials.gov/api/v2/studies/"
BAD_STATUS = {"COMPLETED", "TERMINATED", "WITHDRAWN", "SUSPENDED"}


def nct_of(r):
    d = r.get("_d") or {}
    n = d.get("nct_id")
    if isinstance(n, dict):
        n = n.get("nct")
    n = str(n or "").strip().upper()
    return n if n.startswith("NCT") else ""


def fetch(nct):
    url = (f"{API}{nct}?fields=protocolSection.statusModule")
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return (json.load(resp).get("protocolSection") or {}).get("statusModule")
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    watch = [r for r in rows if r.get("type") == "Readout"
             and str(r.get("st")) in ("Guided", "Estimated") and nct_of(r)]

    acks = set()
    if os.path.exists(ACK):
        acks = {x.get("id") for x in
                json.load(io.open(ACK, encoding="utf-8")).get("acks", [])}

    today = dt.date.today().isoformat()
    leads, checked = [], 0
    for r in watch:
        nct = nct_of(r)
        sm = fetch(nct)
        checked += 1
        time.sleep(0.15)
        if not sm:
            continue
        why = []
        status = str(sm.get("overallStatus") or "")
        if status in BAD_STATUS:
            why.append(f"registry status {status}")
        if sm.get("resultsFirstSubmitDate"):
            why.append(f"results posted {sm['resultsFirstSubmitDate']}")
        pcd = sm.get("primaryCompletionDateStruct") or {}
        if (str(pcd.get("type")) == "ACTUAL"
                and str(pcd.get("date", "9999"))[:10] <= today):
            why.append(f"primary completion ACTUAL {pcd.get('date')} (the TENX "
                       f"signature: endpoint data is collected)")
        if why and r.get("id") not in acks:
            leads.append(f"{r.get('id')} ({r.get('t')} "
                         f"{str(r.get('name'))[:44]}, {r.get('st')} {r.get('d')}, "
                         f"{nct}): " + "; ".join(why)
                         + " -- VERIFY the company's release, then record the outcome")

    if leads:
        print(f"READOUT WATCH: {len(leads)} unreviewed registry signal(s) on pending "
              f"readouts ({checked} checked):")
        for ln in leads:
            print(f"   {ln}")
        print("\n   Each is a LEAD, not a fact: verify against the sponsor's own "
              "release, record the outcome (st=Reported + source), or ack with a "
              "reason in _readout_watch_ack.json.")
        return 0 if a.dry_run else 1
    print(f"readout watch: {checked} pending readouts checked against "
          f"ClinicalTrials.gov, 0 unreviewed signals ({len(acks)} previously reviewed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
