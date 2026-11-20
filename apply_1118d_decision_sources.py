# -*- coding: utf-8 -*-
"""apply_1118d_decision_sources.py -- six CRL pages re-sourced to the FDA's own Complete Response Letter.

2026-11-18 (David, 2026-11-17 Eastern: "Red team the readout and pdufa dates again, let's build our moat here too
as the most accurate"). A citation audit found decision pages whose source row pointed at a different FDA action:

  * ALDX-2025-04-03 cited Aldeyra's March 17, 2026 release (the SECOND reproxalap CRL), not the April 2025 one;
  * ATRA-2025-01-16 cited Atara's May 5, 2025 release (the clinical-hold lift), months after the January CRL;
  * FBIO-2025-10-01 cited the January 2026 approval letter, which only mentions the September 30, 2025 CRL.

Each now links the CRL file the FDA published for that action (openFDA CRL corpus), with the line it was checked
against kept in _decision_verification.json. Three more CRL pages that cited a release or 8-K (MIST-2025-03-28,
ALDX-2026-03-17, ATRA-2026-01-12) get the same primary source, and with it the FDA's own action day, which is a
day or a weekend before the announcement on all three. Signature stamps on the letters are Eastern (RULE 1).
tests/test_decision_citations_match.py keeps a page from citing a letter for another action again.

A drug-row audit of the run-up study's decision pages found 14 with no drug row, whose FAQ then read the badge
as the drug ("Was source-verified approved by the FDA?"). Eight more get the FDA letter as source, the FDA's action
day and the drug it names; SNY-2026-02-24 is Dupixent for allergic fungal rhinosinusitis (BLA 761055 S-075,
letter February 23, 2026), not the venglustat the study row carries. PHAR-2026-02-01 keeps its source and gains the
drug row (VTRS-2026-07-29 and CORT-2026-03-25 already name theirs as "Brand / candidate" and in a facts table). tests/test_decision_citations_match.py keeps every study page naming its drug.

Idempotent. Facts only, not investment advice.

    python apply_1118d_decision_sources.py [--dry-run]
"""
import argparse
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from apply_1118b_decision_sources import SITE, TODAY, esc, jload, jsave, kv, patch  # noqa: E402

C = "https://download.open.fda.gov/crl/"
L = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/"

FIX = {
    "ALDX-2025-04-03": dict(oc="CRL", fda="2025-04-02", ann="2025-04-03", rec="NDA 216442 CRL",
                            url=C + "CRL_NDA216442_20250402.pdf",
                            label="FDA Complete Response Letter, NDA 216442, April 2, 2025",
                            quote="NDA 216442 COMPLETE RESPONSE ... 04/02/2025 06:34:06 PM",
                            drug="Reproxalap ophthalmic solution"),
    "ATRA-2025-01-16": dict(oc="CRL", fda="2025-01-15", ann="2025-01-16", rec="BLA 125745 CRL",
                            url=C + "CRL_BLA125745_20250115.pdf",
                            label="FDA Complete Response Letter, BLA 125745, January 15, 2025",
                            quote="Our STN: BL 125745/0 COMPLETE RESPONSE January 15, 2025 Atara Biotherapeutics, Inc.",
                            drug="EBVALLO (tabelecleucel)"),
    "FBIO-2025-10-01": dict(oc="CRL", fda="2025-09-30", ann="2025-10-01", rec="NDA 211241 CRL",
                            url=C + "CRL_NDA211241_20250930.pdf",
                            label="FDA Complete Response Letter to Sentynl Therapeutics, NDA 211241, September 30, 2025",
                            quote="NDA 211241 COMPLETE RESPONSE Sentynl Therapeutics, Inc. ... 09/30/2025 01:15:03 PM",
                            drug="CUTX-101 (copper histidinate)"),
    "MIST-2025-03-28": dict(oc="CRL", fda="2025-03-27", ann="2025-03-28", rec="NDA 218571 CRL",
                            url=C + "CRL_NDA218571_20250327.pdf",
                            label="FDA Complete Response Letter, NDA 218571, March 27, 2025",
                            quote="NDA 218571 COMPLETE RESPONSE Milestone Pharmaceuticals USA, Inc. ... 03/27/2025 02:58:11 PM",
                            drug="Etripamil nasal spray"),
    "ALDX-2026-03-17": dict(oc="CRL", fda="2026-03-16", ann="2026-03-17", rec="NDA 216442 CRL",
                            url=C + "CRL_NDA216442_20260316.pdf",
                            label="FDA Complete Response Letter, NDA 216442, March 16, 2026",
                            quote="NDA 216442 COMPLETE RESPONSE Aldeyra Therapeutics, Inc. ... 03/16/2026 12:30:24 PM",
                            drug="Reproxalap ophthalmic solution"),
    "ATRA-2026-01-12": dict(oc="CRL", fda="2026-01-09", ann="2026-01-12", rec="BLA 125745 CRL",
                            url=C + "CRL_BLA125745_20260109.pdf",
                            label="FDA Complete Response Letter, BLA 125745 (Pierre Fabre, Atara's partner), January 9, 2026",
                            quote="Our STN: BL 125745/0 COMPLETE RESPONSE January 9, 2026 Pierre Fabre Pharmaceuticals Inc.",
                            drug="EBVALLO (tabelecleucel)"),
    # run-up study pages with no drug row (their FAQ asked "Was source-verified approved by the FDA?", reading the
    # badge as the drug); each now names the drug from the FDA's own letter
    "UNCY-2025-06-30": dict(oc="CRL", fda="2025-06-27", ann="2025-06-30", rec="NDA 218607 CRL",
                            url=C + "CRL_NDA218607_20250627.pdf",
                            label="FDA Complete Response Letter, NDA 218607, June 27, 2025",
                            quote="NDA 218607 COMPLETE RESPONSE Unicycive Therapeutics Inc. ... 06/27/2025 04:49:06 PM",
                            drug="Oxylanthanum carbonate tablets"),
    "CAPR-2025-07-11": dict(oc="CRL", fda="2025-07-09", ann="2025-07-11", rec="BLA 125842 CRL",
                            url=C + "CRL_BLA125842_20250709.pdf",
                            label="FDA Complete Response Letter, BLA 125842, July 9, 2025",
                            quote="Our STN: BL 125842/0 COMPLETE RESPONSE JULY 9, 2025 Capricor, Inc.",
                            drug="Deramiocel"),
    "REPL-2025-07-22": dict(oc="CRL", fda="2025-07-21", ann="2025-07-22", rec="BLA 125827 CRL",
                            url=C + "CRL_BLA125827_20250721.pdf",
                            label="FDA Complete Response Letter, BLA 125827, July 21, 2025",
                            quote="Our STN: BL 125827 COMPLETE RESPONSE JULY 21, 2025 Replimune, Inc.",
                            drug="RP1 (vusolimogene oderparepvec) with nivolumab"),
    "OTLK-2025-08-28": dict(oc="CRL", fda="2025-08-27", ann="2025-08-28", rec="BLA 761320 CRL",
                            url=C + "CRL_BLA761320_20250827.pdf",
                            label="FDA Complete Response Letter, BLA 761320, August 27, 2025",
                            quote="BLA 761320 COMPLETE RESPONSE Outlook Therapeutics, Inc. ... 08/27/2025 01:00:37 PM",
                            drug="ONS-5010 (bevacizumab-vikg)"),
    "ALVO-2025-11-02": dict(oc="CRL", fda="2025-10-31", ann="2025-11-02", rec="BLA 761462 CRL",
                            url=C + "CRL_BLA761462_20251031.pdf",
                            label="FDA Complete Response Letter, BLA 761462, October 31, 2025",
                            quote="BLA 761462 COMPLETE RESPONSE Alvotech USA Inc. ... for AVTO5 ... 10/31/2025 08:04:52 AM",
                            drug="AVT05 (proposed golimumab biosimilar)"),
    "CORT-2025-12-31": dict(oc="CRL", fda="2025-12-30", ann="2025-12-31", rec="NDA 219398 CRL",
                            url=C + "CRL_NDA219398_20260128.pdf",
                            label="FDA Complete Response Letter, NDA 219398 (corrected letter; action date December 30, 2025)",
                            quote="The effective action date will remain December 30, 2025, the date of the original letter.",
                            drug="Relacorilant capsules"),
    "SNY-2026-02-24": dict(oc="Approved", fda="2026-02-23", ann="2026-02-24", rec="BLA 761055 S-075",
                           url=L + "2026/761055Orig1s075ltr.pdf",
                           label="FDA approval letter, BLA 761055 S-075, February 23, 2026",
                           quote="This Prior Approval sBLA provides for a new indication of treatment of adult and pediatric patients aged 6 years and older",
                           drug="DUPIXENT (dupilumab)"),
    "ETON-2026-02-25": dict(oc="Approved", fda="2026-02-25", ann=None, rec="NDA 219873",
                            url=L + "2026/219873Orig1s000ltr.pdf",
                            label="FDA approval letter, NDA 219873, February 25, 2026",
                            quote="It is approved, effective on the date of this letter",
                            drug="DESMODA (desmopressin acetate) oral solution"),
}

# pages whose source already stands; only the missing drug row is added (named from the cited source)
DRUG_ONLY = {
    "PHAR-2026-02-01": "JOENJA (leniolisib)",
}


def write_ledgers():
    ver = jload("_decision_verification.json")
    for slug, s in FIX.items():
        e = ver["results"].setdefault(slug, {"ticker": slug.split("-")[0], "date": slug.split("-", 1)[1],
                                             "asset": s["drug"],
                                             "claimed": "crl" if s["oc"] == "CRL" else "approval"})
        ev = e.get("evidence") or {}
        want = {"kind": "primary", "source_url": s["url"], "source_label": s["label"],
                "quote": s["quote"], "quote_checked": TODAY,
                "fda_action_date": s["fda"], "announced": s["ann"]}
        if ev == want:
            continue
        if ev and "evidence_before_recheck" not in e:
            e["evidence_before_recheck"] = ev
            e["status_before_recheck"] = e.get("status")
        e["status"] = "verified_crl" if s["oc"] == "CRL" else "verified_approved"
        e["evidence"] = want
    jsave("_decision_verification.json", ver)
    arch = jload("_fda_action_archive.json")
    k = 0
    for slug, s in FIX.items():
        cur = arch.get(slug) or {}
        mine = (cur.get("basis") or "").startswith("red team 2026-11-18")
        basis = ("red team 2026-11-18: FDA Complete Response Letter file read directly" if s["oc"] == "CRL"
                 else "red team 2026-11-18: FDA approval letter read directly")
        name = s["drug"] if (mine or not cur.get("name")) else cur["name"]
        if (cur.get("date") == s["fda"] and cur.get("source_url") == s["url"] and cur.get("name") == name
                and cur.get("basis") == basis):
            continue
        arch[slug] = {"checked": TODAY, "date": s["fda"], "record": s["rec"], "source_url": s["url"],
                      "name": name, "oc": s["oc"],
                      "basis": basis}
        k += 1
    jsave("_fda_action_archive.json", dict(sorted(arch.items())))
    print(f"_fda_action_archive.json: {k} FDA action day(s) recorded or re-sourced")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.dry_run:
        write_ledgers()
    n = 0
    for slug, s in FIX.items():
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        doc = io.open(p, encoding="utf-8").read()
        new = patch(doc, slug, s)
        if s["url"] not in new:
            raise SystemExit(f"{slug}: source row not patched (template not recognised)")
        if new != doc:
            n += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"decision pages re-sourced: {n} of {len(FIX)}")
    m = 0
    for slug, drug in DRUG_ONLY.items():
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        doc = io.open(p, encoding="utf-8").read()
        if re.search(r'<span>Drug(?: / candidate)?</span>', doc):
            new = re.sub(r'(<div class="kv"><span>Drug(?: / candidate)?</span><b>)[^<]*(</b></div>)',
                         lambda g: g.group(1) + esc(drug) + g.group(2), doc, count=1)
        else:
            new = re.sub(r'(<div class="kv"><span>FDA decision date</span><b>[^<]*</b></div>'
                         r'(?:<div class="kv"><span>Announced</span><b>[^<]*</b></div>)?)',
                         lambda g: g.group(1) + kv("Drug", esc(drug)), doc, count=1)
        if "<span>Drug</span><b>" + esc(drug) not in new:
            raise SystemExit(f"{slug}: drug row not added (template not recognised)")
        if new != doc:
            m += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"drug rows added: {m} of {len(DRUG_ONLY)}")


if __name__ == "__main__":
    main()
