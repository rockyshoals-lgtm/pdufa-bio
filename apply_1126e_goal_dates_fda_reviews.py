# -*- coding: utf-8 -*-
"""apply_1126e_goal_dates_fda_reviews.py -- 41 more FDA actions since 2024 get a sourced goal date, most from the FDA's
own review documents.

2026-11-26 (David, 06:51 UTC: "keep building our databases ... most accurate dates"; the coordinator's 10:04 UTC note
asked to source the goal dates still missing from the early, on-time and late counts).

Pass 4 of the decision-timing census (decision_timing_2024_2025.json) re-searched the 187 candidates for 2024 and 2025
that were left out because no goal date had been sourced to the day, the sponsor gave only a month or quarter, the
FDA's action day was not established, or the row had not been researched. Three earlier passes looked only for a
sponsor or partner statement. Pass 4 added the FDA's own record of the goal: the cover sheet or application table of
the FDA review posted with the approval package on Drugs@FDA (Multidiscipline, Integrated, Summary, Clinical or
Statistical review), and for CBER products the Summary Basis for Regulatory Action or review memo, each of which
prints "PDUFA Goal Date". For a complete response letter, the FDA's review of the later approval states the first
cycle's goal where it is quoted here, and in one case (penpulimab) the FDA's CRL itself states the extended goal.

Every row below was then read again at source by a separate check (both dates, the application and the review cycle):
41 confirmed, none corrected. Shingrix (C245) is not added: GSK's release says the decision was "expected by June 20,
2025" and never calls that a PDUFA goal date, so it stays out as before with the reason updated.

Because an FDA review is posted only with an approval, the rows whose goal comes from an FDA document (goal_source
"fda_review" or "fda_letter") are kept out of the "do late decisions end in a CRL" table, which uses only candidates
not chosen by outcome; they count in the timing totals. Sponsor-sourced additions (Yutrepia, ONAPGO's first cycle,
EYLEA HD 24-week dosing) stay in it like any tracked row.

Also: BBIO-2026-11-23 (Welgemda) takes its FDA action day, November 23, 2026, from the FDA's Novel Drug Approvals 2026
table (read 2026-11-26; "Approval Date 11/23/2026"), so it enters the 2026 count four days before its November 27,
2026 goal (BridgeBio 8-K, August 10, 2026).

Idempotent. Facts only, not investment advice.

    python apply_1126e_goal_dates_fda_reviews.py [--dry-run]
"""
import argparse
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "decision_timing_2024_2025.json")
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
FAQ = os.path.join(HERE, "_decision_extra_faq.json")
P4 = "/mnt/project-files/pdufa-bio/decision-timing/pass4"
ROWS = os.path.join(HERE, "decision_timing_pass4_rows.json")   # frozen copy of the 41 red-teamed rows, kept in git
RT = "Pass 4 (2026-11-26): goal and action dates re-read at source by a separate check; confirmed."

TICKER_FIX = {"C240": []}           # Zegfrovy: applicant Dizal (Shanghai), not Exelixis
DOC_DATE_FIX = {"C040": "2023-11-02"}   # Supernus release, "ROCKVILLE, Md., November 2, 2023"
DROP = {"C245"}
C245_REASON = ("pass 4: GSK's January 10, 2025 release says the decision was \"expected by June 20, 2025\" and does "
               "not call it a PDUFA goal date; the FDA approved the prefilled-syringe supplement on July 16, 2025 "
               "(CBER letter). No sponsor or FDA document states a PDUFA goal day.")
KEEP = ["cid", "drug", "application", "sponsor", "tickers", "goal_date_original", "goal_original_url",
        "goal_original_doc_date", "goal_original_quote", "extended", "goal_date_extended", "goal_extended_url",
        "goal_extended_doc_date", "goal_extended_quote", "extension_reason", "goal_in_effect", "goal_verified_by",
        "action_date", "action_basis", "action_url", "action_quote", "announcement_date", "announcement_url",
        "outcome", "goal_source_type", "goal_fda_doc_title", "notes"]


def frozen_rows():
    """The 41 rows, from the frozen copy in git (written from the pass-4 output on first run)."""
    if os.path.exists(ROWS):
        return json.load(io.open(ROWS, encoding="utf-8"))
    inc = json.load(io.open(os.path.join(P4, "included_p4.json"), encoding="utf-8"))
    b1 = json.load(io.open(os.path.join(P4, "out_B1.json"), encoding="utf-8"))
    inc += [x for x in b1 if x.get("cid") == "L004"]
    verdicts = {}
    for i in range(1, 6):
        for v in json.load(io.open(os.path.join(P4, "redteam", f"rt_out_{i}.json"), encoding="utf-8")):
            if v.get("verdict") == "confirmed":
                verdicts[v.get("cid") or v.get("id")] = v
    out = []
    for x in inc:
        if not x.get("cid") or x["cid"] in DROP:
            continue
        assert x["cid"] in verdicts, f"{x['cid']} not confirmed by the red team"
        r = {k: x.get(k) for k in KEEP}
        if x["cid"] == "L004":
            r["goal_source_type"] = "fda_letter"
            r["goal_fda_doc_title"] = "FDA complete response letter (states the extended goal)"
        out.append(r)
    io.open(ROWS, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    doc = json.load(io.open(DATA, encoding="utf-8"))
    have = {x["cid"] for x in doc["actions"]}
    ex = {x["cid"]: x for x in doc["excluded_rows"]}
    added = 0
    for r in frozen_rows():
        cid = r["cid"]
        if cid in have:
            continue
        e = ex.get(cid)
        assert e, f"{cid}: not among the excluded rows"
        tk = TICKER_FIX.get(cid, [t for t in str(e.get("tickers") or "").split("/") if t and t != "None"])
        row = dict(r)
        row.update({
            "tickers": tk, "members": [cid], "origin": e["origin"], "excluded": None, "scope_note": None,
            "red_team": RT, "goal_original_doc_date": DOC_DATE_FIX.get(cid, r.get("goal_original_doc_date")),
            "extended": True if r.get("extended") else (False if r.get("extended") is False else None),
            "goal_verified_by": r.get("goal_verified_by") or "fetched",
        })
        nt = (r.get("notes") or "").strip()
        row["notes"] = nt if nt.startswith("Pass 4") else ("Pass 4. " + nt).strip()
        doc["actions"].append(row)
        doc["excluded_rows"] = [x for x in doc["excluded_rows"] if x["cid"] != cid]
        added += 1
    for x in doc["excluded_rows"]:
        if x["cid"] == "C245" and not x["reason"].startswith("pass 4"):
            x["reason"] = C245_REASON
    doc["about"] = doc["about"].replace(
        "Goal dates from sponsor or partner documents dated before the action;",
        "Goal dates from sponsor or partner documents dated before the action, or from the FDA's own review "
        "documents (review cover sheets, CBER Summary Basis for Regulatory Action) posted with the approval;").replace(
        "(three research passes)", "(four research passes)")
    print(f"census: +{added} actions -> {len(doc['actions'])} actions, {len(doc['excluded_rows'])} excluded")

    # ---- BBIO-2026-11-23: the FDA's own day ----
    src = io.open(DATASET, encoding="utf-8").read()
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    asc = src[i:j] == json.dumps(rows, indent=1, ensure_ascii=True)
    r = next(x for x in rows if x["id"] == "pdufa_bbio_2026-11-27")
    assert r["dcd"] == "2026-11-23" and r["d"] == "2026-11-27"
    d = r["_d"]
    changed = False
    if d.get("fda_action_date") != "2026-11-23":
        fda = "https://www.fda.gov/drugs/novel-drug-approvals-fda/novel-drug-approvals-2026"
        d.pop("decision_date_unsourced", None)
        d.update({
            "fda_action_date": "2026-11-23", "fda_action_source_url": fda,
            "fda_action_record": "FDA, Novel Drug Approvals for 2026 table",
            "decision_note": ("The FDA's Novel Drug Approvals 2026 table lists Welgemda (ribitol) as approved on November 23, "
                              "2026, the day BridgeBio announced it, four days before the November 27, 2026 goal date "
                              "BridgeBio disclosed on August 10, 2026."),
        })
        changed = True
    if not a.dry_run and changed:
        io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=asc) + src[j:])
    faq = json.load(io.open(FAQ, encoding="utf-8"))
    qa = faq.get("BBIO-2026-11-23") or []
    for q in qa:
        if q[0] == "Was the Welgemda decision early?":
            q[1] = ("Yes, by four days. The FDA's Novel Drug Approvals 2026 table lists the approval on November 23, "
                    "2026; BridgeBio had disclosed a PDUFA goal date of November 27, 2026.")
    print(f"BBIO-2026-11-23: fda_action_date 2026-11-23 ({'set' if changed else 'already set'})")
    if a.dry_run:
        return
    io.open(DATA, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    io.open(FAQ, "w", encoding="utf-8").write(json.dumps(faq, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
