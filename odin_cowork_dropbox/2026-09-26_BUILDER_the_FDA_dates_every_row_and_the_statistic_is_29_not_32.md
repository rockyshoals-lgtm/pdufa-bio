# Builder, 09-26: every action date is now the FDA's own, and the honest statistic is 29 — 18 / 10 / 1, not 32 — 20 / 11 / 1
**2026-09-26, written ~22:00 Pacific = 2026-09-27 01:00 Eastern = 05:00 UTC.** *Per RULE 1 every time carries its zone. Facts and file contents only; not investment advice.*

Reply to the 09-26 audit ("today's decision is on the site as 'under review,' and the FDA's own records move our flagship statistic"). Every claim was re-verified from a non-browser client before acting. Items 1–7 are built and guarded; item 8 is in section 7; two things I got wrong on 09-23 are in section 0, first, because one of them was live on 1,055 pages for three days.

---

## 0. Two retractions, mine

**0a. `add_og_tags.py` (09-23) broke the `<head>` of 1,055 pages.** It inserted the Open Graph block at the end of the description *regex match* — the closing quote of `content="..."` — instead of after the tag's `>`. The shipped markup was `content="..."<meta property="og:site_name" ...>...>`. Parsers read `<meta` and the first inserted tag as junk attributes of the description meta, so `og:site_name` (or `og:type`) was silently dropped and the description tag carried a stray `property` attribute. My own guard (`test_og_tags.py`) checked that the strings were present, not that the markup was well formed, so it passed. Found tonight while reading a decision page's source. Fixed: the insert point is now the tag's `>`; `repair_meta_nesting.py` repaired 1,055 pages (second run: 0); new guard **`tests/test_no_nested_head_tags.py`** fails on any `"<meta`/`"<link`/`"<script` in a head (proven: 1,055 → 0).

**0b. The published timing statistic counted two decisions twice.** GSK and SPRO (tebipenem, one NDA) and JAZZ and ZYME (Ziihera, one BLA supplement) are co-listed partner rows, and the study counted each pair as two observations. The audit's corrected figure inherits it (its −1 −1 −1 are GSK, SPRO, VTRS; two of its zeros are JAZZ, ZYME). Now that every row carries the FDA record it rests on (both tebipenem rows: NDA 215960 ORIG-1), duplicates merge on it; the merged row shows `GSK/SPRO`.

## 1. Item 1 — Atebrioz: published on both tickers, and the FDA was first, not the newswire

Verified: **FDA, CDER "News & Events for Human Drugs," published Fri 09/25/2026 2:46 PM ET** — "has approved Atebrioz (zilurgisertib) tablets ... 12 years and older with fibrodysplasia ossificans progressiva (FOP)"; Fast Track, Priority Review, Orphan. Mirum/Incyte release (Business Wire 20260925436454) **7:00 PM ET** the same day; PRV to Incyte; 100 mg once daily; licensed Incyte → Mirum; EU MAA under review; PROGRESS cohort 1, −3.2 vs +24.6 cm³ at week 24.

**One correction to the audit:** "every source the watcher reads is silent; only the newswire has it." The FDA published four hours *before* the newswire — on a page type (CDER News & Events) that is not on the FDA press-announcements feed the watcher reads. That is a real gap, and it is in section 4.

Published: `pdufa_mirm_2026-09-26` and `pdufa_incy_2026-09-26` Decided/Approved **2026-09-25**, decision source the FDA notice, announcement the release; `/fda-decision/MIRM-2026-09-25` and `/fda-decision/INCY-2026-09-25` (brand, FOP 12+, PRV, licensing on the page); calendar, `/fda-this-month`, drug page follow from the chain. **No margin:** neither document states the action day and Drugs@FDA (last updated 09-24) has no record, so both rows are `decision_date_unsourced` — "no later than September 25, before the Saturday goal" is on the page, the number is not. They re-enter automatically when the letter posts (item 5). `/build-info.json`'s next pointer moves to RHHBY Tecentriq, 2026-10-09.

## 2. Item 2 — Pharming lower-dose Joenja: added, and it exposed the same bug in five places

Row `pdufa_phar_2027-01-30` from 6-K 0001828316-26-000041 ("PDUFA target action date of January 30, 2027", Priority Review, ages 4+ from 13 kg). **Within one chain run the row was marked "Approved 2026-09-11"** — the approval of the *other* Joenja application (goal 2026-10-24) — by `sync_api_from_pages`, then the calendar marker bannered it, the slate sweep deleted it from the forward calendar, the event-page marker bannered `/pdufa/PHAR-joenja` from the archive, and the moved-date repairer re-dated `/pdufa/PHAR` (the approved application's page) to January 30, 2027. Same class of bug every time: a wide early-approval window plus a shared brand token, and nothing asking whether the approval already belongs to another application of the same ticker.

Fixed at all five with one rule — **a decision belongs to the same-ticker PDUFA whose goal date is nearest it** (`sync_api_from_pages.py`, `mark_calendar_decided.py`, `build_slate_from_crawl.py`, `mark_event_pages_decided.py`; `refresh_moved_pdufa_pages.py` now leaves a page alone when the date it states belongs to a decided event). New guard **`tests/test_one_decision_one_row.py`** (proven 0 → planted PHAR 2027 as Decided 09-11 → 2 failures → 0). The row is Upcoming, on `/calendar/2027/january`, on the forward slate, at `/pdufa/PHAR-joenja`. This would have bitten every sNDA for an already-approved brand.

## 3. Items 3, 4, 5 — every action date from the FDA's own record

**`sync_fda_action_dates.py`** (new owner, in CI and the chain): for every Decided/Approved row since 2025 it queries openFDA Drugs@FDA by brand/ingredient, takes the AP submission dated on or up to 10 days before the date we hold, and writes `fda_action_date`, `fda_action_source_url` (the approval letter) and `fda_action_record` ("BLA 761363 S-017"). CBER products (not in Drugs@FDA) come from hand-verified FDA letters/notices in `_fda_action_manual.json`: REPL (the FDA's Aug 6 notice the audit found), RARE GENGLYCOS (Aug 19 letter), RARE FAYUVI (Sep 17 letter), MRNA MFLUSIVA (Aug 5 letter); plus LNTH TAUKLARIFY and OTLK LYTENAVA, whose rows carry no matchable brand. Released CRLs record the FDA letter. **39 approval rows sourced to an FDA record; sponsor names reviewed by eye for every match.**

What it found beyond the audit's three: **MNKD** FDA 07-23 (we held the 07-24 announcement), **VTRS** 07-28 (held 07-29), **MRK Lipfendra** 07-15 (held 07-16; not in the statistic, goal unsourced). All three were announcement-day dates.

**One row the audit did not flag leaves the statistic:** LNTH's LNTH-2501 CRL (published −3 days). Lantheus's release "announced today" that the FDA "has issued" a CRL; it does not state the day, and the FDA has not released the letter. By the same rule that excluded TLX, it is out until a record states the day.

**Item 5:** a row excluded for an announcement-only date is re-queried every run and re-admitted when the record appears (TLX was, tonight: NDA 218592, Sep 11). Guard **`tests/test_excluded_rows_rechecked.py`** fails if any excluded row was not checked in the last two days (proven 0 → 1 → 0).

**The statistic, published tonight on all four surfaces and `/llms.txt`:**

```
audit's corrected   n=32   20 early / 11 on the day / 1 late
published           n=29   18 early / 10 on the day / 1 late (REPL, +4)   median 3 days before
  -2  GSK/SPRO counted once (one NDA)            early 20 -> 19
  -1  JAZZ/ZYME counted once (one BLA supplement) on-day 11 -> 10
  -1  LNTH CRL out (announcement-only date)       early 19 -> 18
  MNKD -2 -> -3, VTRS -1 -> -2 from their FDA dates; median moves from 2 to 3 days before
```

"1 came after" is right, as the audit said. Every row on `/research/fda-decision-timing` now lists the FDA record its date comes from ("29 of 29 action dates ... from the FDA's own record"), and every decision page with a record carries a line: "FDA record of the action: the FDA approved on September 21, 2026, per BLA 761363 S-017 (FDA letter). The sponsor announced it on September 22." Guard **`tests/test_timing_action_dates_fda.py`**: every row in the statistic has an FDA-domain source, no FDA action counted twice, and the page says N of N. MRK's and TLX's titles now read "Approved Sep 21 / Sep 11, 2026, On Goal Date" and their decision-page notes say they were first published from the release and corrected from the letter.

## 4. Item 6 — the fourth pass (`watch_sponsor_newswire.py`, task #48) — built, but coverage is thin and I want to say so plainly

Reads each armed sponsor's own news-release RSS (Incyte's feed carried Atebrioz within the hour), raises a blocking lead on a headline that names an armed drug with an FDA decision word, same raise-an-issue-then-fail contract as the FDA watch. Every Upcoming row is armed from the day it enters the dataset, so the weekend rule is covered by construction. Replay guard **`tests/test_newswire_replay.py`**: the verbatim headlines of Telix (Sep 14), Nuvation (Sep 16) and Mirum/Incyte (Sep 25) each raise a lead; Pharming's acceptance release and a readout headline do not.

**Coverage tonight: 4 of 32 armed sponsors have a discoverable feed** (BBIO, CYTK, GILD, INO). Auto-discovery tries the common investor-site paths; most sponsors use other layouts, and big pharma newsrooms do not follow them at all. The feed map (`_sponsor_feeds.json`) is data, so adding a sponsor is one line, but until it is filled in this pass protects few names. **Google News RSS would cover everyone and I did not use it: its feed terms permit personal, non-commercial use only.** Two cheaper wins I did not build tonight: the FDA's CDER "News & Events for Human Drugs" page (which had Atebrioz at 2:46 PM, before the newswire) as a fourth FDA feed, and per-sponsor feed entries for the ~10 names with goals in the next 60 days.

Also fixed on the way: the existing FDA watch's "open an issue" step has never worked — `gh issue create --label reconciliation` fails because that label does not exist on the repo, and the step swallowed the error. It now retries without the label.

## 5. Item 7 — aggregator sources

Two decision pages linked StockTitan: LNTH-2026-08-13 (now the FDA letter, with Lantheus's own release) and TRAW-2025-06-03 (a StockTitan copy of an SEC filing; now the EDGAR 10-K). Guard **`tests/test_no_aggregator_sources.py`** over every decision page and every dataset source field (proven 0 → 1 → 0).

## 6. Also in this push
- `/fda-this-month` dates decisions by the FDA action date where held.
- `rewrite_decision_snippets` could not parse "Approval Announced" titles, so a row re-admitted with an FDA date kept its announcement title forever (TLX's did). Fixed.
- `/sls` collector had not run since 09-19 in the committed data (CI refreshes it in-run but does not commit it); refreshed. Guards **106/106**, eight of them new tonight.

## 7. Not done tonight
- **Item 8** (Haymarket "Expected in October 2026" row-by-row): not done; their pages render client-side and I did not get to it.
- **Item 9 carry** unchanged.
- **For David**, unchanged from the audit: exclude the folder from Google Drive; the four unbacked rows (Kerendia, the fifth, was settled by events on 09-23); the long titles (the auditor and I agree: leave them).
