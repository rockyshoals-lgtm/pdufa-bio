# Builder ack, 2026-09-09 12:45 Pacific: ORDER 1 to 4 shipped, two findings, one near-miss
*Facts and build mechanics only; not investment advice. Machine Pacific, Vercel and GitHub UTC.*

## Live build
Pushed `c2725d3bd`. Live at the time of writing: `built 2026-09-09T19:29:28Z`, commit `440a75649` (CI's refresh; my commit deploys on the next promotion, and every check below was run against the live site after the push). Guards **75 green**, 0 failing, up from 74 (one new).

## Token
Parked, per your §1. No action taken, no token re-created, nothing spent on it. The step still logs one line naming the token as the failing half, and it will keep doing so until the manual dashboard purge answers your step 2.

## ORDER
| # | item | status | evidence (live, `Cache-Control: no-cache`) |
|---|---|---|---|
| **1** | /ticker/PFE description | **DONE** | `Pfizer Inc. (PFE) FDA catalyst hub. No upcoming catalyst on file. 10 past FDA decisions. Source document and measured run-up on every one.` Names Pfizer, states 10, and the phantom Palbociclib catalyst is gone. Applies to all 352 hubs, not just the 34. |
| **2** | titles break on a word boundary | **DONE** | `Pfizer Inc. (PFE) FDA Catalysts: BRAFTOVI (encorafenib) | pdufa.bio`. Zero of 352 hub titles now end on a fragment, a dangling function word or an open bracket. |
| **3** | pending drug pages state the PDUFA date | **DONE** | `/drug/aficamten`: `Aficamten: FDA PDUFA date November 14, 2026. For CYTOKINETICS INC. ...` Quarter-only rows state the quarter and are never promoted to a day we do not hold. |
| **4** | /conferences description carries the finding | **DONE** | `Every major 2026 medical conference where biotech companies present clinical data. Across 1,425 presentations we find no reliable pre-conference run-up.` Same numbers, same owner (`inject_conference_runup_sentence.py`), same build as the lede. |
| 5 | "approval date" phrasing | **NOT STARTED** | Deferred with 6. Your `tavapadon fda approval date` observation is the interesting one and deserves a real pass, not a tail-end patch. |
| 6 | UNCY case study | **NOT STARTED** | Unchanged: a full content build against 09-06f. |

## Root causes
**Item 1 was a one-owner-per-field violation, not a missed page.** `fix_meta_lengths.ticker_desc` is the LAST writer of ticker descriptions, and it rebuilt the text from its own dataset-derived company map, silently overwriting what `enrich_ticker_hubs.py` had written from the majority vote I shipped on 09-08. So the title said Pfizer and the description said Roivant/Priovant on the same page, from the same run. It also counted decisions from dataset rows (1) while the page counted rendered rows (10).

The fix does not teach a fourth writer how to resolve a company name. It reads both facts off the page being described: the hub already renders `<div class="sub">{company} · {upcoming} · {N} past FDA decisions</div>` and an `<h1>`, and those are what a reader sees. A description built from them cannot contradict the page. The dataset path survives as a fallback for hubs not yet rebuilt.

**Item 2's mid-word cut was not the 62-character title cap.** It was `d[:28]` on each drug name, one line earlier. `"BRAFTOVI (encorafenib) in combination with c"[:28]` is `"BRAFTOVI (encorafenib) in co"`. Both cuts now take whole words, balance brackets, and drop a trailing function word.

## New guard
`tests/test_ticker_hub_snippet_matches_page.py` — for every hub carrying the rendered summary: the description names the company the `<h1>` names; when the summary states a decision count the description states the same count; the title does not end on a dangling word, an open bracket, or mid-word. Proved 0 → 1 → 0 by planting the live PFE title and description back into the page; all three assertions fired, and healed on regeneration.

**A near-miss worth recording.** My first version of the mid-word check flagged any title ending in a one- or two-letter token. It produced three false positives on real names — `ALPHA-1 MP`, `Deucrictibant IR`, `Neffy 1 mg` — so I threw it away. The version that shipped judges the cut against the page's own text: if the title clause appears in the page followed immediately by an alphanumeric character, the cut landed inside a word. That is the difference between a guard and a nuisance, and I would rather say so than let you find it.

## Two findings I owe you
**NEW-1: six decision pages publish a drug name cut mid-word.** This is where item 2's bad string actually came from — the hub inherited it. `/fda-decision/PFE-2026-02-24` reads `BRAFTOVI (encorafenib) in combination with c` in its own "Drug / candidate" field. The full list: `AMRX-2026-06-04` (`...27.5 mg/5.5 m`), `ANIP-2026-04-08` (`...(generic o`), `GILD-2026-06-24` and `MRK-2026-06-24` (`Trodelvy (sacituzumab govitecan-hziy) plus K`), `NVO-2026-03-26` (`...injection 700 u`), `PFE-2026-02-24`. `build_decision_page.py` renders `e["drug"]` verbatim, so the truncation is in the event data written at publish time, not in the renderer. I have **not** guessed at the missing text: restoring these needs the sponsor release or FDA notice for each, which is a sourced job, not a string repair. Flagging rather than fixing tonight.

**NEW-2: a rebase conflict nearly published nothing, quietly.** Committing this batch, my `git pull --rebase` hit conflicts across 32 files, stopped, and left HEAD detached at origin's tip — at which point the push in the same command line reported success because it pushed the SHA already on origin. Zero of my work reached the site and the transcript said "pushed". I caught it on the status check, aborted, took `origin/main -- pdufa_site_src _sitemap_lastmod.json`, re-ran every generator on the clean base, counted markers (0), and pushed properly as `c2725d3bd`. Recording it because "the push said pushed" is exactly the kind of evidence I ask you to distrust from me.

## Queued
Items 5 and 6; NEW-1's six sourced drug names; the 09-08 `<caption>` question (still only worth doing if you want real `<table>` markup on /calendar); your TLX watch on Sept 11.

*Informational and educational only; not investment advice. Builder, 12:45 PT.*
