# -*- coding: utf-8 -*-
"""merge_redteam_readouts.py -- merge a RED-TEAMED miner file into the site. Merge, never replace.

Audit 2026-10-11 (R7): the new phase_readout_miner.py is not a superset of what the site holds (27 Guided
tickers the site sourced from SEC filings have no row in the miner's output), so a straight replacement would
be a regression. This script is the only path from a miner run to the dataset, and its contract is:

  1. NO SITE ROW IS EVER REMOVED OR RE-DATED BY THE REGISTRY HERE. Estimated rows follow the registry via
     refresh_readout_registry.py; Guided rows follow the company via this script, with a date_history entry.
  2. Only rows a human has red-teamed are read: the file must carry `rt_verdict`, and only
     PUBLISH / PUBLISH_FIX / PUBLISH_CAVEAT rows are used, with the `rt_*` columns (window, drug, trial,
     indication, presentation type, session date) taking precedence over the miner's.
  3. company_guidance rows become Guided readout rows (new) or move an existing Guided row for the same
     ticker + program to the window a LATER filing states (date_history records the move and the filing).
     Half-year windows are published at YEAR precision (the schema has no half); the half is kept in
     `_d.guided_window` and the guidance sentence.
  4. conference_schedule rows become hand-verified presenter rows in
     catalysts_out/conference_presenters_VERIFIED_{date}.csv, which build_conferences.py publishes.
  5. ctgov_pcd rows are NOT merged here (R5/R8: most are big-pharma Phase 1/2 completion windows). They stay
     in the red-team file for a ruling.

    python merge_redteam_readouts.py odin_cowork_dropbox/2026-10-11_REDTEAM_miner_NEW_2026-10-11.csv [--apply]
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
SEC_TICKERS = os.path.join(HERE, "sec_company_tickers.json")
CONF_JSON = os.path.join(HERE, "conferences.json")
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

TODAY = eastern_today().isoformat()
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
USE = {"PUBLISH", "PUBLISH_FIX", "PUBLISH_CAVEAT"}
LAST = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def window_fields(win):
    """'2027-Q1' / '2026-11' / '2027-H2' / '2027' -> (d, dm, dp, guided_precision)."""
    w = str(win or "").strip()
    m = re.match(r"^(\d{4})-Q([1-4])$", w)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        em = 3 * q
        return f"{y}-{em:02d}-{LAST[em - 1]:02d}", f"{y}-{em:02d}", "quarter", "quarter"
    m = re.match(r"^(\d{4})-(\d{2})$", w)
    if m:
        return f"{w}-15", w, "month", "month"
    m = re.match(r"^(\d{4})-H([12])$", w)
    if m:
        y = int(m.group(1))
        return f"{y}-12-31", None, "year", "half"
    m = re.match(r"^(\d{4})", w)
    if m:
        return f"{m.group(1)}-12-31", None, "year", "year"
    return None, None, None, None


def program_token(s):
    s = str(s or "").split(";")[0].split("(")[0].strip()
    return re.sub(r"[^a-z0-9]", "", s.lower().split()[0]) if s.split() else ""


def load_rows():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    return src, i, j, json.loads(src[i:j])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--apply", action="store_true", help="write; default is a dry run")
    a = ap.parse_args()
    rt = list(csv.DictReader(io.open(a.csv, encoding="utf-8-sig", errors="replace")))
    if not rt or "rt_verdict" not in rt[0]:
        sys.exit("refusing: the file carries no rt_verdict column; only a red-teamed file is merged")
    names = {v["ticker"]: v["title"] for v in json.load(io.open(SEC_TICKERS, encoding="utf-8")).values()}
    conf_codes = {c["code"].upper(): c for c in json.load(io.open(CONF_JSON, encoding="utf-8"))["conferences"]}
    src, i, j, rows = load_rows()
    n_before = len(rows)
    guided = {}
    for r in rows:
        if r.get("type") == "Readout" and r.get("st") == "Guided":
            guided.setdefault((r["t"], program_token((r.get("_d") or {}).get("program") or r.get("name"))), []).append(r)

    use = [r for r in rt if r.get("rt_verdict") in USE]
    # ---- company guidance -> Guided rows (dedupe by ticker + program + window, latest filing wins)
    best = {}
    for r in use:
        if r.get("date_basis") != "company_guidance":
            continue
        key = (r["ticker"].upper(), program_token(r.get("rt_drug")), r.get("rt_window"))
        if key not in best or str(r.get("filed")) > str(best[key].get("filed")):
            best[key] = r
    added, moved, kept = [], [], []
    for (tk, prog, win), r in sorted(best.items()):
        d, dm, dp, gp = window_fields(win)
        if not d:
            print(f"  skip {tk} {prog}: window {win!r} unreadable")
            continue
        drug = str(r.get("rt_drug") or "").split(";")[0].strip()
        if drug.count("(") != drug.count(")"):
            drug = drug.split("(")[0].strip()
        trial = str(r.get("rt_trial") or "").strip()
        trial = re.sub(r"\s*\((?:unnamed)[^)]*\)", "", trial).strip()
        name = f"{drug} {trial}".strip() if trial and trial.lower() not in drug.lower() else drug
        name = re.sub(r"\s+", " ", name)
        if len(name) > 70:
            short = drug.split("(")[0].strip()
            name = f"{short} {trial}".strip() if trial else short
        if len(name) > 70:
            name = short
        quote = str(r.get("rt_quote") or "").strip()
        existing = guided.get((tk, prog), [])
        same = [e for e in existing if str(e.get("dm") or e.get("d", "")[:7]) == (dm or d[:7]) and e.get("dp") == dp]
        if same:
            kept.append(f"{tk} {name}: already on site as {same[0]['id']}")
            continue
        # Move an existing Guided row only when a LATER filing re-dates a readout whose window has NOT
        # yet ended. A row whose window has passed is a different question (reported, or not yet) and a
        # later-dated readout of the same program (GPCR: SAD reported Sep 2026, MAD guided 1H 2027) is a
        # NEW row, never a rewrite of the old one.
        later = [e for e in existing if str((e.get("_d") or {}).get("guided_filed") or "") < str(r.get("filed") or "")
                 and str(e.get("d") or "") >= TODAY]
        if later and len(existing) == 1:
            e = later[0]
            old = f"{e.get('d')} ({e.get('dp')})"
            hist = (e.setdefault("_d", {})).get("date_history") or []
            if not hist:
                hist.append({"date": str(e["id"])[-10:], "note": "date the row was keyed on when created"})
            hist.append({"date": d, "changed": TODAY,
                         "why": (f"Company guidance moved the window: {names.get(tk, tk)}'s {r.get('form')} filed "
                                 f"{r.get('filed')} states \"{quote[:220]}\" (red team 2026-10-11).")})
            e["_d"]["date_history"] = hist
            e["d"], e["dp"] = d, dp
            if dm:
                e["dm"] = dm
            else:
                e.pop("dm", None)
            e["url"] = r.get("source_url") or e["url"]
            e["ua"] = NOW
            e["_d"].update({"guided_precision": gp, "guided_form": r.get("form"), "guided_filed": r.get("filed"),
                            "guidance_text": quote, "source_url": r.get("source_url"), "guided_window": win})
            if r.get("rt_indication"):
                e["_d"]["indication"] = r.get("rt_indication")
            moved.append(f"{e['id']}: {old} -> {d} ({dp}) per {r.get('form')} {r.get('filed')}")
            continue
        rid = f"readout_{tk.lower()}_{d}"
        if any(x.get("id") == rid for x in rows):
            rid = f"{rid}-{prog[:8]}"
        row = {"id": rid, "t": tk, "company": names.get(tk, tk), "d": d, "dp": dp, "name": name,
               "type": "Readout", "ta": "", "cap": "", "st": "Guided", "url": r.get("source_url"), "ua": NOW,
               "_d": {"nct_id": None, "indication": r.get("rt_indication") or None, "market_cap_usd": None,
                      "source": "company guidance (SEC filing)", "guided_precision": gp,
                      "guided_form": r.get("form"), "guided_filed": r.get("filed"), "program": drug,
                      "guided_window": win, "guidance_text": quote, "source_url": r.get("source_url"),
                      "red_team": "2026-10-11: verbatim timing sentence read from the filing; "
                                  + str(r.get("rt_note") or "")[:300]}}
        if dm:
            row["dm"] = dm
        rows.append(row)
        added.append(f"{rid}: {name} {win} ({r.get('form')} {r.get('filed')})")

    # ---- conference rows -> verified presenter rows
    vrows = []
    for r in use:
        if r.get("date_basis") != "conference_schedule":
            continue
        code = str(r.get("conference") or "").upper()
        c = conf_codes.get(code) or next((v for k, v in conf_codes.items() if k.replace(" ", "") == code), None)
        if not c:
            print(f"  skip conference row {r['ticker']}: unknown meeting {code!r}")
            continue
        tk = r["ticker"].upper()
        vrows.append({"ticker": tk, "cik": "", "company": names.get(tk, tk), "conference": c["code"],
                      "conf_start": c["start"], "drug": r.get("rt_drug") or "", "pres_type": r.get("rt_pres_type") or "",
                      "filing_url": r.get("source_url") or "", "accession": "", "filed": r.get("filed") or "",
                      "matched_sentence": (str(r.get("rt_trial") or "") + "; session " + str(r.get("rt_session_date") or "")).strip("; "),
                      "retrieved_at": r.get("retrieved_at") or NOW, "reviewer": "cowork-redteam 2026-10-11",
                      "review_note": str(r.get("rt_note") or "")[:300]})
    vpath = os.path.join(HERE, "catalysts_out", "conference_presenters_VERIFIED_2026-10-11.csv")

    print(f"dataset rows {n_before} -> {len(rows)}; readout rows added {len(added)}, moved {len(moved)}, "
          f"already present {len(kept)}; verified presenter rows {len(vrows)}")
    for x in added:
        print("  + " + x)
    for x in moved:
        print("  ~ " + x)
    for x in kept:
        print("  = " + x)
    if len(rows) < n_before:
        sys.exit("CONTRACT VIOLATED: fewer rows after merge")
    if not a.apply:
        print("dry run: nothing written")
        return 0
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    with io.open(vpath, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(vrows[0].keys()) if vrows else ["ticker"])
        w.writeheader()
        for v in vrows:
            w.writerow(v)
    print(f"written: {DATASET} and {vpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
