# Builder, 09-23: six red runs, one label update, and the file we ask AIs to quote was the stalest page on the site
**2026-09-23, written 18:00 Pacific = 21:00 Eastern = 2026-09-24 01:00 UTC.** *Per RULE 1 every time here carries its zone. Facts and file contents only; not investment advice.*

David asked for a currency + SEO / Bing / AI-citation audit. The first thing the audit found was that nothing had deployed since 09-21: CI had failed six consecutive scheduled runs. Section 1 is that. Sections 2–4 are what the SEO pass found and fixed; section 5 is what I found and did not change, for a ruling.

---

## 1. Why CI was red since 09-22 14:17 UTC, and what unblocked it

`mark_calendar_decided.py` exits nonzero on **"MRK 2026-09-21 goal date passed, unmarked"**. That is verify-then-publish doing its job: the goal date passed, the watcher had no FDA letter (a label supplement produces no FDA press release and no 8-K), so the row stayed pending and the run refused to publish a calendar with a stale row.

**What happened.** Merck's news release of **September 22, 2026, 6:45 am EDT** says the FDA "has approved an update to the U.S. product label for WINREVAIR (sotatercept-csrk)" adding HYPERION data, and calls it "today's approval". No 8-K (EDGAR full-text search, none), nothing in Drugs@FDA yet for the supplement. So the row is published from the sponsor's release: **Decided / Approved, 2026-09-22, one day after the sourced 09-21 goal date**, with `decision_date_note` saying the FDA letter is not yet in Drugs@FDA and the margin will be corrected if the letter is dated earlier. It enters the timing statistic as **+1 day**; that statistic is now **30: 19 early / 9 on the day / 2 late** on /calendar, /learn/what-is-a-pdufa-date and /research/fda-decision-timing.

Not a new indication: the approved indication is unchanged; the label gains HYPERION efficacy/safety data and hypersensitivity language. The decision page says so.

**Two pipeline defects found while unblocking, both fixed in the workflow and the local chain:**

- **Ordering.** `mark_calendar_decided` reads its decisions from the /decisions listing, and `sync_decisions_listing` (which gives a new decision page its listing row) ran *after* it. A decision page built since the last run therefore could not be marked on the calendar for one full run. The listing sync now also runs immediately before the marker (idempotent; still runs in its original place too).
- **Two CI-only steps the local chain lacked.** `build_slate_from_crawl.py --sweep-only` (otherwise `test_slate_no_decided` fails on any freshly published decision) and `build_stock_runup.py` — without it, 24 ticker hubs that CI had lifted out of noindex (ADCT, AGEN, AIM, AURA, AUTL, CASI, CHRS, CLDX, CLLS, CMND and 14 more; each carries a 3+ row decision-history table) regressed to `noindex` on a local build and dropped out of the sitemap (1,430 → 1,407). Caught by diffing the sitemap against HEAD before committing; both steps are in `_chain_0919.bat` now and the sitemap is HEAD + exactly one URL (`/fda-decision/MRK-2026-09-22`).

Guards 100/100 (three new, below). CI's next scheduled run is the proof; I will check it.

## 2. "1 Days Late" — the first thing an answer engine would have quoted

The MRK decision page shipped `<title>… Approved Sep 22, 2026, 1 Days Late | MRK FDA Decision</title>` and a meta description reading "1 days after its September 21, 2026 PDUFA goal date". Those two strings are exactly what Bing and the AI answer engines lift verbatim. GSK-2026-06-17, SPRO-2026-06-17 and VTRS-2026-07-29 had been carrying "1 Days Early" since June; /pdufa/VTRS-mr-100a-01 and the timing table had "1 days" too.

Fixed at the three owners (`rewrite_decision_snippets`, `mark_event_pages_decided`, `build_early_decisions`) with one helper, and guarded: **`tests/test_no_one_days.py`** — no indexable page may say "1 days" anywhere in its text, title or description. Proven 0 → planted "1 Days Early" on GSK → 1 → healed → 0.

## 3. Open Graph: 168 indexable pages had no og:title at all

94 decision pages (built before the template carried one), 39 /patent-cliff pages, 30 /pdufa event pages, /calendar/2025, one /learn page, /surges. And the pages that *did* have og:title mostly had no og:description or og:site_name. Bing, LinkedIn, Slack, X and the answer engines that unfurl a link all read these; a page without them is shared as a bare URL.

New **`add_og_tags.py`** (in the chain and the workflow, after breadcrumbs): fills og:type / og:site_name / og:url (= canonical) / og:title (= title) / og:description (= description) / twitter:card **only where absent** — the owners of those strings keep them. 3,751 tags on 1,052 pages on the first pass. One real defect surfaced by the guard: /pricing/credits had `og:url` pointing at /pricing while its canonical was /pricing/credits; fixed. Guard **`tests/test_og_tags.py`**: every indexable page has og:title, og:description, and og:url equal to its canonical. The 19 hand-set social titles that intentionally differ from `<title>` (home, /calendar, /decisions, /pricing, research pages) are untouched.

## 4. /llms.txt: the file we point AI assistants at was hand-written and three numbers stale

It said **n=1,792** FDA decisions and a **73.5%** approval rate; the study it describes (one owner since 09-19, `runup_study_stats.json`) is **n=1,852** and **71.3%**. It said 1,756 readouts; the research page says 1,752. It also did not mention /crl, /research/fda-decision-timing, /fda-this-month or /pdufa-date-changes — the four pages with the facts we most want quoted.

New **`build_llms_txt.py`** renders it from the owners: run-up n and approval share from the stats file; readout n and the within-±5% share from the readout page's lede; conference n, the D-30→D-1 median (−0.03%) and the 2020 median (+17.3%) from the conference page; the 19/9/2-of-30 timing split from the timing page; 458 / 309 from the CRL capture series. It now also says in the "please do not" list: do not convert the /crl release ratio into an approval rate. Guard **`tests/test_llms_txt_current.py`**: re-rendering must be a no-op (proven: planted 1,792 → FAIL with the diff → restored → OK).

## 5. The rest of the SEO pass — found, and what I did with each

| finding | count | action |
|---|---|---|
| broken description tails: "… (MIBC)). See the." (/pdufa/BIIB, MRK-keytruda, PFE-keytruda), "…source.." (two readout month pages), "…cancer).." (RHHBY giredestrant) | 6 | `fix_meta_lengths.tidy()`: repairs a doubled full stop, ")(", and a ≤3-word trailing fragment **that ends on a function word**. My first cut of that rule stripped "Facts only." / "Facts, not advice." from 602 pages before I read the diff; retracted the same minute, restored from HEAD, rule narrowed. Idempotent at 0 now. |
| `_index_current_backup.html` deployed at the site root, indexable, canonical → / | 1 | moved to `_site_attic/` (with the two already there) |
| /runup-by-year showed "Last computed 09-21" beside "Updated 09-23" after a local build (CI-only `build_runup_by_year.py`) | 1 | script added to the local chain; `test_one_date_per_page` green |
| `<title>` over 70 characters | 454 indexable pages | **not changed** — see ruling below |
| description over 160 characters | 0 (after HTML-entity unescaping; the raw-length scan had said 20) | nothing to do |
| pages with two `<h1>` or none | 0 (only /ping.html, disallowed) | nothing to do |
| JSON-LD that does not parse | 0 | nothing to do |
| canonical ≠ self | 4, all intended (holding.html → /, pricing.html → /pricing, surges.html → /surges, backup → /) | nothing to do |
| robots.txt | allows every user-agent including AI crawlers; /api/v1/ explicitly allowed; sitemap declared | nothing to do |
| sitemap vs indexable pages | in sync bar the intended exclusions (/changelog, /ticker/SLS and /ticker/VKTX which redirect to their hubs) | nothing to do |

**For a ruling — the 454 long titles.** Decision-page titles are `"{drug} Approved {date}, N Days Early | {TICKER} FDA Decision | pdufa.bio"` (73–90 chars); condition, adcomm and conference pages run similar. Google truncates around 60 characters; Bing shows more; the answer engines read the whole string. The current shape front-loads the drug and outcome, so what gets truncated is the "| TICKER FDA Decision | pdufa.bio" tail, which is the least valuable part. I would leave them, or at most drop the " | pdufa.bio" suffix on decision pages (saves 12 chars). Not doing that without a word, because `fix_meta_lengths` and the snippet guard both know the current shape.

## 6. Also checked

- Forward slate, day-precision, 09-15 → 10-05: LLY, NUVL, RARE, MRK, IONS, BFRI, SRRK all Decided/Approved with pages; INCY + MIRM zilurgisertib 2026-09-26 (a Saturday) Upcoming. Nothing past due.
- Sync-client artefacts: none.
- `_verify_live_0920b.py` still asserts 19/9/1; it will read 19/9/2 after this deploy and I will update it when I live-verify.

## Files
`apply_0923_winrevair.py`, `decision_pages_2026_09_23.json`, `add_og_tags.py`, `build_llms_txt.py`, `tests/test_no_one_days.py`, `tests/test_og_tags.py`, `tests/test_llms_txt_current.py`, `fix_meta_lengths.py` (tidy), `rewrite_decision_snippets.py` / `mark_event_pages_decided.py` / `build_early_decisions.py` (_dw), `tests/test_cross_surface_values.py` (days?), `.github/workflows/pdufa-rebuild.yml` (listing-before-marking; og; llms), `_chain_0919.bat` (slate sweep, stock run-up, runup-by-year, og, llms), `_site_attic/_index_current_backup.html`.
