# Builder ack — 2026-09-02c audit actioned
*2026-09-02 evening (Pacific). Facts and build mechanics only — not investment advice.*

## Your order, in your order

**1. ChEMBL molecule_synonyms — DONE, and your correction was the right call.**
`fetch_chembl_synonyms.py` pulled all 554 drug names against ChEMBL with a strict
same-molecule rule (a synonym is accepted only when the hit's pref_name equals our name
or our name appears verbatim in its own synonym list — a fuzzy hit for a different
molecule would publish wrong aliases, worse than none). Result: **259 of 554 drugs now
carry verified aliases** (was ~4%). Your three named examples all resolved:
rusfertide → PTG-300, PTG-300FB · camizestrant → AZD9833, AZD-9833, AZ-14066724 ·
avexitide → exendin 9-39 (four surface forms). Cache-first and incremental, so the daily
CI run costs seconds; wired before add_drug_schema in the workflow.

**2. "LLY (LLY):" — fixed at the source.** When the archive record's company IS the
ticker, the snippet says it once ("URGN: ZUSDURI was approved on June 12, 2025.").
187 pages corrected, idempotent.

**3. CRL letters — first 11 pages now cite FDA's own letter.** The letters are publicly
hosted at download.open.fda.gov/crl/{file} (verified 200). Match rule: letter dated on
or up to 4 days BEFORE the page's decision date (the letter carries the action day, our
page often carries the announcement day — ACHV decided Friday, announced Monday) AND
company-name token overlap; ambiguity skips loudly. 11 is the honest count — most of the
458 letters belong to companies without decision pages or predate the archive. Daily in
CI; floor guard `test_crl_letters_linked.py` proven by stripping all 11 cards (fails)
and letting the linker heal them.

**4. /crl hub · /pdufa-date-changes** — still open (tasks #44/#46), next batch.

**5. Sept 8 console read** — nothing touched on /fda-decisions-today or the explainer
since your snapshot; the read will be clean.

## Also closed on the way
`/pdufa/TAK-rusfertide` (flagged 09-02b): traced to the founding site commit — a Dec-31
placeholder for rusfertide under its ex-US partner's ticker. The FDA application is
Protagonist's. Dir deleted, 301 → /pdufa/PTGX-rusfertide, sitemap rebuilt.

**56 guards green.** The alternateName breadth lever you corrected is now real data:
an engine resolving "PTG-300 pdufa date" and "rusfertide pdufa date" sees one entity,
our markup, both ways.
