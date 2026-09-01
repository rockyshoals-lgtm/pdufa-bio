# -*- coding: utf-8 -*-
"""watch_fda_approvals.py -- independent early-approval watch against FDA's own data.

THE GAP THIS CLOSES (David, 2026-09-01): every safeguard we had was downstream of our
own news crawl -- if nobody told us about an approval, nothing looked for it. But the
FDA deciding EARLY is the norm (16 of 28 sourced 2026 decisions came before the goal
date; CORT was 108 days early), and the crawl's attention keys off the goal date.

This watcher asks FDA directly. Daily, for every Upcoming day-precision PDUFA event, it
queries the openFDA Drugs@FDA endpoint by drug name and flags any AP (approved)
submission dated within the last 60 days that falls in the same-review-cycle window of
the event's goal date (-180..+45). Probe results 2026-09-01: garetosmab's Aug 19
approval appeared in the feed by Aug 28 (~9-day lag); capivasertib's Jun 12 approval is
recorded to the exact day. So this is a SAFETY NET measured in days, not a same-day
detector -- the crawl stays the fast path.

Discipline:
  - A hit is a LEAD, never an auto-publish. Verify against the sponsor/FDA release,
    publish the decision page, and the sync propagates it (verify-then-publish).
  - NEW unacknowledged hits EXIT 1 so CI blocks and the lead gets looked at.
    Reviewed hits go in _fda_watch_ack.json (with a reason) and stop alerting --
    same pattern as _calendar_flags_known.json. Shrink it; never grow it silently.
  - ~55 events -> ~55 requests/day, well inside openFDA's unkeyed limits.

    python watch_fda_approvals.py [--dry-run]   (dry-run: report, never exit 1)
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
SITE = os.path.join(HERE, "pdufa_site_src")
ACK = os.path.join(HERE, "_fda_watch_ack.json")
API = "https://api.fda.gov/drug/drugsfda.json"
LOOKBACK_DAYS = 60


def search_terms(name):
    """Best query candidates from an event name: parenthetical generic first (it is the
    INN openFDA indexes), then the lead brand/code token. 'Mim8 (denecimig)' ->
    ['denecimig', 'Mim8']."""
    s = str(name or "")
    out = []
    STOP = {"combination", "subcutaneous", "extension", "sublingual", "injection",
            "tablet", "tablets", "capsule", "capsules", "solution", "release",
            "weekly", "monthly", "intravenous", "topical", "inhaled", "prefilled"}
    for par in re.findall(r"\(([^)]+)\)", s):
        for w in re.findall(r"[A-Za-z][a-z]{5,}", par):   # generic-looking, lowercase-ish
            if w.lower() not in STOP:   # dosage-form words query the wrong universe:
                out.append(w)           # 'sublingual' hit an unrelated dexmedetomidine
    lead = re.search(r"[A-Za-z][A-Za-z0-9]{3,}", s)
    if lead and lead.group(0) not in out:
        out.append(lead.group(0))
    return out[:2]


def query(term):
    # openFDA needs EXPLICIT +OR+ between clauses; bare '+' returns NOT_FOUND
    # (proven 2026-09-01: the first version silently found nothing for garetosmab).
    t = urllib.parse.quote(f'"{term}"')
    q = (f"products.active_ingredients.name:{t}+OR+openfda.generic_name:{t}"
         f"+OR+openfda.brand_name:{t}")
    url = f"{API}?search={q}&limit=5"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.load(r).get("results", [])
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    up = [r for r in rows if r.get("type") == "PDUFA" and r.get("dp") == "day"
          and str(r.get("st", "")).lower() != "decided" and r.get("d")]

    acks = {}
    if os.path.exists(ACK):
        acks = {(f["ticker"], f["ap_date"]): f.get("reason", "")
                for f in json.load(io.open(ACK, encoding="utf-8")).get("acks", [])}

    today = dt.date.today()
    floor = (today - dt.timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")
    new_hits, known = [], 0
    for r in up:
        tk, goal, name = str(r.get("t", "")).upper(), str(r.get("d"))[:10], r.get("name")
        gdate = dt.date.fromisoformat(goal)
        for term in search_terms(name):
            for res in query(term):
                for s in res.get("submissions", []) or []:
                    if s.get("submission_status") != "AP":
                        continue
                    # Administrative supplements are not decisions on our tracked
                    # applications: WINREVAIR's SUPPL-13 AP 2026-08-12 was LABELING
                    # while the HYPERION efficacy sBLA (goal 09-21) was still pending.
                    # A PDUFA event resolves as an ORIG or an EFFICACY/TYPE-coded
                    # supplement; unknown class codes stay IN (fail loud, not silent).
                    cls = str(s.get("submission_class_code", "")).upper()
                    if cls in ("LABELING", "MANUFACTURING (CMC)", "MANUFACTURING",
                               "REMS", "PACKAGE CHANGE"):
                        continue
                    sd = str(s.get("submission_status_date", ""))
                    if not (sd >= floor and re.match(r"^\d{8}$", sd)):
                        continue
                    ad = dt.date(int(sd[:4]), int(sd[4:6]), int(sd[6:8]))
                    if not (-180 <= (ad - gdate).days <= 45):
                        continue
                    key = (tk, ad.isoformat())
                    if key in acks:
                        known += 1
                        continue
                    new_hits.append(
                        f"{tk} {str(name)[:40]} (goal {goal}): FDA feed shows AP "
                        f"{ad.isoformat()} on '{term}' "
                        f"({s.get('submission_type')}-{s.get('submission_number')}, "
                        f"class {cls or 'unstated'}) "
                        f"-- VERIFY against the sponsor/FDA release, then publish")
            time.sleep(0.3)

    if new_hits:
        print(f"EARLY-APPROVAL WATCH: {len(new_hits)} unreviewed FDA-feed approval(s) "
              f"on armed events:")
        seen = set()
        for h in new_hits:
            if h not in seen:
                print(f"   {h}")
                seen.add(h)
        print(f"\n   Each is a LEAD, not a fact: verify, publish the decision page, and "
              f"the sync propagates it. Reviewed non-events go in _fda_watch_ack.json.")
        return 0 if a.dry_run else 1
    print(f"early-approval watch: {len(up)} armed events checked against FDA's feed, "
          f"0 unreviewed approvals ({known} previously reviewed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
