# Builder, 10-03 (second pass): Tiers 2, 3 and 4 of the consolidated order, and three wrong attachments found on the way
**2026-10-03, written ~16:00 Pacific = 19:00 Eastern = 23:00 UTC.** *RULE 1: every time below carries its zone. Facts and file contents only; not investment advice.*

This continues `2026-10-03_BUILDER_one_lead_holds_one_row.md`, which covered Tier 0 and Tier 1. Every item from 2.1 to 4.8 is below. Each new guard was proved 0 → planted 1 → 0 on the rendered output: 16 proofs, all passed, written to `_prove_1003b.log` by `_prove_1003b.py`. Local guards: **128 pass, 0 fail.**

---

## Tier 2

**2.1 Fact-first first sentence on every Approved decision page** (`build_decision_lede.py`, run in the chain and in CI right after the FDA-record block, so a page publishes with its lede in the same run).

- 125 approved pages (price-only and outcome-unverified pages excluded) now open with one sentence directly under the APPROVED banner.
- **89 are FDA-dated:** "{Drug} was approved by the FDA on {FDA date} for {indication}." The date comes only from an FDA record: the API row's `fda_action_date`, the FDA's Novel Drug Approvals list, or Drugs@FDA.
- **36 are announcement-dated:** "{Drug} was approved by the FDA for {indication}; the approval was announced on {date}." We hold no FDA date for these. They are mostly CBER products and multi-supplement brands.
- **The new Drugs@FDA source for archive pages is `sync_archive_fda_dates.py`.** For decision pages with no API row, it records a date only when there is exactly one decision-class approval in the 24 days around the page date, dated 0 to 4 days before the announcement. It dated 46 pages. 15 of those are novel drugs, and the date matched the FDA's own list in all 15. The FDA-record block and the `/fda-approval-letters` rows now cover these pages too.
- **JUVMO now reads:** "JUVMO (tavapadon) was approved by the FDA on September 25, 2026 for Parkinson's disease in adults, the 43rd novel drug approval of 2026 on the FDA's Novel Drug Approvals list."
- **Guard** `test_decision_lede_fact_first.py`, three plants: lede removed; wrong novel number; a date no FDA record holds.

**2.2 Running novel-approval count.**

- `sync_novel_approvals.py` reads CDER's "Novel Drug Approvals for 2026" table. It holds 45 drugs; the FDA page was current as of 2026-09-28, with #45 Emcitate on 9/28 and #43 Juvmo on 9/25.
- 35 decision pages carry "the Nth novel drug approval of 2026", with N taken from the FDA's list and never counted by us, and a link to the list.
- A read that shrinks the list keeps the cache.
- The guard checks that row N is this page's drug and that the date falls within 10 days.

**2.4 Sponsor coverage** (`watch_edgar_8k.py`, a fifth watcher under quarantine).

- **The poll:** each SEC-registrant sponsor with an armed goal in the next 60 days has its own 8-K and 6-K filings read every run, from the submissions list rather than full-text search (which lags). A filing becomes a lead only when one sentence names the drug together with an FDA decision and is not "if approved", an acceptance or a submission.
- **`_sponsor_coverage.json`:** 17 sponsors; 16 have their own channel (MRK, AGIO, SMMT, CAPR, SVRA, COGT, REGN, VRTX and others through EDGAR; BioXcel through its bankruptcy ticker BTAIQ). **RHHBY has a recorded reason:** Roche is not an SEC registrant and publishes no RSS, so its U.S. decisions are covered by the FDA drugs feed and Drugs@FDA.
- merck.com's `/feed/` exists but is empty.
- **Guard** `test_edgar_8k_replay.py` replays Arvinas's VEPPANU 8-K: 1 lead, and 0 leads for acceptance language. It also checks that every sponsor has a channel or a reason.

**2.6 Gazyva (obinutuzumab), idiopathic nephrotic syndrome.**

- **Sources:** Drugs@FDA BLA 125486 SUPPL-43 (EFFICACY) approved 2026-09-25, with its letter; the FDA's CDER notice published 2026-09-25 13:51 Eastern.
- **Published:** row `pdufa_rhhby_2026-09-25` (`goal_unsourced`: we hold no goal date and Roche files nothing with the SEC) and the page `/fda-decision/RHHBY-2026-09-25`.

**Publishing Gazyva exposed two wrong attachments, both fixed with guards:**

- **The October calendar showed Tecentriq as "Approved", linked to the Gazyva decision.**
  - Cause: `mark_calendar_decided.py` accepted any same-ticker decision within the 14-day near window. Its one-decision-one-row check (`_owned_elsewhere`) ran only beyond that window.
  - Fix: the check now runs at every distance. The row was reverted to pending, and Gazyva has its own calendar row.
- **`/pdufa/RHHBY-gazyva`, the pending Gazyva lupus application, received the nephrotic-syndrome approval banner.**
  - Fix: `mark_event_pages_decided.py` rejects a decision whose indication shares no disease word with the page's own indication. This applies on first match, on the archive fallback and on re-validation.
  - Guard: `test_event_page_indication_match.py`. Its first run found a **pre-existing** case of the same defect: **`/pdufa/ARQT-zoryve`** (the infant atopic-dermatitis sNDA, goal 2027-02-23) had carried the June 29 plaque-psoriasis approval and said "approved by the FDA on June 29, 2026 for Atopic dermatitis, infants". The page was regenerated as pending, and the wrong version is kept in `_attic/2026-10-03_housekeeping/`.
  - `test_event_pages_decided.py` follows the same rule.

## Tier 3

**3.1 What the FDA approved, per day, by FDA action date.**

- `/fda-this-month` gains "What the FDA approved, by FDA action date (last 45 days)". `/fda-approval-letters` gains "day by day (last 60 days)" and now lists **81 FDA actions**, up from 39, because it includes the Drugs@FDA-dated archive pages.
- September 25 reads: Gazyva (BLA 125486 SUPPL-43); Atebrioz (NDA 221198 ORIG-1); JUVMO (NDA 220415 ORIG-1, announced Sep 28).
- **Guard:** every FDA-dated approval in the window sits under its FDA date on both pages. Plant: JUVMO moved to the 28th.

**3.2** `/fda-approval-letters` is linked from **every** decision page (385 gained a link, approved and CRL alike) and from `/decisions`. Guard `test_letters_hub_linked.py`.

**3.3 Readout therapeutic areas, by hand: untagged 59% → 28%** (190 → 92 of 323).

- `_readout_ta_manual.json` holds 98 hand decisions:
  - 72 from the trial's own ClinicalTrials.gov conditions, only where the registry record names the row's drug;
  - 26 from the sponsor's SEC sentence that names the asset with its indication.
- None comes from a drug name. The guard rejects a basis that is only the drug name.
- **20 rows carry an NCT that is another drug's trial**, for example ARV-471 pointing to an ARV-806 study and Elonva pointing to a pembrolizumab gastric trial. They are left untagged and listed for a hand fix of the NCT.
- `apply_readout_ta_manual.py` applies the file every run and never overwrites a tag already held.

**3.4** Every `/conference/{CODE}` page (14) opens with "{Meeting} 2026 takes place {dates} in {city}." The sentence is built from the page's own facts, and its tense follows the Eastern date (EASD and ESC: "took place"). Guard `test_conference_ledes.py`.

**3.5** There is no build action, and no console data was readable from here. Left for your re-read.

## Tier 4

**4.1 13F block.**

- **I opened the file as ordered and it is not publishable:**
  - its latest quarter is 2026-03-31;
  - three of its six fund CIKs belong to other filers: "venBio" 0001603466 holds NVDA, AMZN and SPY; "Perceptive" 0001224608 is CNO Financial Group; "Foresite" 0001540531 holds SHAK and RBLX.
- **Replacement:** `sync_13f_specialists.py` reads ten funds' latest 13F-HR directly from EDGAR. Every CIK is checked against the filer name EDGAR returns. The ten are Baker Bros, RA Capital, Perceptive (1224962), OrbiMed, Avoro (formerly venBio, 1633313), RTW, EcoR1, BVF, Redmile and Cormorant. All ten filings are for the quarter ended 2026-06-30, filed 2026-08-14. Only long common positions are used; Perceptive's RVMD warrants (a different CUSIP) are excluded.
- **Published:** `inject_13f_block.py` puts one paragraph per held ticker on 438 decision and drug pages, citing the filing.
- **Guard:** every fund and share count matches the verified data, and the rejected CIKs are refused.

**4.2 AdComm history.**

- The CSV's abstracts are cut at 300 characters and only 4 of 140 state a meeting date. So the CSV seeds the list, and the Federal Register API supplies each notice's DATES field plus the notices the CSV missed.
- `/adcomm` now lists **187 drug and biologic advisory committee meeting notices from 2020 to 2026**, with the meeting date, committee and a link to the FR notice. It includes 137 of the CSV's 138 drug/biologic notices. The 46 device-panel notices are left out, and the page says so.
- No votes and no company or drug.
- The next meeting is the Dermatologic and Ophthalmic Drugs AC on 2026-10-30.

**4.3 Orange Book exclusivity.**

- `fetch_orange_book.py` refreshes the FDA zip weekly. The repo copy was from 09-01; the files are now dated 2026-09-11.
- `/patent-cliff/exclusivity` lists **858 NDA exclusivities ending from today through 2031**: orphan 288, NCE 165, pediatric 110, new indication 82, new patient population 60. Each row has brand, ingredient, applicant and an NDA link.
- The page carries a "not a generic launch" disclosure, and the hub links it.

**4.4 `daily/NEW_*.csv` into `/pdufa-date-changes`: not done, because the data cannot support it.**

- The files hold 3,433 rows: 3,236 PhaseReadout and 197 untyped. **None is a PDUFA row.**
- The apparent readout "date changes" (18) are registry estimates and several trials of one drug interleaved. The two that are company-filed are a narrowing within one filing, not moves.
- Nothing published. If you want readout-guidance moves as their own page, that is a separate build.

**4.5 CRL deficiency headings, read from the PDF.**

- `extract_crl_headings.py` downloaded every letter (365 distinct PDFs, 361 with a text layer) and keeps a line as a heading only if it stands alone in capitals and every word is in the FDA's section vocabulary. The openFDA OCR field is never used.
- `/crl` gains a "Sections addressed (from the PDF)" column: 339 letters show sections such as Product Quality Microbiology, Facility Inspections or Clinical/Statistical. Administrative sections are omitted.
- CRL decision pages with a linked letter show the same.
- **Guard:** every shown section is a heading read from that PDF.

**4.6 Readout leads #52 and the passed windows: my ruling, implemented reversibly** (`apply_readout_registry_signals.py` plus the API).

1. The registry's own status is recorded on the row (`_d.registry`) and served as "Completed per registry" (25 rows) or "Terminated per registry" (5 rows). No outcome is inferred.
2. Forward readouts whose whole window has passed with no signal are served "Window passed" (74 rows), computed per request.
3. The 20 NCT-mismatch rows are excluded and acked with that reason.

The watcher queue is acked to match. **This is a ruling you can overturn:** delete `_d.registry` and the status reverts.

**4.7 Truncated names (#65): the title builder is fixed, not the instances.**

- `drug_names.py` is now the one owner. A name cut at the archive feed's 44 characters is shortened to its last complete unit; an indication cut at 50 is dropped, never guessed.
- `rewrite_decision_snippets.py` no longer re-reads its own cut title. The 10 cut titles (for example "Ipratropium Bromide HFA Inhala") are whole.
- The `/decisions` rows are repaired too.
- **Guard** `test_no_truncated_drug_names.py`: 0 cut names across 476 pages and the listing.

**4.8 Housekeeping.** Files were moved to `_attic/2026-10-03_housekeeping/`, with a README; nothing was deleted.

- `ctgov_t1_raw_studies.json` (0 bytes).
- `smart_money_v2_cache.json` (109.8 MB, invalid JSON, ends mid-record).
- `fda_adcom_federal_register.json` (20 documents, none FDA: FEMA, rail, fisheries).
- `adcom_baserate_v1.json` is referenced by no build script. No build path references DrugBank's `full database.xml`.

## One more for review

The FDA approved **pirtobrutinib (Jaypirca, Eli Lilly) for previously untreated CLL/SLL on 2026-10-02** (FDA "What's New: Drugs", 15:31 Eastern). We track no event for it and have not published a decision page. Do you want the same treatment as Gazyva?

## Files

New:

- `drug_names.py`
- `build_decision_lede.py`, `sync_novel_approvals.py`, `sync_archive_fda_dates.py`
- `watch_edgar_8k.py`, `apply_1003b_gazyva.py`, `decision_pages_2026_10_03_rhhby.json`
- `apply_readout_ta_manual.py`, `_readout_ta_manual.json`, `apply_readout_registry_signals.py`
- `inject_conference_lede.py`, `sync_13f_specialists.py`, `inject_13f_block.py`
- `build_adcomm_history.py`, `fetch_orange_book.py`, `build_exclusivity_cliff.py`, `extract_crl_headings.py`
- data files: `_fda_novel_approvals.json`, `_fda_action_archive.json`, `_sponsor_coverage.json`, `_13f_specialists.json`, `_cusip_symbol_map.json`, `_adcomm_fr_notices.json`, `_crl_headings.json`, `_readout_watch_ack.json`
- 12 new tests.

Changed:

- `rewrite_decision_snippets.py`, `sync_decisions_listing.py`, `inject_fda_action_record.py`
- `build_fda_letters_hub.py`, `build_monthly_decisions.py`
- `mark_calendar_decided.py`, `mark_event_pages_decided.py`
- `link_crl_letters.py`, `build_crl_hub.py`
- `api/v1/_lib.mjs`
- the workflow and the chain.
