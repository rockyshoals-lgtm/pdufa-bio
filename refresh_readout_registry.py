# -*- coding: utf-8 -*-
"""Re-sync pending readout rows with ClinicalTrials.gov, WITHOUT asserting any result.

THE PROBLEM. 50 readout rows carry dates that have already passed, some by three months, and
watch_readouts flags 22 where the registry now contradicts the pending status outright -- trials
marked COMPLETED or TERMINATED, primary completion dates flipped from ESTIMATED to ACTUAL, and
in one case (HUMA) results posted in March 2025 against a row still advertising a readout in
September 2027.

WHAT THIS DOES AND DOES NOT DO. /readouts says, in its own words, that these dates are
"estimated primary-completion windows from ClinicalTrials.gov, not fixed announcements - they
shift". The date IS the registry's primary-completion date. So when the registry moves it, or
firms it from ESTIMATED to ACTUAL, refreshing our copy is not new editorial judgement -- it is
keeping the field equal to its own definition. That is what this does.

It does NOT set an outcome, and does not change `st`. A registry status of COMPLETED means the
trial finished, not that the sponsor has said what happened; the result is still a LEAD that
needs the company's own release, and those stay in the watcher's queue. Conflating "the trial
completed" with "the readout was positive" would be exactly the fabrication this codebase keeps
having to undo.

    python refresh_readout_registry.py [--dry-run]
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
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
API = "https://clinicaltrials.gov/api/v2/studies/{nct}?fields=ProtocolSection"
UA = "pdufa.bio builder rockyshoals@gmail.com"
TODAY = dt.date.today().isoformat()


def fetch(nct):
    req = urllib.request.Request(API.format(nct=nct), headers={"User-Agent": UA})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=45).read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    ps = d.get("protocolSection", {})
    st = ps.get("statusModule", {})
    pc = st.get("primaryCompletionDateStruct", {}) or {}
    return {
        "status": st.get("overallStatus"),
        "pcd": pc.get("date"),
        "pcd_type": (pc.get("type") or "").upper(),
        "results_posted": (st.get("resultsFirstSubmitDate")
                           or st.get("resultsFirstPostDateStruct", {}).get("date")),
        "updated": (st.get("lastUpdateSubmitDate")
                    or st.get("lastUpdatePostDateStruct", {}).get("date")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])

    todo = []
    for r in rows:
        if r.get("type") != "Readout":
            continue
        # ESTIMATED ONLY. The first run of this script moved company-GUIDED rows too, and
        # test_guided_readouts_current caught it: SLS's REGAL Phase 3 topline is guided by
        # SELLAS, and the script rewrote that guidance to NCT04229979's registry primary
        # completion date. An Estimated row's date IS the registry window, which is why
        # re-syncing it is just keeping a field equal to its own definition. A Guided row's
        # date is what the COMPANY said, and the registry has no authority to overwrite it --
        # doing so silently replaces a sourced company statement with a different number.
        if str(r.get("st") or "") != "Estimated":
            continue
        # `_d.nct_id` is a dict on enriched rows and a bare "NCT…" string on older ones
        raw = (r.get("_d") or {}).get("nct_id")
        nct = raw.get("nct") if isinstance(raw, dict) else (raw if isinstance(raw, str) else None)
        if nct and str(nct).upper().startswith("NCT"):
            todo.append((r, str(nct)))

    print(f"checking {len(todo)} pending readout(s) with an NCT id")
    moved = firmed = noted = 0
    for n, (r, nct) in enumerate(todo, 1):
        info = fetch(nct)
        time.sleep(0.25)
        if not info or not info.get("pcd"):
            continue
        dd = r.setdefault("_d", {})
        if not isinstance(dd.get("nct_id"), dict):      # promote the bare-string form
            dd["nct_id"] = {"nct": nct}
        blk = dd["nct_id"]
        old_pcd = blk.get("pcd")
        blk.update({"nct": nct, "status": (info["status"] or "").lower(),
                    "pcd": info["pcd"], "pcd_type": info["pcd_type"].lower(),
                    "updated": info["updated"],
                    "ongoing": (info["status"] or "").upper() in
                               ("RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION",
                                "NOT_YET_RECRUITING")})
        if info.get("results_posted"):
            blk["results_posted"] = info["results_posted"]

        pcd = str(info["pcd"])
        pcm = pcd[:7]
        cur = str(r.get("dm") or str(r.get("d") or "")[:7])

        # the published window IS the registry primary-completion window; keep them equal
        if len(pcm) == 7 and pcm != cur and r.get("dp") in ("month", "quarter", "year", None):
            r["dm"] = pcm
            # keep `d` as the month-midpoint sentinel the rest of the pipeline expects
            r["d"] = f"{pcm}-15"
            r["dp"] = "month"
            moved += 1
            print(f"  [{n}/{len(todo)}] {r.get('t'):<6} {nct}  window {cur} -> {pcm}"
                  f"  ({info['pcd_type'].lower()}, registry {blk['status']})")

        if info["pcd_type"] == "ACTUAL" and old_pcd != info["pcd"]:
            firmed += 1

        if (info["status"] or "").upper() in ("TERMINATED", "WITHDRAWN", "SUSPENDED"):
            dd["registry_note"] = (
                f"ClinicalTrials.gov records {nct} as {info['status'].replace('_', ' ').lower()} "
                f"as of {TODAY}, with primary completion {info['pcd']} "
                f"({info['pcd_type'].lower()}). A terminated or withdrawn trial may never "
                f"produce the readout this row anticipated. We have not seen a sponsor statement "
                f"and record no outcome.")
            noted += 1

    if a.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    io.open(DATASET, "w", encoding="utf-8").write(
        src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    print(f"\n{moved} window(s) re-synced to the registry, {firmed} primary-completion date(s) "
          f"now ACTUAL, {noted} terminated/withdrawn row(s) annotated. No outcome was set: the "
          f"result of each remains a lead for the sponsor's own release.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
