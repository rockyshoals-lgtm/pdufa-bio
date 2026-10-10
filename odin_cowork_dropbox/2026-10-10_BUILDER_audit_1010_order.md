# Builder: the 10-10 order, items 1 to 7, plus the 10-04 UX order (items 2 to 10)
**2026-10-10, written ~10:30 Pacific = 13:30 Eastern (Saturday). CI times UTC.** *RULE 1.*
*Facts and build mechanics only. Not investment advice.*

## 1. Remibrutinib: published 09:55 Pacific, and why the lead was slow

Published before this order arrived (`e26ec6022`, note of 10-10 09:25). One correction to the audit: the application is **NDA 218436** (Rhapsido), not 219139; SUPPL-1, efficacy, FDA data say AP 2026-10-06, Novartis announced 10-07. The letter URL openFDA lists returned 404 on 10-10 and will be swapped in by `sync_fda_action_dates.py` when it is served.

**The slow link, named.** The drug-page watcher had three passes: the FDA press RSS (the FDA issued no notice for this supplement), the FDA oncology notifications page (not oncology), and openFDA, whose Drugs@FDA data updated on 10-09 with the 10-06 action. The sponsor-feed watcher never looked because it arms only rows with a pending PDUFA date, and this supplement had none (Novartis is a 20-F filer; its Q4-2025 submission carried no date we captured). So openFDA was the only path, and openFDA runs ~3 days behind. The first build after openFDA updated was 10-10 00:27Z.

**Fix.** The drug-page watcher gained a fourth pass that reads **every** feed in `_sponsor_feeds.json` for any sponsor, armed or not, and scans headlines for tracked drug names with approval language. Novartis publishes no RSS (four URLs tried, all 404) but its US news archive embeds a schema.org ItemList of NewsArticle with `datePublished`; `watch_sponsor_newswire.parse_listing` now reads JSON-LD listings for any host, and NVS carries `html:https://www.novartis.com/us-en/news/news-archive`. Tested from the builder machine: 12 items, the Rhapsido release first, classified as an approval lead. Guard `tests/test_drug_watch_hears_sponsor_newsrooms.py`: the planted Novartis headline yields a remibrutinib lead; a readout decoy does not; NVS must carry a feed. Proved 0 → 1 (NVS feed removed) → 0. Had this pass existed on 10-07, the lead would have arrived with that night's build.

## 2. One page per pending application

* **Root cause:** `build_pdufa_event_pages.py` tested "slug already exists" before its own "does that page state THIS row's date" check, so a second application of the same drug never got a page.
* The Dec 18 giredestrant page **did** exist, under a slug cut mid-word (`/pdufa/RHHBY-giredestrant-in-combinatio`, title ending in an ellipsis) that nothing linked. Moved to `/pdufa/RHHBY-giredestrant-evera` (title "RHHBY PDUFA date: Giredestrant (evERA, with everolimus), Dec 18, 2026"); 301 added in vercel.json.
* `/pdufa/COGT-bezuclastinib-summit` written (Dec 30, 2026).
* Both rows carry `_d.event_slug` and `_d.trial`; the generator honours `event_slug`, and on a collision with a true sibling (another pending row, same ticker, same drug) derives `{TK}-{drug}-{trial}`. A lone row whose page states an old date (neladalkib, day → month today) is `fix_event_page_windows`' job and must not spawn a second page; the first run did, and that was caught and corrected.
* **`event_pages.py`** is now the one owner of "which page is this row's event page": a page qualifies only if it states the row's date (title, or Event startDate for day rows; `site_windows.window_label` for windows).
* **`enrich_event_pages.py`** (new, CI and chain) puts on every pending event page, from one generator: an Event schema at the row's date where none exists; a **sibling link** ("Also under FDA review from Cogent Biosciences, as a separate application: Bezuclastinib + sunitinib (PEAK), Nov 30, 2026 ..."); and the hand-sourced sentence and description from `_event_trial_facts.json`.
* **Guard `tests/test_event_page_titles_carry_date.py`:** every pending row (day or window) resolves to a page whose title carries its date; its `url` is that page; its calendar row links it; the page's Event startDate is the row's date. **40 of 40** pending rows (34 day-dated after the neladalkib ruling, 6 windows). Proved 0 → 1 (SUMMIT url planted back to the hub) → 0.

## 3. API `url` → the event page

`sync_event_urls.py` (new; runs before `ensure_calendar_rows` and again after the event pages are built) sets each pending row's `url` to `event_pages.resolve(row)` and repoints calendar rows that linked a bare hub. **36 dataset rows repointed, 7 calendar pages updated.** The loop was: the calendar followed the row's url, `sync_api_urls_to_calendar` followed the calendar, and nothing asked which page states the date. Enspryng's row now ends `/pdufa/RHHBY-enspryng`.

## 4. Enspryng, and the Event-schema claim

* `/pdufa/RHHBY-enspryng` carries the audit's description (146 chars) and the SatraGO sentence, quoted from Genentech's June 29 release and linked: "...in SatraGO-2 53% of patients on Enspryng achieved a proptosis response at week 24 versus 23% on placebo, meeting statistical significance; in SatraGO-1 the figures were 49% versus 31%, which did not meet statistical significance."
* The same file carries sentences and descriptions for both giredestrant pages and both bezuclastinib pages, each quoting only what its linked source states (the Cogent 8-K says "bezuclastinib in GIST", so the sentence does, not "plus sunitinib").
* **On "no Event schema":** I checked the live page, cache-busted. `/pdufa/RHHBY-enspryng` carries `"@type": "Event"` with `startDate 2026-10-15`, written with a space after the colon. Locally, **0 of the 38 resolved pending pages lack an Event schema.** The 09-02 `article:modified_time` on 26 pending pages is real: those pages' content had not changed since 09-02. `build_date_modified.py` moves that date only on a content change, by design (twice before, a stamp that advanced nightly had to be undone). Today's enrichment changed 6 of them (the 4 trial-fact pages and the 2 sibling pages); the rest keep their true date. If the ruling is that every pending page should restate "status as of" daily, that is a content change and the stamp would follow; I did not fabricate it.

## 5. Neladalkib ruling applied

`pdufa_nuvl_2026-11-27`: `dp` month, `dm` 2026-11, `date` null in the API; source GSK plc 6-K 2026-07-28 (Q2 results), quote verbatim: "Neladalkib is an investigational ALK tyrosine kinase inhibitor (TKI) currently under review with the US FDA for use by patients with TKI pre-treated ALK-positive NSCLC, with PDUFA date anticipated in November 2026." `date_history` records the former day and its Royalty Pharma origin. `/pdufa/GSK-neladalkib` re-windowed to "Nov 2026".

## 6. The 10-04 UX order

| # | Done |
|---|---|
| 2 stylesheet | `site_style.HUB_STYLE` is the one hub stylesheet; `/patent-cliff/exclusivity` uses it plus fonts.css. Guard `tests/test_header_styled.py` reads each page's own header markup (`.top`/`.hd`, `<nav>`/`.nav`) and requires the inline CSS to style it: failed on the real stub (1 page), 0 after. 1,432 indexable pages checked. |
| 3 /adcomm | One count. Title "FDA Advisory Committee Meetings 2020-2026: 187 Federal Register Notices, 2 Votes"; lede "187 ... 2 of them (July 2026) carry a hand-sourced vote"; FAQ the same; history **above** the FAQ (it had been inserted inside the FAQ's own marker block and was wiped on every FAQ rebuild, which is why it sat under the footer); each vote card links its FR notice and each of the two notice rows says "vote recorded above". `_adcomm_counts.json` written by the history builder feeds the lede and FAQ; CI already ran it first, the local chain now does too. Guard `tests/test_adcomm_counts_agree.py`, proved 0 → 1 (lede planted to 2) → 0. |
| 4 13F | A headed table (fund / shares / value / filing) above the FAQ with the caveat beneath, on 436 pages. `sync_13f_specialists.py` now records `sshPrnamtType` and `titleOfClass` and keeps only SH + common-stock classes; the renderer refuses anything else; EDGAR re-read: 10 funds, 315 tickers (was 317: the non-common rows left). Guard `tests/test_13f_rows_common_stock.py`: 623 rows all SH/common; a planted PRN note and a planted warrant are refused. |
| 5 letters count | One owner `n` already fed title and h1; the Dataset schema now states `size` too. Guard `tests/test_letters_hub_count_one_owner.py`: title = h1 = schema = table rows (84). |
| 6 freshness strip | "Page updated {date} · next FDA decision ... · Data as of {rebuild time ET}" on 1,677 pages. The strip is excluded from the content hash, so relabelling it moved no lastmod. |
| 7 chart caption | JUVMO reads "Announced 9/28/26 (FDA action 9/25/26)" and the SVG label says "announced"; `fix_chart_captions.py` repaired 5 more (MNKD, MRK, TLX, UNCY ...). Guard `tests/test_chart_caption_fda_date.py`, proved 0 → 1 → 0. |
| 8 ⌘K pill | Below 480px it is a 44px icon (no "Search ⌘K" text) that hides on scroll-down and returns on scroll-up; `aria-label` added. |
| 9 exclusivity lede | Confirmed computed at build from `eastern_today()`: today reads "between October 10, 2026 and December 31, 2031". |
| 10 | see 7 below |

## 7. Weekly page, NOINDEX list, rulings carried

* **`/fda-approval-decisions-this-week`** (`build_weekly_decisions.py`, daily in CI and the chain). Title "FDA approval decisions this week: Oct 5 to Oct 11, 2026"; sections Decided this week (dated by the FDA's action day, announcement day shown where it differs), Withdrawn this week, Still ahead this week, Goal date passed, Next week; FAQPage. Linked from `/fda-decisions-today` and `/fda-this-month`. This week: 2 decided (Tecentriq Oct 8, Rhapsido Oct 6), 0 ahead, next week 3.
* **NOINDEX, listed and each intended** (252 files): 119 `/fda-decision/` pages that are price-inferred records with no primary source (noindex lifts when `upgrade_verified_decisions.py` finds the source); 124 `/ticker/` hubs that are thin (no verified catalyst), set by `enrich_ticker_hubs.py`; 11 `/pdufa/` twins canonicalised to their primary by `canonicalise_duplicate_event_pages.py`; 8 legacy flat files (`app.html`, `calendar.html`, `capr.html`, `policy.html`, `preview.html`, `product.html`, `runup.html`, `today.html`). None is a page we want ranked.
* **Rulings still carried for David:** `goal_date_held:false` on goal_unsourced rows; the Jaypirca SUPPL-5 letter date (Drugs@FDA 12/02/2025 vs the notice's Dec 3); the RXC-005 / LY3527727 aliases on /drug/jaypirca; SMTP secrets; Google Drive exclusion; sources for AZN Ultomiris, NVO CagriSema, NVO Mim8.

## Live (appended ~11:05 Pacific = 14:05 Eastern; CI times UTC)

Commit `e62560970`, CI run 38072885662 **green** (guards passed in CI); build-info built 2026-10-10T17:51:07Z, next RHHBY 2026-10-15, `held_since` null. The push rebased over CI's 10-10 daily refresh (970 generated-file conflicts, mine taken; CI regenerated them).

Acceptance, read live and cache-busted:
* **Item 1:** published 09:55; watcher pass and guard in this commit.
* **Item 2:** `/pdufa/RHHBY-giredestrant-evera` 200, title "... Giredestrant (evERA, with everolimus), Dec 18, 2026", sibling line names lidERA Nov 30; `/pdufa/COGT-bezuclastinib-summit` 200, "Bezuclastinib, Dec 30, 2026", sibling line names PEAK Nov 30; the cut slug 308s to the new one. Guard: 40 of 40 pending rows.
* **Item 3:** API `pdufa_rhhby_2026-10-15` url ends `/pdufa/RHHBY-enspryng`; the calendar row links the same page.
* **Item 4:** Enspryng description and SatraGO sentence live; Event `startDate` 2026-10-15; `article:modified_time` 2026-10-10T13:25:56-04:00 (the content changed today). Pages still on the 09-02 stamp: 20 (26 before; the six that changed today moved). Those pages' content did not change; see section 4.
* **Item 5:** API `pdufa_nuvl_2026-11-27`: `date` null, `date_precision` month, `date_month` 2026-11; calendar row "GSK · Nov 2026" → `/pdufa/GSK-neladalkib`; page title "Neladalkib, Nov 2026".
* **Item 6:** `/patent-cliff/exclusivity` carries `.top`, `.brand`, `.nav a`; `/adcomm` title "187 Federal Register Notices, 2 Votes"; RVMD decision page carries the headed 13F table; strip reads "Page updated October 10, 2026 · ... · Data as of ..."; JUVMO caption "Announced 9/28/26 (FDA action 9/25/26)".
* **Item 7:** `/fda-approval-decisions-this-week` 200, "FDA approval decisions this week: Oct 5 to Oct 11, 2026".

**Guards this pass (all proved 0 → planted 1 → 0 on rendered output, or on the real defect → 0):** test_drug_watch_hears_sponsor_newsrooms, test_event_page_titles_carry_date, test_header_styled, test_adcomm_counts_agree, test_13f_rows_common_stock, test_letters_hub_count_one_owner, test_chart_caption_fda_date. Local guards 139 pass, 1 fail (SLS collector, which runs in CI).
