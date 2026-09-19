# Builder reply to the 09-15 audit: the key, the source, and the page that lied for 78 days
**2026-09-15, written 12:30 Pacific = 15:30 Eastern = 19:30 UTC.** *Per RULE 1 every time here carries its zone. Not investment advice.*

The seven-item ORDER is shipped. Your framing held: every item was one value corrected somewhere and its copies left behind. Working the copies turned up four things the audit did not have, one of them a live forward PDUFA page stating a date the FDA had replaced eleven weeks earlier. Those are in section 3 and they are the reason this note is longer than the ORDER.

---

## 1. The ORDER, item by item

**1. The CORT row.** `readout_cort_2026-09-15` is now `pdufa_cort_2026-12-17`: `date_month` 2026-12, `therapeutic_area` "Endocrinology / Metabolic", `indication` "Cushing's syndrome (hypercortisolism)", `url` `/pdufa/CORT-relacorilant`, and the date is sourced first-hand to Corcept's 8-K of 2026-07-29 (EX-99.1, accession 0001628280-26-050607: *"New Drug Application for relacorilant resubmitted with a Prescription Drug User Fee Act (PDUFA) date of December 17, 2026"*). The calendar linked `/pdufa/CORT` for the same row; it now links the same page the API does (section 2c).

**2. `date_month == date[:7]`.** `tests/test_row_fields_agree.py`, invariant 1. Proved 0 → planted 1 → 0.

**3. The id carries the row's date; the prefix matches the type.** Same file, invariants 2 and 3, and here I need to report a decision rather than just a proof. Your check was right and it found **39 rows, not one**: 38 ids beyond CORT embed a date the row no longer holds. Two rows are sponsor moves (CAPR Aug 22 → Nov 22; NVO Mim8's withdrawn Sep 30), one is a decided row keyed on its action date (CORT ROSELLA), and **35 are readouts whose ClinicalTrials.gov estimate slid in the 09-14 registry re-sync**. No row in the dataset carried a `date_history` field, so none of the 39 moves was recorded anywhere on the row.

Re-keying all 39 would have been the literal reading of item 3. I did not do it, for one reason: **an id is a primary key an API consumer may already hold.** Rewriting it turns one event into two in their store every time the FDA extends a date or a registry estimate moves, which is often. The rule as shipped: a MOVE keeps its key and documents the move in `_d.date_history` (the date the row was keyed on, the date it holds, when it changed, why, and the announcing document where there is one); a CORRECTION (the date was never real: a manufactured 15th, a `readout_` prefix on a decision) is re-keyed. CORT was a correction and was re-keyed. The 38 moves now each carry a `date_history`, and the guard fails any id/date disagreement that `date_history` does not cover — so a stale key with no history is still impossible, which was the point. Proved 0 → 1 → 0 on both branches (a history that covers the id's date passes; a history for a different date fails). `/developers` now states the id policy so consumers know the key is stable. If you want the literal re-key instead, it is one flag away and I will do it; I think it would be the wrong call.

**4. `source_url` in the API.** Shipped, with `source` and `date_history` beside it; `/developers` documents all three. Coverage went from **0 of 456 to 262 of 456** in one pass because the provenance already existed in the wrong field: 246 rows carried their primary document in `url` (55 SEC filings, 180 registry records, press releases). Those are copied to `source_url` and left in `url` only where `url` is the row's page (section 2c). RARE is sourced first-hand to Ultragenyx 8-K 2026-04-02 (accession 0001193125-26-139084; quote read from the document before writing), with the February "third quarter of 2026" statement recorded on the row as the lower-resolution statement the day supersedes. MRK was already sourced on 09-09 (8-K 2026-02-03 + Q2 10-Q) and MIRM on 09-10; both now reach the API. The next ten upcoming PDUFAs in your table all return a `source_url` now. **Still null: 37 forward PDUFA rows whose only link was our own page.** That is the EDGAR pass, and it is next.

**5. build-info.** `next_days` is `null` when `next_status` is "awaiting" (you were right that 0 reads as "today"); `days_since_goal` says how long it has waited. The guard fails a non-null `next_days` on an awaiting pointer. The two-region experiment is in section 4 with what I could and could not measure.

**6. The precision-provenance rule.** In the harvester: `catalyst_crawler.resolve_date_precision()`, applied inside `merge()` so every harvest passes through it. Most recent day-precision statement wins; a quarter, half, month or year is never rounded to a day (a "day" whose value is a quarter label is demoted, not served); a later coarse statement does not override an earlier day — when the day falls inside the later window the coarse row is dropped as redundant, when it falls outside both are kept and the coarse row is flagged `window-conflict` for a person. `merge_crawl_to_slate.py` no longer defaults a blank precision to "day" (it was doing exactly that) and holds any non-day or unknown-precision candidate for review. `tests/test_precision_provenance_rule.py` proves the three rules on synthetic records including your RARE trap. Publicly: `/methodology#date-precision`, three rules in plain words.

**7. Canonicals.** `ABBV-tavapadon-2` → `ABBV-tavapadon`, `NVO-cagrisema` → `NVO-am833`; MRK/GILD trodelvy kept as you ruled. The duplicate gets a canonical, `noindex,follow`, a visible pointer to the maintained page, drops out of the sitemap, and loses every internal link; no page deleted. **The guard's title census then found eight more pairs** (section 3d).

---

## 2. Found while working the ORDER

**a. `/pdufa/PRAX` told readers relutrigine's goal date was September 27, 2026 — twelve days from today — for 78 days after the FDA moved it.** Praxis 8-K 2026-06-29 (accession 0001689548-26-000069): the FDA extended the review *"from September 27, 2026 to December 27, 2026"* after a major amendment; the 8-K of 2026-08-06 restates December 27 and gives ulixacaltamide's January 29, 2027. The dataset held December 27 the whole time. The page did not move because `refresh_moved_pdufa_pages.py` skips any ticker with two live events ("a wrong rewrite is worse than a stale date"), and PRAX has two. Fixed on the page, both PRAX rows sourced, the move recorded in `date_history` and on `/pdufa-date-changes` (which now reads sourced `date_history` entries as well as `prior_pdufa_date`). The refresher now disambiguates a two-event ticker by the date the page states against each row's `date_history`, then by the page's own "Drug / candidate" fact, and it no longer writes a day onto a month or quarter row (it was queuing seven `2026-12-31` rewrites; the window fixer was undoing them downstream). New guard: `tests/test_event_page_states_row_date.py` — the page an upcoming day-precision row links must state that row's date. Proved by planting Sep 27 back on the page.

**b. Two rows linked the page describing the ticker's OTHER event.** COGT's PEAK combination (Nov 30) linked the SUMMIT page (Dec 30); PRAX's ulixacaltamide (Jan 29, 2027) linked the relutrigine page (Dec 27). Both events had their own per-event page all along; the rows now name them, and so does the calendar. Cause: `build_pdufa_event_pages.py` treated a page that merely *mentions* a drug as covering its event, so a second event on a ticker never got a page it was pointed at. "Covered" now means the drug is in the page's title or the page states this row's date.

**c. One event, one page.** 17 of 49 upcoming rows sent an API consumer somewhere other than where the calendar sends a reader: MRK, VTRS, NUVL, ABBV, AZN, BAYRY, NVO to the bare ticker page while the calendar linked the per-event page; CAPR, GILD, IRD to a press release; MIRM, NVCR, AXSM, BBIO to an SEC filing. `sync_api_urls_to_calendar.py` aligns `url` to the calendar's per-event page (the document moving to `source_url`), and where the API already named a per-event page and the calendar the ticker's history page, the calendar moves instead. `tests/test_api_url_matches_calendar.py` holds it: 36 rows link the same page on both surfaces; no upcoming row's `url` is an off-site document. This closes your 09-09b item 5.

**d. `/readouts` JSON-LD: all 81 Events said the 15th.** 64 were ClinicalTrials.gov month estimates stamped `2026-MM-15T00:00:00-04:00` by `fix_event_schema.py`, which looked up a date without its precision; 17 were readouts no longer in the dataset or the crawl, orphaned structured data. Month estimates now publish `startDate: "2026-09"` (ISO 8601 reduced precision, valid schema.org Date); unbacked Events are demoted to WebPage. Fifth invariant in `test_cross_surface_values.py`, proved by plant. This was the one hub the 09-14 window fix did not cover, and the day-of-month histogram you ran was on the API, which is why it stayed hidden.

**e. Eight more duplicate pairs.** The canonical guard's title census (no two indexable `/pdufa` pages may share a title) found BFRI, JAZZ, PHAR, PTGX, ROIV, TAK and ZYME each with a bare-ticker decision page (linked by the dataset, the drug pages and the screener) and a thinner drug-slug twin with zero inbound links, plus `GILD-bictegravir-and` / `-lenacapavi` (a truncated slug; one of the six truncated names). All canonicalised to the linked page, ten in total.

**f. The crawl re-surfaced "NUVL 2026-09-18 Neladalkib" as AUTO-SAFE.** September 18 is zidesamtinib's goal date, approved July 22; the crawler mis-attributed it and the decided-ticker check only looked at decision dates (58 days away). It now blocks on a decided row's goal date too; the candidate shows `ticker-decided-2026-09-18(±0d)` and is held.

**g. The decided banner over a windowed page.** GILD-trodelvy and RHHBY-lunsumio-polivy (the two decided pages the 09-14 window pass had rewritten to "not sourced") could not be retitled by the decided marker because it expected an ISO date in the title and the fact; it now handles the windowed and unsourced shapes, and both pages read "FDA decision: … Approved …" in title, fact and FAQ.

---

## 3. Guards

Seven new or extended: `test_row_fields_agree` (3 invariants), `test_precision_provenance_rule` (4 rules + merge wiring + slate default), `test_duplicate_event_pages_canonical` (canonical + noindex + sitemap + unlinked + title census), `test_api_url_matches_calendar`, `test_event_page_states_row_date`, `test_cross_surface_values` (+ awaiting/null and readouts-schema invariants), and `build_date_modified.py` now strips its own dateModified from pages that became noindex. Every plant is recorded above at the item it protects. **Full suite: 89 pass, 0 fail.**

---

## 4. Section 5, the two clients

What the code says: `built` is the GENERATION time of the tree and `commit_at_build` is HEAD at generation; Vercel's `last-modified` is the DEPLOY time. They are two different clocks by design, and the gap between them is generation-to-deploy latency. On your 09-15 read that gap was 12 hours (a 04:58Z build served with a 17:07Z `last-modified`), which fits a redeploy of an unchanged file — the CDN-purge step re-deploys the same artifact — not a field that failed to refresh: the field cannot disagree with the deployed bytes, because it is inside them. The `age: 2626` against `max-age=300` with `HIT` on every probe is the edge serving past its own TTL, which is Vercel's stale-while-revalidate behaviour, not ours; and your non-browser client at 17:44Z receiving `c1bfc628c` while your browser at 17:50Z received `a62614368` is one edge that had not revalidated yet.

**Measured today after this push, three clients within ten seconds** (default UA, browser-like UA, `Cache-Control: no-cache`), all from my egress (`x-vercel-id` edge `pdx1`): one body (`built 2026-09-15T18:39:47Z`, `commit_at_build bc399f348`), one `last-modified` (18:46:52 GMT, 7 minutes after generation, which is the push-to-deploy latency), first probe `MISS age 0` then `HIT age 2, 4`. Consistent with the edge explanation. **The qualification stands**: three fetches from one region is not a two-region experiment, and I cannot egress from a second PoP from this machine. If you can run the same three fetches from your side within the same minute, the comparison is the `last-modified` header: equal with a different body would indict the field; both different would indict the edge.

**Made durable:** the post-deploy verifier now takes `--expect-commit` (the pushed SHA and its parent, since the stamp is taken before the CI commit) and fails the run if the live `commit_at_build` names any other build; it also prints `last-modified`, `age` and the edge on every pass so the next disagreement is on the record with its mechanism.

---

## 5. The source pass over every unsourced forward PDUFA (task #77, first half)

`edgar_source_pass.py`: for each of the 34 upcoming rows still without `source_url` after the ORDER, search EDGAR full-text for the row's date phrase with "PDUFA", **restricted to the sponsor's own filings** (a first dry run matched Nuvalent's November 27 to BridgeBio's 8-K and Roche's November 30 to Cogent's — same date, other company — so the filer must now be the sponsor or the row's CIK), fetch the document, and write `source_url` only when the date sits within 400 characters of "PDUFA"/"target action date" in the text. 22 rows sourced that way, each with the quote on the row. The rest by hand, each document read before writing:

- **Roche ×4** (not an SEC registrant): Genentech press releases state every one — Tecentriq adjuvant dMMR/MSI-H colon "by October 9, 2026" (2026-06-10), Enspryng TED "by October 15, 2026" (2026-06-29), giredestrant adjuvant "by November 30, 2026" (2026-06-01), giredestrant + everolimus "by December 18, 2026" (2026-02-19).
- **GSK bepirovirsen**: Ionis, the licensor, 8-K 2026-07-29: "PDUFA target action date of October 26, 2026".
- **REGN cemdisiran — a precision defect, caught.** Regeneron's 8-K of 2026-07-30 states "a target action date in **November 2026**", a month. The row carried **November 30 at day precision**: a month-end sentinel of exactly the class the 09-10 P0 found, and one the quarter-end guard does not cover because it is a month-end, not a quarter-end. Downgraded to month, recorded in `date_history`, calendar and page windowed to "Nov 2026". The accepted NDA is cemdisiran monotherapy for gMG; the row had named the cemdisiran + pozelimab combination and is renamed.
- **NUVL neladalkib — the sponsor no longer exists as a ticker.** GSK completed its acquisition of Nuvalent in July 2026 (tender at $124.00 per share from June 24; Nuvalent 8-K 2026-07-15, merger completion). The site carried NUVL as a live Mid-cap sponsor with a price frozen at $123.96 — the tender price. The row, the slate, the calendar row, the event page and `/ticker/NUVL` now say GSK (formerly Nuvalent, NUVL) with the 8-K linked. The PDUFA date itself is sourced to Royalty Pharma's 8-K of 2026-08-05, which quotes Nuvalent's May 2026 acceptance announcement ("Priority Review with a PDUFA date of November 27, 2026"); Nuvalent's own May release is not retrievable from EDGAR full-text under any phrasing I tried, and the company will not file again.

**Live count after this batch: upcoming PDUFA rows with `source_url` 43 of 48.** The five still null are the ones no filing supports even at month precision — ABBV tavapadon, AZN Ultomiris, BAYRY Kerendia, NVO CagriSema (the 09-10 "month kept" four, publicly listed as unbacked and ratcheted) and NVO Mim8 (year). These are the auditor's item 8 carry, and the honest end state for them is a further downgrade or a withdrawal, which I would rather have ruled on than do unilaterally.

## 6. Carried

The 9 unbacked window pages (ratchet holding), 22 readout leads, the TA back-fill by hand, the openFDA pass over the 36 Decided rows (second half of #77, next), and — new today — 13 Estimated readouts the 09-14 registry re-sync moved to dates already in the past (one to 2023), which are neither reported nor visibly upcoming and need a ruling on treatment.

---

## 6. Live, from a non-browser client, after the deploy

**Push `297e7ea1a`, verified 2026-09-15 ~11:50 Pacific = 14:50 Eastern = 18:50 UTC, `Cache-Control: no-cache`.**

- API 456 rows, `as_of` 2026-09-15. **`source_url` present on 265 of 456** (was 0); `date_history` on 39.
- CORT: `pdufa_cort_2026-12-17`, `date` 2026-12-17, `date_month` 2026-12, `therapeutic_area` Endocrinology / Metabolic, `indication` Cushing's syndrome (hypercortisolism), `url` /pdufa/CORT-relacorilant, `source_url` the Corcept 8-K, `days_to_decision` 93. Four faults, four closed.
- `date_month != date[:7]` over the live corpus: **0 rows.**
- Next ten upcoming PDUFAs: RARE, MRK, INCY, MIRM, IRD sourced; RHHBY ×2, MRK 10-10, VTRS, GSK still null (the EDGAR pass).
- build-info: `next_days: null`, `next_status: "awaiting"`, `days_since_goal: 4`, `commit_at_build bc399f348` (parent of the push, as the stamp convention says).
- `/pdufa/PRAX` title "PRAX-562, Dec 27 2026"; "Sep 27" nowhere on the page. `/pdufa/PRAX-relutrigine` fact 2026-12-27. `/pdufa-date-changes` lists the PRAX and CAPR moves with their filings.
- `/calendar` links `/pdufa/CORT-relacorilant`, same as the API.
- `/developers` documents `source_url` and `date_history`; `/methodology#date-precision` is live.
- `/pdufa/ABBV-tavapadon-2` → canonical ABBV-tavapadon, noindex; `/pdufa/NVO-cagrisema` → NVO-am833, noindex; `/pdufa/PTGX-rusfertide` → PTGX, noindex.
- `/readouts`: 64 Events, **0 day-stamped** (81 of 81 were, this morning).
