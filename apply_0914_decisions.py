# -*- coding: utf-8 -*-
"""2026-09-14 currency pass: four FDA decisions the site was still calling "Upcoming".

WHY THE SITE WENT STALE. CI has failed every run since 2026-09-11 22:54, seven in a row, all
stuck on the same SHA -- so nothing rebuilt for three days. The failure was not a bug: the
early-approval watcher found approvals on armed events and exits 1 BY DESIGN so a human looks
before anything is published. It was doing its job. Nobody came.

Every fact below was read first-hand in the filing or FDA document named.

1. SRRK apitegromab -> ISEMBYLD (apitegromab-mstn), SMA. APPROVED 2026-09-11.
   Scholar Rock 8-K 2026-09-14, acc 0001104659-26-107273, tm2625362d1_ex99-1.htm: "Scholar Rock
   Announces FDA Approval of ISEMBYLD(TM) (apitegromab-mstn), the First and Only Muscle-Targeted
   Treatment for Children and Adults with Spinal Muscular Atrophy (SMA) ... September 11, 2026 ...
   approved for use in all adults and children >=2 years of age with SMA who are currently
   receiving a survival motor neuron 2 (SMN2)-targeted treatment".
   GOAL SOURCED (2026-09-30, Scholar Rock 8-K 2026-05-07, sourced by us on 09-10), so this is a
   real 19-days-early measurement and may enter /research/fda-decision-timing.

2. PHAR leniolisib -> Joenja, paediatric APDS. APPROVED 2026-09-11.
   Pharming 6-K 2026-09-11, acc 0001828316-26-000037, fdaapprovespharmingsjoenja.htm.
   GOAL SOURCED: Pharming 6-K 2026-06-04: "The FDA has assigned a Prescription Drug User Fee Act
   (PDUFA) target action date of October 24, 2026" -- a RESUBMISSION covering paediatric patients
   weighing 27 kg or more. 43 days early, and legitimately measurable.

3. BFRI Ameluz PDT -> superficial basal cell carcinoma. FDA ACTED 2026-09-09.
   openFDA NDA208081 SUPPL-40, status AP, date 20260909, class EFFICACY. Biofrontera did not
   announce until 2026-09-14 (8-K acc 0001493152-26-042508): "Biofrontera Announces FDA Approval
   of Ameluz Red Light PDT for the Treatment of Superficial Basal Cell Carcinoma ... the first and
   only photodynamic therapy approved in the United States to treat a skin cancer".
   THE TWO DATES DIFFER BY FIVE DAYS and the decision page must say so: `dcd` is the FDA's action
   date, but the market could not react until the 14th, so no price move on the 9th means anything.
   GOAL SOURCED: Biofrontera 8-K 2026-05-14: "...sNDA for Ameluz PDT for the treatment of
   superficial basal cell carcinoma (sBCC), with a PDUFA target action date of September 28, 2026."

4. BAYRY sevabertinib -> HYRNUO, HER2-mutant NSCLC. FDA ACTED 2026-09-09.
   FDA approval letter NDA 219972/S-001 (accessdata, 219972Orig1s001ltr.pdf), read directly:
   "Please refer to your supplemental new drug application (sNDA) dated and received on March 16,
   2026 ... for Hyrnuo (sevabertinib) tablets. This 'Prior Approval' sNDA provides for the use of
   Hyrnuo (sevabertinib) for the treatment of adult patients with locally advanced or metastatic
   non-squamous non-small cell lung cancer (NSCLC) whose tumors have HER2 (ERBB2) tyrosine kinase
   domain (TKD) activating mutations, as detected by an FDA-authorized test ... It is approved
   under accelerated approval ... effective on the date of this letter."
   Sevabertinib's ORIGINAL NDA was approved 2025-11-19 (openFDA ORIG-1, new molecular entity), so
   the drug was already on the market and this is the indication expansion our row tracked.
   GOAL **NOT** SOURCED. Bayer is not an SEC registrant and no filing anywhere states a
   2026-11-30 goal date -- the only EDGAR hits for "sevabertinib" + "target action date" are
   NUVALENT's, discussing a competitor. A March 16 submission under priority review lands in
   September, not November, so our unsourced November 30 was probably wrong all along. The day is
   therefore withdrawn (dp -> month) so this decision CANNOT enter the earliness statistic as a
   fabricated 82-days-early. Same rule as the 09-10 pass: no sourced goal, no earliness claim.

ALSO: two watcher hits acked as NON-events. check_pdufa_decided matches a ticker's approval PR
against that ticker's forward rows, which reaches across applications:
   GILD 2027-02-02 is once-weekly oral Yeztugo; the Aug 27 Bixlenvo approval is already published.
   ARQT 2027-02-23 is ZORYVE cream 0.05% for infants 3-24 months; the Jun 29 approval was cream
   0.3% for paediatric plaque psoriasis and is already published. Arcutis' own 8-K names both
   separately. Neither is a missed decision.
"""
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
LEDGER = os.path.join(HERE, "_unsourced_day_dates.json")
ACK = os.path.join(HERE, "_fda_watch_ack.json")

SRRK_8K = ("https://www.sec.gov/Archives/edgar/data/1727196/000110465926107273/"
           "tm2625362d1_ex99-1.htm")
PHAR_APPROVAL = ("https://www.sec.gov/Archives/edgar/data/1828316/000182831626000037/"
                 "fdaapprovespharmingsjoenja.htm")
PHAR_GOAL = ("https://www.sec.gov/Archives/edgar/data/1828316/000182831626000031/"
             "pharmingannouncesusfdaacce.htm")
BFRI_APPROVAL = ("https://www.sec.gov/Archives/edgar/data/1858685/000149315226042508/"
                 "ex99-1.htm")
BFRI_GOAL = ("https://www.sec.gov/Archives/edgar/data/1858685/000149315226022875/"
             "ex99-1.htm")
BAYRY_LETTER = ("https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/"
                "219972Orig1s001ltr.pdf")

DECISIONS = {
    ("SRRK", "2026-09-30"): {
        "oc": "Approved", "dcd": "2026-09-11",
        "name": "ISEMBYLD (apitegromab-mstn) - (SAPPHIRE)",
        "indication": "Spinal muscular atrophy (SMA), adults and children 2 years and older "
                      "already on an SMN2-targeted treatment",
        "source": "Scholar Rock 8-K 2026-09-14 (EX-99.1)",
        "source_url": SRRK_8K,
        "review": "The FDA approved ISEMBYLD (apitegromab-mstn) on September 11, 2026, 19 days "
                  "before the September 30 goal date Scholar Rock had stated. It is the first "
                  "muscle-targeted treatment for SMA, approved for adults and children 2 years "
                  "and older who are already receiving an SMN2-targeted therapy. The BLA had "
                  "been resubmitted on March 31, 2026 after a September 2025 CRL tied to a "
                  "third-party fill-finish facility rather than to the drug itself.",
    },
    ("PHAR", "2026-10-24"): {
        "oc": "Approved", "dcd": "2026-09-11",
        "name": "Joenja (leniolisib) - paediatric APDS",
        "indication": "Activated PI3K-delta syndrome (APDS) in children (resubmission covering "
                      "patients weighing 27 kg or more)",
        "source": "Pharming 6-K 2026-09-11",
        "source_url": PHAR_APPROVAL,
        "goal_source": "Pharming 6-K 2026-06-04",
        "goal_source_url": PHAR_GOAL,
        "review": "The FDA approved Joenja (leniolisib) for children with APDS on September 11, "
                  "2026, 43 days before the October 24 goal date Pharming had stated. The "
                  "application was a resubmission adding data the FDA had requested on "
                  "analytical methods for production batch testing, and covers paediatric "
                  "patients weighing 27 kg or more; Pharming has said a separate sNDA for lower "
                  "doses in patients under 27 kg is planned.",
    },
    ("BFRI", "2026-09-28"): {
        "oc": "Approved", "dcd": "2026-09-09",
        "name": "Ameluz (aminolevulinic acid hydrochloride) with RhodoLED red light - sBCC",
        "indication": "Superficial basal cell carcinoma (sBCC), photodynamic therapy with the "
                      "RhodoLED lamp series",
        "source": "Biofrontera 8-K 2026-09-14 (EX-99.1); FDA action date from openFDA "
                  "NDA208081 SUPPL-40 (AP 2026-09-09)",
        "source_url": BFRI_APPROVAL,
        "goal_source": "Biofrontera 8-K 2026-05-14 (EX-99.1)",
        "goal_source_url": BFRI_GOAL,
        "announced": "2026-09-14",
        "review": "The FDA approved Ameluz photodynamic therapy with red light for superficial "
                  "basal cell carcinoma, making it the first photodynamic therapy approved in "
                  "the United States to treat a skin cancer. The FDA's action date is September "
                  "9, 2026 (openFDA records the efficacy supplement as approved that day), 19 "
                  "days before the September 28 goal date Biofrontera had stated, but "
                  "Biofrontera did not announce it until September 14 -- so any share-price "
                  "move dates from the announcement, not from the FDA's action.",
    },
    ("BAYRY", "2026-11-30"): {
        "oc": "Approved", "dcd": "2026-09-09",
        "name": "HYRNUO (sevabertinib) - HER2-mutant NSCLC",
        "indication": "Locally advanced or metastatic non-squamous NSCLC with HER2 (ERBB2) "
                      "tyrosine kinase domain activating mutations (accelerated approval)",
        "source": "FDA approval letter, NDA 219972/S-001 (2026-09-09)",
        "source_url": BAYRY_LETTER,
        "downgrade_goal": True,
        "date_note": "Our published goal date of November 30, 2026 was never sourced. No Bayer "
                     "filing or release states it, and Bayer is not an SEC registrant so EDGAR "
                     "cannot confirm one; the only EDGAR hits for sevabertinib plus 'target "
                     "action date' belong to Nuvalent discussing a competitor. The FDA's letter "
                     "shows the sNDA was received March 16, 2026, which under priority review "
                     "lands in September rather than November. Day withdrawn 2026-09-14; the "
                     "decision itself is sourced to the FDA's own approval letter.",
        "review": "The FDA granted accelerated approval to HYRNUO (sevabertinib) on September 9, "
                  "2026 for adults with locally advanced or metastatic non-squamous NSCLC whose "
                  "tumours carry HER2 (ERBB2) tyrosine kinase domain activating mutations, as "
                  "detected by an FDA-authorised test. Sevabertinib's original NDA was approved "
                  "on November 19, 2025, so this decision expands an already-marketed drug "
                  "rather than introducing a new one. We do not state how early the decision "
                  "was, because the goal date we had carried was never sourced.",
    },
}

ACKS = [
    {"ticker": "ARQT", "ap_date": "2026-06-29",
     "reason": "ZORYVE (roflumilast) cream 0.3% for paediatric plaque psoriasis, already "
               "published as ARQT-2026-06-29. The hit is against the SEPARATE ZORYVE cream "
               "0.05% sNDA for infants aged 3-24 months (goal 2027-02-23), which remains "
               "pending -- Arcutis' 8-K of 2026-08-05 names both applications separately. Not a "
               "missed decision. Reviewed 2026-09-14."},
]


def main():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    a, b = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[a:b])
    done, downgraded = 0, 0

    for r in rows:
        key = (str(r.get("t") or "").upper(), str(r.get("d") or ""))
        if key not in DECISIONS or r.get("type") != "PDUFA":
            continue
        spec = DECISIONS[key]
        dd = r.setdefault("_d", {})
        r["st"], r["oc"], r["dcd"] = "Decided", spec["oc"], spec["dcd"]
        r["name"] = spec["name"]
        dd["indication"] = spec["indication"]
        dd["source"], dd["source_url"] = spec["source"], spec["source_url"]
        dd["review"] = spec["review"]
        for k in ("goal_source", "goal_source_url", "announced"):
            if spec.get(k):
                dd[k] = spec[k]
        if spec.get("downgrade_goal"):
            r["dp"] = "month"
            r["dm"] = str(r.get("d"))[:7]
            dd["date_note"] = spec["date_note"]
            downgraded += 1
        done += 1
        print(f"  {key[0]} {key[1]} -> Decided/{spec['oc']} on {spec['dcd']}"
              + ("  [goal day withdrawn]" if spec.get("downgrade_goal") else ""))

    io.open(DATASET, "w", encoding="utf-8").write(
        src[:a] + json.dumps(rows, indent=1, ensure_ascii=False) + src[b:])

    # ledger: the BAYRY goal day joins the withdrawn list
    led = json.loads(io.open(LEDGER, encoding="utf-8").read())
    have = {(x["ticker"], x["was_date"]) for x in led["rows"]}
    if ("BAYRY", "2026-11-30") not in have:
        led["rows"].append({
            "ticker": "BAYRY", "was_date": "2026-11-30", "month_kept": "2026-11",
            "new_precision": "month",
            "why": DECISIONS[("BAYRY", "2026-11-30")]["date_note"]})
        led["rows"].sort(key=lambda x: (x["ticker"], x["was_date"]))
        io.open(LEDGER, "w", encoding="utf-8").write(
            json.dumps(led, indent=1, ensure_ascii=False) + "\n")

    ack = json.loads(io.open(ACK, encoding="utf-8").read())
    seen = {(x["ticker"], x["ap_date"]) for x in ack["acks"]}
    for x in ACKS:
        if (x["ticker"], x["ap_date"]) not in seen:
            ack["acks"].append(x)
    io.open(ACK, "w", encoding="utf-8").write(
        json.dumps(ack, indent=1, ensure_ascii=False) + "\n")

    print(f"\n{done} decision(s) applied, {downgraded} unsourced goal day withdrawn, "
          f"{len(ack['acks'])} watcher ack(s) on file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
