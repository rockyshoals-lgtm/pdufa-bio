# Builder note: the Sunday freeze (cause, fix, and why it will never be silent again); audit 10-18 orders
**2026-10-18, work 15:30 Pacific onward = 18:30 Eastern = 22:30 UTC (Sunday).** *RULE 1.*
*Facts only. Not investment advice.* Responds to the audit of 2026-10-18 (measured 17:17 to 17:45 Eastern).

## 0. The freeze: what blocked both Sunday runs
**Guard:** `test_no_past_target_pending_pages`, on runs 39132717124 (13:42 UTC) and 39140611287 (15:28 UTC). Its message:
- `/pdufa/IRD`: target 2026-10-17 has passed and the page still says "is under FDA review"
- `/pdufa/VTRS-mr-141`: same

**Why.** Those are two older twin pages for the RYZUMVI presbyopia event, from before the partner page `/pdufa/IRD-phentolamine-ophthalmic` existed. No page links to them (only the sitemap did), neither was in the duplicate map, and `mark_event_pages_decided.py` never visited them. The guard only fires once the goal date has passed in Eastern time, which was Saturday night; the Saturday evening build predates that, so the first failing run was Sunday's 13:42 UTC.

**Fix.** Both are added to the duplicate map in `canonicalise_duplicate_event_pages.py`: canonical to the partner page, `noindex,follow`, out of the sitemap. And a twin must never contradict its primary: the canonicaliser now copies the primary's decision banner into the twin, rewrites "is under FDA review", and retitles it ("IRD FDA decision: MR-141, Approved October 16, 2026"). Both guards pass.

**Why nobody was told, and the fix for that.**
- The guard step ran `set -e` over the tests: first failure, job red, nothing else. The only record was a job log that needs admin rights to read.
- New `run_ci_guards.py` runs **every** guard (a second failure is no longer hidden behind the first) and, on failure, writes `_blocked.md`: the failing tests, each one's output, the run URL.
- New `blocked_issue.py`, in a `failure()` step, turns that into **one** open issue titled "BLOCKED: pdufa.bio rebuild failed {tests}". A later blocked run updates the same issue and comments with the new run, never a second issue (the 10-15 escalation lesson). The next green run closes it (`--resolve`, in the passing path before the commit step).
- Guard `test_blocked_run_reports.py`: checks the workflow wiring (runner, failure step, resolve), then replays a temp tree with one passing and one planted failing guard and requires `_blocked.md` to name the failing test, quote its output and name the run, and `blocked_issue.py --dry-run` to compose the BLOCKED title. Planted removal of the issue step fails.
- `_blocked.md` / `_blocked.json` are gitignored.

**Runner pinned** to `ubuntu-24.04` (GitHub migrates `ubuntu-latest` to Ubuntu 26 from 10-19). Moving later is a deliberate, dispatched change.

**David:** VERCEL_TOKEN still does not authenticate, so the post-push CDN purge is not running. Re-create it at vercel.com/account/tokens and update the secret.

## 1. Three dates, three sources, one line (order 1)
New `inject_verified_against.py` (CI and chain, after `inject_fda_action_record.py`) places one line under the fact-first lede of every decided row's decision page, 53 tonight:

> Verified against: FDA action day October 14, 2026 (FDA approval notification) · Announcement October 14, 2026 (ImmunityBio 8-K exhibit 99.1) · Goal date January 6, 2027 (ImmunityBio, Inc. 8-K).

It states only what the row holds: "FDA action day not yet posted on Drugs@FDA" for Enspryng, RYZUMVI and LNTH; "Goal date none sourced" where the goal is unsourced or a window; and "Goal date {day} (source not recorded on this row)" for **16 decided rows that carry a day-precision goal with no `source` field** (ACHV, BMY-08-17, CELC, CORT-03-25, GSK/SPRO-06-18, IONS-09, LNTH-06-29, MNKD, NUVL, OTLK, RARE, REGN, REPL, UNCY, VTRS-07-30). Those 16 are a visible backlog now, not an implied source.

**Enspryng's line names both datelines**: Genentech (South San Francisco) October 15 and Roche (Basel) October 16, the latter read tonight from roche.com/media/releases/med-cor-2026-10-16. The row records it as `announcement_2`, and the decision page's note says in a sentence why both dates circulate. Guard `test_verified_against_line.py` (planted "FDA action day October 15, 2026" on Enspryng fails).

## 2. /corrections (order 2)
A hand-written `/corrections` page already existed (14 entries, July to September, including rejected bug reports); the audit read it as absent. It is now rendered from `_corrections.json` by `build_corrections_page.py` (CI and chain): 18 dated, sourced entries from the 10-15 to 10-18 passes above the 14 legacy entries, 32 in all, each with page, was, now and source. Title "Corrections: 32 published facts fixed, dated and sourced". Footer already linked it; it is in the sitemap. Guard `test_corrections_page.py` (planted entry fails).

**Found while building it:** the six decision slugs retired on 10-15 redirected to `/drug/canalevia-ca1`, `/drug/miplyffa` and `/drug/papzimeos`, drug pages that no longer exist (they dropped with the false rows), so the redirects landed on 404s. They now go to the ticker hubs. Logged as a correction.

## 7 and 8. PBYI/VYGR; goal_date_held
- `enrich_ticker_hubs.py`: a hub with at least one row carrying a `source_url` is not thin. And the reverse case was never written: a hub that became substantive stayed noindex for good. Both fixed; the step prints how many it re-indexed.
- `goal_date_held` on every PDUFA row in the API, derived at request time: true for a day-precision sponsor-disclosed goal, false for action-only, unsourced or window rows, null on readouts and conferences. Documented on `/developers`. `type` stays "PDUFA".

## Local guards before push
149 pass; `test_one_date_per_page` (the `--no-state` stamp) and `test_sls_activity` (local data age) are the known local-only failures. The runner's own `_blocked.md` was what I read to get here, which is the point of it.
