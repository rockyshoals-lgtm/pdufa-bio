# Builder note, afternoon, 2026-09-07: what the 08:20 slot did, the Vercel deployment list, /api/data, CI timing
*Written 15:40 Pacific (18:40 Eastern) by the builder, off-cadence, at David's request to verify today's scheduled runs end to end. Facts and build mechanics only; not investment advice. Machine clock Pacific; GitHub and Vercel timestamps UTC; every timestamp below names its zone.*

## 1. The 08:20 slot fired. It died mid-run.
The scheduler shows `builder-0820` last ran at 15:20:49Z (08:20:49 PT). Its session transcript exists (session `local_3e50a96c`). It read the 08:00 audit, edited `_lib.mjs` (C1), edited `build_freshness_stamp.py` (C2), read `mark_goal_date_passed.py` and began the NRXP research (C3): an EDGAR fetch, a Perplexity search, then a `secFilings` connector call. That call is the last entry. No result, no final message, no ack, no commit. The session was terminated in the middle of that tool call, before it had written anything to the dropbox.

So "08:20 slot silent again" is half right: no file, but not "did not fire". And for the record, yesterday's 08:20 slot did file: `2026-09-06_BUILDER_ACK_0820.md` was committed in cf96839d8 at 08:56:32 PT on 09-06; the 09-06 0840 note (filed ~08:55) checked just before it landed. Today is the first no-file day, and the cause is the run dying with everything still in the working tree.

Fix, deployed this afternoon (before 15:30 PT) into BOTH builder task prompts (`builder-0820`, `builder-0900`; the two bodies are byte-identical, a copy is in this folder as `BUILDER_PROMPT_as_deployed_2026-09-07.md`):
- **STEP 0, stub first**: the first tool call writes `RUN STARTED <HH:MM> Pacific ...` into the ack file, prepends the INDEX line, commits and pushes that stub before any work.
- **Commit and push after every item**, not at the end.
- **25 minutes per slot, maximum 5 ORDER items**; a research call that hangs twice is deferred in writing, not retried.
- **No push while a CI run is in progress** (`gh run list --workflow 320578931 --limit 1`), then rebase and push.
- Rule 12 now says to fetch each graded page twice, 60 s apart, and compare body md5 to the ETag before claiming it.
Acceptance for you tomorrow: `2026-09-07`-style stub present within two minutes of 08:20 PT and 09:00 PT, even if the run later dies.

## 2. Vercel production deployment list (project `pdufa-bio-staging`, target production, all READY; times UTC)
| created | commit | source |
|---|---|---|
| 03:49:44Z | d515530a1 SLS page + calendar+check favicon | builder push (evening) |
| 03:55:41Z | a42ec7940 Odin's-eye favicon | builder push (evening) |
| *(nothing for 12 h 23 min)* | | |
| 16:19:06Z | 59ba8f997 (one push carrying c3eec4e82 + the stamp; one deployment) | 09:00 slot |
| 16:23:20Z | 364aa861b CI: install pillow | 09:00 slot |
| 16:26:30Z | 701779168 chore: daily data refresh | CI run 34143020141 (dispatch) |
| 17:25:46Z | 5b44394b9 chore: daily data refresh | CI run 34147301074 (schedule) |

Two consequences:
- **In 16:15 to 16:35Z there were three production promotions, not four** (c3eec4e82 never got its own deployment; it shipped inside 59ba8f997's push). Your body #1 at 16:30:02Z arrived about 3.5 minutes after the 16:26:30Z deployment was created, i.e. right at its promotion.
- **At 15:01Z there had been no deployment for 11 hours.** The 87/49/38 body the 08:00 audit saw cannot be a promotion race. Whatever served it, it was not caused by overlapping deploys.

## 3. Whose bodies were they (git forensics on `pdufa_site_src/calendar/index.html`)
- Body #1 (16:30:02Z MISS; `og:updated_time 2026-09-06T00:21:37+00:00`, "updated September 5", 87/49/38) is byte-for-byte the calendar committed in **24d0cff60** (2026-09-05 17:23 PT, "Regenerate surfaces on CI base after rebase (audit 09-05c batch)"). That deployment was ~40 hours old at the time.
- Body #2 (16:32:25Z HIT; `og:updated_time 2026-09-07T01:50:15+00:00`) is the calendar in **a42ec7940 / c084bca05** (the 03:55Z favicon deployment and the 04:xx CI refresh on it), **not** c3eec4e82's, whose calendar carries `2026-09-07T12:14:51-04:00`. Correction to your P0 text: the second body was one deployment older than you recorded.
- Body #3 (from 16:32:51Z, md5 == etag) is 701779168's, the correct one.

So across a two-minute window one edge node handed out bodies from two superseded deployments under the newest deployment's ETag and content-length. That is Vercel's CDN, not our build; the same 24d0cff60 body at 15:01Z, with no deploy anywhere near, says it can also happen outside promotions. I do not have edge logs to go further. The post-deploy verifier you asked for is the right instrument and is queued as the first item of tomorrow's 08:20 slot (acceptance: script name + one real run's output in the ack); the dispatch task in section 5 also means fewer same-hour promotions.

## 4. /api/data: intent stated, then aligned, guarded
Both readings were true. `api/data.js` line 69 set `s-maxage=16000, stale-while-revalidate=86400` (the ack read the source); Vercel rewrites the client-facing `Cache-Control` of a function response to a bare `public` while the edge still honours the original (your HEAD read the wire). `vercel.json` carried a second writer of the same header for `/api/data`.
Intent: one policy for every feed. Done in this note's commit: `data.js` now sets `public, max-age=0, s-maxage=300, stale-while-revalidate=300, stale-if-error=3600` on `Cache-Control`, `CDN-Cache-Control` and `Vercel-CDN-Cache-Control` (pro sessions stay `private, no-store`); the `vercel.json` Cache-Control entry for `/api/data` is removed (X-Robots-Tag noindex stays). `tests/test_api_cache_policy.py` now also reads `api/data.js` and every `vercel.json` header rule on an `/api/` path. Proved 0 → planted `s-maxage=16000` back into data.js → 1 (two directives flagged) → healed 0. Acceptance: `curl -sI /api/data` shows `cdn-cache-control: public, max-age=0, s-maxage=300, stale-while-revalidate=300, stale-if-error=3600`.

## 5. CI on the fixed workflow, and why the morning build is late
- Your P1 #3 is already answered: run **34147301074**, event `schedule`, created 17:22:00Z, success; live `/build-info.json` `built 2026-09-07T17:24:26+00:00`, `commit 7017791`; Vercel deployment 5b44394b9 at 17:25:46Z. CI deploys.
- The workflow's crons are 12:00Z and 21:00Z. Actual scheduled starts this week: 15:51Z / 22:39Z (09-04), 14:42Z / 22:30Z (09-05), 15:01Z / 22:35Z (09-06), 17:22Z (09-07). GitHub runs them 1.5 to 5.4 hours late, so the "05:00 PT" refresh has been landing at 07:42 to 10:22 PT, on the wrong side of your 08:00 run, and the "14:00 PT" one at ~15:30 PT. Expect tonight's `built` around 22:30 to 23:00Z, not 21:0xZ (at 22:36Z, when this note was finished, the 21:00Z run had not yet started).
- Fix: a new local scheduled task `pdufa-ci-dispatch-0715` (07:15 PT daily) dispatches the workflow if no run is live, so a same-day build is live by ~07:30 PT. Acceptance tomorrow at 08:00: `built` reads ≈14:2xZ Sept 8 with a `workflow_dispatch` run in `gh run list`.
- SHA length: `build_freshness_stamp.py` now uses `git rev-parse --short=9` (bare `--short` gave 7 on CI's shallow clone, 9 locally). From the next CI stamp, always 9.

## 6. Housekeeping in this commit
The 09:00 slot committed its site work but not its ack: `2026-09-07_BUILDER_ACK_0900.md` and the INDEX line existed only on disk (the very failure mode STEP 0 now prevents). Committed here, with today's three auditor files and their root mirrors. `_builder_*.log` scratch files are now git-ignored.

## Carry-forward I accept for 08:20 tomorrow (in this order, five items)
1. Post-deploy verifier (your #1), in CI after the push step and runnable by hand.
2. `SITE_BUILD_CLOCK` planted-clock proof for C2 (your #5).
3. ItemList 49 vs 47 unique upcoming links (your #7).
4. Readout registry backlog, first 5 of 19 (ARDX ×2, TRVI, AMGN tezepelumab, CALC), each with the sponsor release read and cited (your #6).
5. NEW-4 API `source_url` / `page_url` split (your #9).
Everything else on your list stays queued in the order you gave it. Torque item 7 (the 90.2% sentence) and the JUVÉDERM PMA ruling remain David's / your call respectively.

*Informational and educational only; not investment advice. Builder, 15:40 PT.*
