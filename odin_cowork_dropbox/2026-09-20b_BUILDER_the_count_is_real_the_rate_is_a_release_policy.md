# Builder, 09-20b: the count is real, the rate is a release policy, and the letters moved two "late" decisions onto their goal day
**2026-09-20, written 19:15 Pacific = 22:15 Eastern = 2026-09-21 02:15 UTC.** *Per RULE 1 every time here carries its zone. Facts and file contents only; not investment advice.*

Reply to the second data sweep ("the best fact we own is sitting in a file we already publish half of"). Items 1, 2 (the four named letters) and 3 are built and guarded in this push; 4–8 are queued below with what I found while opening the files. One disagreement with the audit's framing, argued from the data, in section 1.

---

## 1. Item 1: the number is on `/crl` — as a count, with the shape that explains it, and not as 67%

**The field, confirmed the way the audit asked.** openFDA's own field reference for this endpoint (`open.fda.gov/fields/transparencycrl.yaml`) does **not** document `approval_status` at all; it documents file_name, application_number, letter_type, letter_date, company fields and text. The meaning comes from the FDA's July 10, 2025 release announcement, which describes the first batch as "decision letters associated with since-approved applications", and from the endpoint's own count: `api.fda.gov/transparency/crl.json?count=approval_status` returned **Approved 309 / Unapproved 149** live on 09-20 (total 458; openFDA `last_updated` 2026-08-13 live vs 2026-08-26 in our August file, same record set). So the sentence the field supports is: *309 of the 458 released letters were issued to applications the FDA has since approved.* That is now on the page, sourced to the endpoint.

**Why I did not write 67%, and I want to argue it rather than assert it.** The by-year split of `approval_status`, now a table on the page:

| letter year | since approved | not approved |
|---|---|---|
| 2026 | 0 | 32 |
| 2025 | 0 | 59 |
| 2024 | 14 | 55 |
| 2023 | 29 | 1 |
| 2022 and earlier | 266 | 2 |

Every letter dated 2023 or earlier but two is on a since-approved application; every letter from 2025 on is on an unapproved one. That is not what "most CRLs lead to approval" looks like; it is what the FDA's release policy looks like — archived letters published only for applications it had approved, then everything from 2024 onward regardless of outcome. 309/458 is the share of the *release* the FDA chose to draw from approved files. Publishing it as the empirical proof that a CRL is not a rejection would be teaching answer engines a number that measures FDA's publication choices. `build_crl_hub.py`'s own docstring from 09-02 says the same thing ("approved-by-construction"), and the corpus README discipline is counts, never rates. The page now says, in plain language: what a CRL is, that it is not a permanent rejection, that 309 released letters precede an approval — *and* that the corpus cannot say how often, because of the shape above. I think that is the stronger moat sentence: nobody else states the release policy correctly either.

**Also on `/crl`:** the record count reconciled (**458 records → 455 listed letters**: 13 letters the old file-name filter dropped because FDA named them with spaces or commas, all resolving once URL-encoded, HEAD 200 checked; 2 records that repeat another verbatim in FDA's own release; 1 marked "Under Review for Release" with no file). Odd-named files are listed now. Guard `tests/test_crl_hub_counts.py`: title count, released-block counts and the by-year totals must equal the corpus file, and the page must state no percentage rate from it. Proven against the committed 444-page → FAIL → rebuilt → OK.

## 2. Item 3: the capture is scheduled, and it is keyed on records, not on openFDA's clock

`capture_crl_corpus.py` runs every CI build before `/crl`: pages the endpoint (five requests), compares the set of (file, letter date, status) with the newest snapshot on disk, writes `CRL_corpus_openFDA_<date>.json` only when that set changed, and appends one row to `_crl_capture_series.json` every run. The two hand-made snapshots seed the series (439 → 458, +19), and `/crl` renders it as "The release over time". Two things learned on the first run: openFDA's `last_updated` went *backwards* (08-26 in our file, 08-13 live) for an identical record set, so change detection cannot use it; and the builders (`build_crl_hub`, `link_crl_letters`, `build_hub_faq`, the guard) now read `newest_corpus()` instead of a hard-coded August file name.

## 3. Item 2: the letters — four read against the PDF, and what they did to the timing statistic

`_crl_letter_findings.json` is a hand-verified ledger: for each letter, page 1 rendered from the FDA-hosted PDF and the rest via pdftotext (page 1 of three of the four has no text layer, which is exactly why the audit said not to trust the OCR field). `link_crl_letters.py` renders the ledger on the decision page under "What the letter says has to be fixed", headings and summaries only, no OCR pasted.

| letter | what the FDA said, in its own section headings |
|---|---|
| **ACHV** cytisinicline, NDA 218995, dated 2026-06-20 | *Facility inspections* (CGMP deficiencies at a listed facility, Form 483 responses, possible re-inspection and PAI); *Prescribing information* (labeling responsive to FDA's June 4 communication). Clinical pharmacology comment on ESRD dosing, which the letter itself labels not an approvability issue. No efficacy or safety deficiency. |
| **UNCY** oxylanthanum carbonate, NDA 218607, dated 2025-06-27 | *Facility inspections* only (CGMP + PAI deficiencies at a listed facility). Labeling reserved. |
| **UNCY** same NDA, second letter dated 2026-06-29 | *Facility inspections* only; acknowledges the Dec 29, 2025 resubmission; both PAI and CGMP surveillance outcomes needed before approval. |
| **CORT** relacorilant, NDA 219398, **corrected** letter dated 2026-01-28 | *Clinical and statistical — substantial evidence of effectiveness*: 455 met its endpoint in a highly enriched population (40 of 102 hypertensive subjects discontinued open-label; 46 entered randomized withdrawal), 456 missed (−0.85 mmHg, 95% CI −6.7 to 4.9, p 0.77), the post-hoc subgroup was not pre-specified and failed FDA's own imputation; *Benefit-risk — drug-induced liver injury*: four probable DILI cases, one ALT of 1,952 U/L. The letter states the action date **remains December 30, 2025**. |

LNTH's June 26 CRL is not in the release; nothing to quote.

**The finding underneath.** ACHV's letter is dated **Friday June 20** — its goal date. The company announced it Monday June 22, and our page (and the timing statistic) carried June 22, "+2 days". UNCY's is dated **June 29**, its goal date; announced June 30, "+1". Both had been counted as *late*. With the FDA's own document in hand, the action date is the letter date, so:

- Dataset rows carry `_d.fda_action_date` (new field, in the API's `CORE_EXTRA`, documented on `/developers`), with the letter as `decision_source` / `decision_source_url`; the page slug keeps the announcement day (it is the page's id) and the row says both.
- **Timing statistic 29: 19 early / 7 on the day / 3 late → 19 / 9 / 1**, restated on `/calendar`, `/learn/what-is-a-pdufa-date`, `/research/fda-decision-timing`; the study rows read "June 20, 2026 (FDA letter date; announced June 22, 2026), +0 days". The one remaining late decision is REPL (+4, goal Sunday August 2, announced August 6, no FDA document). This is the mirror of this morning's P0-A: today's "late" bucket was announcement lag twice over.
- Decision-page snippets: "CRL Jun 20, 2026 | ACHV FDA Decision", "received a Complete Response Letter dated June 20, 2026 (announced June 22, 2026), its PDUFA goal date". `fix_meta_lengths` recognises the new answer format.
- `link_crl_letters` had been matching **zero** letters since 09-02: it parsed the company from the meta description, which the snippet rewriter had shortened to "ACHV: …", so the token set was {"achv"}. The dataset's company field is the owner now; nine pages link their letter (ABBV, ACHV, ALDX, CING, CORT, GRCE, RGNX, UNCY ×2), each card dated with the **letter's** date (the old card printed the page date on the FDA's letter — a wrong primary-source date on the UNCY 2025 page since 09-02).
- `/pdufa/CORT` and `/pdufa/CORT-relacorilant` (the December 17 resubmission) carry "What the FDA said the last time": the corrected letter's two deficiency sections, with the PDF, and the sentence that this states what the FDA wrote and is not a view on the outcome.

## 4. Items 4–8: queued, with what I saw

- **4, AdComm notices.** Agreed on scope: a meeting calendar from Federal Register URLs, votes stay hand-sourced. Not started tonight.
- **5, one 09-05 dataset.** Agreed the 13F block leads. Not started tonight; it needs the holdings file opened and its as-of dates checked before a sentence is written.
- **6, exclusivity.txt.** Not started.
- **7, daily/NEW_*.csv into `/pdufa-date-changes`.** Not started.
- **8, housekeeping.** `adcom_baserate_v1.json` is a hand-typed probability file and must never reach a page: agreed; it will be moved to `_site_attic/` (not walked by any build script) in the next push, not this one, so the move is its own commit. DrugBank: nothing on the site derives from `full database.xml` that I know of; a grep of the build scripts for it is the check, and it goes in the next push with the licence question flagged for David rather than answered by me. The 93.9 GB bruteforce file and the truncated caches are David's disk; listed, not deleted.

## 5. Item 5 of the morning audit, still open

The five unbacked rows (ABBV tavapadon, AZN Ultomiris, BAYRY Kerendia, NVO CagriSema, NVO Mim8): the auditor recommends withdrawing the day and the forward listing, keeping the drug pages. That is David's ruling; asked in this session, ratchet holds at 9 until it comes.

## 6. The sync client, again

During the evening rebuild, 60 `index (1).html` copies appeared at 19:04:59–19:05:05 Pacific, walking condition → fda-decision → fda-this-month → research → ticker in alphabetical order — the signature of something copying files as a build writes them. No tracked pages were deleted this time. The artefact guard from this afternoon caught them before the guard suite ran; I removed them by hand. Until the folder is out of Google Drive's backup set, every local rebuild needs that check, and I am treating CI as the only clean build.

*Live verification follows the deploy in `_verify_live_0920b.py`. Not investment advice.*
