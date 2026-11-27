# -*- coding: utf-8 -*-
"""apply_1127_truqap_indication.py -- Truqap's June 12, 2026 approval named a disease that does not exist.

2026-11-27 phone pass: /fda-decision/AZN-2026-06-12, /drug/truqap and /drug/capivasertib said Truqap was approved
"for dephosphorylated Phosphatase and Tensin Homolog (dPTEN) Hormone-Sensitive Prostate Cancer (HSPC)". The
indication came from a scraped tracker row; "dPTEN" there stood for PTEN-deficient. The FDA's approval notice
(June 12, 2026) approves capivasertib (Truqap, AstraZeneca) with abiraterone and prednisone for adults with
metastatic androgen pathway modulation-naive or -sensitive (mAPMN/S) prostate cancer, previously referred to as
metastatic hormone-sensitive prostate cancer, that is PTEN-deficient as detected by an FDA-authorized test.

This sets the dataset row's indication to the FDA's text, adds a short form for the decision lede, cites the notice,
and appends a /corrections entry. Idempotent. Guard: tests/test_pinned_indications.py.

    python apply_1127_truqap_indication.py
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
CORR = os.path.join(HERE, "_corrections.json")
ROW = "pdufa_azn_2026-06-30"
FDA = ("https://www.fda.gov/drugs/resources-information-approved-drugs/"
       "fda-approves-capivasertib-abiraterone-and-prednisone-pten-deficient-androgen-pathway-modulation")
IND = ("In combination with abiraterone and prednisone, adults with metastatic androgen pathway modulation-naïve "
       "or -sensitive (mAPMN/S) prostate cancer (previously referred to as metastatic hormone-sensitive prostate "
       "cancer) that is PTEN-deficient as detected by an FDA-authorized test")
SHORT = "PTEN-deficient metastatic hormone-sensitive prostate cancer, with abiraterone and prednisone"
OLD = "Dephosphorylated Phosphatase and Tensin Homolog (dPTEN) Hormone-Sensitive Prostate Cancer (HSPC)"


def main():
    src = io.open(DATASET, encoding="utf-8").read()
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    r = next(x for x in rows if x.get("id") == ROW)
    d = r.get("_d") or {}
    changed = d.get("indication") != IND or d.get("indication_short") != SHORT
    if changed:
        # edit the row's own lines in place: re-serializing the whole file would rewrite unrelated escapes
        b = src.index(f'"id": "{ROW}"')
        e = src.index('\n {\n  "id": ', b) if '\n {\n  "id": ' in src[b:] else j
        blk = src[b:e]
        line = f'"indication": {json.dumps(d.get("indication"), ensure_ascii=False)},'
        if line not in blk:
            line = f'"indication": {json.dumps(d.get("indication"))},'
        assert blk.count(line) == 1, "indication line not found once in the row"
        pad = blk[:blk.index(line)].rsplit("\n", 1)[1]
        add = (f'"indication": {json.dumps(IND, ensure_ascii=False)},\n{pad}'
               f'"indication_short": {json.dumps(SHORT, ensure_ascii=False)},\n{pad}'
               f'"indication_source": {json.dumps(FDA)},')
        for k in ("indication_short", "indication_source"):
            blk = __import__("re").sub(r'\n\s*"' + k + r'": "[^"\n]*",', "", blk)
        blk = blk.replace(line, add, 1)
        now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        blk = __import__("re").sub(r'"ua": "[^"]*"', f'"ua": "{now}"', blk, count=1)
        src = src[:b] + blk + src[e:]
        json.loads(src[src.index("["):src.rindex("]") + 1])
        io.open(DATASET, "w", encoding="utf-8").write(src)
    c = json.load(io.open(CORR, encoding="utf-8"))
    page = "/fda-decision/AZN-2026-06-12"
    if not any(e.get("page") == page and "PTEN" in e.get("now", "") for e in c["entries"]):
        c["entries"].append({
            "date": "2026-11-27",
            "page": page,
            "was": f"Truqap (capivasertib) was listed as approved on June 12, 2026 for \"{OLD}\".",
            "now": ("Approved, with abiraterone and prednisone, for adults with metastatic androgen pathway "
                    "modulation-naïve or -sensitive prostate cancer (previously called metastatic hormone-sensitive "
                    "prostate cancer) that is PTEN-deficient. The old wording came from a tracker row that expanded "
                    "\"dPTEN\" wrongly; the indication is now the FDA's own text, also on /drug/truqap."),
            "source": "FDA approval notice, June 12, 2026",
        })
        io.open(CORR, "w", encoding="utf-8").write(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
    print(("updated" if changed else "already current") + f": {ROW} indication; /corrections entry present")


if __name__ == "__main__":
    main()
