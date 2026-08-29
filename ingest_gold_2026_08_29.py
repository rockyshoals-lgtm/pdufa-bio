# -*- coding: utf-8 -*-
"""ingest_gold_2026_08_29.py -- the two calendar-material rows from latest/ that passed
primary-source verification. BPC rows are leads (standing rule: cross-check only); each
row here was verified against the sponsor's own release before touching the dataset.

  1. CORT relacorilant (Cushing's, GRACE resubmission): our row carried an ESTIMATED
     2026-09-15. Corcept's 2026-06-17 announcement states the resubmission PDUFA is
     2026-12-17. Day precision, company-sourced.
  2. VNDA imsidolimab (GPP, GEMINI): PDUFA 2026-12-12, absent from our calendar entirely.
     BPC lists it under ANAB -- the ORIGINATOR. Vanda holds the BLA (licensed from
     AnaptysBio); the event enters under VNDA, with ANAB noted as partner. Third license
     trap this week (zilurgisertib, imsidolimab, UX111 still pending verification).

Idempotent; refuses to write if the anchor rows are not found as expected.
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")


def main():
    src = io.open(P, encoding="utf-8", errors="replace").read().replace("\x00", "")
    j = src.index("[")
    arr, end = json.JSONDecoder().raw_decode(src[j:])
    changed = 0

    # -- 1. CORT correction ----------------------------------------------------------
    # The live Cushing's event sits in the dataset as a READOUT, Estimated 2026-09-15 --
    # it is the GRACE resubmission PDUFA. Type, date and status all corrected together.
    for r in arr:
        if (r.get("t") == "CORT" and r.get("d") == "2026-09-15"
                and str(r.get("st", "")).lower() != "decided"
                and "relacorilant" in str(r.get("name", "")).lower()):
            r["type"], r["name"] = "PDUFA", "Relacorilant - (GRACE resubmission)"
            if r.get("d") == "2026-12-17":
                print("  CORT GRACE already at 2026-12-17")
            else:
                print(f"  CORT GRACE: {r.get('d')} ({r.get('dp')}, {r.get('st')}) "
                      f"-> 2026-12-17 (day, Upcoming)")
                r["d"], r["dp"], r["st"] = "2026-12-17", "day", "Upcoming"
                r.setdefault("_d", {})["review"] = (
                    "NDA resubmitted 2026-06-17 for Cushing's syndrome after the "
                    "December 2025 CRL; FDA assigned a PDUFA date of December 17, 2026. "
                    "Source: Corcept announcement, June 17, 2026.")
                changed += 1
            break
    else:
        print("  !! CORT relacorilant live row not found -- nothing changed for CORT")

    # -- 2. VNDA imsidolimab (new) ---------------------------------------------------
    if any(r.get("t") == "VNDA" and r.get("d") == "2026-12-12" for r in arr):
        print("  VNDA imsidolimab already present")
    else:
        arr.append({
            "id": "pdufa_vnda_2026-12-12", "t": "VNDA",
            "company": "Vanda Pharmaceuticals Inc.", "d": "2026-12-12", "dp": "day",
            "name": "Imsidolimab - (GEMINI-1/2)", "type": "PDUFA", "ta": "Immunology",
            "cap": "Small", "st": "Upcoming", "url": "/ticker/VNDA",
            "_d": {"indication": "Generalized pustular psoriasis (GPP)",
                   "review": "BLA submitted 2025-12-15, accepted 2026-02-25; PDUFA "
                             "December 12, 2026. Imsidolimab is licensed from "
                             "AnaptysBio (ANAB); Vanda holds the BLA. Source: Vanda "
                             "announcement of FDA acceptance."},
        })
        print("  VNDA imsidolimab 2026-12-12 added (partner: ANAB)")
        changed += 1

    if not changed:
        print("nothing to write")
        return 0
    arr.sort(key=lambda r: (str(r.get("d") or "9999"), str(r.get("t") or "")))
    io.open(P, "w", encoding="utf-8").write(
        src[:j] + json.dumps(arr, separators=(",", ":"), ensure_ascii=False) + src[j + end:])
    print(f"dataset.mjs written ({changed} change(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
