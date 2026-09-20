# Builder, 09-20: the announcement that was wearing an action date, the id that kept a withdrawn day, and the sync client in the build tree
**2026-09-20, written 14:20 Pacific = 17:20 Eastern = 21:20 UTC (Sunday).** *Per RULE 1 every time here carries its zone. Facts and build mechanics only; not investment advice.*

Reply to the 09-20 audit ("the data is the most accurate it has ever been"). All four claims verified live before anything was touched; items 1–4 of the ORDER are done and guarded; item 5 is David's ruling and I have put my recommendation to him directly; item 6 carries. One thing the audit could not see from outside: an external process is corrupting the build tree on this machine, and it cost most of the afternoon. It is at the end because it matters most for tomorrow.

---

## 1. P0-A, TLX: the auditor is right, and the rule already existed one field over

Confirmed: `/research/fda-decision-timing` rendered "goal September 11, 2026 → September 14, 2026, +3 days" for a date that is Telix's announcement day, and the API returned `decision_date_note: null` because the field was never in `CORE_EXTRA`. Friday goal, Monday announcement — the commonest approval pattern there is — and it sat in the "came after" bucket as one of four.

**One owner now.** `site_windows.earliness_allowed(row)` had one gate (precision); `build_early_decisions.collect()` had grown a second (`goal_unsourced`) that the renderers did not share. That was two owners of "may we measure this margin", and the TLX row slipped between them. The function now carries all three gates — precision, goal provenance (`goal_unsourced`, 09-18), action-date provenance (`decision_date_unsourced`, today) — and `collect()` calls it instead of its own check. Every renderer that already gated on it (event pages, decision snippets, the prose cleaner, the cross-surface guard) inherited the rule without a line changed.

What that produced, live-verified at the end of this note:
- Timing statistic **30 → 29: 19 early / 7 on the day / 3 late**, restated on `/calendar`, `/learn/what-is-a-pdufa-date` and the study page. Median unchanged.
- The study page now names what it leaves out and why, in a section the reader sees: *"4 2026 decisions with a sourced outcome are not counted above: LLY, MRK, OTSKY (no sponsor filing states a goal date); TLX (the date held is the sponsor's announcement day; the filing does not state the day the FDA acted)."* The 09-18 exclusions had been silent; now they are on the page next to the number.
- `/fda-decision/TLX-2026-09-14`: title **"Pixclara Approval Announced Sep 14, 2026"**, not "Approved Sep 14, 2026, 3 Days Late"; meta and FAQ say the sponsor announced and the action day is not stated; the "+3 days" sentence in the body is gone (the cleaner now strips margins in BOTH directions — the 09-14 version only knew "early", which is how "3 Days Late" got through a guard built for exactly this).
- `/pdufa/TLX`: "Approval announced September 14, 2026" in title, key fact and FAQ; the **goal date of September 11 stays**, because it is sourced — only the margin and the "approved on" tense changed. (The first version of the fix withdrew the goal-date facts too, treating "no margin" as "no goal"; caught on the rendered page, fixed by splitting the two cases.)
- `/fda-this-month`: "As announced by the sponsor on September 14 (the filing does not state the day the agency acted), the FDA approved Pixclara".
- API `CORE_EXTRA` +5: `decision_source`, `decision_source_url`, `decision_date_note`, `decision_date_unsourced`, `goal_unsourced`. Documented on `/developers`. The row's note now says no margin is published until the FDA letter or Drugs@FDA supplies the action date.
- Guard: `test_cross_surface_values` earliness check widened to early **and** late, and it now asserts the study page lists no gated row.

**Found underneath it, live for six days:** `/pdufa/TLX` carried a hand-verified "Goal date passed · no decision has been disclosed as of September 20, 2026" banner directly above "FDA decision: Approved September 14". `mark_goal_date_passed.py`'s docstring said the ledger entry "is removed when a decision is published" and nothing ever removed it. It now retires any entry whose dataset row is Decided — banner stripped, pending-tense phrases restored, entry dropped — every run.

## 2. P0-B: the date came from `d`, not the id — same defect, one field over

Confirmed live: "Ahead of its September 30 goal date, on August 5, the FDA approved Oveporexton (TAK)" and the other three. The mechanism is slightly different from the audit's read and worth recording: the dataset keeps a coarse row's `d` as the **end of its window** (`2026-09-30`, `dp: quarter`) and only the API nulls `date` for non-day precision. `build_monthly_decisions.ev_sentence()` read `d` as a goal day and never looked at `dp`. Same shape as the audit described — a withdrawn day surviving in a field a renderer picks up — just a different field.

Fixed: the sentence builder imports `site_windows` (the one owner of window labels) and a coarse row reads *"On August 5, within the window the sponsor had given (the third quarter of 2026; no goal day was published), the FDA approved …"*. No earliness is ever stated against a window. New guard `tests/test_no_goal_day_from_coarse_row.py`: for every coarse-precision row, no indexable page may print "<window-end day> goal date" next to that ticker or drug. Proven against the live defect: the committed page → **5 FAIL** (TAK, PFE, ROIV, PTGX, BAYRY) → rebuilt → 0.

## 3. P0-C: the countdown is computed when you ask, not when we built

Confirmed: `next_days: 2` at 16:52 Eastern for a date one day away. The homepage already hydrated its own countdown at view time from `next_date`; the file itself was the stale surface, and it is the file consumers read.

`/build-info.json` is now a serverless function (`api/build-info.mjs`, rewritten from `/build-info.json`). It reads the build's static output (`api/_build-info.json`) and recomputes `next_days`, `days_since_goal` and `next_status` from the **Eastern calendar date of the request**; `as_of_eastern` and `served_at` say which date the count is true for. Edge cache is capped at 10 minutes and expires at Eastern midnight. The static copy stays in the tree for the guards and is excluded from the deploy. Tested locally under Node 24 (`next_days: 1` at 13:56 Pacific); the acceptance test — fetch more than 24 hours after a build and read the right number — is tomorrow's verifier run.

## 4. Two dates, two decisions, three rows

Confirmed: lede and meta said "3 FDA decision dates remain in September". Cause: `merge_partners()` stripped the parenthesis **before** splitting on it, so "Zilurgisertib (licensed to Mirum; MIRM holds the NDA)" and "zilurgisertib" never merged. Split first, then normalise. The lede and meta now count distinct dates and, when they differ, distinct decisions: "2 FDA decision dates remain in September 2026, with 13 already decided."

## 5. Item 5 — my recommendation, put to David

The auditor's recommendation is to withdraw the day and the forward listing for ABBV tavapadon, AZN Ultomiris, BAYRY Kerendia, NVO CagriSema and NVO Mim8, keeping the drug pages. I have asked David for the ruling in this session and will apply whichever way it goes; the ratchet holds at 9 until then.

## 6. Also today, time-triggered: ABEO

`/pdufa/ABEO` is the partner-ticker page for FAYUVI (Abeona / Ultragenyx). The decision is filed under RARE, so the automatic banner never found it, and on the morning of September 20 — the day after the goal date — the guard `test_no_past_target_pending_pages` began failing: "target 2026-09-19 has passed and the page still says a drug is under FDA review". Tonight's autonomous run would have been the fourth blocked morning in a week. Hand-linked (`ABEO → RARE-2026-09-17`), the same shape as RPRX → NUVL on 09-19. The page now says "Approved 2026-09-17, 2 days before its September 19, 2026 goal date."

## 7. The thing the audit could not see: a sync client is writing into the build tree

At **14:01:03 Pacific** today, during a rebuild, **260 `index (1).html` copies** appeared under `pdufa_site_src` and **133 tracked pages were deleted** — their directories left empty: `/learn/what-is-a-pdufa-date`, `/pdufa/NVO-am833`, 25 decision pages, 14 drug pages, `/calendar/2025`. The chain then failed in three places and the timing statistic collapsed to 13 of 30 before I noticed. Yesterday it was 11 copies at 13:54. Three ` (1)` copies of my own source files (the workflow, the nav-freeze file, `fix_dead_internal_links.py`) also appeared in the repo root — an existing guard caught those. `GoogleDriveFS` is running against this machine; ` (1)` is a sync client's duplicate naming.

Restored every page from git, removed every copy, and added `tests/test_no_sync_artefacts.py`: the build refuses to publish a tree containing ` (N)` duplicates or an empty page directory. It also flushed five empty directories left by retired pages (ACHV/ARQT/LNTH/UNCY goal-keyed decision dirs, `TAK-rusfertide`). But a guard is a tripwire, not a cure. **David: if Google Drive is backing up `Documents\Python\9realms`, please exclude it.** Until then every rebuild on this machine is a coin toss, and CI (which runs on a clean checkout) is the only build I fully trust.

---

*Live verification of this push follows in the commit and in `_verify_live_0920.py`. Timezones per RULE 1 throughout. Not investment advice.*
