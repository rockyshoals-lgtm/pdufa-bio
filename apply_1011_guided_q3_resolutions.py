# -*- coding: utf-8 -*-
"""apply_1011_guided_q3_resolutions.py -- the 26 company-Guided Q3-2026 readouts, each resolved against the
sponsor's own 8-K/6-K exhibits (EDGAR full-text search, 2026-07-01 to 2026-10-11, read 2026-10-11).

tests/test_guided_readouts_current.py: a Guided date that has passed needs the outcome recorded or a
written reason. Three outcomes here, all sourced to the filing read:
  REPORTED  the sponsor's exhibit states the readout (headline quoted): st=Reported, d=exhibit date,
            url=exhibit, _d.review=the headline's own words, readout_reported_manual.json entry.
  MOVED     the sponsor's later filing re-dates the readout (MBRX: Part A enrolment complete, data Q1 2027).
  NO_TOPLINE no results exhibit found for the program in the window: _d.resolution no_topline, dated, with
            the search stated; served "No topline as of 2026-10-11".
  ACK       the row's program or the exhibit needs a human reading before a status is claimed.
Facts only; no outcome is inferred beyond the headline. RULE 1: exhibit dates are EDGAR filing dates.
"""
import datetime as dt
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
MANUAL = os.path.join(HERE, "readout_reported_manual.json")
ACK = os.path.join(HERE, "_readout_watch_ack.json")
TODAY = "2026-10-11"
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
A = "https://www.sec.gov/Archives/edgar/data/"
_CIK = {v["ticker"]: str(v["cik_str"]) for v in json.load(io.open(os.path.join(HERE, "sec_company_tickers.json"), encoding="utf-8")).values()}


def exh(tk, accn, fn):
    return f"{A}{_CIK[tk]}/{accn}/{fn}"


REPORTED = {
    "readout_dftx_2026-09-30": ("2026-09-14", exh("DFTX", "000110465926107275", "tm2625365d1_ex99-1.htm"), "positive",
        "Definium Therapeutics announced positive topline results from the Phase 3 Panorama study of DT120 ODT in "
        "generalized anxiety disorder on September 14, 2026: the study met its primary and all key secondary efficacy "
        "endpoints (8-K exhibit 99.1)."),
    "readout_evmn_2026-09-30": ("2026-09-09", exh("EVMN", "000119312526385430", "evmn-ex99_1.htm"), "negative",
        "Evommune announced top-line results from the EVO756 Phase 2b trial in moderate-to-severe atopic dermatitis on "
        "September 9, 2026: the trial did not meet its primary endpoint (8-K exhibit 99.1)."),
    "readout_gpcr_2026-09-30": ("2026-09-08", exh("GPCR", "000110465926105688", "tm2624945d1_ex99-1.htm"), "positive",
        "Structure Therapeutics reported clinical data across its oral amylin (ACCG-2671) and GLP-1 programs on "
        "September 8, 2026, describing the ACCG-2671 results as positive (8-K exhibit 99.1)."),
    "readout_immx_2026-09-30": ("2026-09-29", exh("IMMX", "000149315226044761", "ex99-1.htm"), "positive",
        "Immix Biopharma announced an interim update across all NEXICART-2 patients on September 29, 2026: an 89% "
        "complete response rate (8-K exhibit 99.1). Interim data, not a final readout."),
    "readout_iron_2026-09-30": ("2026-09-10", exh("IRON", "000119312526387351", "iron-ex99_1.htm"), "reported",
        "Disc Medicine presented initial results from the RESTORE-PV Phase 2 trial of DISC-3405 in polycythemia vera "
        "at the SOHO Annual Meeting, announced September 10, 2026 (8-K exhibit 99.1). Initial results; outcome not "
        "characterised in the headline."),
    "readout_kod_2026-09-30": ("2026-09-28", exh("KOD", "000119312526403481", "d185059dex991.htm"), "positive",
        "Kodiak Sciences announced on September 28, 2026 that Zenkuda and tabirafusp-ted (KSI-501) met the primary "
        "endpoints in the pivotal DAYBREAK trial in wet AMD (8-K exhibit 99.1)."),
    "readout_phvs_2026-09-30": ("2026-09-08", exh("PHVS", "000119312526384339", "phvs-ex99_1.htm"), "positive",
        "Pharvaris announced positive topline data from the CHAPTER-3 pivotal study of deucrictibant XR for prophylaxis "
        "of HAE attacks on September 8, 2026: primary endpoint met, 83% attack-rate reduction versus placebo "
        "(6-K exhibit 99.1)."),
    "readout_tecx_2026-09-30": ("2026-09-29", exh("TECX", "000119312526407823", "d20857dex991.htm"), "positive",
        "Tectonic Therapeutic announced favorable Phase 1 safety, tolerability and PK results for TX2100 in hereditary "
        "hemorrhagic telangiectasia on September 29, 2026 (8-K exhibit 99.1)."),
    "readout_abcl_2026-09-30": ("2026-08-10", exh("ABCL", "000170305726000053", "a2026-08x10abcl635phase2.htm"), "reported",
        "AbCellera announced ABCL635 Phase 2 results on August 10, 2026 (8-K exhibit 99.1); recorded in "
        "readout_reported_manual.json on the day with the company's release."),
    "readout_alms_2026-09-30": ("2026-09-01", exh("ALMS", "000110465926104145", "tm2624540d1_ex99-2.htm"), "reported",
        "Alumis presented LUMUS Phase 2b topline results for envudeucitinib in moderate-to-severe systemic lupus "
        "erythematosus on September 1, 2026 (8-K exhibit 99.2, investor deck); the deck says key insights support a "
        "path to Phase 3 and does not state the primary endpoint result in its summary. This row's earlier label "
        "'anifrolumab' was an extraction error."),
}
MOVED = {
    "readout_mbrx_2026-09-30": ("2027-03-31", "2027-03", "quarter",
        exh("MBRX", "000143774926031419", "ex_1020544.htm"), "2026-09-29",
        "Moleculin Biotech Completes Enrollment in Part A of Phase 2/3 R/R AML MIRACLE Trial, Keeping Program on Track "
        "for Q1 2027 Data Readout"),
}
NO_TOPLINE = ["readout_aard_2026-09-30", "readout_bolt_2026-09-30", "readout_mnkd_2026-09-30",
              "readout_ocgn_2026-09-30", "readout_pmn_2026-09-30", "readout_ppbt_2026-09-30",
              "readout_scyx_2026-09-30", "readout_sttk_2026-09-30", "readout_whwk_2026-09-30",
              "readout_xene_2026-09-30"]
ACKS = {
    "readout_alzn_2026-08-31": "2026-10-11: the only Q3 exhibit (2026-09-29 EX-99.1) is an MGH 7T lithium PK-imaging "
                               "results poster from a Phase 1/2A study, not the Phase II bipolar topline this row guides; "
                               "no Phase II results exhibit through 2026-10-11. Needs a human reading of the row's program.",
    "readout_roiv_2026-09-30": "2026-10-11: brepocitinib was approved as LISRAYA on 2026-08-27 (ROIV 8-K EX-99.1 2026-08-27); "
                               "no brepocitinib readout exhibit in Q3. The row's guided program needs a human reading.",
    "readout_syre_2026-09-30": "2026-10-11: Spyre's 2026-09-08 release (SPY003 SKYLINE Part A) states proof-of-concept is "
                               "complete for all three components; SPY001's own Part A date was not in the 2026-07-01 to "
                               "10-11 exhibits read. Confirm SPY001's release date before marking Reported.",
    "readout_vktx_vanquish2_2026q3": "2026-10-11: Viking's 2026-09-22 EX-99.1 is the Phase 2 maintenance study of VK2735, not "
                                     "VANQUISH-2; no VANQUISH-2 topline exhibit through 2026-10-11.",
    "readout_vtgn_2026-09-30": "2026-10-11: Vistagen's 2026-09-22 EX-99.1 is preliminary open-label-extension data from "
                               "PALISADE-4; the pivotal topline this row guides is not in the exhibits through 2026-10-11.",
    "readout_evmn_2026-09-30": "2026-10-11: marked Reported from the 2026-09-09 EX-99.1 (did not meet primary endpoint).",
}


def main():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    by = {r["id"]: r for r in rows}
    man = json.load(io.open(MANUAL, encoding="utf-8"))
    have = {m["id"] for m in man["reported"]}
    n_rep = n_mv = n_nt = 0
    for rid, (d, url, outcome, review) in REPORTED.items():
        r = by.get(rid)
        if not r:
            print("missing", rid); continue
        old = f"{r.get('d')} ({r.get('dp')})"
        r["st"], r["d"], r["dp"], r["url"], r["ua"] = "Reported", d, "day", url, NOW
        r.pop("dm", None)
        dd = r.setdefault("_d", {})
        dd["review"] = review
        dd["reported_source_url"] = url
        hist = dd.get("date_history") or []
        if not hist:
            hist.append({"date": rid[-10:], "note": "date the row was keyed on when created"})
        hist.append({"date": d, "changed": TODAY,
                     "why": f"The sponsor's SEC exhibit of {d} states the readout; a reported row carries the day it was reported. Was {old}."})
        dd["date_history"] = hist
        if rid == "readout_alms_2026-09-30":
            r["name"] = "Envudeucitinib LUMUS Phase 2b topline (SLE)"
            dd["program"] = "envudeucitinib"
        if rid not in have:
            man["reported"].append({"id": rid, "t": r["t"], "drug": dd.get("program") or r["name"], "reported_date": d,
                                    "outcome": outcome, "summary": review, "source_url": url,
                                    "guided_window": "Q3 2026", "note": "red team 2026-10-11, EDGAR exhibit read"})
        n_rep += 1
    for rid, (d, dm, dp, url, filed, headline) in MOVED.items():
        r = by.get(rid)
        if not r:
            continue
        old = f"{r.get('d')} ({r.get('dp')})"
        r["d"], r["dm"], r["dp"], r["url"], r["ua"] = d, dm, dp, url, NOW
        dd = r.setdefault("_d", {})
        hist = dd.get("date_history") or []
        if not hist:
            hist.append({"date": rid[-10:], "note": "date the row was keyed on when created"})
        hist.append({"date": d, "changed": TODAY, "why": f"Company guidance moved the window: {r['t']}'s 8-K exhibit filed {filed} is headed \"{headline}\". Was {old}."})
        dd.update({"date_history": hist, "guided_precision": dp, "guided_form": "EX-99.1", "guided_filed": filed,
                   "guidance_text": headline, "source_url": url})
        n_mv += 1
    for rid in NO_TOPLINE:
        r = by.get(rid)
        if not r:
            continue
        dd = r.setdefault("_d", {})
        prog = dd.get("program") or r["name"].split()[0]
        dd["resolution"] = {"state": "no_topline", "checked": TODAY,
                            "searched": f"EDGAR full-text search of {r['t']} 8-K/6-K exhibits for \"{prog}\", 2026-07-01 to {TODAY}: no results exhibit"}
        n_nt += 1
    ack = json.load(io.open(ACK, encoding="utf-8"))
    ids = {a["id"] for a in ack["acks"]}
    for rid in NO_TOPLINE:
        if rid not in ids:
            ack["acks"].append({"id": rid, "reason": f"{TODAY}: no results exhibit in the sponsor's 8-K/6-K filings 2026-07-01 to {TODAY} (EDGAR full text); served 'No topline as of {TODAY}' and re-checked daily by resolve_past_readouts.py."})
    for rid, why in ACKS.items():
        if rid not in ids and rid not in REPORTED:
            ack["acks"].append({"id": rid, "reason": why})
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    io.open(MANUAL, "w", encoding="utf-8").write(json.dumps(man, indent=1, ensure_ascii=False))
    io.open(ACK, "w", encoding="utf-8").write(json.dumps(ack, indent=1, ensure_ascii=False))
    print(f"reported {n_rep}, moved {n_mv}, no_topline {n_nt}, acks {len(ack['acks'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
