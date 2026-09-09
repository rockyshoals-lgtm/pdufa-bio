# Audit, 2026-09-08 11:15 Pacific: did the scheduled loop run, and are the channels still moving
**Live build `2026-09-08T16:09:15Z` commit `fa5d08330`. Bing and Google consoles read live at 11:00 PT (Bing data through Sept 6). Scheduler state read from the task list.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. DID THE SCHEDULED TASKS RUN? Fired: 10 of 10. Filed: 5 of 10.

Every slot fired on both days, on time, per the scheduler's `lastRunAt`. What each produced:

| Slot (PT) | Sun 09-07 | Mon 09-08 |
|---|---|---|
| 07:15 CI dispatch (new, builder-added) | n/a | **fired 07:18, CI built 14:21Z** ✓ |
| 08:00 auditor | **full** (13.8 KB) | **STUB ONLY** (319 b) |
| 08:20 builder | **nothing filed** (died mid-run, see below) | **STUB ONLY** (206 b, committed as `fa5d08330`) |
| 08:40 auditor | **full** (10.5 KB) | **full** (13.3 KB) |
| 09:00 builder | **full** (11.7 KB) | **STUB ONLY** (268 b) |
| 09:20 auditor | **full** (13.0 KB) | **STUB ONLY** (104 b) |

**Sunday: 4 of 5 filed. Monday: 1 of 5.** Monday is the worst day since the cadence started.

## What stub-first bought us

It worked exactly as designed. Every Monday stall is now visible as a file that says `RUN STARTED HH:MM` and nothing else. Before Saturday, those four runs would have been indistinguishable from runs that never fired.

## Why they die (the builder's forensics, Sunday 15:40 PT, verified against the transcript reference it cites)

The 08:20 slot on Sunday did not fail to start. It read the audit, edited two files, began the NRXP research, made an EDGAR fetch, **a Perplexity search, then a `secFilings` connector call, and that call is the last entry in the session.** No result, no final message. The session was terminated in the middle of an external tool call.

Two facts bear on this:

1. **The Perplexity API returned `401 insufficient_quota` when I called it on Sept 6.** Any run whose prompt reaches for Perplexity is calling a dead connector. Whether a dead connector hangs the run or just errors is unverified from this evidence, but it is the first thing to remove.
2. **The 08:40 auditor prompt is the only one that has completed every single day (09-06, 09-07, 09-08).** It is also the only prompt with no web search, no Perplexity, no Chrome, and no EDGAR: it reads files, curls the live site, and writes. The two prompts that died Monday (08:00, 09:20) both reach outward.

**The pattern is consistent: runs die on external connector calls, and the run with no external calls never dies.** Correlation on two days, not proof. But it is the cheapest thing to fix first.

## What I have changed (auditor side, effective tomorrow)

All three auditor prompts now: **no Perplexity; web search capped at two calls per run; no Chrome in the 08:00 or 09:20 slot** (Chrome reads move to a separate weekly slot); every external call is bounded by "if it does not return, write what you have and move on." The 08:40 shape is the template.

## What needs David or the builder

- **Perplexity**: the API key is over quota. Either top it up or remove the connector from every prompt, including the builder's two. A dead connector in a scheduled prompt is a stall waiting to happen.
- **Builder prompts**: same removal. The builder's Sunday fix (push after every item, 25-minute cap, defer a research call that hangs twice) is right, and Monday shows it is not enough while the connector is dead.
- **A run-level timeout the scheduler enforces**, if the app exposes one. I could not find it.

---

# 2. WHAT THE RUNS THAT DID COMPLETE FOUND (and I re-checked live)

| Finding | Source | Live at 11:00 PT |
|---|---|---|
| **Vercel CDN served bodies from two superseded deployments under the newest ETag** during a two-minute window Sunday; also once with no deploy anywhere near. Not our build. | builder forensics, git-verified against `pdufa_site_src/calendar/index.html` at three commits | post-deploy verifier still queued; today's 7 graded pages had body md5 == etag on both fetches, but outside a promotion window that check cannot fail and is not credited |
| **GitHub's 12:00Z / 21:00Z crons run 1.5 to 5.4 h late**, so the "05:00 PT" build was landing after the 08:00 audit | builder, from run history | **fixed**: 07:15 PT dispatch task fired today, `built` 14:21Z, then 16:09Z |
| `/api/data` cache policy: source said 16000 s, wire said `public`; both were true | builder | **fixed**: `s-maxage=300, stale-while-revalidate=300, stale-if-error=3600` on all three cache headers, guard added |
| `build-info.json` commit SHA standardized to 9 chars | builder | ✓ |
| **ERS (European Respiratory Society, 2026-09-05) still `Scheduled` on Sept 8**; ESC (08-28) correctly `Ended`, so the flipper exists but missed ERS | 08:40 auditor | **still open** at 11:00 PT |

## Currency gates, 10:55 PT
API `as_of` 2026-09-08 (456 rows; cannot fail today, not credited). Past-goal day-precision PDUFAs undecided: **0**. Past Guided readouts without outcome: **0**. Past conferences not marked ended: **1 (ERS)**.

## The content ORDER from the weekend: not started

| Item (from 09-06b / 09-06f) | Live |
|---|---|
| UNCY case study `/case-studies/unicycive-…` | 404 |
| `/company/{slug}` pages | 404 |
| `<caption>` on `/calendar` grids | 0 |
| `/research/conference-runups` | 308 (redirects; not a study page) |
| CRL reason taxonomy, positioning block, 13F block | not started |

The weekend went to infrastructure: CDN forensics, CI timing, cache policy, cadence hardening. That work was necessary and it is done well. But **nothing that moves a ranking signal has shipped since Saturday's calendar explainer**, and the answer-box test below says the explainer alone has not moved the box.

---

# 3. THE CHANNELS (Bing through Sept 6; Google through Sept 6)

## Bing search: still climbing on the three-month view

| | Sept 3 read | **Sept 6 read** |
|---|---:|---:|
| Clicks (3 mo) | 293 | **317** |
| Impressions (3 mo) | 9.7K | **10.7K** |
| CTR | 3.02% | 2.97% |

Daily impressions: Sept 3 **698** (record), Sept 4 446, Sept 5 (Sat) 239, Sept 6 (Sun) 278. Sunday clicks 12 on 278 impressions is a 4.3% day. Weekend dip is normal; Monday's number is the one to watch.

Keywords: `pdufa calendar` 28 impressions, 8 clicks, **28.6% at position 2.64** (was 27.3% at 2.05). `pdufa` 874 impressions, 4 clicks, 0.46% at 6.25: the head term still leaks ~870 a month. **`camizestrant pdufa date`: 29 impressions, 0 clicks at position 4.62**, on a drug approved Sept 4 that we are the top AI source for; the Bing web snippet for that page is not converting. `pfizer pfe pdufa dates…` still 82 impressions, 0 clicks at 3.23; the company page is still 404.

## Bing AI citations: total up, daily rate down, breadth flat

| | Sept 3 | **Sept 6** |
|---|---:|---:|
| Citations (3 mo) | 3.3K | **3.7K** |
| Avg cited pages | 15 | 15 |
| Grounding queries | 19 | **19** |

**Daily citations fell after the Sept 1 to 3 peak**: 348 / 255 / 279, then **178 / 79 / 87** (Fri / Sat / Sun). Cited pages per day 28 to 34, then 16 / 14 / 12. Two cautions before reading that as a decline: Sept 5 and 6 are a weekend, and Bing labels this panel "a sample of overall activity, results may be refined," and recent days have revised upward in every prior read. Friday at 178 is the number that is not explained by the weekend. **Watch Sept 7 to 9 before drawing anything.**

Movers: `pdufa date` 307 → 337 · `fda calendar 2026` 183 → 201 · **`camizestrant pdufa date` 72 → 82 at 32.0% share** (the approval we published Sept 5) · `upcoming clinical trial readouts rare disease…` 66 → 75 · **`major upcoming Phase 3 oncology trial readouts next 12 months` 7 → 28 at 65.1% share** (the readouts hub is being grounded on) · `rusfertide` 72 flat · asundexian 24 flat.

**Grounding queries 19 for a second week.** Breadth is the metric that needs entities, and no new entity pages shipped this weekend.

## The answer-box test: not in it

Bing `pdufa dates 2026`, 11:00 PT: we are **organic #1** ("2026 FDA PDUFA Calendar: 97 Dates, Updated Daily", "1 day ago"). The AI answer above us cites **biomednexus, medswitcher (new), novapharmanews (twice), assyro.** Not us.

Three observations:
- The box's content is now **exactly the shape of our Saturday explainer**: "standard reviews typically taking 10 months and priority reviews 6 months", "extensions typically add about three months." The sentences exist on our page. Bing is quoting them from sites with older authority. Two days is too soon to call this an authority filter; a week is not. **Re-test Sept 13.**
- **medswitcher.com** is being cited for *naming drugs*: "CagriSema… Q2 2026", "Survodutide, Retatrutide, Pivlicaftor, Relutrigine." The box rewards a sentence with drug names and dates in it. Our calendar has the names in a table.
- **novapharmanews shows "17 hours ago" against our "1 day ago."** Their stamp is fresher than ours on the SERP. Our build was 16:09Z today; the stamp Bing displays lags the build. Worth checking what `dateModified` / `og:updated_time` the calendar emits and whether it updates on every CI build or only on content change.

## Google: unchanged shape, plus a first read of the AI report

Search (Jun 7 to Sep 6): clicks **53** (flat), impressions **3.2K** (up from 2.98K), CTR **1.7%** (down), position **19** (up from 19.6), queries **162** (up from 157). Impressions up, clicks flat, for the fourth read running. Entity queries convert (pdufa.bio 3/3, monalizumab, giredestrant, nct04229979, miplyffa all 1/1); head terms do not (`pdufa dates` 0/64, `pdufa date` 0/51).

**New: Google Search Console now exposes a "Generative AI on Search results" report, and I read it for the first time.** Impressions in Google's AI features, Jun 7 to Sep 6: **58**, across **15 pages**. Homepage 38 (www) + 10 (non-www) = 48; `/pdufa-dates` 3; `/pdufa/VNDA` 3; `/calendar`, `/developers`, `/learn/what-is-a-pdufa-date`, `/odin`, `/odin-track-record`, `/pdufa-calendar` 1 each.

Three things from that:
1. **This is the Google AI baseline: 58 in three months.** The end-2027 target row "Google AI Overview: cited" now has a number to move.
2. **Google's AI is surfacing both `www.pdufa.bio/` and `pdufa.bio/`.** The non-www 308s to www correctly, so this is Google's index carrying both, not a site defect; but 10 of 58 impressions are attributed to a URL we redirect. Worth a look at whether the AI surface honours the canonical.
3. **`/odin-track-record` appears in Google's AI features and returns 404.** `/odin` correctly 308s to `/why-no-approval-probability`. The track-record URL should redirect to the same page rather than 404 to an AI surface. (I also confirmed: neither page leaks a probability. `/why-no-approval-probability` is the natural home for the UNCY case study link.)

---

# 4. ORDER (for the next builder slot that completes)

| # | Item | Acceptance |
|---|---|---|
| **1** | **Remove Perplexity from both builder prompts; bound every external call** | prompt files in the dropbox show no `perplexity`; ack states the change |
| **2** | ERS conference status → `Ended` (and whatever let ESC flip but not ERS) | API row ERS status `Ended`; `/conferences` shows it under past |
| **3** | `/odin-track-record` → 308 to `/why-no-approval-probability` | curl returns 308 with that Location |
| 4 | UNCY case study per 09-06f (12 sources, no em dashes, vocabulary guard) | 200; acceptance list in 09-06f §5 |
| 5 | `<caption>` on every `/calendar` grid; one dated sentence naming the month's drugs under each heading (the medswitcher shape, with our sourcing) | `grep -c '<caption'` = grid count; each month heading followed by a sentence naming ≥3 drugs with dates |
| 6 | Check `og:updated_time` / `dateModified` on `/calendar` update on every CI build | value equals the build's timestamp within the hour |
| 7 | `/company/pfizer` and peers | 200; title answers "pfizer pdufa dates 2026 2027" |
| 8 | Post-deploy verifier (from Sunday's P0) | script named, one run's output in the ack |

---

# BOTTOM LINE

**The loop fires perfectly and completes badly.** Ten of ten slots ran on time across Sunday and Monday; five of ten produced work. Stub-first did its job, and the four Monday stubs are the evidence: the runs that die are the ones that call out to external connectors, and the one prompt that never does (08:40) has completed every day. The Perplexity key has been over quota since at least Sept 6. Remove it from every prompt before tomorrow.

**The site is current** on every gate but one (ERS still "Scheduled" three days after it ended), and the weekend's infrastructure work was real: CI now builds before the audit, the cache policy is one policy, and the builder found Vercel's CDN serving stale bodies under fresh ETags, which is not something we can fix but is something we can now detect.

**The channels are up on every three-month total** (Bing 317 clicks / 10.7K impressions; AI citations 3.7K; Google impressions 3.2K and queries 162) **and flat or down on every leading indicator**: grounding queries 19 for a second week, daily citations off sharply after Sept 3, Google clicks 53 for the fourth read, and the Bing answer box still citing five other sites two days after we shipped the sentences it quotes. Nothing that adds an entity or a quotable sentence has shipped since Saturday. The first read of Google's own Generative AI report puts our baseline there at 58 impressions in three months.

---
*Consoles read live 2026-09-08 11:00 PT. Bing publishes through Sept 6 and revises recent days upward; treat Sept 4 to 6 as provisional. Not investment advice.*
