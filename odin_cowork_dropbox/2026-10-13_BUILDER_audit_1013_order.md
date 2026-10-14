# Builder note: the 10-13 audit (UTC "today", submission order, lastmod churn, VTRS/IRD), actioned
**2026-10-13, work 20:00 to 21:30 Pacific = 23:00 to 00:30 Eastern (Tuesday night into Wednesday).** *RULE 1.*
*Facts and build mechanics only. Not investment advice.*

## 1. The audit, checked

| Claim | Verdict |
|---|---|
| `/fda-decisions-today` stamps "today" from the UTC clock | **True.** Re-read at 22:59 Eastern on Oct 13: "published today, October 14, 2026"; build-info `as_of_eastern` 2026-10-13. `build_today_page.py` line 91 was `dt.date.today()`. |
| The other nine surfaces are clean for "October 14" | Agreed; but two more builders used the runner's clock for countdowns and a 60-day window (`build_home_board.py` TODAY, `build_fda_letters_hub.py`), which would read one day off in the same four-hour window. Fixed with the page. |
| Submission is ~1,300 unordered URLs, Bing gets the first 80 | **True.** `changed_urls()` sorted by lastmod then depth; on 10-13 it was 1,022 URLs with the hubs scattered. |
| No-op rewrites move lastmod | **True, and the mechanism is now known** (section 3). |
| VTRS MR-141 row links the IRD page while `/pdufa/VTRS-mr-141` exists | **True.** `sync_event_urls.py` merged partner rows onto one page for the API as well as the calendar. |
| `end_date` retraction | Noted, thank you. |

## 2. Order 1: "today" is Eastern everywhere

`build_today_page.py`, `build_home_board.py`, `build_fda_letters_hub.py` now take `site_dates.eastern_today()`. New guard `tests/test_today_is_eastern.py` reads the rendered daily pages (`/fda-decisions-today`, `/fda-this-month`, `/fda-approval-decisions-this-week`, `/`, `/calendar`) and fails when any "today, {date}" / "as of {date}" differs from the Eastern build date. 0 → planted 1 (tomorrow's date on the today page) → 0. Rendered tonight: "published today, October 13, 2026".

## 3. Order 3: why unchanged pages kept advancing their lastmod

`build_sitemap.content_hash()` strips the modified-time stamps before hashing so that stamping cannot move the date. The strip for the JSON-LD key was `"dateModified":"...",?`: it dropped the trailing comma but not the **preceding** one, and the key is almost always the last in its node, so a stamped page hashed as `...},}` while the same page before stamping hashed as `...}}`. Whether a page was hashed with or without its stamp depended on whether that run had regenerated it, so the hash flip-flopped and ~1,000 pages advanced on 10-11. Fixed (preceding comma stripped; `og:updated_time` / `article:modified_time` metas stripped too); the hash is now provably invariant to stamping (`tests/test_search_submission_order.py` asserts it, and fails on the old regex). `_sitemap_lastmod.json` was re-keyed for 37 pages whose stored hash was the pre-stamp form, dates untouched. `build_sitemap.py` now prints "lastmod == today on N of M URLs" every run so a runaway is visible in the CI log the night it happens.

**A second churn source, found while proving this, is environmental and is NOT fixed:** a local chain run renders some blocks differently from CI (no Polygon key locally, so run-up and reaction blocks differ), so a local build that writes `_sitemap_lastmod.json` re-dates those pages and CI re-dates them back. The first local chain tonight moved 1,072 of 1,468 URLs for that reason. Rule for me: a local chain must not be the one that writes the lastmod state; tonight's commit carries CI's state file re-keyed, not the local chain's. A proper fix is `build_sitemap.py --no-state` for local runs; carried.

## 4. Order 2: submission order

`ping_search_engines.py`: `prioritise()` puts the nine daily hubs first (`/`, `/fda-decisions-today`, `/fda-approval-decisions-this-week`, `/fda-this-month`, `/calendar`, `/decisions`, `/readouts`, `/fda-approval-letters`, `/conferences`), then the pages of the most recently updated dataset rows (PDUFA rows first, then AdComm, Readout, Conference; newest `ua` first), then the rest. The Bing SubmitUrlBatch takes the first 80 of that order; IndexNow takes all of it. The first 20 are printed every run ("submission order, first 20"). Dry run tonight: the nine hubs, then `/pdufa/MRK-ifinatamab-deruxtecan` and the tickers whose rows moved most recently. Guard in `tests/test_search_submission_order.py`.

## 5. Order 5: VTRS / IRD

One page each. `sync_event_urls.py` keeps the partner merge for the shared **calendar** row only; each API row links its own page when one exists. `pdufa_vtrs_2026-10-17` → `/pdufa/VTRS-mr-141`. The guard `test_event_page_titles_carry_date` now also requires the linked page's title or h1 to name the row's ticker; proved 0 → planted 1 (VTRS back on the IRD page) → 0.

## 6. Order 4: Thursday runbook (Enspryng, goal 2026-10-15)

1. The workflow has an hourly cron 13:00 to 23:00 UTC on Oct 15 (09:00 to 19:00 Eastern). Watchers: FDA press RSS, CDER News & Events, gene.com JSON-LD listing, openFDA.
2. The moment the FDA record or the Genentech release is seen: `gh workflow run pdufa-rebuild.yml --ref main` (do not wait for the cron; GitHub queues 1.5 to 5 h late).
3. The lead lands in quarantine (`held_leads`) and a GitHub issue; the decision page is published from the FDA record (action date, application, letter where released), never from a headline alone; `/fda-decisions-today` then reads "published today, October 15" because order 1 is in.
4. After the deploy: David opens Bing Webmaster → URL Inspection → "Request indexing" for `/fda-decision/RHHBY-2026-10-15` (the slug the publisher prints) and `/fda-decisions-today`. The prioritised batch (order 2) submits both automatically in the same run, but the console request is the only path that beats the queue.
5. Target: decision page live within 60 minutes of the record. Not promised: the record's own timing.

## 7. Order 6, the 131 registry-estimate rows
Recommendation agreed: do not publish them as calendar rows; they stay in the red-teamed file as a watch list that the already-read-out pass (`resolve_past_readouts.py`) and the registry re-sync can consume. David's ruling stands open.

## Carried
`goal_date_held`; Jaypirca SUPPL-5 date; RXC-005 aliases; SMTP; Drive exclusion; AZN Ultomiris / NVO CagriSema / NVO Mim8 sources; the 20 nct-mismatch readout rows; Bing Webmaster key in `.env`; `build_sitemap.py --no-state` for local runs.
