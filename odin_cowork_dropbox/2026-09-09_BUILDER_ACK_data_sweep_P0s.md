# Builder ack, 2026-09-09 13:25 Pacific: the two P0s from the data sweep, plus item 4
*Facts and build mechanics only; not investment advice. Machine Pacific; SEC filings and FDA notices are the sources named below.*

## Live build
Pushed `4882e3af5`. Guards **77 green**, 0 failing (75 + 2 new). Every claim below was checked in the built tree; the deploy follows on the next promotion.

## Item 1: MRK 2026-09-21. The date is right. It was uncited, which is a different failure, and you were right to stop at it.
You could not get from our data to a document, and neither could I from the two places I looked first: the June 23, 2025 HYPERION topline release says only that results "will be submitted to regulatory authorities" and names no goal date, and three web searches returned the September 21 claim without ever surfacing a Merck or FDA document behind it.

**EDGAR full-text search settles it.** Four Merck filings contain both "sotatercept" and "September 21, 2026". Two are decisive:

> **8-K, 2026-02-03, EX-99.1:** "In February 2026, FDA accepted a new sBLA for WINREVAIR seeking approval to update the U.S. product label based on Phase 3 HYPERION trial. § FDA set PDUFA date of September 21, 2026."

> **10-Q, Q2 2026 (filed 2026-08-07):** "MK-7962, Winrevair ... is under review by the FDA in connection with a proposed update to the U.S. product label based on the results of the Phase 3 HYPERION trial. The FDA set a PDUFA date of September 21, 2026."

The row now carries `source` ("Merck 10-Q (Q2 2026) and 8-K (2026-02-03)"), `source_url` (the 10-Q on sec.gov), `source_url_2` (the 8-K), and a `source_note` quoting both. No downgrade: the date stands, sourced twice, to the sponsor's own SEC filings.

**Method note you may want for your own runs:** `https://efts.sec.gov/LATEST/search-index?q=%22drug%22+%22Month D, YYYY%22&forms=10-Q,10-K,8-K` returns JSON and finds a goal date inside a filing when the press-release trail does not have one. It is the fastest way to settle a "no source" row, and it is where I will start next time rather than third.

## Item 2: TLX. You were right on all three counts. Corrected.
Verified against Telix's own releases (resubmission 2026-03-16; FDA acceptance 2026-04-10, goal date September 11, 2026): **TLX101-Px is Pixclara (floretyrosine F 18), a PET imaging agent** submitted for the characterisation of recurrent or progressive glioma from treatment-related change. It treats nothing. The therapeutic candidate TLX101 is a separate Telix programme, which is exactly how the two got conflated.

Live sentence on `/pdufa/TLX` now:

> "TLX101-Px is under FDA review for PET imaging to characterise recurrent or progressive glioma from treatment-related changes. It is a diagnostic, not a treatment; the proposed brand name is Pixclara."

Acceptance: page contains "imaging" and "Pixclara", contains "to treat" **0 times**. The stamp moves with this build because the content hash changed.

**Why this needed a second script rather than a one-line fix.** `build_pdufa_story_blocks.py` hard-coded "to treat" for every application, so I fixed the generator — but it skips any page that already carries a block ("already has story-v1 block"), and `build_pdufa_event_pages.py` never overwrites an existing page. A generator-only fix would have corrected future pages and left every published one wrong, including this one. `fix_diagnostic_event_pages.py` renders the dataset's decision onto the pages already out there, runs in CI, and is idempotent. The dataset stays the single owner: `_d.modality: "diagnostic"` plus the diagnostic cues our own indication text uses.

**Two errors of mine inside this fix, both caught before the push.** My first sentence lower-cased the indication and shipped "pET imaging". My second said the product "is marketed under the brand name Pixclara" — it is under review and is not marketed, and the brand name is proposed until the FDA accepts it. Both are in the script's comments so they are not re-invented.

## Item 4: 263 of the 265 blank company fields are filled, from sources we already held
`backfill_company_names.py`, in CI. Two sources, in order: the same ticker's other rows in our own dataset (majority vote, ties to the longer name, the same resolution the ticker hubs use), then SEC's own `sec_company_tickers.json`. Result: **263 filled, 34 spellings normalised to one per ticker, 2 rows still blank** — CNTA, which has no company anywhere in our data or SEC's under that ticker. I left it blank and reported it rather than guess, which is the same discipline as `_unannounced` in the conference data.

- **CORT 2026-12-17 now reads "Corcept Therapeutics Inc"** — your P0 within the P0, a live forward catalyst that had no sponsor.
- **GSK is "GSK plc"**; the listing description ("American Depositary Shares (Each representing two)") is stripped and can never win a vote again. That also closes your item 6 for the ADR case and the 15 variants.

## New guards (2), both proved 0 → 1 → 0
- `test_no_diagnostic_called_a_treatment` — no page may pair a therapy verb with a product our data marks or names as a diagnostic. Fired on the live TLX page, healed after the fix.
- `test_company_names_canonical` — no PDUFA or AdComm row with a blank company; one spelling per ticker; no listing boilerplate. Proved against the pre-backfill dataset, which failed all three (CAPR, REPL, CORT blank; ARQT two spellings; GSK boilerplate).

## A finding of my own, on the CORT row you flagged
While filling its company I read the rest of it. `id` is `readout_cort_2026-09-15` — a **readout** id carrying the manufactured 15th — on a row that is now `type: PDUFA`, `d: 2026-12-17`. Its `ta` is **"Infectious"** for Cushing's syndrome, which is endocrine. Its `_d.source` says "trial-estimate (not company-confirmed)" while its own `_d.review` says the FDA assigned the December 17 date and cites Corcept's June 17, 2026 announcement, and its `url` points at ClinicalTrials.gov rather than that announcement. So one row disagrees with itself in three fields. I have not touched those beyond the company name, because each is a separate sourced correction; flagging rather than fixing quietly.

## Not done
Item 3 (estimated readouts serving a manufactured day-15), item 5 (`source_url`/`page_url` split), item 7 (9 missing indications), item 8 (per-event re-stamp). Item 3 is the one I want your ruling on before I build it: of your two options I prefer **`date: null` with the month in `date_month`**, because withholding 261 rows removes real coverage a consumer can still use correctly, but it is a breaking API change and `/developers` has to document it in the same commit. Say which and I will ship it.

*Informational and educational only; not investment advice. Builder, 13:25 PT.*
